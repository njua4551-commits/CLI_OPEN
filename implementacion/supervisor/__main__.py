"""Expose the PLAN profile and inspect the current runtime."""
import argparse
import ctypes
import json
import os
import platform
import shutil
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
    return {
        "profile": "PLAN",
        "system": system,
        "release": release,
        "architecture": platform.machine(),
        "shell": shell.replace("\\", "/").rsplit("/", 1)[-1] if shell else None,
        "wsl": wsl,
        "elevated": elevated(system),
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
        print(f"Linux: aislamiento no verificado ({type(error).__name__}). PLAN/DIAG disponibles.",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Supervisor de CLI_OPEN. PLAN muestra el perfil activo sin herramientas del host.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspeccionar el entorno efectivo")
    commands.add_parser("plan", help="Mostrar capacidades del perfil activo")
    commands.add_parser("diag", help="Iniciar el broker MCP de solo lectura sobre stdio")
    commands.add_parser("qualify-linux", help="Calificar el aislamiento con una sesión sintética fija")
    options = parser.parse_args(argv)
    if options.command == "doctor":
        print(json.dumps(doctor(), ensure_ascii=True, indent=2))
    elif options.command == "qualify-linux":
        return qualify_linux()
    elif options.command == "diag":
        broker = Path(__file__).resolve().parent.parent / "broker"
        return subprocess.run([sys.executable, "-I", "-B", str(broker)], env={}, check=False).returncode
    else:
        print("PLAN activo. Ejecución, escritura e inferencia remota deshabilitadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
