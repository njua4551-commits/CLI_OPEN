"""Exercise the pinned Effect SDK recovery gate in a clean Linux namespace."""
import hashlib
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    backend = shutil.which("bwrap", path="/usr/bin:/bin")
    suite = runpy.run_path(str(ROOT / "tests/run-suite.py"))
    bun_name = "tools/bun-linux-x64-baseline/bun"
    bun = ROOT / ".fase1" / bun_name
    sdk_tree = ROOT / ".fase1/opencode"
    sdk = "packages/sdk"
    effect = f"{sdk}/node_modules/effect"
    if not backend or not bun.is_file() or not (sdk_tree / effect).is_dir():
        raise SystemExit("BLOCKED: Bubblewrap, pinned Bun and prepared SDK dependencies are required")
    with bun.open("rb") as binary:
        if hashlib.file_digest(binary, "sha256").hexdigest() != suite["ARTIFACTS"][bun_name]:
            raise SystemExit("BLOCKED: unexpected Bun artifact")
    supervisor = runpy.run_path(str(ROOT / "implementacion/supervisor/__main__.py"))
    with tempfile.TemporaryDirectory(prefix="cli-open-sdk-fixture-") as directory:
        stage = Path(directory)
        (stage / "node_modules/@opencode").mkdir(parents=True)
        for name, target in {
            "@opencode/sdk": sdk, "@opencode/core": "packages/core", "effect": effect,
        }.items():
            (stage / "node_modules" / name).symlink_to("/sdk/" + target)
        mounts = [
            (bun, "/fixture/bun"), (sdk_tree, "/sdk"), (stage, "/stage"),
            (ROOT / "tests/d079-sdk-admission.ts", "/stage/tests/d079-sdk-admission.ts"),
            (ROOT / "implementacion/supervisor/task_sdk.ts", "/stage/implementacion/supervisor/task_sdk.ts"),
        ]
        for _, target in mounts[-2:]:
            local = stage / Path(target).relative_to("/stage")
            local.parent.mkdir(parents=True)
            local.touch()
        command = supervisor["bubblewrap_command"](backend, mounts, [
            "/usr/bin/env", "HOME=/tmp", "/fixture/bun", "--no-install", "/stage/tests/d079-sdk-admission.ts",
        ])
        subprocess.run(command, env={}, check=True, timeout=30)


if __name__ == "__main__":
    main()
