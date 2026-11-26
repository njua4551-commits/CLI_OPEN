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

## Estabilización · saturación del gateway (2026-11-25)

- `python3 -I -B tests/fase6-concurrencia.py` pasó. Ráfaga de 12 clientes con límite 2: respuestas 200 válidas y rechazos 503 (`concurrency`), pico de upstream 2 y ninguna solicitud perdida. Ráfaga de 10 con endpoint de 1 s: 503 inmediato al exceso, pico 2 y recuperación a 200 tras liberar. 2 clientes streaming completaron `[DONE]`. Con timeout 1 s y endpoint de 2 s: 502 en ~1 s. Sin `BrokenPipe`.
