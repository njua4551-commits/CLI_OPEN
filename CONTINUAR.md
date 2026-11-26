# Continuar CLI_OPEN

## Punto de reanudación

**Checkpoint verificado:** `26aea308fcf6dae2e3deeb4f3b4d22170e394a14` (`26aea30`). Rama `fase-1` / `origin/main`.
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
   - Concurrencia acotada: `_BoundedThreadingHTTPServer` usa `CLI_OPEN_GATEWAY_MAX_CONCURRENCY` (1..64, default 4).
   - SSE y Timeouts: Streaming passthrough sin amortiguador total, captura de desconexión mid-stream y emisión de evento de error SSE `{"error":"local gateway rejected the request"}`. Timeouts de socket mediante `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` (default 30 s, máx 300 s).
   - Campos OpenAI amplia compatibilidad (`reasoning_effort`, `response_format`, `parallel_tool_calls`, `seed`, `stop`, etc.).

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

# 4. Fixture HTTP Gateway
python3 -I -B tests/fase6-gateway.py

# 5. Fixtures Memoria y Contexto
python3 -I -B tests/fase7-memoria.py
python3 -I -B tests/fase7-contexto.py

# 6. Suite de Línea Base F7.1
python3 -I -B tests/fase7-lineabase.py

# 7. Verificación de formato e higiene Git
git diff --check
```

## Prompt para iniciar la siguiente sesión

```text
Lee AGENTS.md, ESTADO.md, CONTINUAR.md y docs/DECISIONES.md. Confirma git status en el commit 26aea30. Ejecuta la suite de regresión completa (unittest discover, qualify-linux, fase6-gateway, fase7-lineabase) y continúa con la verificación de estabilización o el siguiente paso autorizado según las reglas del proyecto.
```