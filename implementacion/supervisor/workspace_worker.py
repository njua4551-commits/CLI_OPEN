"""Apply explicit edits and validate their disposable copies inside Bubblewrap."""
import json
from pathlib import Path
import sys


def validate(path):
    text = path.read_bytes().decode("utf-8")
    if path.suffix == ".json":
        json.loads(text, parse_constant=reject_constant)


def reject_constant(_):
    raise ValueError("invalid JSON constant")


def main():
    edits = json.load(sys.stdin)
    for edit in edits:
        path = Path(edit["path"])
        mode = "xb" if edit["operation"] == "create" else "wb"
        with path.open(mode) as output:
            output.write(edit["text"].encode("utf-8"))
        validate(path)


if __name__ == "__main__":
    main()
