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
- Pasó la sesión integrada con el catálogo restringido, el broker aprobado, denegación de escritura y `skill`, exclusión del plugin local y MCP de prueba, SIGINT y limpieza de procesos. Tres pruebas del supervisor pasaron, incluida la degradación con Bubblewrap ausente del PATH. Queda pendiente validar el arrancador del supervisor ante fallo efectivo del backend. [Evidencia](evidencias/FASE4.md)
