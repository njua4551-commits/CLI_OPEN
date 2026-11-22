"""Exercise the supervisor review flow against real Bubblewrap."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SUPERVISOR = Path(__file__).resolve().parents[1] / "implementacion" / "supervisor"


def run(source, edits):
    return subprocess.run(
        [sys.executable, "-I", "-B", str(SUPERVISOR), "review-workspace", str(source)],
        input=json.dumps({"edits": edits}).encode(), capture_output=True, timeout=20, check=False,
    )


def main():
    with tempfile.TemporaryDirectory(prefix="cli-open-original-") as original:
        source = Path(original)
        (source / "notes.txt").write_text("before\n")
        edits = [
            {"operation": "replace", "path": "notes.txt", "text": "after\n"},
            {"operation": "create", "path": "data.json", "text": '{"synthetic":true}\n'},
        ]
        result = run(source, edits)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["mode"] == "review-only"
        by_path = {entry["path"]: entry for entry in report["changes"]}
        assert "-before\n+after\n" in by_path["notes.txt"]["diff"]
        assert '--- /dev/null\n' in by_path["data.json"]["diff"]

        edits[1]["text"] = "{invalid\n"
        rejected = run(source, edits)
        assert rejected.returncode == 1, rejected.stderr
        assert not rejected.stdout
        assert b"Copia descartada." in rejected.stderr
        assert (source / "notes.txt").read_text() == "before\n"
        assert sorted(path.name for path in source.iterdir()) == ["notes.txt"]
        print("PASS create, replace, validation, review and discard")


if __name__ == "__main__":
    main()
