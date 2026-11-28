"""Own a read-only native task using the existing gateway and sandbox."""
from contextlib import ExitStack, closing, contextmanager
import ctypes
import fcntl
import hashlib
import hmac
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
import stat
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


def private_info(path, *, directory=False):
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    mode = 0o700 if directory else 0o600
    if (not kind(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != mode or (not directory and info.st_nlink != 1)):
        raise ValueError("invalid supervised task state")
    return info


def reopen_binding(ledger, identity, recovery_key):
    private_info(ledger)
    with closing(sqlite3.connect(ledger.as_uri() + "?mode=ro", uri=True)) as db:
        if (db.execute("PRAGMA user_version").fetchone() != (2,)
                or db.execute("SELECT identity FROM task LIMIT 2").fetchall() != [(identity,)]):
            raise ValueError("supervised task identity mismatch")
        rows = db.execute("SELECT session, workspace, binding FROM task_owner LIMIT 2").fetchall()
    if len(rows) != 1:
        raise ValueError("invalid supervised task owner")
    session, workspace, raw = rows[0]
    if not isinstance(raw, str) or len(raw) > 8192:
        raise ValueError("invalid supervised task owner")
    saved = json.loads(raw)
    if (not isinstance(saved, dict) or not isinstance(saved.get("recovery_key"), str)
            or not hmac.compare_digest(saved["recovery_key"], recovery_key)):
        raise ValueError("supervised recovery authentication failed")
    return session, workspace, saved


def check_native_scope(database, session, workspace, directory):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        sessions = db.execute("""SELECT id, workspace_id, directory, parent_id, permission, fork_session_id,
                                         revert, time_archived, time_suspended
                                  FROM session_v2 LIMIT 2""").fetchall()
        workspaces = db.execute("SELECT id, provider, binding FROM workspace LIMIT 2").fetchall()
        if (len(sessions) != 1 or sessions[0][:-1] != (session, workspace, str(directory), *([None] * 5))
                or len(workspaces) != 1 or workspaces[0][:2] != (workspace, "supervised")
                or json.loads(workspaces[0][2]) != {"workspaceID": workspace}
                or db.execute("SELECT 1 FROM job LIMIT 1").fetchone()
                or db.execute("SELECT 1 FROM automation LIMIT 1").fetchone()):
            raise ValueError("supervised native session is outside the read profile")
        return sessions[0][-1] is not None


def run(options, sandbox):
    with ExitStack() as stack:
        run_owned(options, sandbox, stack)


def run_owned(options, sandbox, stack):
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

    state = options.state.absolute()
    ledger_module = runpy.run_path(str(HERE.parent / "gateway" / "task_ledger.py"))
    ledger_module["validate_ancestors"](state.parent)
    if any(
        state.is_relative_to(Path(directory).resolve())
        for directory in ("/usr/bin", "/usr/lib", "/usr/lib64", "/lib", "/lib64", "/proc", "/dev")
    ):
        raise ValueError("trusted state must be outside the sandbox mounts")
    token = os.environ.get("CLI_OPEN_TASK_RECOVERY_TOKEN")
    if (token is not None and not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token)
            or options.recover and token is None):
        raise ValueError("invalid supervised recovery credential")
    recovery_key = hashlib.sha256(token.encode("ascii")).hexdigest() if token else None
    native_db, workspace_dir, ledger = (state / name for name in ("native.sqlite", "workspace", "task.sqlite"))
    if options.recover:
        private_info(state, directory=True)
        session, workspace, saved = reopen_binding(ledger, options.identity, recovery_key)
    source = options.source.absolute()
    if options.recover and saved.get("source") != str(source):
        raise ValueError("supervised source is outside the original authorization")
    if source.resolve(strict=True) != source:
        raise ValueError("authorized input must have a canonical path")
    read = runpy.run_path(str(HERE / "workspace.py"))
    if read["sensitive_path"](source.as_posix()):
        raise ValueError("sensitive source is outside the read profile")
    directory = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        source_dir = os.fstat(directory)
        snapshot = read["snapshot"](directory, source.name)
    finally:
        os.close(directory)
    if snapshot is None:
        raise ValueError("authorized input missing")
    data = snapshot[1].encode()
    if not options.recover:
        state.mkdir(mode=0o700)
        descriptor = os.open(native_db, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(descriptor)
        workspace_dir.mkdir(mode=0o700)
        session, workspace = ("ses_" + secrets.token_hex(16), "wrk_" + secrets.token_hex(16))
    native_info = private_info(native_db)
    native_fd = os.open(native_db, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stack.callback(os.close, native_fd)
    if not os.path.samestat(native_info, os.fstat(native_fd)):
        raise ValueError("supervised native database identity changed")
    fcntl.flock(native_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    info = private_info(workspace_dir, directory=True)
    policy = hashlib.sha256()
    for path in (HERE / "task_run.ts", HERE / "task_sdk.ts", HERE / "task_read_worker.py",
                 HERE / "task_owner.py", HERE / "workspace.py", HERE / "workspace_limits.py",
                 HERE.parent / "context_policy.py"):
        policy.update(hashlib.sha256(path.read_bytes()).digest())
    binding = dict(source=str(source), source_directory=[source_dir.st_dev, source_dir.st_ino],
                   source_version=snapshot[0], source_digest=hashlib.sha256(data).hexdigest(),
                   workspace_directory=[str(workspace_dir), info.st_dev, info.st_ino],
                   native_database=[str(native_db), native_info.st_dev, native_info.st_ino],
                   policy=policy.hexdigest(), scope="read:input.txt", recovery_key=recovery_key)
    resume = False
    if options.recover:
        # JSON arrays are persisted for the source stat tuple.
        binding["source_version"] = list(binding["source_version"])
        if saved != binding:
            raise ValueError("supervised task binding or policy changed")
        resume = check_native_scope(native_db, session, workspace, workspace_dir)
    bearer = secrets.token_urlsafe(32)
    stage = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="cli-open-task-", dir="/tmp")))
    staged = stage / "input.txt"
    staged.write_bytes(data)
    worker = sandbox(backend, [(staged, "/input.txt"), (HERE / "task_read_worker.py", "/worker.py"),
                               (HERE / "workspace_limits.py", "/workspace_limits.py")],
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
         *([] if options.recover else ["--create-task"]), "--task-budget", "8", "131072", "4096", "--task-seconds", str(options.seconds)],
        env={**profile, "CLI_OPEN_GATEWAY_TASK_TOKEN": bearer,
             "CLI_OPEN_GATEWAY_TASK_BINDING": json.dumps(binding, ensure_ascii=True)}, stdout=subprocess.PIPE,
    ))
    if not select.select([gateway.stdout], [], [], min(10, options.seconds))[0]:
        raise ValueError("gateway startup timed out")
    ready = re.fullmatch(rb"LISTEN ([0-9]+)\n", gateway.stdout.readline(64))
    if ready is None:
        raise ValueError("gateway admission failed")
    with closing(sqlite3.connect(ledger.absolute().as_uri() + "?mode=ro", uri=True)) as db:
        expires, = db.execute("SELECT expires FROM task").fetchone()
    settings = dict(session=session, workspace=workspace, directory=str(workspace_dir),
                    database=str(native_db), worker=worker, size=len(data),
                    port=int(ready[1]), model=options.model, bearer=bearer, recover=options.recover, resume=resume)
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
