"""F7.1: línea base reproducible de recuperación de contexto antes de extender.

Mide, sin red ni inferencia, el coste del sobre selectivo de memoria para
presupuestos fijos y comprueba determinismo, ajuste al límite e invalidación.
La salida incluye una única línea JSON con las métricas para comparar futuras
extensiones (Repo Map, presupuesto dinámico) contra la misma referencia.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

MEMORY = Path(__file__).resolve().parents[1] / "implementacion" / "memoria"

TEXTS = [
    ("loopback recibe el sobre como datos sin autoridad", "loopback,contexto", "fixture.txt"),
    ("el supervisor encapsula el contexto no confiable", "contexto,supervisor", "fixture.txt"),
    ("la memoria invalida entradas cuando cambia el archivo", "memoria,invalidate", ""),
    ("repo map debe reutilizar tree-sitter del motor fijado", "repomap,tree-sitter", ""),
    ("presupuesto dinámico de tokens para contexto", "contexto,presupuesto", ""),
]

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    project = root / "project"
    project.mkdir()
    (project / "fixture.txt").write_text("baseline")

    def invoke(command, *arguments):
        return subprocess.run([
            sys.executable, "-I", "-B", str(MEMORY), "--store", str(root / "store"),
            command, "--project", str(project), *arguments,
        ], timeout=10, capture_output=True)

    for text, tags, files in TEXTS:
        arguments = ["--text", text, "--tags", tags]
        if files:
            arguments += ["--files", files]
        assert invoke("add", *arguments).returncode == 0

    measurements = {}
    for budget in (512, 2048, 8192):
        first = invoke("context", "--query", "contexto", "--max-bytes", str(budget)).stdout
        second = invoke("context", "--query", "contexto", "--max-bytes", str(budget)).stdout
        assert first == second, f"non deterministic output at {budget} bytes"
        assert first.endswith(b"\n")
        payload = json.loads(first)
        size = len(first)
        assert size <= budget, "envelope exceeded its byte budget"
        assert payload["authority"] == "none"
        measurements[str(budget)] = {
            "bytes": size,
            "entries": len(payload["entries"]),
            "tokens_estimate": -(-int(size * 0.25) // 1),
        }

    # Un presupuesto menor que el sobre vacío no puede excederse ni romper el límite.
    minimal = invoke("context", "--query", "contexto", "--max-bytes", "128").stdout
    assert len(minimal) <= 128 and json.loads(minimal)["entries"] == []

    # La invalidación por cambio de archivo debe retirar la entrada marcada.
    (project / "fixture.txt").write_text("updated")
    after = json.loads(invoke("context", "--query", "loopback", "--max-bytes", "2048").stdout)
    assert after["entries"] == []

    # Límites del contrato: fuera de rango se rechaza con error, no se trunca.
    assert invoke("context", "--query", "contexto", "--max-bytes", "64").returncode == 1

    metrics = {"budgets": measurements, "stale_excluded": True, "deterministic": True}
    assert metrics["budgets"]["512"]["entries"] <= metrics["budgets"]["8192"]["entries"]
    print(json.dumps(metrics, ensure_ascii=True, sort_keys=True))

print("PASS fase7 baseline: determinismo, presupuesto de bytes, invalidación y rechazo")
