"""Expose the PLAN profile and inspect the current runtime."""
import argparse
import ctypes
import json
import os
import platform
import runpy
import shutil
import signal
import sqlite3
import subprocess
import sys
from pathlib import Path


def elevated(system):
    if system == "Windows":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return None
    return os.geteuid() == 0 if hasattr(os, "geteuid") else None


def doctor():
    system = platform.system()
    release = platform.release()
    wsl = system == "Linux" and (
        "microsoft" in release.casefold() or bool(os.environ.get("WSL_DISTRO_NAME"))
    )
    backend = shutil.which("bwrap") is not None if system == "Linux" else None
    shell = os.environ.get("SHELL") or os.environ.get("ComSpec")
    project = Path(__file__).resolve().parents[2]
    artifacts = Path(os.environ.get("CLI_OPEN_ARTIFACTS", str(project / ".fase1")))
    return {
        "profile": "PLAN",
        "system": system,
        "release": release,
        "architecture": platform.machine(),
        "shell": shell.replace("\\", "/").rsplit("/", 1)[-1] if shell else None,
        "wsl": wsl,
        "elevated": elevated(system),
        "runtime": {
            "python": platform.python_version(),
            "python_3_11_or_later": sys.version_info >= (3, 11),
            "git_on_path": shutil.which("git") is not None,
            "node_on_path": shutil.which("node") is not None,
            "ripgrep_on_path": shutil.which("rg") is not None,
            "prepared_bun": (artifacts / "tools/bun-linux-x64-baseline/bun").is_file(),
            "prepared_opencode": (artifacts / "opencode/packages/cli/dist/cli-linux-x64/bin/opencode").is_file(),
            "prepared_sdk": (artifacts / "opencode/packages/sdk/node_modules/effect").is_dir(),
        },
        "isolation": {"bubblewrap_on_path": backend, "verified": False},
        "capabilities": {"execute": False, "write": False, "remote": False},
    }


def bubblewrap_command(backend, mounts, program, *, writable_workspace=None):
    command = [
        backend, "--die-with-parent", "--new-session", "--unshare-user", "--unshare-pid",
        "--unshare-ipc", "--unshare-net", "--unshare-uts", "--disable-userns",
        "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--clearenv",
        "--setenv", "PATH", "/usr/bin:/bin",
    ]
    for directory in ("/usr/bin", "/usr/lib", "/usr/lib64", "/lib", "/lib64"):
        if Path(directory).is_dir():
            command.extend(["--ro-bind", directory, directory])
    command.extend(["--symlink", "usr/bin", "/bin"])
    for source, destination in mounts:
        command.extend(["--ro-bind", str(source), destination])
    if writable_workspace is not None:
        command.extend(["--bind", str(writable_workspace), "/work"])
    directory = "/work" if writable_workspace is not None else "/tmp"
    return command + ["--chdir", directory, "--", *program]


def qualify_linux():
    """Exercise the fixed synthetic session through the supervisor's Linux boundary."""
    try:
        if platform.system() != "Linux" or platform.machine() != "x86_64" or os.geteuid() == 0:
            raise ValueError("unsupported qualification environment")
        backend = shutil.which("bwrap", path="/usr/bin:/bin")
        if not backend:
            raise FileNotFoundError("Bubblewrap")
        project = Path(__file__).resolve().parents[2]
        artifacts = project / ".fase1"
        mounts = (
            (artifacts / "tools/bun-linux-x64-baseline/bun", "/fixture/bun"),
            (artifacts / "opencode/packages/cli/dist/cli-linux-x64/bin/opencode", "/fixture/opencode"),
            (project / "tests/fase1-loopback.ts", "/fixture/loopback.ts"),
            (project / "implementacion", "/implementacion"),
        )
        if not all(source.exists() for source, _ in mounts):
            raise FileNotFoundError("qualification artifacts")
        command = bubblewrap_command(backend, mounts, [
            "/fixture/bun", "/fixture/loopback.ts", "/fixture/opencode",
            "/implementacion/supervisor", "--qualification",
        ])
        subprocess.run(command, env={}, check=True, timeout=45)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Linux isolation could not be verified ({type(error).__name__}). PLAN and DIAG remain available.",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="CLI_OPEN supervisor. PLAN displays the active profile without host tools.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspeccionar el entorno efectivo")
    commands.add_parser("plan", help="Mostrar capacidades del perfil activo")
    commands.add_parser("diag", help="Start the read-only MCP broker over stdio")
    commands.add_parser("qualify-linux", help="Qualify isolation with a fixed synthetic session")
    review = commands.add_parser("review-workspace", help="Review a disposable copy with explicit changes")
    review.add_argument("source", type=Path)
    apply = commands.add_parser("apply-workspace", help="Publish an approved review to a separate Git branch")
    apply.add_argument("source", type=Path)
    apply.add_argument("--approve", required=True)
    task = commands.add_parser("run-read-task", help="Run or reopen a read-only native task with a local provider")
    task.add_argument("source", type=Path)
    task.add_argument("--state", type=Path, required=True)
    task.add_argument("--identity", required=True)
    task.add_argument("--port", type=int, required=True)
    task.add_argument("--model", required=True)
    task.add_argument("--seconds", type=int, default=45)
    task.add_argument("--recover", action="store_true",
                      help="Reopen an eligible task using CLI_OPEN_TASK_RECOVERY_TOKEN")
    inject = commands.add_parser("inject-context", help="Incorporar sobre de memoria como datos no confiables")
    inject.add_argument("--prompt", required=True, help="Prompt del usuario")
    inject.add_argument("--envelope", required=True, help="Sobre JSON de contexto emitido por memoria context")
    inject.add_argument("--max-context-bytes", type=int, help="Presupuesto del sobre de memoria, 128–16384 bytes")
    options = parser.parse_args(argv)
    if options.command == "doctor":
        print(json.dumps(doctor(), ensure_ascii=True, indent=2))
    elif options.command == "qualify-linux":
        return qualify_linux()
    elif options.command == "run-read-task":
        try:
            owner = runpy.run_path(str(Path(__file__).with_name("task_owner.py")))
            owner["run"](options, bubblewrap_command)
        except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError):
            print("Supervised read task rejected or failed.", file=sys.stderr)
            return 1
    elif options.command in ("review-workspace", "apply-workspace"):
        workspace = runpy.run_path(str(Path(__file__).with_name("workspace.py")))
        git_workspace = runpy.run_path(str(Path(__file__).with_name("workspace_git.py")))
        try:
            source = options.source.absolute()
            edits = workspace["parse_request"](sys.stdin.buffer)
            base = git_workspace["base_commit"](source)
            changes = workspace["review"](source, edits, bubblewrap_command)
            if git_workspace["base_commit"](source) != base:
                raise workspace["SourceChanged"]("Git base changed")
            digest = git_workspace["approval"](source, base, changes, edits)
            report = {
                "mode": "review-only", "base": base, "approval": digest,
                "changes": [{key: value for key, value in change.items() if key != "before_version"}
                            for change in changes],
            }
            if options.command == "apply-workspace":
                if not base or options.approve != digest:
                    raise workspace["SourceChanged"]("missing Git base or approval mismatch")
                reference, commit, already_published = git_workspace["publish"](
                    source, base, edits, changes, digest, workspace["verify_sources"],
                )
                report = {
                    "mode": "already-published" if already_published else "published-review",
                    "reference": reference, "commit": commit,
                }
        except git_workspace["PublicationConflict"] as error:
            print(str(error), file=sys.stderr)
            return 1
        except workspace["SourceChanged"]:
            print("Review rejected because the original changed during the operation.", file=sys.stderr)
            return 1
        except (workspace["IsolatedEditFailed"], subprocess.SubprocessError):
            print("Isolated editing or validation failed. The copy was discarded.", file=sys.stderr)
            return 1
        except (ValueError, OSError, RecursionError):
            print("Review rejected due to invalid input, an invalid source, or unavailable isolation.", file=sys.stderr)
            return 1
        print(json.dumps(report))
    elif options.command == "diag":
        broker = Path(__file__).resolve().parent.parent / "broker"
        return subprocess.run([sys.executable, "-I", "-B", str(broker)], env={}, check=False).returncode
    elif options.command == "inject-context":
        context_mod = runpy.run_path(str(Path(__file__).with_name("context.py")))
        try:
            if len(options.envelope.encode("utf-8")) > 65536:
                raise ValueError("input exceeds 64 KiB")
            envelope_data = json.loads(options.envelope)
            budget = options.max_context_bytes
            if budget is None:
                budget = context_mod["MAX_CONTEXT_BYTES"]
            prompt = context_mod["incorporate_prompt"](options.prompt, envelope_data, budget)
            print(prompt)
        except (ValueError, RecursionError) as exc:
            print(f"Context envelope rejected: {exc}", file=sys.stderr)
            return 1
    else:
        print("PLAN active. Execution, writes, and remote inference are disabled.")
    return 0


def terminate(signum, _frame):
    # Unwind the active subprocess and disposable workspace on service stop.
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminate)
    raise SystemExit(main())
