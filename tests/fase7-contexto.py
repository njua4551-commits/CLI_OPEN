"""Verify the selective context envelope independently of prior memory tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

MEMORY = Path(__file__).resolve().parents[1] / "implementacion" / "memoria"

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    project = root / "project"
    project.mkdir()
    (project / "fixture.txt").write_text("baseline")

    def invoke(command, *arguments):
        return subprocess.check_output([
            sys.executable, "-I", "-B", str(MEMORY), "--store", str(root / "store"),
            command, "--project", str(project), *arguments,
        ], timeout=10)

    invoke("add", "--text", "loopback " + "雪" * 100, "--tags", "loopback")
    entry = json.loads(invoke("add", "--text", "loopback válido", "--files", "fixture.txt"))
    invoke("add", "--text", "Contenido de tema distinto")
    result = invoke("context", "--query", "loopback", "--max-bytes", "128")
    assert len(result) <= 128
    assert json.loads(result) == {
        "authority": "none", "source": "project-memory",
        "entries": [{"id": entry["stored"], "text": "loopback válido"}],
    }
    (project / "fixture.txt").write_text("updated")
    assert json.loads(invoke("context", "--query", "loopback", "--max-bytes", "128"))["entries"] == []
print("PASS selective context: byte budget, untrusted envelope, stale exclusion")
