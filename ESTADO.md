# Estado del proyecto

**Directiva vigente:** estabilizar CLI_OPEN antes de continuar el roadmap (gateway, streaming, concurrencia, APIs, sandbox, edición real, CI, pruebas reproducibles); luego modelo local real e integración remota con presupuestos y autorización explícita. Texto completo en `AGENTS.md`. Posponer funcionalidades nuevas, incluido Computer Use.

Referencia pública: `dfcdd822b358b96f19be2d64c0ad1b61d1404f6a`.

Checkpoint técnico de la prueba HTTP física: `5335b70c2bece3a3d8c0256358e1d16e19c88350` (`5335b70`). Anterior: `242c3b1`. Rama `fase-1` / `origin/main`.

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
  - Concurrencia acotada con `_BoundedThreadingHTTPServer` (`CLI_OPEN_GATEWAY_MAX_CONCURRENCY`). Al saturarse, el exceso se rechaza de inmediato con HTTP 503 sin crear hilos en cola.
  - Coincidencia estricta de modelos: `model_matches` requiere ID exacto o par explícito autorizado (`alias=canonical`). Sin coincidencia por prefijo.
  - Streaming SSE (`complete_streaming`): passthrough con validación por línea, timeouts por socket/entorno (`CLI_OPEN_GATEWAY_TIMEOUT_SECONDS`), y retransmisión de eventos de error SSE con cierre de conexión.
  - Compatibilidad ampliada de API OpenAI (`frequency_penalty`, `presence_penalty`, `seed`, `stop`, `parallel_tool_calls`, `reasoning_effort`, `response_format`, etc.).
  - Fixture HTTP y CLI en loopback pasados (`tests/fase6-gateway.py`, `tests/fase6-cli-gateway.ts`).
  - Carga real con `http.client`: 12 clientes en ráfaga, 2 en streaming y 10 bajo saturación; límite 2 efectivo (pico medido 2), exceso rechazado con 503 y timeout de entorno aplicado a 1 s (`tests/fase6-concurrencia.py`). Timeout acepta `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` (nombre documentado) y el alias legado `CLI_OPEN_GATEWAY_TIMEOUT`.

### 3. Fase 7 — Memoria Persistente y Contexto (En Curso / Módulos 1 y 2 Cerrados)
- Memoria por proyecto (`implementacion/memoria/`): JSONL fuera del repo, invalidación automática por SHA-256 de archivos referenciados, ranking por presupuesto de tokens (`tests/fase7-memoria.py`).
- Contexto no confiable (`implementacion/supervisor/context.py`): Sobre `authority: none` inyectado determinísticamente. Demostrado sin elevación de privilegios en loopback CLI (`tests/fase7-contexto-loopback.ts`).
- F7.1 Auditoría & Línea Base: Matriz de reutilización (`docs/MATRIZ_F7.md`) y suite determinista (`tests/fase7-lineabase.py`). D24: Repo Map aplazado hasta reutilizar Tree-sitter/LSP/ripgrep del motor OpenCode; sin indexador Python independiente.
- F7.2 Compuerta de reutilización: `tests/fase7-repomap.py` verifica en el SHA fijado 36 gramáticas limitadas a `highlights.scm`, ausencia de consultas de símbolos, ausencia de servicio LSP y disponibilidad de ripgrep. Sin runtime Tree-sitter (CLI ni binding Python) ni gramáticas `.wasm`, el Repo Map permanece bloqueado; no se creó `implementacion/repomap/`.

## Clasificación de Funcionalidades (Verificadas vs Pendientes)

### Verificadas en Entorno Real/Sintético (Pasan Tests Reproducibles)
1. Supervisor de permisos, broker DIAG MCP y calificador Bubblewrap Linux.
2. Edición aislada de archivos reales con prevención de path traversal en subdirectorios anidados.
3. Gateway OpenAI-compatible con concurrencia acotada, streaming SSE, coincidencia estricta de alias y límites configurables.
4. Memoria persistente JSONL con invalidación por hash e inyección de contexto con autoridad nula.
5. Concurrencia del gateway con clientes HTTP reales (12 + 8 hilos), límite efectivo y timeout configurable.
6. Regresión automatizada completa (11 unittest, qualify-linux, review, workspace, gateway, concurrencia, memoria, contexto, lineabase, compuerta repomap).

### Pendientes de Validación Física Real (Requieren Entorno / Hardware / Autorización)
1. Inferencia con modelo físico local: **verificada** en CPU. `llama.cpp` `b12753` + Llama 3.2 1B Instruct Q4_K_M (~771 MiB), aislados en `/tmp/opencode`; `tests/fase6-modelo-local.py` pasó chat, streaming SSE y tool call real a través del gateway. Usa loopback y CPU. Verificar primero si los artefactos temporales aún existen antes de considerar otra descarga.
2. Presupuesto y autorización para integración remota externa (D07): **bloqueado**. Requiere autorización explícita nueva y credencial/entorno remoto; no se habilitó ninguna ruta remota.
3. Adaptación Repo Map (F7.2): **bloqueado con evidencia ejecutada** (`tests/fase7-repomap.py`). Reutilizar Tree-sitter/LSP no es posible en este entorno y crear un indexador independiente viola D24; siguiente paso: incorporar el runtime/consultas de símbolos del motor o clasificar `AUSENTE` con aprobación.

## Reanudar el trabajo
1. Leer `AGENTS.md`, `CONTINUAR.md`, `ESTADO.md` y `docs/DECISIONES.md`.
2. Verificar `git status` y contrastar HEAD con la referencia pública.
3. Ejecutar las pruebas de regresión:
   ```sh
   python3 -B -m unittest discover -s tests
   python3 -I -B implementacion/supervisor qualify-linux
   python3 -I -B tests/fase6-gateway.py
   python3 -I -B tests/fase6-concurrencia.py
   python3 -I -B tests/fase7-lineabase.py
   python3 -I -B tests/fase7-repomap.py
   git diff --check
   ```
4. Consultar `CONTINUAR.md` para las siguientes acciones autorizadas de la directiva de estabilización.

## Sesión física local con OpenCode

La lectura permitida y el rechazo de una lectura fuera de la regla pasaron con OpenCode, gateway y llama.cpp en el mismo loopback privado de Bubblewrap. La respuesta final quedó vacía tras ejecutar la herramienta. La sesión completa sigue abierta. La evidencia y la cobertura están en [PRUEBAS.md](docs/PRUEBAS.md).

## Lectura web y documentos

Auditoría nativa y línea base HTML aislada ejecutadas. Filtro HTML opt-in implementado y calificado con fixtures. Recuperación externa y conversión adicional aplazadas. Véanse [decisiones](docs/DECISIONES.md) y [mediciones](docs/PRUEBAS.md).

## Comparación con API real

**BLOCKED.** El catálogo público mostró un endpoint gratuito de Gemma con herramientas. La cuenta y cuota de OpenRouter no pudieron verificarse. La integración OpenAI activa en OpenCode carece de evidencia de acceso autorizado a una API de costo cero para este fixture. D07 sigue pendiente de consentimiento específico y de una ruta supervisada calificada con presupuesto compartido. A–D remotas sin ejecutar. El diagnóstico comparativo con Llama 3.2 1B sigue **INCONCLUSIVE**. Véase [continuidad](CONTINUAR.md).


**Revalidación D07:** destino, límites por solicitud y aislamiento local pasaron con proveedor simulado. **FAIL** cancelación durante SSE inactivo. **BLOCKED** autenticación del canal, presupuesto compartido, cuota OpenRouter y ejecución remota. Bubblewrap y el gateway local conservan su configuración.

## OpenCode Console gratuito

**PASS** consulta del catálogo oficial y regresión de cancelación con upstream SSE inactivo. **BLOCKED** sesión remota de CLI_OPEN: los modelos chat gratuitos de Console se restringen a OpenCode y el canal actual solo admite loopback. El acceso efectivo y la cuota de la sesión no se acreditaron. Véase [PRUEBAS.md](docs/PRUEBAS.md).

## Reproducibilidad y CI

Runner por perfiles portable, Linux y OpenCode precompilado. GitHub Actions ejecuta portable y Linux en jobs separados. En el perfil OpenCode se verifican los hashes de los binarios calificados antes de ejecutarlos. La construcción desde cero y la integración de artefactos en CI siguen pendientes.

## Contexto selectivo y Repo Map

El supervisor comprueba el presupuesto del sobre de memoria en la incorporación al prompt. Esto cubre memoria. El presupuesto compartido con código, web y salidas de herramientas sigue pendiente. Repo Map F7.2 permanece **BLOCKED**. El stash conserva un indexador separado con AST y expresiones regulares, incompatible con D24. No se aplicó al checkout.

El perfil OpenCode pasó con los artefactos existentes. Se verificó reanudar una sesión en un proceso nuevo después de una lectura completada. F7.3 conserva el filtro opcional. La selección por secciones queda aplazada hasta disponer de una consulta explícita. D07 sigue bloqueado.

## Diagnóstico de GitHub Actions

La primera ejecución en `f74ab48` dio **PASS** en portable y **FAIL** en Linux al configurar el loopback de Bubblewrap. El ajuste local prepara el perfil de AppArmor empaquetado por Ubuntu y conserva las pruebas estrictas. CI remota de la corrección **PENDIENTE DE VALIDACIÓN**.

`810af0c` llegó a ejecutar Bubblewrap en CI y superó el bloqueo del loopback. El error siguiente de arranque ELF se reprodujo con un layout de bibliotecas separado. El ajuste de F4 está preparado para recalificación remota.

## F7.2 · Repo Map parcial

Implementado y probado el descubrimiento bajo demanda de rutas con ripgrep y un presupuesto común con memoria. Sigue **BLOCKED** la extracción de símbolos y relaciones estructurales con D24. Las rutas funcionan de forma independiente del lenguaje. No se acreditó extracción de símbolos para Python, JS, TS, Java ni C#. El flujo de ampliación usa grep y read nativos. D07 sigue bloqueado.

F7.2 cuenta con el preset optativo `contexto-selectivo` y un fixture de integración que verifica ruta → coincidencia con línea → página → respuesta, bajo Bubblewrap. La selección estructural y el presupuesto global de inferencia siguen pendientes. D24 y D07 conservan sus puertas.

## D07 · ChatGPT y admisión local

Autenticación OAuth nativa **DISPONIBLE** en el motor fijado. Acceso de cuenta, catálogo efectivo y pruebas remotas **BLOCKED** para CLI_OPEN. El perfil local de tarea pasa autenticación y reserva acumulada por listener contra un proveedor simulado. El canal supervisado hasta ChatGPT aún no está calificado.

El perfil autenticado tiene plazo de proceso, retención de reservas ante fallos y terminación SSE estricta. Se calificó cancelación del cliente y expiración con upstream simulado. OAuth real, contabilización de tokens del proveedor y recuperación de una reserva tras reinicio siguen pendientes.

El perfil loopback D07 puede usar una base SQLite privada por tarea. Se calificó reinicio, rechazo de estado corrupto, plazo persistido y uso reportado separado del presupuesto. Sigue **BLOCKED** la inferencia real de ChatGPT con supervisión.
