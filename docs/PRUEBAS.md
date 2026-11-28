# Pruebas y evidencia

| Hito | Comprobación | Resultado |
|---|---|---|
| Fase 0 | Git, licencia, manifiesto, lockfiles, guía de contribución y entorno | Inventario completado. Véase [ESTADO.md](../ESTADO.md). |
| Fijación de P-1 | `git rev-parse 'v2.3.2^{commit}'` y commit asociado al release oficial | Coinciden en `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. |
| Revisión estática | Manifiesto raíz, `fix-node-pty.ts`, acción `setup-bun`, workflow `check-test.yml` y build de CLI en el tag | CI instala con lockfile congelado. El postinstall ajusta el bit de ejecución de helpers locales de node-pty. El manifiesto confía en esbuild, node-pty, protobufjs y electron. El build limpia su salida y puede descargar activos de Bun incluso con `--skip-install`. |
| Prerrequisitos | Consulta del PATH y `git init -b fase-1` | Bun y Ollama no resuelven en PATH. Git devolvió `.git/hooks/: Read-only file system`. La inicialización y el checkpoint quedaron bloqueados. |
| Integridad del clon | `git --no-optional-locks status --short --branch` y `git rev-parse HEAD` | Árbol limpio en `dev`, SHA `73a0eae88de47f10068a0f9dc7a743638fa3d830`. |
| Git propio y remoto | `git init -b fase-1` con autorización específica y `git ls-remote --symref` | Repositorio propio inicializado. CLI_OPEN respondió correctamente y no devolvió ramas ni etiquetas. |
| Publicación | Revisión de los diez archivos preparados, búsqueda de patrones de secretos y datos personales, `git check-ignore` y `git push origin HEAD:refs/heads/main` | Exclusiones verificadas. Sin coincidencias en la búsqueda. Push inicial correcto. |
| Copia y Bun | `git archive` en el SHA fijado, comparación de `bun.lock`, SHA-256 del activo oficial y `bun --version` | Versión de la copia 2.3.2. Blob del lockfile `0ea44ccaa17fcfccbc057839ae8aa8fe31e38af3`. SHA-256 de Bun `e0446eb55995772eb9894bebae9a6be368d985a8b9271ee124486f9946eedd76`. Bun 1.4.4. |
| Dependencias | `bun install --frozen-lockfile --ignore-scripts` | El primer intento falló por DNS. El reintento autorizado dentro de Bubblewrap instaló 1594 paquetes. El lockfile conservó su hash. Quedaron advertencias de parches y paquetes de otras plataformas. |
| Build de CLI, intento 1 | `bun run script/build.ts --single --skip-install`, tiempo máximo de 120 s | Código 124. Vite transformó 5376 módulos y llegó al cálculo de tamaños gzip. El reintento fija `OPENCODE_VERSION=2.3.2` y usa el límite de CI de 600 s. |
| CLI desde fuentes | `bun run --cwd packages/cli src/index.ts --help` y `--version` | La ayuda muestra `--standalone`, `--server`, `mcp` y `serve`. La CLI desde fuentes reportó `opencode vlocal`. |
| Build de CLI, intento 2 | `OPENCODE_VERSION=2.3.2 bun run script/build.ts --single --skip-install` con límite de 600 s | Código 0. Artefacto `dist/cli-linux-x64/bin/opencode`, SHA-256 `2a04919c134da80f95ffb8b2e3661d1c9aa6ca6c31c775a7efad6b497e6b6d24`. `--version` reporta `opencode v2.3.2`. La ayuda confirma ambos flags de conexión. |
| Servicio compilado | `bun run script/service-smoke.ts` | La sesión base bloqueó `listen` con EPERM. En Bubblewrap con red privada, código 0. Validó arranque, autenticación, OpenAPI, UI, inicio del canal MCP WebSocket, detección de plugin, elección de servicio y parada. |
| Sesión no interactiva | `bun test test/standalone.test.ts test/run/noninteractive.test.ts` | 23 pruebas no interactivas aprobadas, incluidas cancelación simulada y solicitudes MCP. El caso standalone agotó los 5 s del runner en Bubblewrap. |
| Terminación standalone | `bun test --timeout 30000 test/standalone.test.ts` en Bubblewrap sin red externa | Sin versión explícita faltó la señal de arranque. Con `OPENCODE_VERSION=2.3.2` pasó. Verificó HTTP 200 en loopback y que el servidor termina al matar a su proceso propietario. |

## Pruebas tras adaptar la inferencia de P-1

Ejecutadas sobre el SHA fijado con Bun 1.4.4, `OPENCODE_VERSION=2.3.2` y Bubblewrap sin red externa.

| Suite | Resultado |
|---|---|
| Core: `session-runner.test.ts`, `mcp.test.ts`, `session-error.test.ts` | 379 pasaron. Incluye llamadas múltiples, interrupción, recuperación de errores, descubrimiento e invocación MCP sintética y terminación de descendientes del transporte MCP. |
| Core: `session-runner-recorded.test.ts`, `tool-read.test.ts`, `tool-output.test.ts` | 57 pasaron. Incluye replay del transporte HTTP, rechazo de límite inválido, lectura acotada y límites de salida. |
| CLI: `server-connection.test.ts` | 4 pasaron. Incluye servidor simulado registrado y selección explícita del endpoint. Falta probar un proceso standalone con el señuelo activo en la misma ejecución. |
| OpenRouter | Sin solicitudes. `OPENROUTER_API_KEY` ausente. La credencial comunicada corresponde a otro proveedor y no se guardó. |
| Preparación de inferencia física local | Sin binarios, pesos ni directorio de inferencia local detectado. Se conservaron Bun y el build de OpenCode para las pruebas. |

## CLI con loopback

Pasó la prueba [fase1-loopback.ts](../tests/fase1-loopback.ts) usando el artefacto Linux fijado y Bun 1.4.4 en Bubblewrap, con loopback privado y sin red externa. El sandbox de la sesión rechazó `listen` con EPERM. Se reutilizaron las 440 pruebas ya registradas.

| Caso | Aserción aprobada |
|---|---|
| Argumento inválido | `read` rechaza el límite cero. |
| Ruta Windows escapada | El resultado conserva los separadores de la ruta sintética. Se ejecutó en Linux. |
| Ruta Unicode | Lee el archivo sintético y devuelve su marcador. |
| Lectura acotada | Devuelve solo la línea solicitada. |
| Respuesta extensa | Devuelve contenido inicial y excluye el marcador final fuera del límite. |
| Llamada múltiple | Recibe dos resultados con los marcadores correspondientes. |
| Cancelación | SIGINT interrumpe la CLI y cierra el stream del proveedor. |
| Fallo recuperable | Un 429 sintético seguido de una respuesta correcta produce dos solicitudes de sesión y un resultado válido. |
| Servidor señuelo | El servicio HTTP señuelo permanece activo y registrado durante las ejecuciones `--standalone`; recibe cero solicitudes. |

Para reproducir, ejecutar `bun tests/fase1-loopback.ts RUTA_AL_BINARIO` en un entorno con loopback privado permitido. La prueba usa un directorio temporal, registra el señuelo en XDG y monta el binario como solo lectura en la ejecución de referencia.

## Pendiente

Tras reiniciar la sesión, `OPENROUTER_API_KEY` estuvo disponible y `GET /api/v1/key` devolvió HTTP 200. La consulta de endpoints para `openai/gpt-oss-20b:free` devolvió cero y el ID está ausente del catálogo autenticado. La consulta pública de `liquid/lfm-3-1.7b:free` devolvió el endpoint `liquid`, soporte de herramientas y precios cero para entrada y salida. No hubo solicitudes de inferencia ni gasto.

- Inferencia física local pendiente de validar en un entorno adecuado, fuera de la puerta de P-1. Aislamiento de producto pendiente de su fase.


## Inferencia real y Fase 2

- OpenRouter: el usuario aprobó `liquid/lfm-3-1.7b:free`. El endpoint `liquid` anunció herramientas y precio cero. El primer intento obtuvo una llamada a herramienta con costo cero y HTTP 404 en la continuación con `tool_choice: none`. El fixture definitivo omitió ese parámetro en la continuación y pasó ambas solicitudes. Se verificaron el proveedor, el modelo, el argumento, el marcador final y costo USD 0 en cada respuesta. Reproducción: `python3 tests/fase1-openrouter.py` con `OPENROUTER_API_KEY` inyectada. Es una prueba de API directa; la cobertura real de la CLI corresponde a la matriz de loopback.
- Supervisor: `python3 -B tests/test_supervisor.py` pasó dos pruebas de integración local. `python3 -B implementacion/supervisor doctor` detectó Linux x86_64, usuario estándar y Bubblewrap en PATH, con aislamiento no verificado. `PLAN` rechazó las operaciones y argumentos de ejecución y escritura. macOS, Windows y WSL requieren validación en sus entornos.

## Broker DIAG de Fase 3

- `python3 -B -m unittest discover -s tests`: cinco pruebas, cero fallos, en CachyOS x86_64. Pasaron las cinco consultas, errores de protocolo, rechazo de comandos, rutas y parámetros, auditoría sin valores y separación de PLAN.
- Cliente `@modelcontextprotocol/client` 2.4.0 del checkout fijado, ejecutado con Node: inicializó, listó y ejecutó las cinco herramientas con resultados estructurados. El transporte stdio del SDK ejecutado directamente con Bun cerró la conexión durante el handshake; la prueba con Node sí pasó.
- `opencode --standalone mcp list` no enumeró el servidor al inicio. La CLI compilada sí descubrió e invocó `diag_environment` durante `--standalone run`. Con el sobre MCP corregido, el simulador recibió el resultado DIAG y el señuelo recibió cero solicitudes.
- [Configuración y alcance](evidencias/FASE3.md).

## Inicio de Fase 4

- `python3 -B tests/fase4-linux.py` pasó en CachyOS x86_64 con Bubblewrap. La sesión de herramientas necesitó permiso para crear el listener local de control. El primer intento de Bubblewrap exigió `--unshare-user` explícito; el reintento con namespaces explícitos pasó.
- Los fixtures verificaron un destino permitido, denegación en ruta absoluta, traversal, enlaces y política protegida, desconexión del loopback del host, entorno limpio y ausencia de actividad del hijo tras timeout.
- Pasó la sesión integrada con el catálogo restringido, el broker aprobado, denegación de escritura y `skill`, exclusión del plugin local y MCP de prueba, SIGINT y limpieza de procesos. Tres pruebas del supervisor pasaron, incluida la degradación con Bubblewrap ausente del PATH.
- `python3 -I -B implementacion/supervisor qualify-linux`: el entorno base provocó un fallo real de Bubblewrap al crear el socket NETLINK_ROUTE. El supervisor terminó con código 1 e informó que el aislamiento no está verificado. En el entorno autorizado, el mismo comando completó los cuatro casos de la sesión. [Evidencia](evidencias/FASE4.md)

## Inicio de Fase 5

- `python3 -I -B tests/fase5-workspace.py`: edición y validación de la copia sintética dentro de Bubblewrap. La escritura al original fue rechazada. El anfitrión confirmó el contenido original y obtuvo un diff unificado con el cambio esperado.
- `python3 -I -B tests/fase5-review.py` pasó a través del supervisor y Bubblewrap. Validó creación y reemplazo, diffs, rechazo de JSON inválido y conservación del original.
- Nueve pruebas unitarias pasaron. Las carreras sintéticas de creación y reemplazo invalidaron la revisión y descartaron la copia. La edición de agente mediante OpenCode sigue pendiente. [Alcance](evidencias/FASE5.md)
- Cierre P4: diez pruebas automatizadas, más la prueba integrada de OpenCode nativo, Bubblewrap, revisión y publicación Git. La prueba rechazó un cambio concurrente, JSON inválido y una referencia de revisión existente, y preservó el árbol de trabajo. [Evidencia](evidencias/FASE5.md)

## CLI con gateway de Fase 6

`bun tests/fase6-cli-gateway.ts RUTA_AL_BINARIO` pasó en CachyOS x86_64 con Bun 1.4.4 y el binario `v2.3.2` recompilado desde `packages/cli/script/build.ts`. Tres casos: la CLI completó una llamada a herramienta a través del gateway contra un endpoint sintético sin recibir la credencial del cliente; un costo `0.001` fue rechazado; y con el endpoint detenido la CLI no completó y el proveedor señuelo recibió cero solicitudes. El gateway sirvió con `--listen 0`, cuerpo de hasta 128 KiB y respuesta de hasta 64 KiB.

## Gateway local de Fase 6

- `tests/fase6-gateway.py` pasó en Bubblewrap con loopback privado. Verificó una llamada a herramienta en la respuesta, límites de tokens y tamaño, destino y modelo fijos, rechazo de costo positivo, respuesta de modelo distinto, redirección y caída del endpoint sin fallback. La prueba no invocó servicios externos. Sigue pendiente el recorrido desde la CLI de OpenCode y un modelo físico local.

## Fase 7 · Memoria por proyecto

`python3 -I -B tests/fase7-memoria.py` pasó en CachyOS x86_64. Verificó alta con archivo referenciado, ranking por etiquetas y texto, ajuste al presupuesto de tokens, exclusión automática tras cambiar el archivo, informe y purga de entradas inválidas, separación entre proyectos y rechazo de secretos y rutas externas. El almacén usa JSONL con bloqueo y no toca la red.
- `python3 -I -B tests/fase7-contexto.py` pasó. Cubre límite de bytes con Unicode, exclusión de entradas vencidas y sobre de autoridad nula. `python3 -I -B tests/fase7-memoria.py` también pasó como regresión del ranking compartido. No hubo red ni inferencia.

## Fase 7 · Integración de contexto no confiable en loopback

- `python3 -B -m unittest discover -s tests`: 11 pruebas unitarias pasaron en CachyOS x86_64. Se verificó la validación estricta de estructura del sobre en `implementacion/supervisor/context.py`, el encapsulamiento seguro y el rechazo de sobres con autoridad distinta de `none`.
- `bun tests/fase7-contexto-loopback.ts .fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode` pasó con código 0. Demuestra que OpenCode v2.3.2 en `--standalone run` recibe el sobre como datos no confiables en el payload HTTP de loopback, no amplía permisos, rechaza intentos adversarios de crear archivos fuera del workspace (`unauthorized-write`), completa la lectura segura de `sample.txt` y no envía solicitudes al señuelo (0 solicitudes).
- `bun tests/fase1-loopback.ts .fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode`: los 9 casos pasaron con código 0 (`invalid`, `windows`, `unicode`, `bounded`, `large`, `multiple`, `cancel`, `retry`, `context`), con 0 solicitudes al señuelo.
- Regresión completa de Fase 6 y Fase 7: `tests/fase6-gateway.py`, `tests/fase6-cli-gateway.ts`, `tests/fase7-memoria.py` y `tests/fase7-contexto.py` pasaron sin fallos.

## Fase 7 · F7.1 línea base

- `python3 -I -B tests/fase7-lineabase.py` pasó en CachyOS x86_64. Verificó determinismo de salida, ajuste al presupuesto de bytes (512, 2048, 8192), exclusión de entradas inválidas tras cambio de archivo y rechazo de presupuesto fuera de rango. No usó red ni inferencia.

## Validación real de pendientes · 2026-11-25

- `python3 -I -B tests/fase6-concurrencia.py` pasó en CachyOS x86_64. Clientes HTTP reales (`http.client`, no CLI): 12 solicitudes simultáneas con límite 2 dieron pico medido 2 y 12 respuestas 200; 8 solicitudes en streaming dieron todas `data: [DONE]` con pico ≤ 2; con `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS=1` y endpoint de 2 s el gateway respondió 502 en ~1 s.
- `python3 -I -B tests/fase7-repomap.py` pasó. Informe: 36 `highlights.scm`, 0 consultas de símbolos, sin LSP, ripgrep disponible, sin runtime Tree-sitter (CLI ni binding Python) y sin gramáticas `.wasm` en el checkout fijado; `implementacion/repomap/` inexistente. F7.2 queda bloqueado sin duplicar indexador (D24).
- Modelo local físico: bloqueado. `ollama`, `vllm`, `llama-server` y `llama-cli` no están en PATH; `127.0.0.1:11434` y `127.0.0.1:8000` no responden; 0 archivos `*.gguf`/`*.safetensors` bajo `$HOME` (profundidad 5). No se ejecutó inferencia.
- D07 remoto: bloqueado. Sin autorización explícita nueva ni credencial/entorno remoto; no se realizaron solicitudes externas.
- Regresión: 11 unittest, `qualify-linux`, `fase5-review`, `fase5-workspace`, `fase6-gateway`, `fase6-concurrencia`, `fase7-memoria`, `fase7-contexto`, `fase7-lineabase`, `fase7-repomap` y `git diff --check` limpios.

## Inferencia física local · 2026-11-26

- `python3 -I -B tests/fase6-modelo-local.py` pasó en CPU con `llama.cpp` `b12753` y Llama 3.2 1B Instruct Q4_K_M (~771 MiB). Verificó respuesta de chat, streaming SSE con `[DONE]` y tool call real (`leer_archivo`) a través del gateway. Se usaron dos hilos CPU; no se usó GPU ni red durante la inferencia.

## Estabilización · saturación del gateway (2026-11-25)

- `python3 -I -B tests/fase6-concurrencia.py` pasó. Ráfaga de 12 clientes con límite 2: respuestas 200 válidas y rechazos 503 (`concurrency`), pico de upstream 2 y ninguna solicitud perdida. Ráfaga de 10 con endpoint de 1 s: 503 inmediato al exceso, pico 2 y recuperación a 200 tras liberar. 2 clientes streaming completaron `[DONE]`. Con timeout 1 s y endpoint de 2 s: 502 en ~1 s. Sin `BrokenPipe`.

## 2026-11-26 · Línea base de lectura web sin red

`.fase1/tools/bun-linux-x64-baseline/bun tests/lectura-web-lineabase.ts`. Bun 1.4.4, Linux x86_64. A y B comparten exactamente el conversor HTML y estimador originales comprobados por blob. Se midió ese componente común, sin inferencia ni recuperación de red. Cada fila mide 50 conversiones con comparación de salida determinista. El estimador usa caracteres y no representa tokens facturados.

| Caso | Bytes HTML | Bytes Markdown A/B | Tokens estimados A/B | Tiempo total ms | CPU ms |
|---|---:|---:|---:|---:|---:|
| Artículo | 58 | 27 | 7 | 8.91 | 8.79 |
| Menú repetido | 5864 | 3356 | 839 | 156.38 | 168.00 |
| Documentación, enlace y tabla | 246 | 174 | 44 | 16.87 | 20.73 |
| Código | 108 | 60 | 15 | 2.94 | 3.12 |
| Duplicados | 3120 | 2798 | 700 | 40.18 | 38.44 |
| Texto adversario y script | 101 | 59 | 15 | 3.51 | 3.86 |

Pico de RSS del proceso completo: 65 180 KiB. Se verificaron texto técnico, versión, firmas, celdas y enlace de referencia según fixture. El Markdown nativo conserva repetición de menús y avisos. `bun test test/tool-webfetch.test.ts` en el paquete core: **91 PASS**, incluida redirección con listener local autorizado. Sin candidato C medido. PDF, Office, páginas dinámicas, exactitud de respuestas y reducción atribuible a un adaptador quedan pendientes.

## 2026-11-26 · Revalidación de inferencia y aislamiento

- **PASS** `tests/fase6-modelo-local.py` con los artefactos recuperados de `/tmp/opencode`, sin descargas. x86_64, 10 GiB de RAM disponible y 122 GiB libres en el filesystem del proyecto al inspeccionar. Binario llama.cpp b12753, commit `679d8677b`; SHA-256 observado `29ec117ef0611eee883160be37829b50220cbc4bdaf476b47e40a26c0b4c6295`. GGUF SHA-256 observado `6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83`. Son huellas de los archivos locales. El servidor cargó el GGUF y completó las solicitudes.
- El fixture HTTP espera `/health`, comprueba chat no vacío y alias, una respuesta SSE con varios eventos y `[DONE]`, y el nombre de la función en una llamada forzada. Lee el SSE completo antes de comprobarlo. Intenta terminar gateway y llama.cpp en `finally`. No ejerce errores de inferencia, cancelación del cliente, latencia del primer evento, consumo CPU/RAM, limpieza de descendientes ni aislamiento Bubblewrap. No ejecuta la herramienta.
- **PASS** `qualify-linux` y `tests/fase4-linux.py`: catálogo restringido, cancelación sintética, limpieza, red privada y ausencia de acceso a un listener confirmado del host. En el entorno exterior restringido los intentos iniciales dieron EPERM al crear sockets o NETLINK_ROUTE. Los reintentos autorizados mantuvieron `--unshare-net`.
- **PASS** 11 unitarias Python, F5 review y workspace, F6 gateway, F6 concurrencia HTTP, F6 CLI gateway sintético, F7 memoria, F7 contexto Python y loopback, F7.1 línea base, y F7.2 fixture de compuerta. F7.2 como capacidad sigue **BLOCKED**. D07 remoto sigue **BLOCKED**. La regresión de contexto en Bubblewrap usó `HOME=/tmp` junto a los montajes de implementación.

### Sesión física con herramienta nativa

`python3 -I -B tests/fase6-agente-local.py` reutiliza el constructor Bubblewrap del supervisor, con mounts de solo lectura para binarios y GGUF, configuración explícita, workspace temporal y red privada compartida por OpenCode, gateway y llama.cpp. El fixture fija dos hilos CPU, 4096 de contexto, dos pasos de agente y hasta 96 tokens de salida por solicitud. No requiere un puente hacia el host.

- **PASS** lectura real de `sample.txt`. El evento de herramienta registró el marcador del archivo temporal que no aparecía en el prompt.
- **PASS** la llamada real para `forbidden.txt` fue rechazada por permisos y su contenido quedó fuera de los eventos.
- **FAIL** respuesta final. La sesión llegó a otro turno de inferencia y terminó con `stop`, un token de salida y sin texto que contuviera el resultado. En otros intentos el modelo repitió `read` o generó `limit: 0`; OpenCode rechazó el límite inválido. La primera regla del fixture usó una ruta absoluta y se corrigió al confirmar que OpenCode compara la ruta relativa. El resultado final del fixture sigue siendo fallo. Queda pendiente aislar si la respuesta vacía depende del modelo, la plantilla de chat o el historial de herramientas.
- **PASS** F1 loopback completo con HOME temporal: lectura inválida, rutas, límites, múltiples llamadas, cancelación, reintento, contexto y cero solicitudes al señuelo.

## 2026-11-26 · Prevalidación de proveedor para D07

- Base `c777a16a49547ac040cf35d2cb6d40e109bced8f`, `fase-1` limpia y alineada con `origin/main`. Se revisaron el fixture físico, la sesión sintética con herramientas y el gateway, que fija destino y ruta HTTP a loopback. La base tipada de OpenCode se consultó en modo de solo lectura seleccionando metadatos de integración activa. Solo se observó OpenAI. No se leyó el valor de las credenciales. No se encontró `OPENROUTER_API_KEY` en el entorno y no se verificó acceso gratis de OpenAI.
- **PASS** consulta pública al catálogo OpenRouter. `google/gemma-4-26b-a4b-it:free` anunciaba un endpoint `google-ai-studio`, `tools` y `tool_choice`, contexto 262144, salida máxima 32768 y precio anunciado 0 para entrada y salida. `openai/gpt-oss-20b:free` devolvió cero endpoints. Liquid 1.7B anunció precio cero y herramientas, pero ofrece un contraste menos útil con Llama 1B. Catálogo público no acredita cuota, autorización, retención efectiva ni ejecución. [Endpoint de Gemma](https://openrouter.ai/api/v1/models/google/gemma-4-26b-a4b-it:free/endpoints) · [Cuotas](https://openrouter.ai/docs/api/reference/limits) · [Privacidad](https://openrouter.ai/privacy)
- **BLOCKED** A, B, C y D en API real. Cero solicitudes de inferencia y cero tokens enviados o generados por esta validación. Ningún costo de inferencia reportado. Las consultas GET públicas se hicieron sin credenciales ni contenido del fixture. Los resultados locales del checkpoint anterior se preservaron y no se repitieron en esta revisión documental.


## 2026-11-26 · Calificación simulada de D07

- **BLOCKED · Credencial y cuota.** `OPENROUTER_API_KEY` ausente en esta sesión. En la base OpenCode del directorio XDG no se observaron entradas OpenRouter activas ni inactivas. Se consultaron solo identificadores y banderas, sin seleccionar la columna de credenciales. Tampoco se halló la variable en los archivos de inicio inspeccionados. No se realizó `GET /api/v1/key` autenticado.
- **PASS · Destino y límites locales.** `tests/fase6-gateway.py` confirmó ruta fija, rechazo de destino alternativo, redirección, costo positivo, modelo incorrecto y respuesta sobredimensionada, sin fallback. La credencial entrante no se reenvía. `tests/fase6-concurrencia.py` confirmó concurrencia acotada, 503 bajo carga y timeout configurable. El listener actual no autentica al cliente y los límites por solicitud no constituyen presupuesto acumulado ni reserva previa.
- **PASS · Aislamiento y cancelación del proceso.** `qualify-linux` y `tests/fase4-linux.py` confirmaron cancelación sintética del CLI, terminación de procesos, entorno limpio y loopback privado sin acceso al listener del host.
- **FAIL · Cancelación del upstream del gateway.** `tests/fase6-d07-cancel.py` inició SSE con un servidor sintético inmóvil, cerró el cliente y verificó que el upstream no se cerró dentro de 1 s. El cierre se observó con el timeout configurado de 5 s. Cancelar el proceso aislado y cancelar el socket upstream son comprobaciones distintas.
- **BLOCKED · D07 completo.** No hay canal remoto calificado, autenticación o presupuesto compartido acreditados. Cero solicitudes de inferencia externa. No se usaron credenciales ni créditos.

## 2026-11-26 · OpenCode Console y regresión de cancelación D07

- **PASS · Catálogo.** `GET https://opencode.ai/inference/v1/models` confirmó `deepseek-v4.1-flash-free`, `mimo-v2.6-flash-free` y `nemotron-3.5-lightning-free`. Los tres anuncian herramientas, Chat Completions y precios cero para entrada y salida. DeepSeek y MiMo anuncian 200000 tokens de contexto y 32000 de salida. Nemotron anuncia 262144 para ambos. Candidato DeepSeek por su compatibilidad de herramientas y la política de retención cero indicada por Console. [Modelos de Console](https://opencode.ai/docs/console/models/)
- **BLOCKED · Acceso supervisado.** La documentación oficial restringe la inferencia de chat gratuita a OpenCode. El plugin nativo de OpenCode V2 soporta activación pública y credenciales de Console, pero su ruta directa no pasa por el gateway local. `--unshare-net` impide esa salida directa. Sigue sin acreditarse una ruta oficialmente permitida que integre la sesión con D07. No se probó acceso efectivo, cuota ni inferencia desde OpenCode original o CLI_OPEN. Lectura, rechazo, ciclo con respuesta final y SSE reales quedan bloqueados. Cero solicitudes de inferencia, cero tokens de inferencia y ningún costo reportado. [API oficial](https://opencode.ai/docs/console/api/inference/)
- **PASS · Cancelación sintética.** `tests/fase6-d07-cancel.py` cerró el upstream inactivo dentro del umbral de 1 s tras desconectar al cliente, con timeout de socket de 5 s. El gateway sondea el cierre en intervalos de 100 ms mientras el stream está activo y hace shutdown del socket upstream. El cierre del lado de escritura del cliente se interpreta como cancelación durante SSE. El sondeo empieza después de establecer la conexión loopback.
- **PASS · Regresiones.** 11 unitarias Python, gateway sintético, concurrencia y SSE con `[DONE]`, supervisor `qualify-linux` y calificación F4 de red privada. La autenticación del canal remoto, reserva acumulada y límites verificables de entrada de D07 siguen pendientes.
- **PASS · CLI aislada.** `tests/fase6-cli-gateway.ts` completó el ciclo de herramienta y respuesta final con un proveedor simulado bajo Bubblewrap. El costo positivo y el upstream detenido se rechazaron sin fallback. El proveedor señuelo recibió cero solicitudes.

## 2026-11-26 · Compresión HTML sin inferencia

HEAD inicial `dfcdd822b358b96f19be2d64c0ad1b61d1404f6a`, árbol limpio y sincronizado con `origin/main`. A y B comparten exactamente los blobs del conversor y estimador del tag `v2.3.2`. C añade la compresión tras el conversor. Se ejecutó `bun tests/lectura-web-lineabase.ts .fase1/opencode` con `baseline` y `filtered`, en procesos separados, 50 repeticiones por fixture. Estimación por longitud, sin tokens facturados.

| Fixture | Tokens A/B → C | Ahorro | Pared ms A/B → C | CPU ms A/B → C |
|---|---:|---:|---:|---:|
| Navegación repetida | 839 → 42 | 95,0 % | 100,27 → 77,65 | 166,57 → 146,46 |
| Párrafos idénticos | 700 → 21 | 97,0 % | 33,99 → 35,38 | 72,45 → 72,76 |
| Navegación con secciones adicionales | 641 → 49 | 92,4 % | 87,30 → 69,12 | 118,85 → 106,92 |
| Documentación extensa única | 2757 → 2757 | 0 % | 176,53 → 224,08 | 254,69 → 365,91 |

Pico RSS del proceso completo A/B y C: 80032 → 82972 KiB. Son observaciones de una corrida y las diferencias de tiempos incluyen variación del runtime y de la conversión nativa. Otros siete fixtures conservan sus tokens y bytes de salida: artículo, documentación breve, código, tabla, advertencia, contenido adversario y HTML Unicode malformado. Se conservaron cercas con párrafos repetidos, enlaces, código, encabezados y advertencias únicas. El caso sobredimensionado se entregó intacto.

**PASS** integración con OpenCode compilado del tag fijado en Bubblewrap con `--unshare-net`: se observó el resultado Markdown original y comprimido en el historial del proveedor simulado. Una instrucción adversaria permaneció como texto de herramienta y el modelo simulado pidió una URL denegada. El servidor recibió cero peticiones a esa URL. El fixture no demuestra comportamiento de un modelo real frente a instrucciones adversarias. Sin API o inferencia remota. D07 sigue **BLOCKED**.
**PASS** 91 casos nativos de `webfetch`, 11 unitarias Python, memoria, contexto y `qualify-linux` con cancelación, catálogo restringido y rechazo de plugin no aprobado. El repositorio CLI_OPEN no trae un workflow raíz al que añadir el fixture. Los comandos quedan reproducibles con los artefactos F1 existentes.

## Suites reproducibles y CI

- **PASS local** perfiles portable y Linux en CachyOS x86_64. El portable ejecuta unitarias, memoria, contexto, línea base F7.1 y el hook HTML con Node. Linux añade edición de copia, namespaces, gateway, concurrencia, SSE y cancelación.
- La CI de GitHub tiene jobs separados en Ubuntu 24.04, checkout fijado por SHA y permisos de lectura. No ejecuta modelos físicos, proveedores remotos ni el perfil con binario de OpenCode. La ejecución en el runner alojado requiere observar GitHub Actions después de publicar.
- El preflight de OpenCode compara SHA-256 de Bun y CLI contra la pareja calificada, comprueba versiones con HOME desechable y ejecuta las pruebas de artefactos con Bubblewrap. Un paquete reconstruido con otro hash queda explícitamente bloqueado.

### Presupuesto y deduplicación de memoria

**PASS** 12 unitarias, memoria, contexto, línea base F7.1 y prueba del filtro HTML. La regresión verifica que los escapes Unicode consumen presupuesto, que se puede elegir una entrada posterior que quepa y que se omiten duplicados por ID y texto. El perfil portable también pasó desde una exportación limpia del índice sin `.fase1`. Los tests unitarios de edición aíslan los artefactos simulados en un temporal.

Microbenchmark de `incorporate_prompt`: 1000 iteraciones de un sobre con 40 entradas «Observación repetida.» con IDs únicos y una «Requisito independiente.». Comparación entre `5323a87` y la versión actual, en el mismo proceso. El sobre JSON pasó de 2598 a 180 bytes (650 a 45 tokens estimados a 4 caracteres por token). Una corrida tomó 506,56 → 251,73 ms de pared y 445,52 → 221,73 ms de CPU. Pico RSS acumulado: 13348 KiB para el proceso compartido. No se puede atribuir RAM por variante a esa medición. El ahorro corresponde al fixture repetitivo y no pronostica rendimiento general.

### Reanudación nativa de sesión

**PASS** `python3 -I -B tests/run-suite.py opencode` con Bun 1.4.4 y OpenCode v2.3.2 previamente calificados. Pasaron supervisor, MCP, edición revisada, contexto y webfetch bajo Bubblewrap, además de gateway y SSE. Tras completar una lectura, un proceso nuevo reabrió la sesión por ID con `run --session`. El proveedor simulado recibió una sola solicitud con el resultado anterior una sola vez y OpenCode emitió respuesta final sin repetir la herramienta. El escenario cubre reanudación después de un paso completado. Recuperar una sesión tras interrupción a mitad de herramienta queda pendiente.

La compuerta F7.2 se ejecutó y reprodujo el bloqueo estructural. Faltan consultas de símbolos LSP o Tree-sitter reutilizables en el runtime calificado. Se inspeccionó el stash sin aplicarlo. D07 conservó **PASS** de cancelación, límites de concurrencia y destino loopback con mocks. Autenticación, reserva y reconciliación de presupuesto acumulado siguen **BLOCKED**. No hubo inferencia real ni se repitió la prueba física.

## Diagnóstico de CI en GitHub Actions

- **CONFIRMADO.** Ejecución 45863051627, commit `f74ab48`. Job portable aprobado. Job Linux falló en `python3 -I -B tests/run-suite.py linux`, primera prueba `tests/fase4-linux.py`, con código 1. Bubblewrap 0.9.0-1ubuntu0.3, Python 3.12 e imagen Ubuntu 24.04 versión 20261122.23.1. Mensaje exacto `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Sucedió al configurar el namespace de red antes de ejecutar el fixture. El paso de instalación de Bubblewrap había pasado. El job no requiere Bun ni artefactos `.fase1`. [Ejecución original](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/45863051627)
- **BLOQUEADO POR EL ENTORNO.** El runner denegó la asignación de la dirección de loopback. La restricción de namespaces de AppArmor es el diagnóstico más probable según la documentación de Ubuntu y reproducciones en Noble. El log original no muestra el sysctl ni una denegación de auditoría, por lo que el mecanismo exacto del runner queda pendiente de confirmación. Con la restricción activa, CI carga el perfil de `apparmor-profiles` desde el sistema. Mantiene `--unshare-net`, la restricción global y la ejecución sin privilegios de los tests. El job registra arquitectura, UID, Python, versión de Bubblewrap y espacio temporal. [Perfil empaquetado](https://packages.ubuntu.com/noble-updates/all/apparmor-profiles/filelist) · [Comportamiento del perfil](https://documentation.ubuntu.com/release-notes/25.04/#apparmor-profile-for-bwrap)
- **CONFIRMADO.** Ambos jobs emitieron una advertencia de checkout sobre Node.js 20. Se actualizó al SHA oficial de v5.0.1 con Node.js 24. Se mantienen checkout sin credenciales persistentes, permisos de lectura y timeout. Sintaxis de YAML y scripts shell comprobada. [Checkout v5.0.1](https://github.com/actions/checkout/releases/tag/v5.0.1)
- **PASS local.** Perfiles portable (12 unitarias), Linux (F4 y F5, gateway, concurrencia y cancelación SSE) y OpenCode (supervisor, edición revisada, recuperación de sesión, contexto y webfetch). CachyOS x86_64, Bubblewrap 0.13.1 y Python 3.14.9. El error de Ubuntu no se reprodujo en este entorno compatible. Queda por validar la carga del perfil y la suite completa en el runner.

### Segundo fallo del job Linux · arranque de Python

- En `810af0c`, portable pasó. Linux cargó el perfil oficial con la restricción global de AppArmor activa y superó el fallo previo del loopback. El siguiente fallo fue `bwrap: execvp /usr/bin/python3: No such file or directory` en F4. [Ejecución de CI](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/45864416809)
- Reproducción mínima local con Bubblewrap 0.13.1 y layout separado de bibliotecas simulado. `readelf -l /usr/bin/python3` identificó `/lib64/ld-linux-x86-64.so.2` como intérprete ELF. Dentro del fixture, el ejecutable resolvía a `/usr/bin/python3.14` y existía. Invocar el cargador directamente permitió comprobar que el enlace antiguo `/lib64 -> /usr/lib` ocultaba el intérprete requerido, aunque estaba disponible en `/usr/lib64`. Ejecutar Python directamente reprodujo el mismo ENOENT. Cambiar únicamente el destino de ese enlace en el fixture permitió que `python3 --version` pasara.
- F4 utiliza ahora el constructor del supervisor, que conserva los directorios de bibliotecas del host mediante montajes de solo lectura. Los dos subprocesos de F4 comparten montajes y política, con `--unshare-net` y `--disable-userns`. El fixture imprime las rutas resueltas de Python, `/lib`, `/lib64`, `/usr/lib` y el cargador ELF dentro del sandbox. La validación remota de este cambio queda pendiente.
- **PASS local** perfiles Portable (12 unitarias), Linux (F4, edición y gateway) y OpenCode (supervisor, MCP, sesión, contexto y webfetch). Pasó `git diff --check`.

## F7.2 · Pistas de ruta

- **PASS** fixture `test_project_paths.py`: proyecto temporal con rutas Python, TypeScript, término similar, exclusiones de Git, directorio generado, enlaces a otro proyecto y nombre sensible. Verifica salida determinista, presupuesto compartido, rechazo de rutas externas al incorporar, ausencia de cuerpos en el resultado y actualización tras renombrar y borrar. El cambio invalida la nota basada en el hash del archivo anterior. La prueba requiere Linux y ripgrep.
- **PASS** compuerta de reutilización `tests/fase7-repomap.py`. El resultado de la capacidad estructural sigue **BLOCKED**.
- Benchmark sintético con 300 rutas `src/module_0000.py` a `src/module_0299.py` y seis `src/auth_feature_0.py` a `src/auth_feature_5.py`, cuerpos `synthetic body\n`, memoria vacía y consulta `auth`. Una lista amplia en el formato de glob nativo (referencia A, una ruta por línea) ocupa 5831 caracteres, unos 1458 tokens. No se ejecutó el agente para A y una búsqueda nativa específica puede ser más corta. B (memoria sola) emitió 60 bytes, unos 15 tokens, sin rutas. C (nuevo contexto) emitió 214 bytes, unos 54 tokens, con las seis rutas esperadas y ningún cuerpo. El listado evaluó 306 nombres, sin abrir sus cuerpos para la exploración. Esto equivale a 96,3 % menos tokens estimados que la lista amplia A y 39 tokens más que B.
- En una corrida local, B tardó 114,05 ms y usó 108,88 ms de CPU. C tardó 142,63 ms y usó 117,30 ms de CPU. RSS pico acumulado de hijos B/C: 20704/20984 KiB. Es una medición puntual que incluye arranque de Python y ripgrep. No hubo índice inicial ni actualizaciones incrementales de un índice. No se midió exactitud de respuestas de un modelo.
- **PASS local** Portable (13 unitarias), Linux, OpenCode y `git diff --check`. GitHub Actions Portable y Linux pasaron en la base pública `620106b`. CI de este cambio pendiente de publicación. Sin inferencia remota.

### F7.2 · Integración de contexto selectivo

- **PASS** `tests/fase7-contexto-selectivo.ts` con OpenCode fijado, proveedor sintético y Bubblewrap. El supervisor incorporó las rutas del mapa con autoridad nula. Glob encontró ambos candidatos y devolvió vacío para una ruta ausente. Grep literal devolvió ambas coincidencias en la línea 80. El fixture tomó los offsets de esa respuesta y read entregó las páginas de las dos implementaciones. Un comentario pidió leer un archivo restringido. El proveedor simulado ejerció esa solicitud y la política de OpenCode la denegó, sin divulgar su contenido.
- En el historial final del proveedor simulado, las dos lecturas completas acumularon 13205 bytes de resultados y el flujo selectivo, con seis llamadas, acumuló 723 bytes. Con la aproximación de cuatro caracteres por token aplicada al fixture ASCII, son 3301 frente a 181 tokens estimados, un ahorro de 94,5 %. El mismo sobre de memoria fue de 112 bytes. La suma selectiva quedó en 835 bytes. Se conservaron las dos políticas relevantes y la advertencia adversaria como texto. Las cifras excluyen la repetición de mensajes en solicitudes sucesivas, prompts del sistema y esquemas. No se midió uso facturado, latencia ni exactitud de un modelo real.
- El objetivo conjunto de 4096 bytes se cumple en el fixture. El preset lo comunica como pauta y mantiene el límite nativo de pasos. El presupuesto agregado de la sesión todavía no se aplica como cuota dura.
- **PASS local** Portable (13 unitarias), Linux, OpenCode (incluido el fixture selectivo) y `git diff --check`.

## D07 · Reutilización OAuth y presupuesto simulado

- HEAD inicial `85aa32b`, rama `fase-1` limpia y sincronizada. El plugin `chatgpt.ts` del OpenCode fijado registra `Sign in with ChatGPT`, PKCE, estado del callback, almacenamiento mediante Credential.Service y renovación nativa. El plugin `openai.ts` también registra los métodos Codex legacy. El catálogo de ChatGPT en la versión fijada aplica una lista de modelos del plugin. No se comprobó una oferta efectiva para una cuenta. La CLI instalada reportó v2.4.2 con HOME temporal y ofrece login, logout y cambio de cuenta. Ambos binarios contienen las tres etiquetas. La equivalencia de datos de credenciales y compatibilidad de plugins entre versiones quedó **INCONCLUSIVE**. [Guía oficial](https://opencode.ai/docs/cli/providers/)
- **PASS local** `tests/fase6-d07-budget.py`: listener sin token válido no arranca, solicitudes sin autorización o con token incorrecto reciben 401, ruta inesperada y JSON no objeto se rechazan, la reserva de dos solicitudes concurrentes admite sólo una con presupuesto de una, y tres instancias tienen contadores independientes. El proveedor simulado responde 503 y la reserva se conserva en los tres controles. El proveedor recibió cero cabeceras Authorization. El perfil sigue limitado a loopback.
- **PASS local** Portable (13 unitarias), Linux (incluidos presupuesto, concurrencia y cancelación SSE) y OpenCode (sesiones, herramientas, permisos y contexto selectivo) y `git diff --check`. Las regresiones no usaron una cuenta de ChatGPT. La cancelación SSE se verificó en el fixture existente. Falta la prueba combinada del perfil autenticado con cancelación de inferencia remota.
- **BLOCKED** login interactivo y pruebas A–F reales. La ruta nativa de ChatGPT no usa el endpoint local Chat Completions del gateway y el namespace privado carece de salida directa. No se iniciaron sesiones OAuth, no se leyeron credenciales y no se enviaron solicitudes de inferencia a ChatGPT. Cero consumo remoto observado. No se verificaron cuota de plan, renovación efectiva, modelos de cuenta ni respuesta final real. No se habilitó facturación.

### D07 · Plazo global, cancelación y SSE autenticado

- Inicio en `bbab47a`, rama `fase-1` limpia y sincronizada. Se confirmó en el código fijado que el plugin ChatGPT aplica configuración HTTP, compresión zstd cuando corresponde, afinidad nativa de sesión, filtro de modelos y rechazo de reintentos en determinados errores. El adaptador de OpenAI admite Responses. El gateway local sólo admite Chat Completions. El catálogo efectivo, el manejo de errores contra la cuenta y la cancelación remota siguen **BLOCKED**. El flujo nativo de OpenCode se conserva. [Proveedor y plan](https://opencode.ai/docs/providers/#chatgpt)
- **FAIL reproducido y corregido.** Un upstream SSE que cerró luego de un evento sin `[DONE]` terminaba sin señal de error. El perfil autenticado exige tipo SSE, un evento válido y terminador. El fixture comprobó el error explícito para truncado y el éxito para una secuencia completa.
- **PASS simulado.** Cliente que se desconecta cierra upstream y no recupera la reserva. Un plazo de 2 s cerró el listener y el upstream inactivo antes del timeout de socket de 10 s. El proceso salió con 124. Una nueva instancia con otro token rechazó el anterior. No se reenviaron credenciales ni aparecieron sus valores o los nombres de campos inválidos en logs. Se conservó el rechazo previo a la reserva para clientes sin autorización, destino inválido y errores de validación.
- Las reservas siguen contando máximos de salida y bytes de entrada. El plazo es el del proceso gateway y no controla por sí solo el ciclo de vida de las herramientas de OpenCode. La recuperación después de completar una herramienta y la cancelación de procesos se ejercitan en los fixtures previos. Queda pendiente reanudar después de interrumpir una herramienta activa. No hubo inicio de sesión ni inferencia real.
- **PASS local** Portable (13 unitarias), Linux (gateway, concurrencia, SSE y presupuesto) y OpenCode (MCP, edición, reanudación, F7.2 y webfetch). Pasó `git diff --check`.

## D07 · Persistencia y reconciliación

- Base `9b4e84a`, rama limpia y alineada con `origin/main`. La auditoría retomó el plugin nativo ChatGPT del motor fijado: usa HTTP, OAuth nativo y Responses, con modelos filtrados y afinidad de sesión. El listener existente sigue fijo a Chat Completions y al loopback. No se encontró una ruta supervisada oficial calificada. Sin inicio de sesión, puente nuevo ni inferencia remota.
- El fixture `tests/fase6-d07-persist.py` usa un proveedor simulado. Verifica creación explícita, metadata del perfil, modo 0600, exclusión de un segundo proceso, reserva que sobrevive reinicio normal, pérdida del proceso durante SSE, recuperación como incierta, rechazo al agotar presupuesto, concurrencia con saldo de una solicitud, datos reportados en JSON y SSE, uso desconocido, cierre por exceso reportado, vencimiento y rechazo de archivo corrupto.
- Los datos reportados se aceptan por estructura y tipo del mensaje validado. No certifican facturación. El presupuesto registra bytes de entrada y máximos de salida, y conserva la reserva completa. El registro no contiene cuerpos, respuestas, credenciales ni cabeceras. Fallo de escritura al cerrar una operación conserva su reserva y puede dejarla incierta. La apertura de un registro requiere que el lanzador confiable mantenga intactas su ubicación y titularidad.
- **PASS local** Portable (13 unitarias), Linux y OpenCode, incluidos F7.2, gateway, recuperación nativa tras una lectura completada y cancelación. El fixture de muerte abrupta acepta EOF o reset TCP como cierre y sigue fallando si vence la espera. `git diff --check` pasó. La reanudación de una herramienta interrumpida sigue pendiente.

## D07 · Responses simulado

- Base local `7670058`. La consulta a GitHub, tras un primer timeout, confirmó que main seguía en `9b4e84a` antes de publicar. Se conservó el stash de Repo Map.
- El SDK fijado serializa mensajes, llamadas `function_call` y resultados `function_call_output` con `call_id`. Usa eventos Responses específicos. El transporte nuevo conserva los ítems nativos, se limita a HTTP SSE y termina con `response.completed`. La compatibilidad se comprobó con el proveedor original de OpenCode. Quedan excluidos `previous_response_id` y funciones alojadas.
- El fixture cubre 401, ruta alterna, campos o límites inadmisibles, llamada de lectura permitida, lectura denegada, argumentos y texto en fragmentos SSE, respuesta final con el marcador previamente desconocido, fallo HTTP, truncado y cancelación en loopback. SQLite conserva la reserva y registra los tokens reportados sólo en la terminación válida. El proveedor no recibe la credencial. Las pruebas existentes del registro cubren reinicio, corrupción, agotamiento y concurrencia. El nuevo fixture no interrumpe una herramienta activa.
- No hubo inferencia externa, conexión de cuenta ni cambio de permisos. AppArmor y Bubblewrap mantienen sus protecciones. Sigue pendiente un transporte autorizado fuera del namespace y su calificación real.
- **PASS local** Portable (13 unitarias), Linux y OpenCode. La sesión Responses se reabrió por ID en un proceso nuevo. El proveedor recibió el resultado anterior de herramienta en una sola solicitud de continuación y la CLI no volvió a ejecutar read. `git diff --check` pasó.

## D07.2 · Interrupción después de un efecto sintético

- `python3 -I -B tests/run-suite.py opencode` ejecuta el fixture Responses con los binarios fijados y Bubblewrap con `--unshare-net`. El simulador solicita `shell`; la herramienta escribe una sola línea en el workspace temporal y permanece activa. El fixture mata OpenCode y reabre por ID con `shell` denegado. Comprueba que el resultado asociado a la llamada informa de una interrupción, que el proveedor simulado responde señalando la incertidumbre y que no se añade otra línea. La comprobación termina después de un efecto observable pero antes de que la herramienta devuelva su resultado. No aísla los puntos previos a la ejecución ni acredita idempotencia general.
- El mismo fixture comprueba una terminación SSE válida sin uso reportado, con valores nulos para ambos contadores en SQLite. También comprueba modelo incorrecto, truncamiento, fallo HTTP y cancelación de un upstream inactivo. El perfil Linux conserva la cobertura de concurrencia, reservas inciertas tras reinicio, plazo persistido y rechazo de corrupción.
- **BLOCKED** ChatGPT externo. OpenCode documenta `Sign in with ChatGPT`; el motor fijado selecciona un destino específico para la credencial OAuth y admite configuración de proveedores, pero no se encontró soporte documentado para delegar esa sesión a un transporte externo supervisado. La API pública tiene facturación separada. No se consultaron credenciales ni se enviaron solicitudes de inferencia real. [Proveedores de OpenCode](https://opencode.ai/docs/providers/#chatgpt) · [Facturación de ChatGPT y API](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform).

- **PASS local** Portable (13 pruebas unitarias), Linux y OpenCode. `git diff --check` pasó. GitHub Actions ejecuta Portable y Linux. El perfil OpenCode se verificó localmente con sus artefactos fijados.

## D07.3 · Local interruption matrix

OpenCode v2.3.2 at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` uses a synthetic Responses provider. Fresh CLI processes reopen the same native session database with the explicit policy for each run. OpenCode history and the gateway's SQLite reservations track different state.

| Point | Tool and effect | State and permission at recovery | Observed result and remaining scope |
|---|---|---|---|
| A · Tool input started | `shell` arguments still streaming | `streaming` → `error/aborted`, `executed=false`; the reopened catalog omits `shell` | The effect file remains absent. The later native permission fixture covers complete arguments for MCP. |
| B · Active execution | `shell` with an effect file and a live process | OpenCode exits by SIGKILL and the call is interrupted | The PID was visible before the interruption and disappeared afterward. Arbitrary partial effects still require inspection. |
| C · Effect applied, result pending | `shell` appends a line | Recovery returns the interrupted result first with `shell` denied, then with it allowed | The file contains one line after both resumptions. The later MCP fixture covers stdio dispatch and effects separately. |
| D · Stored result | `read` and `edit` | Same call ID and persisted result; an edit denial persists when the new policy allows editing | One model request on resumption and no new tool execution event. External contents survive, even when they again contain the search string. |
| E · Active read or search | `read`, `glob`, `grep` | Completed allowed and denied reads pass in Responses. F7.2 covers path discovery, search, and pagination | The denied marker never reaches the model or fixture output. Interruption after native dispatch remains pending. |

The edit tests cover path denial, ambiguous matches, stale source text, and successful CRLF preservation. The external revision in the earlier fixture predates the next operation. The exact native validation-to-write interval remains open. A distinct call ID with equivalent arguments represents a new operation subject to current policy. The historical fixture established that resumption does not replay the old recorded call.

At this checkpoint, Portable passed 13 unit tests plus memory, context, and web fixtures. Linux passed Bubblewrap, SQLite restart and corruption rejection, deadline, SSE cancellation, HTTP client concurrency, and reservation retention. Provider-reported usage is recorded separately and establishes no billed usage.

The historical OpenCode run passed the expanded matrix, including abort before dispatch, shell-process cleanup, and two SQLite cancellation records. The context fixtures passed untrusted memory and native path, match, and page selection. F7.2 tool output was 13,205 bytes in the baseline and 723 bytes in the selected synthetic run.

## English engineering text benchmark

Run `python3 -I -B tests/english-context-benchmark.py` with baseline `b96229d7d3a3b00a2fe5a147444f2a73c48cfa1b` available locally. Both inputs use the same Spanish request, synthetic memory, path and tool schema. The benchmark uses the pinned OpenCode `Token.estimate` formula (UTF-16 code units divided by four and rounded). Byte counts are exact for the fixture. Token counts are estimates without a model tokenizer or provider request.

| Component | UTF-8 bytes before → after | Estimated tokens before → after |
|---|---:|---:|
| User request | 44 → 44 | 11 → 11 |
| Agent instructions | 1107 → 983 | 272 → 246 |
| Agent description | 66 → 57 | 16 → 14 |
| Tool description schema | 78 → 78 | 20 → 20 |
| Context wrapper | 443 → 390 | 110 → 98 |
| Memory and paths | 152 → 152 | 38 → 38 |
| Combined input | 1890 → 1704 (−9.84%) | 466 → 426 (−8.58%) |

## D07.3 · Native MCP interruption under Bubblewrap

The Responses fixture starts `tests/fase6-d07-mcp-server.py` through OpenCode's native local stdio MCP transport. The server counts calls and appends to disposable state. A release marker gates the append and a separate marker gates the response. The harness verifies the native call is still running at each interruption barrier before killing the CLI.

| Case | Observed result in the OpenCode profile |
|---|---|
| Before effect | One MCP invocation reached the first barrier. After resumption with the tool denied, the effect file was still absent. |
| After effect, before reply | One invocation and one append remained after reopening with the tool denied. OpenCode preserved a terminal error and passed the old call result to the provider. |
| With a persisted result | The stored completion returned to the provider on resume with the tool still permitted. Invocation and effect counts remained one. |

The fixture accepts an aborted tool or a native MCP connection-closed failure because transport teardown can race session settlement. Neither error determines whether the external effect committed. Temporary state is the evidence for this fixture. No live MCP service or remote inference was used. Recent changes passed the local Portable, Linux, and OpenCode profiles. The OpenCode profile runs locally with pinned artifacts. GitHub Actions currently runs Portable and Linux only.

### New equivalent MCP call after resumption

PASS in the local OpenCode profile under Bubblewrap. Reopening the completed MCP session first preserved the existing result with one invocation and one effect. A subsequent explicit request returned a new call ID with the same tool and arguments. With current permission allowing the tool, OpenCode recorded a distinct completion, and the synthetic server recorded exactly two invocations and two effects in total. This demonstrates the difference between replaying history and authorizing a new call. The same test does not establish behavior for a newly proposed call after an uncertain result.

### D07.3 · Permission dispatch and equivalent calls after an uncertain effect

**PASS**, OpenCode v2.3.2 under the existing Bubblewrap Responses profile. The native session permission endpoint exposed the MCP invocation's ID and complete, nonempty arguments while the call was running. The synthetic server had both releases enabled throughout. No invocation reached it while authorization was pending. Session interruption persisted an error, invalidated the old permission request, and left no effect. A fresh call in the same session needed a new decision and executed after a one-time grant. The next identical request needed another decision and its rejection left the total at one dispatch and one effect.

**PASS**, same fixture. Recovery after an observed but unacknowledged MCP effect retained the original call ID and error. The model then requested the same arguments with a distinct ID while the tool was denied. OpenCode recorded an error without dispatching it. A third ID under explicit allow completed and produced one additional effect. The prior records remained session evidence.

### D07.3 · Concurrent edit before reviewed Git publication

**PASS**, `python3 -I -B tests/test_workspace.py`. The test changed a synthetic source at the existing final verification callback, after Git prepared the candidate commit. The production verifier rejected the publication. The external contents and mode survived, HEAD and the live index were unchanged, and no review ref was created.

**PARTIAL** for native `edit`. The pinned engine computes source matches and a preview before requesting permission. Uniqueness and no-op checks run after that request, and the native write follows. The Git publication barrier gives evidence at the supervisor boundary. The native interval after final edit validation and before file write remains untested.

**PENDING** for interruption during active native `read`, paginated `read`, `glob`, and `grep`. Existing F7.2 tests qualify completed search and pagination. **PENDING** for a complete supervisor restart. OpenCode session recovery and SQLite gateway ledger restart are independently exercised. The current supervisor exposes one-shot commands and has no product task start/resume command that owns both processes and their persistent state.

### Verification of the authorization checkpoint

Portable passed 14 unit tests plus memory, context, and HTML compression. Linux passed Bubblewrap, safe workspace operations, gateway concurrency, SSE cancellation, and SQLite reservations, restart, deadline, and corruption checks. OpenCode passed the pinned artifact checks, native edit and supervisor fixtures, Responses recovery, MCP, F7.2 selective context, and loopback webfetch. The standalone Repo Map gate reproduced the D24 blocker. Local regression evidence applies to OpenCode v2.3.2 and Bun 1.4.4. Remote CI was not rechecked for the local commits.

The host has an x86_64 Intel Core i5-7300HQ, four logical CPUs, and 16,245,544 KiB of reported RAM. The HTTP regression observed the configured two-request limit. The shell recovery fixture observed cleanup of the recorded child PID. These are regression observations. F8.0 workload measurements, process-tree RSS, CPU time, and sequential/parallel comparisons remain pending under the roadmap entry gate.

### D07.4 · Launcher restart with native session and task budget

`python3 -I -B tests/fase6-d07-restart.py` runs a fixed test-owned launcher using the supervisor's Bubblewrap command builder and subprocess ownership pattern. The first namespace shares private loopback among OpenCode, the authenticated Responses gateway, and a synthetic upstream. A completed read and an MCP append run in the same persisted session. The MCP call is held after its effect and before reply. A separate stalled Responses stream holds an open SQLite reservation. The host waits for both barriers, kills the launcher, and checks its captured descendant PIDs and Linux process start times. Seven observed descendants stopped executing in the local regression.

A new namespace and listener reopen the same session and ledger. The completed read result is present, the old MCP ID reports interruption, and a different-argument invocation with a fresh ID is denied under the new policy. The fixture observes one original dispatch and one effect through recovery. A third ID with the changed arguments then executes once under explicit allow, leaving the interrupted and denied records unchanged. The listener rejects a wrong bearer before the upstream, retains the original deadline and all reserved amounts, converts the held reservation to uncertain, and returns HTTP 429 at the original request limit without dispatching upstream.

This qualifies the composed synthetic launcher lifecycle. The product supervisor still exposes one-shot commands. The trusted fixture shares a synthetic writable mount across runs for the ledger, session, and operation markers. It does not qualify production separation of ledger ownership from an untrusted agent, automatic product restart, or arbitrary MCP exactly-once effects.

### D07.4 · Native edit permission preview race

**FAIL for conflict protection at the preview boundary.** The pending native permission request contained the old bytes and proposed replacement. While approval was held, the fixture wrote different bytes to the same synthetic file, then approved the edit once. OpenCode reported success and replaced the external revision using the old preview. The final file was complete and retained mode `0640`. This is a deterministic observed overwrite on a disposable target. It does not qualify the strictly later interval between final native checks and the actual write, or atomicity under a concurrent write. The supervised workspace still uses disposable copies and refuses stale source before publishing the separate review ref.

### D07.4 · Read and search result interruption

**PASS at result persistence.** The focused `--read-results` run uses the native `execute.after` hook for `read`, paginated `read`, `glob`, and literal `grep`. The trusted fixture holds a tool result after the operation produces it and before the session records completion. It interrupts OpenCode with the original call still running in SQLite. Recovery must return an interruption without disclosing the held result. An explicit new call under deny must fail. A distinct permitted retry must return the expected data and keep the prior interruption and denial records. The paginated retry checks that the omitted first line stays outside the result. This boundary is after native filesystem or ripgrep work. Mid-I/O cancellation remains open.

### D07.4 · Native ChatGPT pre-browser diagnostics

The clean temporary profile in `tests/fase6-d07-chatgpt-auth.ts` starts the pinned native server inside Bubblewrap with private loopback only. The local provider and model APIs are reachable and report no active OpenAI provider or account models before authentication. The initialized integration catalog exposes OpenAI's native OAuth method without an API key. The fixture prepares a pending PKCE attempt with an OpenAI authorization origin and a private loopback callback, cancels it, and verifies that the profile has zero connections. The authorization URL remains private and the test stops before browser authorization and code exchange.

| Check | Evidence |
|---|---|
| Native method and pre-browser startup | **PASS**, pinned OpenCode v2.3.2, clean diagnostic profile |
| Account authentication and subscription model availability | **PENDING**, require browser consent and authenticated verification |
| Native inference | **NOT RUN**, requires separate authorization |
| Supervised CLI_OPEN Responses | **PASS, SIMULATED**, private loopback, task bearer, deadlines, cancellation, and SQLite reservations |
| Supervised transport for native ChatGPT credentials | **BLOCKED**, no qualified official route across the provider and tool boundary |
| Supervised real inference | **BLOCKED**, depends on the transport and explicit authorization |

The pinned native subscription flow uses direct HTTPS token exchange, credential-bound provider state, and HTTP Responses. The CLI_OPEN listener authenticates a task bearer, strips authorization upstream, forwards only to fixed IPv4 loopback, and accepts a bounded Responses subset. A provider `baseURL` override retains the native connection and does not supply credential isolation or trusted egress. Native workspace/environment drivers are a possible integration seam. No qualified Bubblewrap driver was identified that covers native filesystem, subprocess, MCP, plugin, and background paths while retaining the existing budget and destination guarantees. [OpenCode provider setup](https://opencode.ai/docs/providers/#chatgpt)

### D07.5 · Version-bound workspace approval

The previous final source verifier accepted a mode-only change when the bytes still matched. A temporary-file reproduction ran that verifier from `0cd96c7` and compared it with the current verifier. The current verifier rejected the same change. The workspace tests also replace a file with a different inode containing identical CRLF bytes, at which point final source verification rejects the snapshot. The real review fixture rejects an old approval even after the original bytes are restored. A new review with no further change can publish a separate Git ref without applying anything to the live index or worktree.

The native edit permission preview case is a separate regression. The public permission hook runs before the reply, and the tool hooks surround the entire tool. Neither provides a post-approval, pre-write check in native `edit`. The existing lock only coordinates cooperating native writes. Version-bound review does not provide filesystem compare-and-swap and does not fix the native preview overwrite.

### D07.5 · Native OAuth handoff preparation

The pinned binary's `auth login --help` was checked with isolated HOME and XDG directories and a cleared environment. It exposes `--standalone`, the integration target, and `--method`. The native plugin registers `chatgpt-token-sharing` for the browser flow. The continuity guide records the user-controlled command. Browser consent, authenticated catalog checks, and inference remain pending.

### D07.5 · Disposable edit containment

The supervised entry point mounts only a fresh disposable copy as writable `/work`. The editor permits only the explicit proposal paths. After the sandbox exits, the host reopens each result through the bounded no-follow snapshot and checks exact agreement with the proposal before forming the diff. The focused tests exercise changed bytes, symlinks, and hardlinks at this handoff, as well as same-byte inode replacement and source symlink substitution at final verification. The real OpenCode review test confirms normal approval, stale refusal, fresh approval, and separate Git ref publication without replacing the live source or index.

Direct pinned OpenCode still reproduces the preview-to-write conflict in the Responses fixture. The supervised path contains the defect by keeping live files outside the editor's writable mount. The final host checks are optimistic and do not claim atomicity against external writers.

### D07.5 · Brave account diagnostic

Native OpenCode v2.3.2 opened the official authorization flow in `/usr/bin/brave`. After personal consent, the integration API reported a connection and the model API exposed 18 OpenAI model IDs. No inference request was made. The first interactive invocation successfully verified these values and then exited with a fixture error because a final assertion expected the completed attempt to disappear like a cancelled pending attempt. The assertion now applies only to the automated pre-consent mode. The temporary OpenCode profile was cleaned up in both cases. The reported catalog is not a successful inference test.

### D07.6 · Production review stop and restart

`python3 -I -B tests/fase5-supervisor-stop.py` invokes the actual `review-workspace` CLI under Bubblewrap with a controlled worker artifact. The worker writes a marker after mutating only the disposable copy. The test sends SIGTERM to the supervisor at that barrier and verifies exit status 143, no approval report, no active descendants, removal of the copy, and preservation of the source bytes and mode. A new invocation with the pinned OpenCode artifacts produces the intended diff against the unchanged source. This qualifies production review teardown and fresh review. The production CLI has no session-and-budget task owner entry point, and the composed D07 fixture still shares synthetic state. Production restart with an independently protected ledger and authentication state remains unqualified.

### D07.6 · Native search I/O cancellation

`python3 -I -B tests/fase6-d07-native-io.py` compiles a test-only interposer and mounts it read-only in the existing Bubblewrap fixture. It verifies the pinned binary hashes. The fixture holds successful `readdir64` for `glob` and successful `mmap64` for literal `grep` in ripgrep before returning the result to native code. It checks that the OpenCode call is running in SQLite, interrupts it, observes that the ripgrep worker stops, resumes the same session under deny, and then checks an explicitly allowed retry. The previous call remains interrupted. The held result and restricted marker do not appear on recovery.

The libc interception trials for native `read` and paginated `read` did not reach the file barrier on the pinned Bun/OpenCode binary. Symbol interposition alone did not expose those file operations. The existing result-persistence fixture still passes for both; actual native read I/O remains open. These tests observe I/O completion at the libc boundary for search, not cancellation of an outstanding kernel request.

### D07.6 · Native profile retention preparation

The opt-in diagnostic requires a private user-owned parent outside the repository and creates a unique child for OpenCode's native XDG state. An isolated negative test substituted an executable that exits unsuccessfully for Brave and verified removal of the new profile. Fish syntax for both consent and the native model listing passed. Actual profile retention still requires fresh user consent. No new login or inference was performed in preparing this path.

GitHub Actions reported success for the starting published SHA `791c2b3e3caa16dfab4cf2a34be8962e61c664e0`. [CI run](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/46041750540)

The first OpenCode suite rerun exposed a transient SQLite reader collision with the gateway cancellation commit. The test reader now sets a one-second busy timeout on its read-only connection. The cancellation counts and terminal-status assertions are unchanged.

### D07.7 · Gateway restart negative cases

The starting public SHA was `196c3a98278b46083bf5ec28b31acbc129045cf1`. Its Actions run succeeded. [CI run](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/46087227082)

`python3 -I -B tests/fase6-d07-persist.py` passed against the production gateway with a fake loopback provider. Reopening a valid ledger with a different task ID, a missing parent directory, or a symlink as the immediate state directory fails before listening. Reopening after a killed gateway under a fresh bearer rejects the previous bearer with HTTP 401 and leaves all reservation rows unchanged. The new bearer finishes the sole available request and then receives HTTP 429. An expired task, corrupt ledger, concurrent owner, and mismatched budget remain covered.

The production supervisor still exposes review and qualification entry points without a task owner combining OpenCode restart and trusted gateway state. The smallest remaining production seam is a scoped supervisor-owned transport across its private network boundary with the gateway keeping the ledger and bearer outside the tool's mounts and environment. A gateway-only test leaves that integration unqualified. The pinned native read driver exposes its storage abstraction internally, while the previous libc interposition did not reach the pinned Bun file-transfer path. No new read I/O evidence is claimed.

### D07.7 · Cumulative path budget regression

The supervisor CLI regression supplies 60 individually valid path hints and a memory entry under a 256-byte envelope budget. Before the fix, the envelope was 1,268 bytes and the assertion failed. Afterward it was 204 bytes, including its newline, with four ordered hints and the original memory entry. The focused supervisor and F7.2 context fixtures passed.

### F8 · Bounded preliminary measurements

Use `python3 -I -B tests/f8-measure.py context` or `search`, `review`, and `recovery`. The pinned OpenCode workloads require Bubblewrap. The harness uses a 75-second deadline, a 100 ms process-tree sample, a fixed fixture allowlist, and one to three sequential trials. Environment variables are restricted to a private HOME and system PATH. The local measurements below are preliminary observations while the production entry gate remains closed.

| Fixture | Trials | Wall seconds | Sampled user/system CPU seconds | Sampled peak tree RSS MiB | Sampled process peak |
|---|---:|---:|---:|---:|---:|
| Context envelope | 2 | 1.013–1.119 | 0.61–0.62 / 0.05–0.06 | 34.7 | 2 |
| Native selective search fixture | 2 | 6.995–7.062 | 10.55–11.02 / 0.71–0.73 | 475.6–481.7 | 5 |
| Disposable edit and Git review regression | 1 | 24.177 | 36.30 / 2.32 | 515.8 | 7 |
| Composed gateway and MCP restart | 1 | 15.609 | 20.63 / 1.40 | 560.3 | 9 |

The host reported four logical CPUs and 16,635,437,056 bytes of RAM. Values combine only observed process samples and can miss work between samples. CPU percentages are relative to one core. Summed RSS can count shared pages multiple times. `wait4` provides separate launcher accounting and cannot be substituted for complete process-tree usage through nested PID namespaces. Cross-workload times are not matched OpenCode versus CLI_OPEN speedups. The review includes several intentional stop/reject cases.

The two search trials each recorded 8 synthetic provider requests and 6 tool calls on the selective path, and 4 requests and 2 tool calls on the full-read path. Tool-output estimates were 181 and 3,301 tokens, respectively. The estimator divides UTF-8 bytes by four and excludes total model context and schema tokens. This compares two explicit fixture strategies on the same engine. Gateway admission is covered separately by the Linux concurrency case. Parallel execution, matched launcher overhead, and governor overhead remain unmeasured.

The OpenCode regression observed 0.132 s from interrupting the composed launcher to confirming descendant cleanup, and 8.757 s for its resume invocation. These are single fixture observations. The recovery workload now records both intervals separately when run through the measurement harness.

### D07.8 · Workspace-driver and containment evidence

At project base `ea66e91c6a974dfd0777b5a74c375eb308337c6c`, two tests from the pinned OpenCode SDK `test/embedded.test.ts` passed under network-isolated Bubblewrap using a read-only dependency tree. The test names are `configures workspace providers through the SDK facade` and `blocks the model-selected first tool on lazy provisioning`. Their in-memory driver establishes registration and first-tool gating. Production task ownership, isolated driver execution, and supervisor-to-gateway restart qualification remain open.

The portable workspace regression rejects a source hard link inserted after initial verification and preserves the bytes on both names. The native direct edit race remains **CONTAINED** through disposable editing and reviewed Git publication. The native I/O launcher now rejects unsupported positional arguments. Its default run exercised `glob` and literal `grep`. At OpenCode `c0ad18b`, text and paginated reads go through `ReadToolFileSystem` ranges and the local driver's `node:fs/promises` `FileHandle.read`. The tested libc barrier still provides no evidence at that boundary.

### F8 · Sampler overhead and trial variability

The bounded harness now reports sample counts, sampler CPU time, and per-metric minimum, median, and maximum. The sampler uses a `scandir` pass and binary stat reads. The 100 ms setting is the sleep between samples. Whole-tree RSS may count shared pages repeatedly, and processes shorter than the sampling period can be missed.

| Synthetic fixture | Trials | Wall seconds | Sampled user / system CPU seconds | Peak sampled RSS MiB | Peak sampled processes |
|---|---:|---:|---:|---:|---:|
| Context envelope | 3 | 1.144–1.699 | 0.50–0.82 / 0.04–0.09 | 34.4–34.7 | 2 |
| Selective search | 2 | 7.673–8.706 | 10.84–12.54 / 0.75–0.87 | 489.6–492.4 | 5 |
| Disposable review, original sampler | 2 | 24.732–28.706 | 32.86–37.83 / 2.34–2.84 | 526.0–528.8 | 7 |
| Composed recovery | 2 | 16.089–16.184 | 21.68–22.67 / 1.56–1.70 | 556.9–559.2 | 9 |

In search the sampler used 0.79–0.89 CPU seconds, compared with 1.51–1.97 before the scanner change. The trials were sequential and the host load could vary. The composed recovery recorded cleanup in 0.033–0.137 s and resume in 7.608–7.655 s. Selective versus full tool output was 181 versus 3,301 estimated tokens, with six versus two tool calls. The measurements still lack a matched production/native benchmark and measured supervisor overhead.

The Linux host exposes cgroup v2 CPU, memory, and PID controllers and readable CPU and memory PSI. The existing session scope exposes read-only CPU, memory, and PID counters. An isolated writable task cgroup and user systemd delegation were not qualified. Existing Bubblewrap PID isolation and process cleanup remain the qualified mechanisms in this environment. No host resource settings were changed.

### D07.9 · Native SDK startup admission

At project base `bfc1185a9b0f4ecf2fb04478340c58ab385ac44f`, run `python3 -I -B tests/d079-sdk-admission.py` with the prepared SDK dependency tree. The launcher verifies Bun's SHA-256, uses the supervisor's Bubblewrap builder, and stages imports without installing packages. The examined SDK startup and recovery files and native read sources matched the upstream `c0ad18b` Git objects byte for byte.

The fixture uses a real native SQLite session and a seeded exhausted suspended claim. Its admission callback can look up the session while the claim and resume counter stay unchanged. Rejected and interrupted admission leave both fields unchanged. Successful admission releases the real native sweep, which terminalizes the exhausted claim without model or tool execution. This qualifies startup ordering for the named SDK service. The fixture uses an in-memory workspace driver and does not qualify workspace dispatch, credential placement, MCP reconciliation, or a production task restart.

Portable (18 unit tests plus fixture scripts), Linux, OpenCode, and the separate native search I/O fixture passed. Bubblewrap and HTTP suites ran with approval for their Linux namespace and loopback requirements. The composed restart observed seven stopped descendants, 0.067 s cleanup and 7.436 s resume. Pre-result interruption passed for `read` and paginated `read`; in-flight native file-read I/O remains inconclusive. The native edit race was reproduced and remains contained by disposable review.

Three independent context-envelope benchmark trials on Linux x86_64 (four logical CPUs, 15.49 GiB RAM) measured 0.793–1.047 s wall time (median 0.928 s), 0.490–0.808 s user CPU, 0.055–0.100 s system CPU, 29.0–59.2% sampled utilization relative to one core, 34.47–34.92 MiB sampled aggregate RSS and two sampled processes. The aggregate can count shared pages repeatedly. These trials measure the context fixture; a matched native/supervised comparison and governor overhead remain open.

### D07.9 · Native file-read syscall boundary

Run `python3 -I -B tests/fase6-d07-native-io.py --read` on Linux x86_64 with the pinned binaries. The native reader makes ranged reads through `node:fs/promises` `FileHandle.read`. The test tracer follows the isolated CLI and its threads and holds a successful `pread64` result for the selected synthetic file before returning to userspace. The paginated case places the selected line beyond the initial 256 KiB chunk and requires a positive byte offset at the barrier. The default invocation retains the existing search fixture.

Both file cases observed a running native operation and no persisted result at the barrier. Killing the tracer terminated the traced worker through `PTRACE_O_EXITKILL`. Reopening the same session under deny recorded the interruption and rejected a new attempt. A later, explicitly permitted operation with a new ID returned the selected content. The synthetic upstream received neither the denied marker nor the withheld result before the allowed retry. The barrier observes syscall completion before delivery, with no claim about interrupting an outstanding kernel request or about other Linux architectures.

### D07.9 · Bound gateway admission

Run `python3 -I -B tests/fase6-d07-persist.py` for the opt-in, persistent `--task-owner SESSION WORKSPACE` profile. The production gateway reserves a synthetic request, then the fixture kills it while the upstream is stalled. Concurrent reopen, a wrong session, a wrong workspace, omission of the binding, a reused listener credential, and corrupt owner data all fail startup. The rejected startup attempts preserve the pending reservation. Reopening with the right owner and a fresh credential changes the reservation to uncertain and preserves the task row, original deadline, and exhausted budget. An older credential gets HTTP 401 from the new listener. These checks qualify the gateway's admission boundary. The pinned SDK and gateway still require an exclusive supervisor owner above these boundaries.

### D07.10 · Production read task

Run `python3 -I -B tests/d0710-task.py` on Linux x86_64 with the prepared pinned SDK tree and Bubblewrap. The fixture exercises the public supervisor CLI against a synthetic local provider. It checks the native read result, matching task ownership and original expiry in SQLite, charged inference reservations, and absence of forwarded bearer credentials. The actual read worker verifies PID and network separation, environment allowlist, and invisibility of the trusted state directory. The cancellation case holds the provider at receipt of the persisted tool result, then stops the supervisor and checks child cleanup and retention of the active reservation. Reopening the directory is rejected before admission. The OpenCode suite runs the production task fixture when the prepared SDK dependency tree is present. Actual resumption and MCP effect reconciliation remain open.

Two sequential preliminary trials of `python3 -I -B tests/f8-measure.py production-read --runs 2` at base `64833f2` measured the whole fixture, including a completed task, a cancelled task, and rejected reopen attempts. Wall time was 16.188–16.471 s, wait4 user CPU 19.170–20.358 s, wait4 system CPU 1.567–1.583 s, sampled CPU 125.4–130.4% of one core, sampled aggregate RSS 424.1–425.0 MiB, and sampled peak process count 6–7. The host had four logical CPUs. RSS can count shared pages repeatedly. These are workload measurements and do not isolate native read latency or supervisor overhead.

Portable, Linux, and OpenCode passed on the read-task implementation. OpenCode ran the new production task fixture. Both native file-read cases and both native search cases passed in their standalone I/O regressions.
