# Matriz F7.1 — Capacidades nativas de OpenCode V2 frente a propuestas F7

Revisión fijada: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`.
Ruta del clon: `upstream/upstream/opencode`. Clasificación obligatoria antes de implementar.

| Propuesta F7 | Clasificación | Evidencia en el SHA fijado |
|---|---|---|
| Repo Map incremental con Tree-sitter / grafos de símbolos | APLAZADA (bloqueo verificado) | `packages/cli-rs/assets/queries/manifest.json` contiene gramáticas Tree-sitter para resaltado; `packages/core/src/tool/plugin/grep.ts` (`Ripgrep`) y `packages/core/src/ripgrep.ts` cubren búsqueda textual. No hay índice de símbolos ni servicio LSP expuesto al agente (`packages/core/src/tool/plugin/` no incluye `lsp`). `tests/fase7-repomap.py`: 36 `highlights.scm`, 0 consultas de símbolos, sin runtime Tree-sitter ni `.wasm` de gramáticas. |
| Investigación profunda de dependencias bajo demanda | EXTENSIBLE | `packages/core/src/tool/plugin/subagent.ts`, `packages/core/src/tool/plugin/session-search.ts` y `packages/core/src/tool/plugin/mcp.ts`. |
| Presupuesto dinámico de tokens para contexto | PARCIAL | `implementacion/memoria/__main__.py` (`context`, `tokens`) implementa el sobre acotado; falta adaptación al presupuesto de la sesión. |
| Code Mode / `execute` nativo | EXISTENTE | `packages/core/src/codemode/tool.ts` (`name = "execute"`). |
| Descubrimiento dinámico y selectivo de herramientas | EXTENSIBLE | `packages/core/src/tool/search.ts` y `Tool.Service.transform` (AGENTS de `packages/core/src/tool`). |
| Filtrado determinista de logs y salidas | PARCIAL | `implementacion` no implementa deduplicación; el gateway (`implementacion/gateway/__main__.py`) ya acota cuerpo y respuesta. |
| Caché e invalidación local | EXISTENTE | `packages/core/src/repository-cache.ts`, `packages/core/src/shared-cache.ts`; memoria propia en `implementacion/memoria/`. |
| Enrutamiento adaptativo de modelos | EXTENSIBLE | `packages/core/src/model-resolver.ts`, `packages/core/src/variant.ts`, `packages/core/src/provider.ts`. |
| Compatibilidad con endpoints compatibles con OpenAI | EXISTENTE | `implementacion/gateway/__main__.py` y `tests/fase6-gateway.py`. |
| Presupuestos compartidos por tarea | PARCIAL | `usage-limits.ts` y `implementacion/gateway/__main__.py` (límites fijos); falta unificación. |
| Autocorrección guiada por evidencia | AUSENTE | No hay módulo propio; reutilizar `packages/core/src/session/compaction.ts` y `packages/core/src/model-retry.ts`. |
| Validación automática según lenguaje | AUSENTE | Sin implementación propia; reutilizar `packages/core/src/formatter.ts` y `packages/core/src/vcs.ts`. |
| Coordinación de subagentes y worktrees | EXISTENTE | `packages/core/src/tool/plugin/subagent.ts`, `packages/core/src/worktree.ts`. |
| Revisión transaccional y reversión | PARCIAL | `implementacion/supervisor/workspace*.py` y `workspace_git.py`; falta integración con worktrees nativos. |
| Skills, comandos y flujos reproducibles | EXISTENTE | `packages/core/src/skill.ts`, `packages/core/src/command.ts`. |
| Ejecución headless gobernada por presupuestos | EXTENSIBLE | `packages/core/src/automation.ts` y `packages/core/src/job.ts`. |
| Pair Device y Web UI | EXISTENTE | `packages/core/src/app.ts`, `packages/core/src/session/*`. |
| Tareas asíncronas con cancelación | EXISTENTE | `packages/core/src/session/background.ts`, `packages/core/src/persistent-pty.ts`. |
| Diagnósticos programados de solo lectura | EXISTENTE | `implementacion/broker/__main__.py` y `implementacion/supervisor/qualify-linux`. |
| Rendimiento de TUI sin reemplazar el framework | EXISTENTE | `packages/tui` (framework oficial); no duplicar. |

## Decisión derivada

Repo Map no se implementa como indexador independiente. Debe reutilizar las gramáticas Tree-sitter y las capacidades LSP/ripgrep del motor fijado mediante un adaptador ligero, o clasificarse `AUSENTE` con justificación en una decisión posterior. Hasta entonces, F7.2 avanza únicamente con la línea base y la auditoría. Verificación 2026-11-25 (`tests/fase7-repomap.py`): el entorno no dispone de runtime Tree-sitter ni LSP; la compuerta bloquea la implementación y prohíbe `implementacion/repomap/`.
