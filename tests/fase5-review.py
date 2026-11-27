"""Exercise the supervisor review flow against real Bubblewrap."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SUPERVISOR = Path(__file__).resolve().parents[1] / "implementacion" / "supervisor"


def run(source, edits, approve=None):
    command = ["review-workspace", str(source)] if approve is None else [
        "apply-workspace", str(source), "--approve", approve,
    ]
    return subprocess.run(
        [sys.executable, "-I", "-B", str(SUPERVISOR), *command],
        input=json.dumps({"edits": edits}).encode(), capture_output=True, timeout=45, check=False,
    )


def git(source, *args):
    return subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, timeout=10, check=True,
    ).stdout.decode().strip()


def main():
    with tempfile.TemporaryDirectory(prefix="cli-open-original-") as original:
        source = Path(original)
        (source / "notes.txt").write_text("before\n")
        git(source, "init", "-b", "main")
        git(source, "add", "notes.txt")
        git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost",
            "commit", "-m", "fixture base")
        base = git(source, "rev-parse", "HEAD")
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

        assert report["base"] == base
        approval = report["approval"]
        (source / "notes.txt").write_text("concurrent\n")
        rejected = run(source, edits, approval)
        assert rejected.returncode == 1 and not rejected.stdout
        assert git(source, "for-each-ref", "refs/heads/cli-open/") == ""
        assert (source / "notes.txt").read_text() == "concurrent\n"
        (source / "notes.txt").write_text("before\n")
        assert run(source, edits, approval).returncode == 1
        refreshed = run(source, edits)
        assert refreshed.returncode == 0, refreshed.stderr
        refreshed_approval = json.loads(refreshed.stdout)["approval"]
        assert refreshed_approval != approval
        approval = refreshed_approval
        applied = run(source, edits, approval)
        assert applied.returncode == 0, applied.stderr
        published = json.loads(applied.stdout)
        assert published["mode"] == "published-review"
        reference = published["reference"]
        assert git(source, "show", f"{reference}:notes.txt") == "after"
        assert git(source, "show", f"{reference}:data.json") == '{"synthetic":true}'
        assert git(source, "rev-parse", "HEAD") == base
        collision = run(source, edits, approval)
        assert collision.returncode == 1 and not collision.stdout
        assert git(source, "rev-parse", reference) == published["commit"]

        edits[1]["text"] = "{invalid\n"
        rejected = run(source, edits)
        assert rejected.returncode == 1, rejected.stderr
        assert not rejected.stdout
        assert b"The copy was discarded." in rejected.stderr
        assert (source / "notes.txt").read_text() == "before\n"
        assert sorted(path.name for path in source.iterdir()) == [".git", "notes.txt"]
        print("PASS native edit, validation, reviewed Git publication, concurrent rejection and discard")


if __name__ == "__main__":
    main()
