"""F7.2: compuerta de reutilización del Repo Map antes de implementar.

No crea un indexador. Comprueba en el SHA fijado qué capacidades nativas
existen realmente (gramáticas Tree-sitter, consultas de símbolos, LSP,
ripgrep) y bloquea la implementación independiente si no hay motor reutilizable.
La salida JSON es la evidencia para la matriz F7.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream" / "upstream" / "opencode"
QUERIES = UPSTREAM / "packages" / "cli-rs" / "assets" / "queries"
CORE = UPSTREAM / "packages" / "core" / "src"


def main():
    assert UPSTREAM.is_dir(), "falta el checkout fijado de OpenCode"
    manifest = QUERIES / "manifest.json"
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    assert isinstance(entries, list) and len(entries) >= 36, len(entries)
    assert all(isinstance(entry.get("filetype"), str) for entry in entries)

    queries = sorted(path.name for path in QUERIES.glob("*/*"))
    # Solo hay consultas de resaltado; no hay consultas de símbolos/tags.
    assert queries and set(queries) == {"highlights.scm"}, set(queries)

    # El motor no expone LSP ni un índice de símbolos al agente.
    plugins = CORE / "tool" / "plugin"
    assert not (plugins / "lsp.ts").exists()
    assert not list(plugins.glob("*lsp*"))
    assert not (ROOT / "implementacion" / "repomap").exists(), "indexador independiente no permitido (D24)"

    # Ripgrep sí es nativo y reutilizable como backend de descubrimiento.
    rg = shutil.which("rg")
    ripgrep = CORE / "ripgrep.ts"
    assert ripgrep.is_file()
    assert "RipgrepBinary" in ripgrep.read_text(encoding="utf-8")
    assert rg, "ripgrep no está disponible"

    def runtime(*command):
        try:
            return subprocess.run(command, capture_output=True, timeout=5).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    tree_sitter = runtime("tree-sitter", "--version")
    python_binding = runtime(sys.executable, "-I", "-c", "import tree_sitter")
    parsers = sorted(str(path.relative_to(UPSTREAM)) for path in UPSTREAM.rglob("*.wasm")
                     if "tree-sitter" in path.name.lower())

    report = {
        "fixed_sha": "c0ad18b402eb2827fc1ee71c171b1177b3fc02d1",
        "filetypes": len(entries),
        "highlight_queries": len(queries),
        "symbol_queries": 0,
        "lsp_service": False,
        "ripgrep": bool(rg),
        "tree_sitter_cli": tree_sitter,
        "tree_sitter_python": python_binding,
        "grammar_wasm_found": parsers,
        "duplicate_indexer": False,
        "status": "blocked" if not (tree_sitter or python_binding or parsers) else "ready",
    }
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    assert report["status"] == "blocked", "revisar la matriz: hay motor nativo reutilizable"
    print("PASS fase7 repomap: sin motor Tree-sitter ni LSP reutilizable; indexador independiente bloqueado")


if __name__ == "__main__":
    main()
