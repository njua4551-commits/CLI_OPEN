"""Pruebas de la memoria persistente por proyecto."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import runpy
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "implementacion" / "memoria"


def call(store, *args):
    return subprocess.run([sys.executable, "-I", "-B", str(MODULE), "--store", store, *args],
                          capture_output=True, text=True, timeout=20)


def ok(store, *args):
    result = call(store, *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        other = root / "other"
        project.mkdir()
        other.mkdir()
        (project / "notas.md").write_text("alpha beta\n")
        store = str(root / "store")

        first = ok(store, "add", "--project", str(project),
                   "--text", "La sesión usa loopback y no tiene salida remota.",
                   "--tags", "red,seguridad", "--files", "notas.md")
        assert first["entries"] == 1
        ok(store, "add", "--project", str(project), "--text", "Detalle menor sobre tipografía.",
           "--tags", "ui")

        found = ok(store, "search", "--project", str(project), "--query", "loopback remota", "--budget", "64")
        assert [entry["id"] for entry in found["entries"]] == [first["stored"]]
        assert found["tokens"] <= 64 and found["entries"][0]["score"] >= 2

        narrow = ok(store, "search", "--project", str(project), "--query", "tipografía loopback", "--budget", "8")
        assert narrow["tokens"] <= 8 and len(narrow["entries"]) <= 1

        (project / "notas.md").write_text("alpha beta gamma\n")
        stale = ok(store, "search", "--project", str(project), "--query", "loopback")
        assert stale["entries"] == [] and stale["stale"] == 1
        report = ok(store, "invalidate", "--project", str(project))
        assert report["invalid"] == [first["stored"]] and not report["purged"]
        purged = ok(store, "invalidate", "--project", str(project), "--purge")
        assert purged["purged"] and purged["entries"] == 1

        assert ok(store, "search", "--project", str(other), "--query", "loopback")["entries"] == []

        secret = call(store, "add", "--project", str(project),
                      "--text", "token sk-abcdefghijklmnopqrstuvwx")
        assert secret.returncode == 1 and "secret" in secret.stderr
        escape = call(store, "add", "--project", str(project), "--text", "x", "--files", "../other")
        assert escape.returncode == 1 and "outside" in escape.stderr
        missing = call(store, "add", "--project", str(project), "--text", "x", "--files", "missing.md")
        assert missing.returncode == 1

        doctor = ok(store, "doctor", "--project", str(project))
        assert doctor["entries"] == 1 and doctor["stale"] == 0

        storage = Path(store)
        records, = storage.glob("*.jsonl")
        lock = records.with_suffix(".lock")
        assert stat.S_IMODE(storage.stat().st_mode) == 0o700
        for path in (records, lock):
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            path.chmod(0o644)
        ok(store, "doctor", "--project", str(project))
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in (records, lock))
        storage.chmod(0o755)
        assert call(store, "doctor", "--project", str(project)).returncode == 1
        storage.chmod(0o700)

        original = records.read_bytes()
        corrupt = b"synthetic private corrupt record"
        records.write_bytes(original + corrupt + b"\n")
        for command, extra in (("doctor", ()), ("invalidate", ("--purge",)), ("add", ("--text", "x"))):
            rejected = call(store, command, "--project", str(project), *extra)
            assert rejected.returncode == 1 and "line 2" in rejected.stderr
            assert corrupt.decode() not in rejected.stderr and records.read_bytes() == original + corrupt + b"\n"
        records.write_bytes(original)

        memory = runpy.run_path(str(MODULE / "__main__.py"))
        with memory["open_store"](records) as opened:
            entries = opened.read()
            with patch("os.replace", side_effect=OSError("synthetic interrupted replacement")):
                try:
                    opened.write(entries + entries)
                except OSError:
                    pass
                else:
                    raise AssertionError("interruption was ignored")
            assert opened.read() == entries
        assert not list(storage.glob("*.tmp"))
        assert records.read_bytes() == original

        alternate = root / "untouched.jsonl"
        records.rename(alternate)
        records.symlink_to(alternate)
        assert call(store, "add", "--project", str(project), "--text", "x").returncode == 1
        assert alternate.read_bytes() == original and records.is_symlink()
        records.unlink()
        alternate.rename(records)

        with ThreadPoolExecutor(max_workers=4) as pool:
            added = list(pool.map(lambda i: ok(store, "add", "--project", str(project),
                                               "--text", f"synthetic parallel entry {i}"), range(8)))
        assert sorted(item["entries"] for item in added) == list(range(2, 10))
        assert ok(store, "doctor", "--project", str(project))["entries"] == 9

        for filename in (".env", "development.env", "id_ed25519"):
            (project / filename).write_text("synthetic")
            rejected = call(store, "add", "--project", str(project), "--text", "x", "--files", filename)
            assert rejected.returncode == 1 and "sensitive" in rejected.stderr

        env = {**os.environ, "HOME": str(root), "XDG_STATE_HOME": ""}
        result = subprocess.run([sys.executable, "-I", "-B", str(MODULE), "doctor", "--project", str(project)],
                                capture_output=True, text=True, env=env, timeout=10, check=True)
        assert Path(json.loads(result.stdout)["store"]).parent == root / ".local/state/cli-open/memoria"

    print("PASS memoria: alta, recuperación selectiva, presupuesto, invalidación, purga, aislamiento y secretos")


if __name__ == "__main__":
    main()
