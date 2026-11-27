"""Build and mount the test-only native I/O barrier for OpenCode on Linux."""
from pathlib import Path
import hashlib
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
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
        library = Path(temporary) / "native-io.so"
        subprocess.run([compiler, "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
                        str(ROOT / "tests/native-io-barrier.c"), "-o", str(library), "-ldl"],
                       check=True, timeout=15)
        mounts = [(bun, "/fixture/bun"), (opencode, "/fixture/opencode"),
                  (ROOT / "tests", "/tests"), (ROOT / "implementacion", "/implementacion"),
                  (library, "/fixture/native-io.so")]
        command = supervisor["bubblewrap_command"](backend, mounts, [
            "/usr/bin/env", "HOME=/tmp", "/fixture/bun", "/tests/fase6-d07-responses.ts", "/fixture/opencode",
            "--native-io",
        ])
        subprocess.run(command, env={}, check=True, timeout=110)


if __name__ == "__main__":
    main()
