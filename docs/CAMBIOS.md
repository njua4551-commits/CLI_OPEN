# Cambios

## 2026-11-26 · Filtro HTML opcional

- Se añadió un plugin del hook nativo de OpenCode para comprimir repeticiones adyacentes en Markdown procedente de HTML. Se calificó con benchmark determinista y webfetch real sobre loopback simulado en Bubblewrap. D07 continúa aplazado.

## 2026-11-26 · Cancelación SSE y catálogo OpenCode Console

- El gateway cierra el upstream SSE al detectar que el cliente se desconectó, incluso si el proveedor está inactivo. La regresión sintética verifica el cierre antes del timeout.
- Se comprobó el catálogo oficial y se documentó la restricción de acceso gratuito. Sin inferencia remota.

## 2026-11-26 · Calificación simulada de D07

- Se verificó la disponibilidad local de OpenRouter por metadatos y se añadió un diagnóstico reproducible de cancelación durante SSE inactivo. Sin modificaciones al gateway ni a Bubblewrap.

## 2026-11-26 · Prevalidación comparativa con API

- Se verificó el catálogo público, se documentó un perfil de prueba con Gemma y se registraron los bloqueos de credencial, consentimiento y transporte D07. Sin cambios de ejecución ni solicitudes de inferencia.

## 2026-11-26 · Continuidad de inferencia local y lectura web

- Se añadió un fixture físico de OpenCode y llama.cpp dentro del Bubblewrap del supervisor. Usa el proveedor y la herramienta de lectura nativos y una regla por archivo.
- Se midió el conversor HTML del tag fijado con seis fixtures sin red y se documentó el posible uso de un hook aprobado. La optimización de producto y la recuperación externa quedan aplazadas.

## 2026-11-26 · Inferencia física local verificada

- `tests/fase6-modelo-local.py`: prueba real CPU-only contra `llama.cpp` `b12753` y Llama 3.2 1B Instruct Q4_K_M (~771 MiB). Pasaron chat, streaming SSE y tool call a través del gateway; sin GPU ni red durante la inferencia.
- `README.md`, `ESTADO.md` y `CONTINUAR.md`: documentan requisitos, descarga temporal y resultado. D07 remoto continúa bloqueado.

## 2026-11-25 · Estabilización · saturación determinista del gateway

- `implementacion/gateway/__main__.py`: el semáforo se adquiere en `process_request` antes de crear el hilo; al superar `CLI_OPEN_GATEWAY_MAX_CONCURRENCY` se responde HTTP 503 JSON (`gateway concurrency limit reached`) y se cierra. Se consume la solicitud antes de cerrar para evitar `BrokenPipe`/RST en clientes con cuerpo. Sin cola ilimitada de hilos.
- `tests/fase6-concurrencia.py`: añade ráfaga de 10 clientes con límite 2 (éxitos 200 y rechazos 503), verifica pico 2, correspondencia solicitud/éxito y recuperación posterior; cubre también 2 streaming y timeout de 1 s.
- Regresión: 11 unittest, `qualify-linux`, `fase5-review`, `fase5-workspace`, `fase6-gateway`, `fase6-concurrencia`, `fase7-memoria`, `fase7-contexto`, `fase7-lineabase`, `fase7-repomap` y `git diff --check`.

## 2026-11-25 · Validación de pendientes reales · gateway y F7.2

- `implementacion/gateway/__main__.py`: `TIMEOUT` acepta `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` (nombre documentado) y conserva `CLI_OPEN_GATEWAY_TIMEOUT` como alias; límites 1–300 s.
- `tests/fase6-concurrencia.py`: carga con clientes HTTP reales (`http.client`) contra el listener; 12 solicitudes y 8 en streaming, límite 2 con pico medido 2, todas las respuestas completas y timeout de 1 s aplicado.
- `tests/fase7-repomap.py`: compuerta de reutilización F7.2. Verifica 36 gramáticas limitadas a `highlights.scm`, cero consultas de símbolos, ausencia de LSP y ripgrep nativo disponible; sin runtime Tree-sitter el Repo Map queda bloqueado sin crear indexador independiente.
- Validación bloqueada (sin cambios de código): modelo local físico ausente (sin `ollama`/`vllm`/`llama.cpp`, puertos 11434/8000 cerrados, 0 artefactos `*.gguf`/`*.safetensors`); D07 remoto requiere autorización explícita nueva.

## 2026-11-25 · Consolidación documental para traspaso

- `ESTADO.md` y `CONTINUAR.md` reescritos: checkpoint `26aea30`, mapa de equivalencias documentales, estado por fase y clasificación verificado/pendiente.
- `AGENTS.md` añade el mapa documental, el checkpoint verificado y las áreas pendientes de prueba real.
- Sin cambios de código ni de lógica; solo documentación.

## 2026-11-21 · Continuidad y base de la Fase 1

- `ESTADO.md` registra el cierre de Fase 0, el SHA seleccionado y el procedimiento de reanudación.
- `docs/DECISIONES.md`, `docs/CAMBIOS.md` y `docs/PRUEBAS.md` conservan los hitos y su evidencia.
- `.gitignore` excluye el clon, el área temporal de pruebas y los directorios privados del entorno.
- La autorización específica permitió inicializar Git propio en `fase-1`. Se ampliaron las exclusiones a dependencias, archivos de entorno y claves comunes.
- Se configuró `origin` y se publicó `cf7e0f9` en `main`. La copia y Bun se guardaron bajo `.fase1/`, excluida del repositorio.
- Se instalaron las dependencias fijadas únicamente en la copia separada, con scripts de instalación deshabilitados.
- `AGENTS.md` registra la autonomía dentro de cada fase aprobada y las acciones que requieren autorización.
- Se generó la CLI Linux x86_64 en el área excluida `.fase1/`.
- Se registraron las pruebas de servicio, sesión no interactiva y terminación standalone en `docs/PRUEBAS.md`.
- Se publicó `8abba6a` en `origin/main` tras revisar los cinco archivos del checkpoint. Se adaptaron el plan, el informe y los registros al alcance revisado de inferencia de P-1.
- Se registraron los resultados de replay HTTP, MCP sintético, herramientas y resolución de servidor. No había un modelo o runtime de inferencia instalado que retirar.
- El checkpoint revisado `5ec7fa4` se publicó en `origin/main` mediante fast-forward. Se añadió `tests/fase1-loopback.ts` para los ocho casos y el señuelo. El núcleo permanece intacto.
- El checkpoint `d0dee98` se revisó y se publicó en `origin/main` mediante fast-forward.
- Se registró la autenticación correcta y el bloqueo de disponibilidad del modelo fijado.
- Se actualizó el modelo en el plan y el informe, se añadió `tests/fase1-openrouter.py` y se registró el cierre de Fase 1.
- Se añadieron `implementacion/supervisor/__main__.py` y `tests/test_supervisor.py` para el doctor y el perfil PLAN de Fase 2.
- Se añadió `implementacion/broker/__main__.py` con cinco consultas de solo lectura, una entrada DIAG explícita en el supervisor y pruebas de catálogo, rechazo y límites.
- Se adaptó el sobre MCP del broker y se añadió la prueba focalizada de integración CLI con DIAG. Se inició P2 con `tests/fase4-linux.py`.
- Se añadió un recorrido de calificación de OpenCode y el broker en Bubblewrap y una prueba de degradación con Bubblewrap ausente del PATH. [Evidencia](evidencias/FASE4.md)
- Se incorporó `qualify-linux` al supervisor, la prueba inicial de copia y diff en `tests/fase5-workspace.py`, y el registro de la incidencia no bloqueante de inventario MCP.
- Se añadió `review-workspace`, el trabajador aislado y la cobertura de creación, reemplazo, concurrencia, reversión por descarte y diff. [Evidencia](evidencias/FASE5.md)
- Se sustituyó la escritura propia por la herramienta nativa de OpenCode y se añadió la publicación Git de revisiones aprobadas. Se inició el contrato del gateway de Fase 6.
- Se añadió el adaptador de loopback en `implementacion/gateway/__main__.py`, su fixture HTTP en `tests/fase6-gateway.py` y el punto de reanudación en `CONTINUAR.md`.

## 2026-11-21 · Transporte CLI → gateway de Fase 6

- `implementacion/gateway/__main__.py` añade `--listen`: endpoint OpenAI-compatible local que reutiliza el validador y el destino fijo del modo stdin. Acepta `model`, `max_completion_tokens`, `stream_options` y mensajes con `tool_calls`/rol `tool`; limita `max_tokens` a 512, el cuerpo a 128 KiB y la respuesta a 64 KiB, y valida modelo y costo cero también en SSE.
- `tests/fase6-cli-gateway.ts` cubre `CLI → gateway → endpoint de loopback` con llamada a herramienta, sin credenciales reenviadas, costo distinto de cero y endpoint caído sin proveedor alternativo.
- Corrección de la ruta de build: en `v2.3.2` el script es `packages/cli/script/build.ts`, no `script/build.ts` en la raíz.

## 2026-11-21 · Cierre de Fase 6

- Se verificaron de nuevo las diez pruebas unitarias, el fixture HTTP y los tres casos de CLI con gateway.
- Se cerró la Fase 6 para el perfil local sintético y se aplazaron presupuesto remoto, aprobación por contenido y modelo físico local (D07).
- La Fase 7 queda autorizada y sin comenzar.

## 2026-11-21 · Fase 7 · Módulo 1: memoria por proyecto

- `implementacion/memoria/__main__.py`: almacén JSONL por proyecto fuera del repositorio, con bloqueo de escritura, alta acotada, recuperación por términos y presupuesto de tokens, invalidación por hash de archivos referenciados y purga.
- Rechaza secretos evidentes, rutas fuera del proyecto, archivos ausentes y referencias mayores de 1 MiB.
- `tests/fase7-memoria.py` cubre alta, ranking, presupuesto, invalidación automática, purga, aislamiento entre proyectos y rechazos.
- El comando `context` añade una salida selectiva y acotada. La clasificación compartida evita verificar referencias dos veces por consulta.

## 2026-11-22 · Fase 7 · Módulo 2 e integración del Roadmap Consolidado

- Se incorporó el Roadmap Estratégico Consolidado y Definitivo a `PLAN_PARA_CODEX.md` (versión 3.0), `INFORME_TECNICO.md` (sección 18) y `AGENTS.md`, estableciendo el principio "REUTILIZAR ANTES DE EXTENDER", la clasificación previa de 7 estados y la estructuración de subfases F7.1 a F7.8, D07, F8 y F9.
- `implementacion/supervisor/context.py`: valida la estructura y ausencia de credenciales en el sobre de contexto emitido por `memoria context`, exigiendo estrictamente `authority: none`. Encapsula el sobre con delimitadores de aviso de seguridad antes de adjuntarlo al prompt del usuario.
- `implementacion/supervisor/__main__.py` incorpora el comando `inject-context` para integrar el sobre de memoria persistente de forma determinista y segura.
- `tests/test_supervisor.py` amplía la suite unitaria (11 pruebas) validando la encapsulación del sobre y el rechazo inmediato de autoridades no autorizadas.
- `tests/fase1-loopback.ts` añade el caso `context`: verifica que la CLI fijada de OpenCode en loopback recibe el sobre no confiable en sus mensajes de payload, no amplía permisos ni expone herramientas administrativas, rechaza inyecciones adversarias de escritura exterior (`outsideMarker`), completa la lectura segura de `sample.txt` y no envía solicitudes al señuelo (0 solicitudes).
- `tests/fase7-contexto-loopback.ts`: suite dedicada de integración de contexto en loopback con ejecución focalizada.

## 2026-11-23 · Directiva de estabilización

- `AGENTS.md` incorpora al inicio la directiva vigente: estabilizar CLI_OPEN (límites del gateway, streaming, concurrencia, compatibilidad de APIs, conectividad segura del sandbox, edición real de código, CI y pruebas reproducibles) antes de continuar el roadmap; después validar un modelo local real y preparar la integración remota segura con presupuestos y autorización explícita.
- Conserva F0–F7, capacidades originales de OpenCode y protecciones; los límites de seguridad se hacen configurables y verificables. Sin duplicar componentes. Posposición de nuevas funcionalidades, incluido Computer Use.
- `PLAN_PARA_CODEX.md`, `CONTINUAR.md` y `ESTADO.md` referencian la directiva para que prevalezca sobre el orden del roadmap.

## 2026-11-24 · Fase 7 · F7.1: línea base y auditoría

- `docs/MATRIZ_F7.md`: matriz de clasificación de propuestas F7.2–F7.8 frente a OpenCode V2 (SHA fijado), con evidencia por archivo.
- `tests/fase7-lineabase.py`: suite de referencia reproducible (determinismo, presupuesto de bytes, invalidación, rechazo de límites). Pasó en CachyOS x86_64.
- `D24` en `docs/DECISIONES.md`: Repo Map aplazado hasta reutilizar Tree-sitter/LSP/ripgrep del motor fijado; sin indexador independiente.

## 2026-11-24 · Estabilización · streaming en gateway

- `implementacion/gateway/__main__.py`: añadido `complete_streaming` que retransmite la respuesta del endpoint de loopback sin bufferizarla por completo, validando cada evento SSE (modelo, costo cero) y aplicando el mismo límite de tamaño. `--listen` usa passthrough cuando el cliente solicita `stream: true`.
- `tests/fase6-gateway.py` sigue pasando sin cambios.

## 2026-11-24 · Estabilización · concurrencia en gateway

- `implementacion/gateway/__main__.py`: `--listen` usa `ThreadingHTTPServer` con hilos daemon; se eliminó el deadline basado en `SIGALRM` de las rutas compartidas (`complete`, `complete_streaming`) para evitar interferencia entre solicitudes concurrentes, apoyándose en los timeouts de socket ya configurados. El modo stdin mantiene el deadline por ser proceso único.

## 2026-11-24 · Estabilización · compatibilidad de APIs en gateway

- `implementacion/gateway/__main__.py`: ampliado el conjunto de campos OpenAI-compatible reenviados y validados (`frequency_penalty`, `presence_penalty`, `seed`, `stop`, `tool_stream`, `store`, `parallel_tool_calls`, `reasoning_effort`, `response_format`, y `reasoning_content`/`refusal` en mensajes) para no rechazar solicitudes reales del proveedor fijado.

## 2026-11-24 · Estabilización · edición real

- `implementacion/supervisor/workspace.py`: las rutas de artefactos (Bun y binario de OpenCode) pasan a ser configurables mediante `CLI_OPEN_ARTIFACTS` y se valida su existencia antes de montar, con error claro si faltan.

## 2026-11-24 · Cierre de estabilización

- Regresión completa pasada: `unittest discover` (11), `qualify-linux`, `fase5-review`, `fase5-workspace`, `fase6-gateway`, `fase7-memoria`, `fase7-contexto`, `fase7-lineabase`. `git diff --check` limpio.
- Áreas tocadas: gateway (streaming, concurrencia, compatibilidad de APIs) y edición real (artefactos configurables).

## 2026-11-24 · Estabilización · gateway y edición real (segunda pasada)

- Gateway: límites configurables por entorno (`CLI_OPEN_GATEWAY_*`), timeout por defecto 30 s (hasta 300), manejo de errores durante streaming (evento SSE de error y cierre) y compatibilidad de alias de modelos (`model_matches`, env `CLI_OPEN_GATEWAY_MODEL_ALIASES`).
- Edición: `MAX_FILE` subido a 256 KiB, ampliación de extensiones de código y subdirectorios con validación de ruta segura (sin `..`, sin absolutas, sin segmentos vacíos) y creación de directorios padre en la copia.
- Regresión completa pasada y `git diff --check` limpio.

## 2026-11-24 · Auditoría profunda · gateway y edición

- Gateway: `model_matches` corregido para aceptar solo identificadores exactos o alias explícitos (`alias=canonical`); eliminada la coincidencia por prefijo. Concurrencia acotada mediante `_BoundedThreadingHTTPServer` (`CLI_OPEN_GATEWAY_MAX_CONCURRENCY`).
- Edición: `snapshot` valida cada componente intermedio de la ruta mediante `openat` con `O_NOFOLLOW`/`O_DIRECTORY`, impidiendo redirecciones por enlaces simbólicos en subdirectorios.
- Regresión completa pasada y `git diff --check` limpio.

## Suites deterministas y CI

- Runner por perfiles, prueba del plugin HTML con Node sin artefactos de build y workflow de GitHub Actions limitado a permisos de lectura.

## Presupuesto de memoria en el supervisor

- El sobre de contexto se limita a 16 KiB por defecto y admite un presupuesto menor. La selección conserva el orden de recuperación y omite duplicados por identificador o texto.

## Reanudación de sesión

- El fixture de integración verifica que la CLI nativa reabre por ID una sesión persistida y aprovecha la lectura anterior sin ejecutarla de nuevo.

## Preparación de Bubblewrap en GitHub Actions

- El job Linux carga el perfil oficial de AppArmor para Bubblewrap si la restricción de namespaces está activa. Ambos jobs fijan checkout v5.0.1, que usa Node.js 24.

## Montajes de bibliotecas en el fixture F4

- F4 reutiliza el constructor Bubblewrap del supervisor y registra las rutas de Python y su cargador. Elimina la suposición de que `/lib64` corresponde siempre a `/usr/lib`.

## F7.2 · Pistas de ruta con presupuesto de contexto compartido

- Añadido `memoria context --with-paths`. Reutiliza ripgrep para listar rutas, ordena coincidencias léxicas y preserva el sobre de memoria con autoridad nula. El supervisor vuelve a validar las rutas y el presupuesto antes de incorporarlas.

## F7.2 · Recuperación nativa de páginas por coincidencia

- Preset optativo de agente para priorizar `glob`, `grep` literal y `read` acotado. Se añadió al perfil OpenCode un fixture de varios archivos con ruta inexistente, coincidencias ambiguas y una instrucción adversaria sin autoridad.

## D07 · Admisión y reserva acumulada de pruebas locales

- Perfil optativo autenticado para el listener de loopback. Añade reserva atómica de solicitudes, bytes de entrada y máximos de tokens de salida. Los perfiles de producto existentes conservan su interfaz.

## D07 · Plazo global y detección de SSE incompleto

- El listener autenticado vence con código 124 y cierra sus conexiones. Detecta streams incompletos, conserva reservas al cancelar y deja sólo el tipo de error en logs del handler.
