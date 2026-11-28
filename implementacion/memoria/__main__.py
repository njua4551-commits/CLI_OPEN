"""Persistent project memory with selective retrieval and invalidation.

The JSONL store lives outside the repository. Entries reference files by hash.
Retrieval drops entries if their files changed or disappeared. Writes are
atomic and require neither network access nor external dependencies.
"""
import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import secrets
import selectors
import shutil
import stat
import subprocess
import sys
import time

MAX_TEXT = 8_192
MAX_TAGS = 16
MAX_TAG = 32
MAX_FILES = 16
MAX_FILE_BYTES = 1_048_576
MAX_STORE_BYTES = 4 * 1024 * 1024
TOKENS_PER_CHAR = 0.25
POLICY = runpy.run_path(str(Path(__file__).resolve().parents[1] / "context_policy.py"))
encode_context = POLICY["encode_context"]
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
    if POLICY["looks_secret"](text):
        raise Rejected("memory text looks like a secret")
    return text


def resolve_project(value):
    project = Path(value).resolve()
    if not project.is_dir():
        raise Rejected("project directory not found")
    return project


def file_signature(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def file_digest(project, value, cache=None):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise Rejected("invalid file reference")
    if POLICY["sensitive_path"](value):
        raise Rejected("sensitive memory file reference")
    path = (project / value).resolve()
    if project not in path.parents:
        raise Rejected("file outside the project")
    relative = path.relative_to(project)
    if POLICY["sensitive_path"](relative.as_posix()):
        raise Rejected("sensitive memory file reference")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as stack:
        directory = os.open(project, directory_flags)
        stack.callback(os.close, directory)
        for component in relative.parts[:-1]:
            directory = os.open(component, directory_flags, dir_fd=directory)
            stack.callback(os.close, directory)
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directory)
        handle = stack.enter_context(os.fdopen(descriptor, "rb"))
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise Rejected("referenced file must be a bounded regular file")
        signature = file_signature(before)
        if cache is not None and signature in cache:
            return cache[signature]
        data = handle.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES or file_signature(os.fstat(descriptor)) != signature:
            raise Rejected("referenced file changed while reading")
        digest = hashlib.sha256(data).hexdigest()
        if cache is not None:
            cache[signature] = digest
        return digest


@contextmanager
def private_directory(path):
    """Open each directory component without following links."""
    path = path.absolute()
    if ".." in path.parts or path == Path(path.anchor):
        raise Rejected("invalid memory directory")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(path.anchor, flags)
    system_owner = os.fstat(directory).st_uid
    try:
        for index, part in enumerate(path.parts[1:], 1):
            try:
                child = os.open(part, flags, dir_fd=directory)
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            if index == len(path.parts) - 1:
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                    raise Rejected("memory directory must be user-owned and private (0700)")
            elif info.st_uid not in (system_owner, os.geteuid()) or (
                info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX
            ):
                raise Rejected("untrusted memory directory ancestor")
        yield directory
    finally:
        os.close(directory)


def private_file(directory, name, flags):
    descriptor = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise Rejected("invalid private memory file")
        if stat.S_IMODE(info.st_mode) != 0o600:
            os.fchmod(descriptor, 0o600)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def valid_entry(entry):
    if not isinstance(entry, dict):
        return False
    text, identifier = entry.get("text"), entry.get("id")
    tags, files, created = entry.get("tags"), entry.get("files"), entry.get("created")
    return (
        isinstance(text, str) and 1 <= len(text) <= MAX_TEXT
        and isinstance(identifier, str) and re.fullmatch(r"[a-f0-9]{16}", identifier)
        and isinstance(tags, list) and len(tags) <= MAX_TAGS
        and all(isinstance(tag, str) and TAG.fullmatch(tag) for tag in tags)
        and isinstance(files, dict) and len(files) <= MAX_FILES
        and all(0 < len(name) <= 512 and isinstance(digest, str)
                and re.fullmatch(r"[a-f0-9]{64}", digest) for name, digest in files.items())
        and isinstance(created, str) and bool(created)
    )


def invalid_memory_constant(_):
    raise ValueError("invalid memory constant")


class Store:
    def __init__(self, directory, name):
        self.directory = directory
        self.name = name
        self.size = 0

    def read(self):
        try:
            descriptor = private_file(self.directory, self.name, os.O_RDONLY)
        except FileNotFoundError:
            return []
        with os.fdopen(descriptor, "rb") as handle:
            data = handle.read(MAX_STORE_BYTES + 1)
        self.size = len(data)
        if self.size > MAX_STORE_BYTES:
            raise Rejected("memory store exceeds its size limit")
        entries = []
        for number, line in enumerate(data.splitlines(), 1):
            try:
                entry = json.loads(line, parse_constant=invalid_memory_constant)
                if not valid_entry(entry):
                    raise ValueError
            except (ValueError, RecursionError):
                raise Rejected(f"invalid memory record at line {number}") from None
            entries.append(entry)
        return entries

    def write(self, entries):
        data = "".join(json.dumps(entry, ensure_ascii=True) + "\n" for entry in entries).encode("ascii")
        if len(data) > MAX_STORE_BYTES:
            raise Rejected("memory store exceeds its size limit")
        temporary = f".{self.name}.{secrets.token_hex(16)}.tmp"
        descriptor = private_file(self.directory, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.name, src_dir_fd=self.directory, dst_dir_fd=self.directory)
            os.fsync(self.directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.directory)
            except FileNotFoundError:
                pass


@contextmanager
def open_store(path):
    with private_directory(path.parent) as directory:
        descriptor = private_file(directory, path.with_suffix(".lock").name, os.O_RDWR | os.O_CREAT)
        with os.fdopen(descriptor, "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield Store(directory, path.name)


def stale(project, entry, cache):
    files = entry.get("files") or {}
    if not isinstance(files, dict):
        return True
    for value, digest in files.items():
        try:
            if file_digest(project, value, cache) != digest:
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
    with open_store(path) as store:
        entries = store.read()
        created = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        entry = {
            "id": hashlib.sha256((text + created).encode()).hexdigest()[:16],
            "text": text,
            "tags": sorted(set(tags)),
            "files": digests,
            "created": created,
        }
        entries.append(entry)
        store.write(entries)
    return {"stored": entry["id"], "entries": len(entries)}


def rank(args):
    project = resolve_project(args.project)
    path = store_path(args.store, project)
    with open_store(path) as store:
        entries = store.read()
    terms = set(re.findall(r"[A-Za-z0-9_.:/-]{2,}", args.query.lower()))
    if not terms:
        raise Rejected("empty query")
    ranked, expired = [], 0
    cache = {}
    for entry in entries:
        if stale(project, entry, cache):
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
    with open_store(path) as store:
        entries = store.read()
        keep, invalid, cache = [], [], {}
        for entry in entries:
            (invalid if stale(project, entry, cache) else keep).append(entry)
        if args.purge and invalid:
            store.write(keep)
        remaining = len(entries) - (len(invalid) if args.purge else 0)
    return {"invalid": [entry["id"] for entry in invalid], "purged": bool(args.purge and invalid),
            "entries": remaining}


def doctor(args):
    project = resolve_project(args.project)
    path = store_path(args.store, project)
    with open_store(path) as store:
        entries = store.read()
    cache = {}
    return {"project": str(project), "store": str(path), "entries": len(entries),
            "stale": sum(1 for entry in entries if stale(project, entry, cache)),
            "bytes": store.size}


def main():
    parser = argparse.ArgumentParser(description="Persistent project memory without network access.")
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    parser.add_argument("--store", default=state / "cli-open" / "memoria")
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
    context_parser.add_argument("--with-paths", action="store_true", help="Include relevant paths using ripgrep")
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
        diagnostic = str(exc) if isinstance(exc, Rejected) else "memory operation failed"
        print(json.dumps({"error": diagnostic}), file=sys.stderr)
        return 1
    print(encode_context(result) if args.command == "context" else json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
