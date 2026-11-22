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
import sys

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


def search(args):
    project = resolve_project(args.project)
    path = store_path(args.store, project)
    entries = read_entries(path)
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_.:/-]{2,}", args.query)]
    if not terms:
        raise Rejected("empty query")
    budget = args.budget
    if budget < 1:
        raise Rejected("invalid token budget")
    ranked = []
    for entry in entries:
        if stale(project, entry):
            continue
        value = score(entry, terms)
        if value:
            ranked.append((value, entry.get("created") or "", entry))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected, used = [], 0
    for value, _, entry in ranked:
        cost = tokens(entry["text"])
        if used + cost > budget:
            continue
        selected.append({**entry, "score": value, "tokens": cost})
        used += cost
    return {"entries": selected, "tokens": used, "budget": budget,
            "stale": sum(1 for entry in entries if stale(project, entry))}


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
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
