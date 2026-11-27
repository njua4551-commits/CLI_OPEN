# F7.1 matrix — Native OpenCode V2 capabilities and F7 proposals

Pinned revision: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`.
Clone path: `upstream/upstream/opencode`. Classify proposals before implementation.

| F7 proposal | Classification | Evidence at the pinned SHA |
|---|---|---|
| Incremental Repo Map with Tree-sitter or symbol graphs | APLAZADA (verified blocker) | `packages/cli-rs/assets/queries/manifest.json` contains Tree-sitter highlighting grammars. `packages/core/src/tool/plugin/grep.ts` (`Ripgrep`) and `packages/core/src/ripgrep.ts` cover text search. The agent has no exposed symbol index or LSP service (`packages/core/src/tool/plugin/` contains no `lsp`). `tests/fase7-repomap.py` found 36 `highlights.scm` files, zero symbol queries, and no Tree-sitter runtime or grammar `.wasm` files. |
| On-demand dependency research | EXTENSIBLE | `packages/core/src/tool/plugin/subagent.ts`, `packages/core/src/tool/plugin/session-search.ts`, and `packages/core/src/tool/plugin/mcp.ts`. |
| Dynamic context token budget | PARCIAL | `implementacion/memoria/__main__.py` (`context`, `tokens`) implements a bounded envelope. Session budget integration is pending. |
| Native Code Mode and `execute` | EXISTENTE | `packages/core/src/codemode/tool.ts` (`name = "execute"`). |
| Dynamic selective tool discovery | EXTENSIBLE | `packages/core/src/tool/search.ts` and `Tool.Service.transform` (see AGENTS in `packages/core/src/tool`). |
| Deterministic log and output filtering | PARCIAL | At baseline, `implementacion` had no deduplication. The gateway (`implementacion/gateway/__main__.py`) already bounded request and response bodies. |
| Local caching and invalidation | EXISTENTE | `packages/core/src/repository-cache.ts` and `packages/core/src/shared-cache.ts`. Project memory lives in `implementacion/memoria/`. |
| Adaptive model routing | EXTENSIBLE | `packages/core/src/model-resolver.ts`, `packages/core/src/variant.ts`, and `packages/core/src/provider.ts`. |
| OpenAI-compatible endpoints | EXISTENTE | `implementacion/gateway/__main__.py` and `tests/fase6-gateway.py`. |
| Shared task budgets | PARCIAL | `usage-limits.ts` and `implementacion/gateway/__main__.py` supply fixed limits. Unified budgeting is pending. |
| Evidence-guided self-correction | AUSENTE | No project module. Reuse `packages/core/src/session/compaction.ts` and `packages/core/src/model-retry.ts`. |
| Automated language-specific validation | AUSENTE | No project implementation. Reuse `packages/core/src/formatter.ts` and `packages/core/src/vcs.ts`. |
| Subagent and worktree coordination | EXISTENTE | `packages/core/src/tool/plugin/subagent.ts` and `packages/core/src/worktree.ts`. |
| Transactional review and rollback | PARCIAL | `implementacion/supervisor/workspace*.py` and `workspace_git.py`. Native worktree integration is pending. |
| Reproducible skills, commands, and workflows | EXISTENTE | `packages/core/src/skill.ts` and `packages/core/src/command.ts`. |
| Budget-governed headless execution | EXTENSIBLE | `packages/core/src/automation.ts` and `packages/core/src/job.ts`. |
| Pair Device and web UI | EXISTENTE | `packages/core/src/app.ts` and `packages/core/src/session/*`. |
| Cancellable asynchronous tasks | EXISTENTE | `packages/core/src/session/background.ts` and `packages/core/src/persistent-pty.ts`. |
| Scheduled read-only diagnostics | EXISTENTE | `implementacion/broker/__main__.py` and `implementacion/supervisor/qualify-linux`. |
| TUI performance within the existing framework | EXISTENTE | Reuse the official framework in `packages/tui`. |

## Decision

Repo Map requires a lightweight adapter that reuses the pinned engine's Tree-sitter grammars and LSP or ripgrep capabilities. A later decision may classify Repo Map as `AUSENTE` with supporting evidence. F7.2 advances through the baseline and audit until that gate is met. On 2026-11-25, `tests/fase7-repomap.py` found no Tree-sitter runtime or LSP in the environment. The gate blocks a standalone indexer and prohibits `implementacion/repomap/`.
