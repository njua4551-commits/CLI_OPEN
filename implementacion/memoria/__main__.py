"""Memoria persistente por proyecto, con recuperación selectiva e invalidación.

Almacén JSONL fuera del repositorio. Cada entrada referencia archivos y su
hash; al leer se descartan las entradas cuyos archivos cambiaron o faltan.
Sin red, sin dependencias externas y con escritura atómica.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import selectors
import shutil
import subprocess
import sys
import time

MAX_TEXT = 8_192
MAX_TAGS = 16
MAX_TAG = 32
MAX_FILES = 16
MAX_FILE_BYTES = 1_048_576
TOKENS_PER_CHAR = 0.25
SECRETS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk|ghp|gho|ghs|xox[baprs])[-_][A-Za-z0-9_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
TAG = re.compile(r"[a-z0-9][a-z0-9_.:/-]{0,31}")


class Rejected(ValueError):
    pass


def project_key(project):
    return hashlib.sha256(str(project).encode()).hexdigest()[:16]


def store_path(store, project):
    return Path(store) / f"{project_key(project)}.jsonl"


def tokens(text):
    return math.ceil(len(text) * TOKENS_PER_CHAR)


def check_text(text):
    if not isinstance(text, str) or not 1 <= len(text) <= MAX_TEXT:
        raise Rejected("invalid memory text")
    if any(pattern.search(text) for pattern in SECRETS):
        raise Rejected("memory text looks like a secret")
    return text


def resolve_project(value):
    project = Path(value).resolve()
    if not project.is_dir():
        raise Rejected("project directory not found")
    return project


def file_digest(project, value):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise Rejected("invalid file reference")
    path = (project / value).resolve()
    if path != project and project not in path.parents:
        raise Rejected("file outside the project")
    if not path.is_file():
        raise Rejected("referenced file not found")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise Rejected("referenced file too large")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_entries(path):
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and isinstance(entry.get("text"), str):
            entries.append(entry)
    return entries


def write_entries(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text("".join(json.dumps(entry, ensure_ascii=True) + "\n" for entry in entries),
                         encoding="utf-8")
    os.replace(temporary, path)


class Lock:
    def __init__(self, path):
        self.path = path.with_suffix(".lock")

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a")
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()


def stale(project, entry):
    files = entry.get("files") or {}
    if not isinstance(files, dict):
        return True
    for value, digest in files.items():
        try:
            if file_digest(project, value) != digest:
                return True
        except (Rejected, OSError):
            return True
    return False


def score(entry, terms):
    text = entry["text"].lower()
    tags = [str(tag).lower() for tag in entry.get("tags") or []]
    hits = 0
    for term in terms:
        if term in tags:
            hits += 3
        hits += min(text.count(term), 3)
    return hits


def add(args):
    project = resolve_project(args.project)
    text = check_text(args.text)
    tags = [tag.strip().lower() for tag in (args.tags or "").split(",") if tag.strip()]
    if len(tags) > MAX_TAGS or any(not TAG.fullmatch(tag) for tag in tags):
        raise Rejected("invalid tags")
    files = [value.strip() for value in (args.files or "").split(",") if value.strip()]
    if len(files) > MAX_FILES:
        raise Rejected("too many file references")
    digests = {value: file_digest(project, value) for value in files}
    path = store_path(args.store, project)
    with Lock(path):
        entries = read_entries(path)
        created = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        entry = {
            "id": hashlib.sha256((text + created).encode()).hexdigest()[:16],
            "text": text,
            "tags": sorted(set(tags)),
            "files": digests,
            "created": created,
        }
        entries.append(entry)
        write_entries(path, entries)
    return {"stored": entry["id"], "entries": len(entries)}


def rank(args):
    project = resolve_project(args.project)
    path = store_path(args.store, project)
    entries = read_entries(path)
    terms = set(re.findall(r"[A-Za-z0-9_.:/-]{2,}", args.query.lower()))
    if not terms:
        raise Rejected("empty query")
    ranked, expired = [], 0
    for entry in entries:
        if stale(project, entry):
            expired += 1
            continue
        value = score(entry, terms)
        if value:
            ranked.append((value, entry.get("created") or "", entry))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked, expired


def search(args):
    budget = args.budget
    if budget < 1:
        raise Rejected("invalid token budget")
    ranked, expired = rank(args)
    selected, used = [], 0
    for value, _, entry in ranked:
        cost = tokens(entry["text"])
        if used + cost > budget:
            continue
        selected.append({**entry, "score": value, "tokens": cost})
        used += cost
    return {"entries": selected, "tokens": used, "budget": budget,
            "stale": expired}


def encode_context(result):
    return json.dumps(result, ensure_ascii=True, separators=(",", ":"))


def project_paths(project, query, safe_reference):
    """List paths with ripgrep, the backend also used by OpenCode glob."""
    binary = shutil.which("rg")
    if not binary:
        raise Rejected("ripgrep is required for path discovery")
    terms = set(re.findall(r"[^\W_]{2,}", query.casefold()))
    if not terms:
        return []
    deadline = time.monotonic() + 5
    ceiling = 1024 * 1024
    data = bytearray()
    with subprocess.Popen([
        binary, "--no-config", "--no-require-git", "--files", "--null", "--sort", "path",
        "-g", "!{node_modules,dist,build,target,vendor}/**",
        "-g", "!**/{node_modules,dist,build,target,vendor}/**",
    ], cwd=project, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as scan:
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(scan.stdout, selectors.EVENT_READ)
                while len(data) <= ceiling:
                    if time.monotonic() >= deadline:
                        raise Rejected("path discovery timed out")
                    if not selector.select(max(0, deadline - time.monotonic())):
                        raise Rejected("path discovery timed out")
                    chunk = os.read(scan.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    data.extend(chunk)
            if len(data) > ceiling:
                raise Rejected("path discovery exceeded 1 MiB; select a smaller project root")
            if scan.wait(timeout=max(0, deadline - time.monotonic())) not in (0, 1):
                raise Rejected("ripgrep path discovery failed")
        except subprocess.TimeoutExpired as exc:
            raise Rejected("path discovery timed out") from exc
        finally:
            if scan.poll() is None:
                scan.kill()
    ranked = []
    for raw in data.split(b"\0"):
        path = os.fsdecode(bytes(raw))
        if not safe_reference(path):
            continue
        parts = set(re.findall(r"[^\W_]+", path.casefold()))
        hits = len(terms & parts)
        if hits:
            ranked.append((-hits, path))
    return [path for _, path in sorted(ranked)]


def context(args):
    if not 128 <= args.max_bytes <= 16384 or len(args.query) > 2048:
        raise Rejected("invalid context budget or query")
    ranked, _ = rank(args)
    result = {"authority": "none", "source": "project-memory", "entries": []}
    if args.with_paths:
        adapter = runpy.run_path(str(Path(__file__).resolve().parents[1] / "supervisor" / "context.py"))
        result["paths"] = project_paths(resolve_project(args.project), args.query, adapter["safe_reference"])
        result["entries"] = [entry for _, _, entry in ranked]
        return adapter["validate_envelope"](result, args.max_bytes)
    used = len(encode_context(result)) + 1  # The emitted newline is part of the budget.
    for _, _, entry in ranked:
        try:
            text = check_text(entry["text"])
        except Rejected:
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{16}", identifier):
            continue
        candidate = {"id": identifier, "text": text}
        cost = len(encode_context(candidate)) + bool(result["entries"])
        if used + cost <= args.max_bytes:
            result["entries"].append(candidate)
            used += cost
    return result


def invalidate(args):
    project = resolve_project(args.project)
    path = store_path(args.store, project)
    with Lock(path):
        entries = read_entries(path)
        invalid = [entry for entry in entries if stale(project, entry)]
        if args.purge and invalid:
            keep = [entry for entry in entries if not stale(project, entry)]
            write_entries(path, keep)
        remaining = len(entries) - (len(invalid) if args.purge else 0)
    return {"invalid": [entry["id"] for entry in invalid], "purged": bool(args.purge and invalid),
            "entries": remaining}


def doctor(args):
    project = resolve_project(args.project)
    path = store_path(args.store, project)
    entries = read_entries(path)
    return {"project": str(project), "store": str(path), "entries": len(entries),
            "stale": sum(1 for entry in entries if stale(project, entry)),
            "bytes": path.stat().st_size if path.exists() else 0}


def main():
    parser = argparse.ArgumentParser(description="Memoria persistente por proyecto. Sin red.")
    parser.add_argument("--store", default=os.environ.get(
        "XDG_STATE_HOME", str(Path.home() / ".local" / "state")) + "/cli-open/memoria")
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add")
    add_parser.add_argument("--project", required=True)
    add_parser.add_argument("--text", required=True)
    add_parser.add_argument("--tags", default="")
    add_parser.add_argument("--files", default="")
    add_parser.set_defaults(handler=add)

    search_parser = commands.add_parser("search")
    search_parser.add_argument("--project", required=True)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--budget", type=int, default=512)
    search_parser.set_defaults(handler=search)

    context_parser = commands.add_parser("context")
    context_parser.add_argument("--project", required=True)
    context_parser.add_argument("--query", required=True)
    context_parser.add_argument("--max-bytes", type=int, default=4096)
    context_parser.add_argument("--with-paths", action="store_true", help="Incluir rutas relevantes con ripgrep")
    context_parser.set_defaults(handler=context)

    invalidate_parser = commands.add_parser("invalidate")
    invalidate_parser.add_argument("--project", required=True)
    invalidate_parser.add_argument("--purge", action="store_true")
    invalidate_parser.set_defaults(handler=invalidate)

    doctor_parser = commands.add_parser("doctor")
    doctor_parser.add_argument("--project", required=True)
    doctor_parser.set_defaults(handler=doctor)

    args = parser.parse_args()
    try:
        result = args.handler(args)
    except (Rejected, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(encode_context(result) if args.command == "context" else json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
