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
