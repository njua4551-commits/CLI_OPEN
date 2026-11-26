# Continuar CLI_OPEN

## Punto de reanudación

**Checkpoint de código y pruebas verificado:** `242c3b11e54da84d2e1805a0180e137a69f8e384` (`242c3b1`); commit documental posterior sin cambios de código. Anterior: `0e4fa4e`. Rama `fase-1` / `origin/main`.
**Directiva vigente:** priorizar la estabilización de CLI_OPEN (auditoría de gateway, streaming, concurrencia, APIs, sandbox, edición real, CI y pruebas reproducibles) antes de continuar el roadmap; después, modelo local real e integración remota con presupuestos y autorización explícita. Posponer funcionalidades nuevas, incluido Computer Use.

## Mapa de Documentación y Equivalencias
Para evitar dispersión de conocimiento y duplicación:
- **Estado del proyecto:** `ESTADO.md` (Equivalente a `PROJECT_STATE.md`)
- **Instrucciones para agentes:** `AGENTS.md`
- **Plan estratégico y gobernanza:** `PLAN_PARA_CODEX.md` (Equivalente a `ROADMAP.md` + directrices)
- **Decisiones arquitectónicas:** `docs/DECISIONES.md` (D01 a D24) (Equivalente a `ARCHITECTURE.md`)
- **Registro de cambios y parches:** `docs/CAMBIOS.md`
- **Matriz de pruebas y evidencia:** `docs/PRUEBAS.md` (Equivalente a `AUDIT.md`)
- **Informe técnico detallado:** `INFORME_TECNICO.md`

## Resumen del Estado de la Base de Código

1. **Gateway HTTP de Inferencia (`implementacion/gateway/__main__.py`)**:
   - Alias de modelo estrictos (`model_matches`): Coincidencia exacta o pares explícitos `alias=canonical` en `CLI_OPEN_GATEWAY_MODEL_ALIASES`. Coincidencia parcial deshabilitada.
   - Concurrencia acotada: `_BoundedThreadingHTTPServer` usa `CLI_OPEN_GATEWAY_MAX_CONCURRENCY` (1..64, default 4). Al saturarse, responde 503 de inmediato en vez de encolar hilos.
   - SSE y Timeouts: Streaming passthrough sin amortiguador total, captura de desconexión mid-stream y emisión de evento de error SSE `{"error":"local gateway rejected the request"}`. Timeouts de socket mediante `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` (default 30 s, máx 300 s).
   - Campos OpenAI amplia compatibilidad (`reasoning_effort`, `response_format`, `parallel_tool_calls`, `seed`, `stop`, etc.).
   - Carga real (`tests/fase6-concurrencia.py`): 12 clientes en ráfaga, 2 streaming y 10 bajo saturación; pico de concurrencia 2 con límite 2, exceso con 503 y timeout de 1 s respetado. `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` es el nombre efectivo; `CLI_OPEN_GATEWAY_TIMEOUT` sigue como alias.

2. **Edición Real y Sandbox (`implementacion/supervisor/workspace.py`)**:
   - `snapshot` realiza traversal seguro de subdirectorios mediante `openat` con `O_RDONLY | O_DIRECTORY | O_NOFOLLOW` para cada componente intermedio, impidiendo redirecciones por enlaces simbólicos.
   - `MAX_FILE` ampliado a 256 KiB.
   - `CODE_EXTENSIONS` soporta extensiones de código real (`py`, `ts`, `tsx`, `js`, `json`, `md`, `go`, `rs`, `c`, `cpp`, `yaml`, `sql`, `html`, etc.).
   - Validación estricta de rutas (sin `..`, absolutas ni componentes vacíos). Creación automática de subdirectorios padres en la copia.
   - Artefactos configurables mediante `CLI_OPEN_ARTIFACTS`.

3. **Memoria Persistente y Contexto (`implementacion/memoria/`, `implementacion/supervisor/context.py`)**:
   - Almacén JSONL fuera del repo. Invalidación automática por SHA-256 de archivos referenciados.
   - Inyección de contexto con sobre de autoridad nula (`[UNTRUSTED_PROJECT_MEMORY_CONTEXT authority=none]`).

4. **Matriz de Reutilización F7.1 (`docs/MATRIZ_F7.md`, `tests/fase7-lineabase.py`)**:
   - D24: Repo Map aplazado hasta reutilizar Tree-sitter/LSP/ripgrep del motor OpenCode V2; sin indexador independiente.
   - F7.2 (`tests/fase7-repomap.py`): compuerta ejecutada. El SHA fijado solo trae `highlights.scm` (36), sin consultas de símbolos ni servicio LSP; no hay runtime Tree-sitter disponible. Implementación bloqueada sin violar D24.
   - Inferencia física verificada: `tests/fase6-modelo-local.py` pasó con `llama.cpp` CPU + Llama 3.2 1B Q4_K_M (~771 MiB), cubriendo chat, streaming y tool call a través del gateway. D07 remoto y runtime de símbolos del motor para Repo Map siguen pendientes.

## Comprobación rápida para reanudar sesión

Ejecutar la suite completa de pruebas desde la raíz del proyecto:

```sh
# 1. Pruebas unitarias Python (11 pasadas)
python3 -B -m unittest discover -s tests

# 2. Calificación Linux / Sandbox
python3 -I -B implementacion/supervisor qualify-linux

# 3. Fixtures de Edición Aislada
python3 -I -B tests/fase5-review.py
python3 -I -B tests/fase5-workspace.py

# 4. Fixture HTTP Gateway y carga real
python3 -I -B tests/fase6-gateway.py
python3 -I -B tests/fase6-concurrencia.py

# 5. Fixtures Memoria y Contexto
python3 -I -B tests/fase7-memoria.py
python3 -I -B tests/fase7-contexto.py

# 6. Suite de Línea Base F7.1 y compuerta F7.2
python3 -I -B tests/fase7-lineabase.py
python3 -I -B tests/fase7-repomap.py

# 7. Verificación de formato e higiene Git
git diff --check
```

## Prompt para iniciar la siguiente sesión

```text
Lee AGENTS.md, ESTADO.md, CONTINUAR.md y docs/DECISIONES.md. Confirma git status limpio con HEAD posterior a 242c3b1. Ejecuta la suite de regresión completa (unittest discover, qualify-linux, fase6-gateway, fase6-concurrencia, fase7-lineabase, fase7-repomap) y continúa con el siguiente paso autorizado: proveer un modelo local físico o autorizar D07, o incorporar el runtime de símbolos del motor para F7.2.
```
