"""First workspace fixture: edit an isolated copy and review its diff."""
import difflib
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
        raise SystemExit("Standard-user Linux x86_64 required")
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


if __name__ == "__main__":
    main()
