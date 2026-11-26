"""Run the portable, Linux or prebuilt OpenCode test profile."""
import argparse
import hashlib
from pathlib import Path
import platform
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "tools/bun-linux-x64-baseline/bun": "10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235",
    "opencode/packages/cli/dist/cli-linux-x64/bin/opencode": "2a04919c134da80f95ffb8b2e3661d1c9aa6ca6c31c775a7efad6b497e6b6d24",
}


def run(*args, timeout=120):
    print("+", *args, flush=True)
    subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)


def python(*args):
    run(sys.executable, "-I", "-B", *args)


def preflight():
    for relative, expected in ARTIFACTS.items():
        path = ROOT / ".fase1" / relative
        if not path.is_file():
            raise SystemExit(f"BLOCKED: missing {path.relative_to(ROOT)}")
        with path.open("rb") as binary:
            if hashlib.file_digest(binary, "sha256").hexdigest() != expected:
                raise SystemExit(f"BLOCKED: SHA-256 mismatch for {path.relative_to(ROOT)}")
    bun, cli = (ROOT / ".fase1" / name for name in ARTIFACTS)
    with tempfile.TemporaryDirectory() as home:
        env = {"HOME": home, "PATH": "/usr/bin:/bin"}
        for binary, version in ((bun, "1.4.4"), (cli, "opencode v2.3.2")):
            reported = subprocess.check_output([binary, "--version"], env=env, text=True, timeout=10)
            if reported.strip() != version:
                raise SystemExit(f"BLOCKED: expected {binary.name} {version}, got {reported.strip()!r}")
    python("implementacion/supervisor", "qualify-linux")
    mounts = [(bun, "/fixture/bun"), (cli, "/fixture/opencode"),
              (ROOT / "tests", "/tests"), (ROOT / "implementacion", "/implementacion")]
    python("tests/fase5-review.py")
    supervisor = runpy.run_path(str(ROOT / "implementacion/supervisor/__main__.py"))
    for fixture in ("fase6-cli-gateway", "fase7-contexto-loopback", "fase7-contexto-selectivo", "lectura-web-loopback"):
        run(*supervisor["bubblewrap_command"](
            shutil.which("bwrap"), mounts, [
                "/usr/bin/env", "HOME=/tmp", "/fixture/bun", f"/tests/{fixture}.ts", "/fixture/opencode",
            ],
        ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("portable", "linux", "opencode"))
    profile = parser.parse_args().profile
    if profile == "portable":
        python("-m", "unittest", "discover", "-s", "tests")
        for fixture in ("fase7-memoria", "fase7-contexto", "fase7-lineabase"):
            python(f"tests/{fixture}.py")
        run("node", "tests/lectura-web-unit.mjs")
    else:
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise SystemExit("BLOCKED: this profile requires Linux x86_64")
        if not shutil.which("bwrap"):
            raise SystemExit("BLOCKED: Bubblewrap is required")
        if profile == "linux":
            for fixture in ("fase4-linux", "fase5-workspace", "fase6-gateway",
                            "fase6-concurrencia", "fase6-d07-cancel", "fase6-d07-budget", "fase6-d07-persist"):
                python(f"tests/{fixture}.py")
        else:
            preflight()
    print(f"PASS profile: {profile}")


if __name__ == "__main__":
    main()
