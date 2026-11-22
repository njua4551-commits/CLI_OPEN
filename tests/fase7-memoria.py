"""Pruebas de la memoria persistente por proyecto."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

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

    print("PASS memoria: alta, recuperación selectiva, presupuesto, invalidación, purga, aislamiento y secretos")


if __name__ == "__main__":
    main()
