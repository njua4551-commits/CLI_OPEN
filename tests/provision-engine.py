"""Prepare checksum-pinned Linux test executables from official archives."""
import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Artifact:
    url: str
    archive_size: int
    archive_sha: str
    member: str
    executable_sha: str
    relative: str
    archive_kind: str


BUN = Artifact(
    "https://github.com/oven-sh/bun/releases/download/bun-v1.4.4/bun-linux-x64-baseline.zip",
    51_794_559, "e0446eb55995772eb9894bebae9a6be368d985a8b9271ee124486f9946eedd76",
    "bun-linux-x64-baseline/bun", "10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235",
    "tools/bun-linux-x64-baseline/bun", "zip",
)
OPENCODE = Artifact(
    "https://github.com/anomalyco/opencode/releases/download/v2.3.2/opencode-linux-x64-baseline.tar.gz",
    122_641_607, "563b5d663637226b6e3bb4bb6803281bc39b0d2cd88db06d674b6420aab009b0",
    "opencode", "e6543f6e5c39c40971ba38afd1819ac852c29ac735b5a89065d3d148d47f27ad",
    "opencode/packages/cli/dist/cli-linux-x64/bin/opencode", "tar",
)


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def extract(archive, artifact, output):
    if artifact.archive_kind == "zip":
        with zipfile.ZipFile(archive) as package:
            member = package.getinfo(artifact.member)
            if member.is_dir() or not 0 < member.file_size < 350_000_000:
                raise ValueError("invalid Bun archive member")
            with package.open(member) as binary:
                shutil.copyfileobj(binary, output)
    else:
        with tarfile.open(archive, "r:gz") as package:
            member = package.getmember(artifact.member)
            if not member.isfile() or not 0 < member.size < 350_000_000:
                raise ValueError("invalid OpenCode archive member")
            with package.extractfile(member) as binary:
                shutil.copyfileobj(binary, output)


def provision(root, artifact, local_archive):
    target = root / artifact.relative
    if target.exists():
        if target.is_symlink() or not target.is_file() or digest(target) != artifact.executable_sha:
            raise ValueError(f"existing executable differs from the official pin: {target}")
        print(f"Verified existing {artifact.relative}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".verified-engine-", dir=target.parent) as temporary:
        directory = Path(temporary)
        archive = local_archive or directory / "archive"
        if local_archive is None:
            subprocess.run([
                "curl", "--disable", "--fail", "--silent", "--show-error", "--location",
                "--proto", "=https", "--proto-redir", "=https", "--max-time", "300",
                "--max-filesize", str(artifact.archive_size), "--output", str(archive), artifact.url,
            ], check=True, timeout=310)
        if archive.stat().st_size != artifact.archive_size or digest(archive) != artifact.archive_sha:
            raise ValueError(f"archive size or SHA-256 mismatch: {artifact.relative}")
        executable = directory / "executable"
        with executable.open("xb") as output:
            extract(archive, artifact, output)
        if digest(executable) != artifact.executable_sha:
            raise ValueError(f"executable SHA-256 mismatch: {artifact.relative}")
        executable.chmod(0o755)
        target.hardlink_to(executable)
    print(f"Prepared {artifact.relative}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=ROOT / ".fase1")
    parser.add_argument("--bun-archive", type=Path)
    parser.add_argument("--opencode-archive", type=Path)
    options = parser.parse_args()
    try:
        provision(options.artifact_root, BUN, options.bun_archive)
        provision(options.artifact_root, OPENCODE, options.opencode_archive)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise SystemExit(f"BLOCKED: engine provisioning failed ({error})") from None


if __name__ == "__main__":
    main()
