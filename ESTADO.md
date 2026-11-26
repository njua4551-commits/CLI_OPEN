# Estado del proyecto

**Directiva vigente:** estabilizar CLI_OPEN antes de continuar el roadmap (gateway, streaming, concurrencia, APIs, sandbox, edición real, CI, pruebas reproducibles); luego modelo local real e integración remota con presupuestos y autorización explícita. Texto completo en `AGENTS.md`. Posponer funcionalidades nuevas, incluido Computer Use.

Checkpoint verificado: `26aea308fcf6dae2e3deeb4f3b4d22170e394a14` (`26aea30`). Rama `fase-1` / `origin/main`.

## Equivalencia de Documentación Principal
- **PROJECT_STATE.md** → `ESTADO.md` (Estado actual, SHAs, módulos cerrados y activos).
- **ARCHITECTURE.md** → `INFORME_TECNICO.md` y `docs/DECISIONES.md` (Arquitectura, decisiones D01–D24, supervisión).
- **ROADMAP.md** → `PLAN_PARA_CODEX.md` (Roadmap v3.0, fases F0–F9, matriz F7).
- **AUDIT.md** → `docs/CAMBIOS.md`, `docs/PRUEBAS.md` e `INFORME_TECNICO.md` (Auditoría, parches, cobertura).

## Estado por Fases y Módulos

### 1. Fases 0 a 5 (Cerradas)
- Entorno de calificación: CachyOS Linux x86_64.
- Base: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` (núcleo intacto).
- Supervisor P0 (`implementacion/supervisor/`): Perfil PLAN, Broker DIAG (`implementacion/broker/`), calificado con Bubblewrap Linux (`qualify-linux`).
- Edición segura (`workspace.py`): Edición aislada en copia con validación `snapshot` de componentes de ruta usando `openat` (`O_NOFOLLOW` / `O_DIRECTORY`), soporte para subdirectorios y extensiones de código real (`MAX_FILE` 256 KiB), publicación Git transaccional.

### 2. Fase 6 — Gateway Inferencia Local (Estabilizado & Verificado)
- Gateway local (`implementacion/gateway/__main__.py`):
  - Concurrencia acotada con `_BoundedThreadingHTTPServer` (`CLI_OPEN_GATEWAY_MAX_CONCURRENCY`).
  - Coincidencia estricta de modelos: `model_matches` requiere ID exacto o par explícito autorizado (`alias=canonical`). Sin coincidencia por prefijo.
  - Streaming SSE (`complete_streaming`): passthrough con validación por línea, timeouts por socket/entorno (`CLI_OPEN_GATEWAY_TIMEOUT_SECONDS`), y retransmisión de eventos de error SSE con cierre de conexión.
  - Compatibilidad ampliada de API OpenAI (`frequency_penalty`, `presence_penalty`, `seed`, `stop`, `parallel_tool_calls`, `reasoning_effort`, `response_format`, etc.).
  - Fixture HTTP y CLI en loopback pasados (`tests/fase6-gateway.py`, `tests/fase6-cli-gateway.ts`).

### 3. Fase 7 — Memoria Persistente y Contexto (En Curso / Módulos 1 y 2 Cerrados)
- Memoria por proyecto (`implementacion/memoria/`): JSONL fuera del repo, invalidación automática por SHA-256 de archivos referenciados, ranking por presupuesto de tokens (`tests/fase7-memoria.py`).
- Contexto no confiable (`implementacion/supervisor/context.py`): Sobre `authority: none` inyectado determinísticamente. Demostrado sin elevación de privilegios en loopback CLI (`tests/fase7-contexto-loopback.ts`).
- F7.1 Auditoría & Línea Base: Matriz de reutilización (`docs/MATRIZ_F7.md`) y suite determinista (`tests/fase7-lineabase.py`). D24: Repo Map aplazado hasta reutilizar Tree-sitter/LSP/ripgrep del motor OpenCode; sin indexador Python independiente.

## Clasificación de Funcionalidades (Verificadas vs Pendientes)

### Verificadas en Entorno Real/Sintético (Pasan Tests Reproducibles)
1. Supervisor de permisos, broker DIAG MCP y calificador Bubblewrap Linux.
2. Edición aislada de archivos reales con prevención de path traversal en subdirectorios anidados.
3. Gateway OpenAI-compatible con concurrencia acotada, streaming SSE, coincidencia estricta de alias y límites configurables.
4. Memoria persistente JSONL con invalidación por hash e inyección de contexto con autoridad nula.
5. Regresión automatizada completa (11 unittest, qualify-linux, review, workspace, gateway, memoria, contexto, lineabase).

### Pendientes de Validación Física Real (Requieren Entorno / Hardware / Autorización)
1. Inferencia con modelo físico local (Ollama / vLLM / llama.cpp local activo).
2. Presupuesto y autorización para integración remota externa (D07 aplazado).
3. Prueba de carga de concurrencia límite con clientes HTTP masivos concurrentes reales.
4. Adaptación Repo Map (F7.2) reutilizando indexadores nativos de OpenCode (D24).

## Reanudar el trabajo
1. Leer `AGENTS.md`, `CONTINUAR.md`, `ESTADO.md` y `docs/DECISIONES.md`.
2. Verificar `git status` (debe estar limpio en el commit `26aea30`).
3. Ejecutar las pruebas de regresión:
   ```sh
   python3 -B -m unittest discover -s tests
   python3 -I -B implementacion/supervisor qualify-linux
   python3 -I -B tests/fase6-gateway.py
   python3 -I -B tests/fase7-lineabase.py
   git diff --check
   ```
4. Consultar `CONTINUAR.md` para las siguientes acciones autorizadas de la directiva de estabilización.
