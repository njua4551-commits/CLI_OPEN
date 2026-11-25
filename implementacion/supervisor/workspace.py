"""Prepare a bounded, disposable workspace review without modifying its source."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import tempfile

MAX_FILE = 262_144
MAX_REQUEST = 8 * (MAX_FILE * 6 + 256)
CODE_EXTENSIONS = (
    "txt", "md", "json", "py", "ts", "tsx", "js", "jsx", "mjs", "cjs",
    "go", "rs", "java", "c", "h", "cpp", "hpp", "cc", "cs", "rb", "php",
    "sh", "bash", "yaml", "yml", "toml", "ini", "cfg", "conf", "sql",
    "css", "html", "htm", "xml", "lock", "env", "gitignore",
)
NAME = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_.\-/]{0,240}\.(?:" + "|".join(CODE_EXTENSIONS) + r")"
)


class SourceChanged(ValueError):
    """The review no longer corresponds to the source."""


class IsolatedEditFailed(ValueError):
    """The isolated worker failed before producing a valid review."""


def parse_request(source):
    raw = source.read(MAX_REQUEST + 1)
    if len(raw) > MAX_REQUEST:
        raise ValueError("request exceeds limit")
    request = json.loads(raw)
    if not isinstance(request, dict) or set(request) != {"edits"}:
        raise ValueError("expected an edits list")
    edits = request["edits"]
    if not isinstance(edits, list) or not 1 <= len(edits) <= 8:
        raise ValueError("expected one to eight edits")
    seen = set()
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"operation", "path", "text"}:
            raise ValueError("invalid edit schema")
        name, operation, text = edit["path"], edit["operation"], edit["text"]
        if (
            not isinstance(name, str) or not NAME.fullmatch(name) or name in seen
            or name.startswith("/") or ".." in name.split("/")
            or any(part == "" for part in name.split("/"))
        ):
            raise ValueError("invalid or duplicate file name")
        if operation not in ("create", "replace") or not isinstance(text, str):
            raise ValueError("invalid operation or text")
        if len(text.encode("utf-8")) > MAX_FILE or "\0" in text:
            raise ValueError("invalid text or oversized file")
        seen.add(name)
    return edits


def signature(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def snapshot(directory, name):
    try:
        descriptor = os.open(name, os.O_PATH | os.O_NOFOLLOW, dir_fd=directory)
    except FileNotFoundError:
        return None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_FILE:
            raise ValueError("source file must be a bounded regular file without links")
        with open(f"/proc/self/fd/{descriptor}", "rb") as file:
            data = file.read(MAX_FILE + 1)
        if len(data) > MAX_FILE or signature(before) != signature(os.fstat(descriptor)):
            raise SourceChanged("source changed while reading")
        return signature(before), data.decode("utf-8")
    finally:
        os.close(descriptor)


def verify_sources(root, changes):
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for change in changes:
            current = snapshot(directory, change["path"])
            digest = hashlib.sha256(current[1].encode("utf-8")).hexdigest() if current else None
            if digest != change["before_sha256"]:
                raise SourceChanged("source changed before publication")
    finally:
        os.close(directory)


def review_diff(name, original, edited):
    before = original[1] if original else ""
    lines = difflib.unified_diff(
        before.splitlines(keepends=True), edited.splitlines(keepends=True),
        fromfile=f"a/{name}" if original else "/dev/null", tofile=f"b/{name}",
    )
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def review(root, edits, bubblewrap_command):
    if platform.system() != "Linux" or platform.machine() != "x86_64" or os.geteuid() == 0:
        raise ValueError("workspace requires standard-user Linux x86_64")
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    if not backend:
        raise ValueError("Bubblewrap unavailable")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        identity = os.fstat(directory)
        originals = {edit["path"]: snapshot(directory, edit["path"]) for edit in edits}
        for edit in edits:
            exists = originals[edit["path"]] is not None
            if (edit["operation"] == "replace") != exists:
                raise ValueError("operation disagrees with source state")
        with tempfile.TemporaryDirectory(prefix="cli-open-review-") as temporary:
            copy = Path(temporary)
            for name, original in originals.items():
                if original is not None:
                    target = copy / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(original[1].encode("utf-8"))
            supervisor = Path(__file__).resolve().parent
            artifacts = Path(os.environ.get("CLI_OPEN_ARTIFACTS", str(supervisor.parents[1] / ".fase1")))
            mounts = [
                (supervisor / "workspace_worker.py", "/worker.py"),
                (supervisor / "workspace_opencode.ts", "/fixture/editor.ts"),
                (artifacts / "tools/bun-linux-x64-baseline/bun", "/fixture/bun"),
                (artifacts / "opencode/packages/cli/dist/cli-linux-x64/bin/opencode", "/fixture/opencode"),
            ]
            missing = [str(path) for path, _ in mounts if not path.is_file()]
            if missing:
                raise ValueError("missing editing artifacts: " + ", ".join(missing))
            command = bubblewrap_command(backend, mounts, [
                "/fixture/bun", "/fixture/editor.ts",
            ], writable_workspace=copy)
            result = subprocess.run(
                command, env={}, input=json.dumps(edits).encode("ascii"),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=35, check=False,
            )
            if result.returncode:
                raise IsolatedEditFailed("isolated editing or validation failed; copy discarded")
            try:
                current = os.stat(root, follow_symlinks=False)
            except FileNotFoundError:
                raise SourceChanged("source directory changed; copy discarded") from None
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                raise SourceChanged("source directory changed; copy discarded")
            if any(snapshot(directory, name) != original for name, original in originals.items()):
                raise SourceChanged("source changed concurrently; copy discarded")
            return [
                {
                    "path": name,
                    "operation": "replace" if originals[name] else "create",
                    "before_sha256": hashlib.sha256(originals[name][1].encode("utf-8")).hexdigest()
                    if originals[name] else None,
                    "diff": review_diff(name, originals[name], (copy / name).read_bytes().decode("utf-8")),
                }
                for name in originals
            ]
    finally:
        os.close(directory)
