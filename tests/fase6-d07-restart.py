"""Crash the supervisor's launcher while a fixed synthetic sandbox is active."""
from contextlib import closing
from pathlib import Path
import runpy
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def launch(work, stage):
    # Exercise the same supervisor command builder and subprocess ownership as
    # qualify-linux, with a persistent synthetic mount across two namespaces.
    supervisor = runpy.run_path(str(ROOT / "implementacion/supervisor/__main__.py"))
    artifacts = ROOT / ".fase1"
    mounts = [
        (artifacts / "tools/bun-linux-x64-baseline/bun", "/fixture/bun"),
        (artifacts / "opencode/packages/cli/dist/cli-linux-x64/bin/opencode", "/fixture/opencode"),
        (ROOT / "tests", "/tests"), (ROOT / "implementacion", "/implementacion"),
    ]
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    if backend is None:
        raise SystemExit("BLOCKED: Bubblewrap is required")
    command = supervisor["bubblewrap_command"](backend, mounts, [
        "/fixture/bun", "/tests/fase6-d07-restart.ts", "/fixture/opencode", stage,
    ], writable_workspace=work)
    subprocess.run(command, env={}, check=True, timeout=45)


def processes():
    found = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text().rsplit(")", 1)[1].split()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        found[int(path.parent.name)] = (int(fields[1]), fields[19], fields[0])
    return found


def descendants(parent):
    table = processes()
    seen = {parent}
    while True:
        children = {pid for pid, (ppid, _, _) in table.items() if ppid in seen}
        if children <= seen:
            return {pid: table[pid][1] for pid in seen - {parent}}
        seen.update(children)


def wait_until(predicate, timeout, message):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.025)
    raise AssertionError(message)


def snapshot(work):
    with closing(sqlite3.connect(work / "budget/task.sqlite")) as db:
        task = db.execute("SELECT * FROM task").fetchone()
        operations = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
    return task, operations


def main():
    with tempfile.TemporaryDirectory(prefix="cli-open-d07-restart-") as directory:
        work = Path(directory)
        command = [sys.executable, "-I", "-B", __file__, str(work)]
        with subprocess.Popen([*command, "start"], env={}) as supervisor:
            try:
                wait_until(lambda: (work / "ready").exists() or supervisor.poll() is not None,
                           35, "Interrupted fixture never reached both barriers")
                assert supervisor.poll() is None
                tracked = descendants(supervisor.pid)
                assert len(tracked) >= 5, tracked
                task, reserved = snapshot(work)
                assert reserved[-1][3] == "reserved"
            finally:
                supervisor.kill()
                supervisor.wait(timeout=5)

        def cleaned_up():
            table = processes()
            return all(pid not in table or table[pid][1] != started or table[pid][2] == "Z"
                       for pid, started in tracked.items())

        wait_until(cleaned_up, 5, "A managed descendant survived the launcher crash")
        subprocess.run([*command, "resume"], env={}, check=True, timeout=50)
        reopened, final = snapshot(work)
        assert reopened == task
        assert final[:len(reserved) - 1] == reserved[:-1]
        open_operation = reserved[-1]
        assert final[len(reserved) - 1] == (*open_operation[:3], "uncertain", *open_operation[4:])
        assert len(final) == task[1], (len(final), task[1])
    print(f"PASS D07 restart: native session, MCP uncertainty, SQLite budget and {len(tracked)} stopped descendants")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        main()
    else:
        launch(Path(sys.argv[1]), sys.argv[2])
