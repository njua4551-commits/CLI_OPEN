"""Validate the exact proposed bytes and allowed file set inside Bubblewrap."""
import json
from pathlib import Path
import stat
import sys


def reject_constant(_):
    raise ValueError("invalid JSON constant")


def main():
    edits = json.load(sys.stdin)
    expected = {edit["path"]: edit["text"] for edit in edits}
    if {path.name for path in Path.cwd().iterdir()} != expected.keys():
        raise ValueError("unexpected files in workspace")
    for name, text in expected.items():
        path = Path(name)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 65536:
            raise ValueError("invalid workspace file")
        if path.read_bytes() != text.encode("utf-8"):
            raise ValueError("workspace content differs from proposal")
        if path.suffix == ".json":
            json.loads(text, parse_constant=reject_constant)


if __name__ == "__main__":
    main()
