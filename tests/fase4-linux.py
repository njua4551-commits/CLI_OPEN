"""Qualify a synthetic Bubblewrap boundary, without enabling workspace writes in the product."""
import os
from pathlib import Path
import platform
import runpy
import shutil
import socket
import subprocess
import tempfile
import time

SUPERVISOR = Path(__file__).resolve().parents[1] / "implementacion" / "supervisor" / "__main__.py"

PROBE = """
import errno, os, socket, sys
from pathlib import Path

assert os.geteuid() != 0
assert not os.environ.get("F4_PRIVATE_FIXTURE")
for path in ("/usr/bin/python3", "/lib", "/lib64", "/usr/lib", "/lib64/ld-linux-x86-64.so.2"):
    resolved = Path(path).resolve(strict=True)
    print(f"sandbox runtime: {path} -> {resolved}")
assert Path("/outside/marker").read_text() == "outside"
Path("/work/allowed").write_text("inside")
for target in ("/outside/marker", "/work/../outside/marker", "/work/link",
               "/protected/policy", "/work/policy-link"):
    try:
        Path(target).write_text("must not succeed")
    except OSError as error:
        assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
    else:
        raise AssertionError("outside write succeeded")
try:
    socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1)
except OSError as error:
    assert error.errno in (errno.ECONNREFUSED, errno.ENETUNREACH, errno.EHOSTUNREACH)
else:
    raise AssertionError("host loopback reachable")
print("PASS workspace, denied writes, policy, cleared environment and private network")
"""

CHILDREN = r"""
import subprocess, sys, time
child = "from pathlib import Path; import time; i = 0\nwhile True: i += 1; Path('/work/heartbeat').write_text(str(i)); time.sleep(.05)"
subprocess.Popen([sys.executable, "-I", "-B", "-c", child])
time.sleep(60)
"""


def main():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("Qualification requires Linux x86_64")
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SystemExit("Bubblewrap missing; isolation unverified")
    if os.geteuid() == 0:
        raise SystemExit("Qualification requires a standard user")
    sandbox = runpy.run_path(str(SUPERVISOR))["bubblewrap_command"]

    with tempfile.TemporaryDirectory(prefix="cli-open-p2-") as root, socket.socket() as listener:
        root = Path(root)
        work, outside, policy = (root / name for name in ("work", "outside", "protected"))
        for directory in (work, outside, policy):
            directory.mkdir()
        (outside / "marker").write_text("outside")
        (policy / "policy").write_text("policy")
        (work / "link").symlink_to("/outside/marker")
        (work / "policy-link").symlink_to("/protected/policy")

        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            connection, _ = listener.accept()
            connection.close()

        mounts = [(outside, "/outside"), (policy, "/protected")]
        python = ["/usr/bin/python3", "-I", "-B", "-c"]
        probe = sandbox(bwrap, mounts, [*python, PROBE, str(port)], writable_workspace=work)
        subprocess.run(probe, env={"F4_PRIVATE_FIXTURE": "synthetic"}, check=True, timeout=20)
        assert (work / "allowed").read_text() == "inside"
        assert (outside / "marker").read_text() == "outside"
        assert (policy / "policy").read_text() == "policy"

        heartbeat = work / "heartbeat"
        try:
            command = sandbox(bwrap, mounts, [*python, CHILDREN], writable_workspace=work)
            subprocess.run(command, env={}, check=True, timeout=2)
        except subprocess.TimeoutExpired:
            assert heartbeat.exists(), "child did not start before timeout"
        else:
            raise AssertionError("timeout probe exited early")
        time.sleep(0.2)
        last = heartbeat.read_text()
        time.sleep(0.3)
        assert heartbeat.read_text() == last, "child survived timeout"
        print("PASS timeout ended the child workload")


if __name__ == "__main__":
    main()
