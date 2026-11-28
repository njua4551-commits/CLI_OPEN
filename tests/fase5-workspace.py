"""First workspace fixture: edit an isolated copy and review its diff."""
import difflib
import io
import json
from pathlib import Path
import os
import platform
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "implementacion" / "supervisor" / "__main__.py"
BEFORE = "synthetic before\n"
AFTER = "synthetic after\n"
EDIT = """
import errno
from pathlib import Path

target = Path("/work/fixture.txt")
assert target.read_text() == "synthetic before\\n"
target.write_text("synthetic after\\n")
try:
    Path("/source/fixture.txt").write_text("unexpected")
except OSError as error:
    assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
else:
    raise AssertionError("original became writable")
assert target.read_text() == "synthetic after\\n"
"""


def main():
    if platform.system() != "Linux" or platform.machine() != "x86_64" or os.geteuid() == 0:
        print("SKIP workspace integration: requires standard-user Linux x86_64")
        return
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    if not backend:
        raise SystemExit("Bubblewrap unavailable")
    bubblewrap_command = runpy.run_path(str(SUPERVISOR))["bubblewrap_command"]
    with tempfile.TemporaryDirectory(prefix="cli-open-workspace-") as directory:
        base = Path(directory)
        source = base / "source"
        source.mkdir()
        original = source / "fixture.txt"
        original.write_text(BEFORE)
        copy = base / "copy"
        shutil.copytree(source, copy)
        command = bubblewrap_command(
            backend, [(source, "/source")],
            ["/usr/bin/python3", "-I", "-B", "-c", EDIT],
            writable_workspace=copy,
        )
        subprocess.run(command, env={}, check=True, timeout=15)
        assert original.read_text() == BEFORE
        edited = (copy / "fixture.txt").read_text()
        assert edited == AFTER
        diff = difflib.unified_diff(
            BEFORE.splitlines(keepends=True), edited.splitlines(keepends=True),
            fromfile="fixture.txt (original)", tofile="fixture.txt (copy)",
        )
        print("".join(diff), end="")
        supervisor = SUPERVISOR.parent
        parse = runpy.run_path(str(supervisor / "workspace.py"))["parse_request"]
        command = bubblewrap_command(
            backend,
            [(supervisor / "workspace_worker.py", "/worker.py"),
             (supervisor / "workspace_limits.py", "/workspace_limits.py")],
            ["/usr/bin/python3", "-I", "-B", "/worker.py"],
            writable_workspace=copy,
        )
        for operation in ("create", "replace"):
            target = copy / "fixture.txt"
            target.unlink()
            if operation == "replace":
                target.write_text(BEFORE)
            for size in (65535, 65536, 65537, 200 * 1024, 262144, 262145):
                proposed = "x" * size
                edits = [{"operation": operation, "path": target.name, "text": proposed}]
                request = io.BytesIO(json.dumps({"edits": edits}).encode())
                if size <= 262144:
                    assert parse(request) == edits
                else:
                    try:
                        parse(request)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("parser accepted an oversized file")
                target.write_text(proposed)
                result = subprocess.run(command, env={}, input=json.dumps(edits).encode(),
                                        capture_output=True, timeout=15)
                assert (result.returncode == 0) == (size <= 262144), (operation, size, result.stderr)
        print("PASS isolated workspace validator size boundaries")


if __name__ == "__main__":
    main()
