"""Validate the exact proposed bytes and allowed file set inside Bubblewrap."""
import json
from pathlib import Path
import runpy
import stat
import sys

WORKER_POLICY = runpy.run_path(str(Path(__file__).with_name("workspace_limits.py")))
MAX_FILE = WORKER_POLICY["MAX_FILE"]


def reject_constant(_):
    raise ValueError("invalid JSON constant")


def main():
    edits = json.load(sys.stdin)
    expected = {}
    for edit in edits:
        name = edit["path"]
        if not WORKER_POLICY["canonical_relative"](name) or name in expected:
            raise ValueError("invalid or duplicate workspace file")
        expected[name] = edit["text"]
    directories = {Path(".")}
    for name in expected:
        directories.update(Path(name).parents)
    allowed = directories | {Path(name) for name in expected}
    for directory in sorted(directories, key=lambda path: len(path.parts)):
        if not stat.S_ISDIR(directory.lstat().st_mode):
            raise ValueError("invalid workspace directory")
        if any(path not in allowed for path in directory.iterdir()):
            raise ValueError("unexpected files in workspace")
    for name, text in expected.items():
        path = Path(name)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_FILE:
            raise ValueError("invalid workspace file")
        if path.read_bytes() != text.encode("utf-8"):
            raise ValueError("workspace content differs from proposal")
        if path.suffix == ".json":
            json.loads(text, parse_constant=reject_constant)


if __name__ == "__main__":
    main()
