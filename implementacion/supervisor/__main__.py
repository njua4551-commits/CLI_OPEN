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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Supervisor de CLI_OPEN. PLAN muestra el perfil activo sin herramientas del host.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspeccionar el entorno efectivo")
    commands.add_parser("plan", help="Mostrar capacidades del perfil activo")
    commands.add_parser("diag", help="Iniciar el broker MCP de solo lectura sobre stdio")
    options = parser.parse_args(argv)
    if options.command == "doctor":
        print(json.dumps(doctor(), ensure_ascii=True, indent=2))
    elif options.command == "diag":
        broker = Path(__file__).resolve().parent.parent / "broker"
        return subprocess.run([sys.executable, "-I", "-B", str(broker)], env={}, check=False).returncode
    else:
        print("PLAN activo. Ejecución, escritura e inferencia remota deshabilitadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
