"""Own a fresh, read-only native task using the existing gateway and sandbox."""
from contextlib import ExitStack, closing, contextmanager
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import runpy
import secrets
import select
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUN_SHA = "10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235"


@contextmanager
def managed(command, **options):
    parent = os.getpid()
    libc = ctypes.CDLL(None, use_errno=True)

    def bind_parent():
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
            os._exit(125)

    with subprocess.Popen(command, preexec_fn=bind_parent, **options) as child:
        try:
            yield child
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)


def run(options, sandbox):
    begun = time.monotonic()
    if platform.system() != "Linux" or platform.machine() != "x86_64" or os.geteuid() == 0:
        raise ValueError("unsupported host")
    if not 1 <= options.port <= 65535 or not 1 <= options.seconds <= 300:
        raise ValueError("invalid local destination or deadline")
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    artifacts = ROOT / ".fase1"
    bun = artifacts / "tools/bun-linux-x64-baseline/bun"
    sdk = artifacts / "opencode/packages/sdk"
    if not backend or not (sdk / "node_modules/effect").is_dir():
        raise ValueError("missing sandbox or prepared SDK")
    with bun.open("rb") as binary:
        if hashlib.file_digest(binary, "sha256").hexdigest() != BUN_SHA:
            raise ValueError("unexpected Bun artifact")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", options.identity):
        raise ValueError("invalid task identity")

    # Existing state is deliberately refused until recovery is qualified.
    state = options.state.absolute()
    if state.parent.resolve(strict=True) != state.parent or any(
        state.is_relative_to(Path(directory).resolve())
        for directory in ("/usr/bin", "/usr/lib", "/usr/lib64", "/lib", "/lib64", "/proc", "/dev")
    ):
        raise ValueError("trusted state must be outside the sandbox mounts")
    state.mkdir(mode=0o700)
    session, workspace = ("ses_" + secrets.token_hex(16), "wrk_" + secrets.token_hex(16))
    bearer = secrets.token_urlsafe(32)
    ledger = state / "task.sqlite"
    with ExitStack() as stack:
        stage = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="cli-open-task-", dir="/tmp")))
        workspace_dir = stage / "workspace"
        workspace_dir.mkdir()
        source = options.source.absolute()
        read = runpy.run_path(str(HERE / "workspace.py"))["snapshot"]
        directory = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            snapshot = read(directory, source.name)
        finally:
            os.close(directory)
        if snapshot is None:
            raise ValueError("authorized input missing")
        data = snapshot[1].encode()
        staged = workspace_dir / "input.txt"
        staged.write_bytes(data)
        worker = sandbox(backend, [(staged, "/input.txt"), (HERE / "task_read_worker.py", "/worker.py")],
                         [sys.executable, "-I", "-B", "/worker.py", str(state),
                          os.readlink("/proc/self/ns/net"), os.readlink("/proc/self/ns/pid")])
        (stage / "node_modules/@opencode").mkdir(parents=True)
        for name, target in {"@opencode/sdk": sdk, "@opencode/core": sdk.parent / "core",
                             "effect": sdk / "node_modules/effect"}.items():
            (stage / "node_modules" / name).symlink_to(target)
        for module in ("task_sdk.ts", "task_run.ts"):
            shutil.copyfile(HERE / module, stage / module)
        profile = {"HOME": str(state), "PATH": "/usr/bin:/bin"}
        gateway = stack.enter_context(managed(
            [sys.executable, "-I", "-B", str(HERE.parent / "gateway"), "--listen", "0",
             "--port", str(options.port), "--model", options.model, "--task-id", options.identity,
             "--task-state", str(ledger), "--task-owner", session, workspace,
             "--create-task", "--task-budget", "8", "131072", "4096", "--task-seconds", str(options.seconds)],
            env={**profile, "CLI_OPEN_GATEWAY_TASK_TOKEN": bearer}, stdout=subprocess.PIPE,
        ))
        if not select.select([gateway.stdout], [], [], min(10, options.seconds))[0]:
            raise ValueError("gateway startup timed out")
        ready = re.fullmatch(rb"LISTEN ([0-9]+)\n", gateway.stdout.readline(64))
        if ready is None:
            raise ValueError("gateway admission failed")
        with closing(sqlite3.connect(ledger.absolute().as_uri() + "?mode=ro", uri=True)) as db:
            expires, = db.execute("SELECT expires FROM task").fetchone()
        settings = dict(session=session, workspace=workspace, directory=str(workspace_dir),
                        database=str(state / "native.sqlite"), worker=worker, size=len(data),
                        port=int(ready[1]), model=options.model, bearer=bearer)
        output = stack.enter_context(tempfile.TemporaryFile())
        host = stack.enter_context(managed(
            [str(bun), "--no-install", str(stage / "task_run.ts")], env=profile,
            stdin=subprocess.PIPE, stdout=output, cwd=workspace_dir,
        ))
        remaining = min(begun + options.seconds - time.monotonic(), expires - time.time())
        if remaining <= 0:
            raise TimeoutError("task admission expired")
        payload = json.dumps(settings).encode()
        host.stdin.write(payload)
        host.stdin.close()
        deadline = time.monotonic() + remaining
        while host.poll() is None:
            if gateway.poll() is not None or time.monotonic() >= deadline:
                raise TimeoutError("task gateway ended or deadline expired")
            time.sleep(0.025)
        if host.returncode != 0 or gateway.poll() is not None or time.monotonic() >= deadline:
            raise ValueError("native task failed")
        output.seek(0)
        report = json.loads(output.read(131073))
        print(json.dumps(dict(task=options.identity, session=session, workspace=workspace, expires=expires, **report)))
