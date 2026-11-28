"""Build and mount the test-only native I/O barrier for OpenCode on Linux."""
import argparse
from pathlib import Path
import hashlib
import platform
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(
        description="Interrupt native tools at instrumented I/O result boundaries."
    )
    parser.add_argument("--read", action="store_true", help="Trace native positional reads on Linux x86_64")
    options = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("BLOCKED: this fixture requires Linux x86_64")
    compiler = shutil.which("cc", path="/usr/bin:/bin")
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    if not compiler or not backend:
        raise SystemExit("BLOCKED: this fixture requires a C compiler and Bubblewrap")
    suite = runpy.run_path(str(ROOT / "tests/run-suite.py"))
    artifacts = [ROOT / ".fase1" / name for name in suite["ARTIFACTS"]]
    for path, expected in zip(artifacts, suite["ARTIFACTS"].values(), strict=True):
        with path.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != expected:
                raise SystemExit(f"BLOCKED: unexpected artifact at {path.relative_to(ROOT)}")
    bun, opencode = artifacts
    supervisor = runpy.run_path(str(ROOT / "implementacion/supervisor/__main__.py"))
    with tempfile.TemporaryDirectory(prefix="cli-open-io-") as temporary:
        name = "native-read" if options.read else "native-io.so"
        artifact = Path(temporary) / name
        source = "native-read-barrier.c" if options.read else "native-io-barrier.c"
        flags = [] if options.read else ["-shared", "-fPIC", "-ldl"]
        subprocess.run([compiler, "-Wall", "-Wextra", "-Werror",
                        str(ROOT / "tests" / source), "-o", str(artifact), *flags],
                       check=True, timeout=15)
        mounts = [(bun, "/fixture/bun"), (opencode, "/fixture/opencode"),
                  (ROOT / "tests", "/tests"), (ROOT / "implementacion", "/implementacion"),
                  (artifact, "/fixture/" + name)]
        command = supervisor["bubblewrap_command"](backend, mounts, [
            "/usr/bin/env", "HOME=/tmp", "/fixture/bun", "/tests/fase6-d07-responses.ts", "/fixture/opencode",
            "--native-read" if options.read else "--native-io",
        ])
        subprocess.run(command, env={}, check=True, timeout=110)


if __name__ == "__main__":
    main()
