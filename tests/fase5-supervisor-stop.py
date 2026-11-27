"""Stop and restart the actual review-workspace entry point under Bubblewrap."""
from pathlib import Path
import json
import os
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = runpy.run_path(str(ROOT / "tests/fase6-d07-restart.py"))
SUPERVISOR = ROOT / "implementacion/supervisor"
REQUEST = json.dumps({"edits": [{"operation": "replace", "path": "notes.txt", "text": "after\n"}]}).encode()


def main():
    with tempfile.TemporaryDirectory(prefix="cli-open-stop-test-") as temporary:
        fixture = Path(temporary)
        source = fixture / "source"
        source.mkdir()
        target = source / "notes.txt"
        target.write_text("before\n")
        target.chmod(0o640)
        scratch = fixture / "scratch"
        scratch.mkdir()
        artifacts = fixture / "artifacts"
        worker = artifacts / "tools/bun-linux-x64-baseline/bun"
        worker.parent.mkdir(parents=True)
        # The controlled executable occupies the worker artifact slot. The real
        # supervisor still owns workspace creation and the namespace lifecycle.
        worker.write_text("""#!/usr/bin/python3
from pathlib import Path
import signal
assert Path("/work/notes.txt").read_bytes() == b"before\\n"
Path("/work/notes.txt").write_bytes(b"unreviewed\\n")
Path("/work/ready").touch()
while True:
    signal.pause()
""")
        worker.chmod(0o700)
        cli = artifacts / "opencode/packages/cli/dist/cli-linux-x64/bin/opencode"
        cli.parent.mkdir(parents=True)
        cli.touch()
        command = [sys.executable, "-I", "-B", str(SUPERVISOR), "review-workspace", str(source)]
        environment = {"PATH": "/usr/bin:/bin", "TMPDIR": str(scratch)}
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env={**environment, "CLI_OPEN_ARTIFACTS": str(artifacts)}) as supervisor:
            try:
                supervisor.stdin.write(REQUEST)
                supervisor.stdin.close()
                RECOVERY["wait_until"](
                    lambda: any(scratch.glob("cli-open-review-*/ready")) or supervisor.poll() is not None,
                    10, "The isolated worker did not reach the barrier",
                )
                assert supervisor.poll() is None, supervisor.stderr.read().decode()
                tracked = RECOVERY["descendants"](supervisor.pid)
                assert tracked
                supervisor.terminate()
                assert supervisor.wait(timeout=8) == 143
                assert not supervisor.stdout.read()
            finally:
                if supervisor.poll() is None:
                    supervisor.kill()
                    supervisor.wait(timeout=5)

        def gone():
            table = RECOVERY["processes"]()
            return all(pid not in table or table[pid][1] != started or table[pid][2] == "Z"
                       for pid, started in tracked.items())

        RECOVERY["wait_until"](gone, 5, "An isolated worker survived SIGTERM")
        assert list(scratch.iterdir()) == []
        assert target.read_bytes() == b"before\n"
        assert target.stat().st_mode & 0o777 == 0o640
        review = subprocess.run(command, input=REQUEST, capture_output=True, env=environment, timeout=45)
        assert review.returncode == 0, review.stderr
        assert "-before\n+after\n" in json.loads(review.stdout)["changes"][0]["diff"]
        assert target.read_bytes() == b"before\n"
        assert set(source.iterdir()) == {target}
    print("PASS production review stop, isolated worker cleanup and fresh review after restart")


if __name__ == "__main__":
    main()
