# Continuar CLI_OPEN

## Punto de reanudación

**Referencia pública:** `dfcdd822b358b96f19be2d64c0ad1b61d1404f6a`.

**Checkpoint técnico de la prueba HTTP física:** `5335b70c2bece3a3d8c0256358e1d16e19c88350` (`5335b70`). Anterior: `242c3b1`. Rama `fase-1` / `origin/main`.
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

## Siguiente puerta de estabilización

- Ejecutar `python3 -I -B tests/fase6-agente-local.py` con los artefactos existentes. El supervisor construye el aislamiento y fija la regla de lectura. OpenCode, gateway y llama.cpp comparten únicamente el loopback privado. Mantener la distinción entre operación HTTP, llamada generada, lectura efectiva y respuesta final.
- La lectura permitida y la denegada ya pasaron. La respuesta final quedó vacía. La próxima prueba debe reproducir fuera de OpenCode, mediante el mismo gateway privado, la petición posterior a `read` para distinguir plantilla o modelo de serialización de la sesión.
- La auditoría nativa y la línea base HTML están en [DECISIONES.md](docs/DECISIONES.md) y [PRUEBAS.md](docs/PRUEBAS.md). Medir el candidato de filtrado en fixtures aislados después de cerrar la validación local. La recuperación externa requiere calificación propia.
- D07 remoto y Repo Map conservan sus puertas vigentes.

## Validación con API · Perfil preparado, ejecución bloqueada

Candidato de prueba: OpenRouter, `google/gemma-4-26b-a4b-it:free`, endpoint `google-ai-studio`. Revalidar precio cero, disponibilidad, privacidad, cuota y compatibilidad antes de cada corrida. Autorizar explícitamente ese destino y este contenido: instrucciones, esquema de `read`, nombres de archivos y resultados creados para el fixture. Mantener la credencial fuera de Bubblewrap e inyectarla únicamente en el componente remoto de confianza. La credencial no se introduce en archivos del repositorio ni en el chat.

Configurar el proveedor nativo `@opencode/ai/providers/openai-compatible` con el alias `fixture`, herramientas habilitadas, `baseURL` igual al loopback privado del gateway con sufijo `/v1` y una clave ficticia local. El destino HTTPS y la clave real pertenecen al lado confiable. El gateway de este checkpoint solo reenvía a loopback. El script `tests/fase1-openrouter.py` demuestra un patrón reutilizable de HTTPS con verificación de precio y selección fija de proveedor, pero está fijado a Liquid y no califica un canal desde Bubblewrap.

Para esta prueba, proponer concurrencia 1, hasta 6 solicitudes de inferencia, 4096 tokens de entrada y 384 de salida por solicitud, plazo global 120 s y cero reintentos o fallback. Reservar cada solicitud y su presupuesto antes de enviar. Fallar si OpenCode intenta llamadas auxiliares fuera del presupuesto, si la cuota o precio no se confirma, o si el componente remoto no puede impedir rutas alternativas. Cancelar el upstream al cancelar el cliente. Verificar el costo y uso reportados o registrar que no se pudieron confirmar. El control de entrada requiere una cota verificable para el modelo o rechazo antes de enviar.

A y B deben usar el fixture temporal y la misma política de lectura que la sesión física. C debe repetir el historial sintético con roles y el mismo identificador en `assistant.tool_calls` y `tool.tool_call_id`. Usar SSE en A y B para D y reservar la solicitud restante para cancelar un stream controlado. El error de transporte puede probarse con fixture local. Antes de usar la API, calificar con un upstream simulado un canal de destino fijo desde el espacio de red privado y comprobar cancelación, bloqueo de ruta directa, redirecciones y ausencia de credenciales dentro del sandbox.


### Revalidación previa de D07

La credencial OpenRouter no se observó en el entorno efectivo, en los metadatos activos o inactivos de OpenCode ni en los archivos de inicio inspeccionados. La cuota autenticada sigue pendiente. Usar el mecanismo seguro del entorno para hacerla disponible al proceso confiable, sin incluirla en el chat ni en archivos del proyecto. La consulta autenticada de cuota se limita a `GET /api/v1/key` con salida filtrada.

El diagnóstico `python3 -I -B tests/fase6-d07-cancel.py` reproduce una desconexión del cliente con un SSE upstream inactivo. El socket upstream sobrevivió la ventana de cancelación de 1 s y cerró con el timeout configurado de 5 s. Antes de habilitar el perfil remoto, calificar cancelación independiente del progreso del stream, autenticación del canal y reserva de presupuesto acumulado del lado confiable. Los controles de loopback local no acreditan esos tres requisitos.

## OpenCode Console gratuito · D07

Usar `opencode/deepseek-v4.1-flash-free` como candidato para una sesión oficial permitida cuando haya un canal calificado. El catálogo público confirmó herramientas y costo anunciado cero. La API oficial restringe los modelos chat gratuitos al uso dentro de OpenCode. El proveedor nativo está presente en el motor fijado, pero su acceso directo no atraviesa el gateway local. El gateway independiente tampoco está autorizado como cliente gratuito. Calificar únicamente una ruta oficialmente admitida que preserve autenticación, límites acumulados, destino fijo y Bubblewrap. Si no existe una ruta admitida, mantener A–D remotas bloqueadas.

El diagnóstico de cancelación SSE ahora pasa dentro de 1 s con proveedor simulado. Se mantienen pendientes la autenticación del canal y la reserva verificable de presupuesto acumulado de D07.

## Lectura web · Filtro HTML opcional

Con el OpenCode V2 fijado, añadir el directorio absoluto `implementacion/lectura-web` a `plugins` en una configuración confiable. Ejemplo: `{"plugins":["/ruta/a/CLI_OPEN/implementacion/lectura-web"]}`. Retirar esa entrada restaura la salida original. Mantener deshabilitada la recuperación externa en los perfiles aislados hasta calificar la red. Para obtener el original, desactivar el plugin o solicitar a `webfetch` el formato `html`, sujeto a los límites y permisos nativos. Los encabezados y secciones únicas se conservan en la salida filtrada.

Con artefactos F1 ya disponibles, ejecutar `bun tests/lectura-web-lineabase.ts .fase1/opencode baseline` y repetir con `filtered`. El fixture de integración recibe como único argumento la ruta al binario OpenCode y debe ejecutarse en Bubblewrap con `--unshare-net`, HOME temporal, y montajes de solo lectura del binario, tests y plugin. Usa servidores de loopback dentro del namespace privado.

D07 permanece **BLOCKED** por autenticación y presupuesto acumulado sin calificar y por falta de una ruta gratuita autorizada. La cuota temporal informada por el usuario añade una razón para aplazar inferencia. La cancelación SSE ya corregida se conserva. Retomar D07 con un proveedor autorizado después de demostrar autenticación, reserva y aislamiento con un proveedor simulado.

## Suites reproducibles

- `python3 -I -B tests/run-suite.py portable` requiere Python 3.11+ y Node.js 18+. Ejecuta unitarias, memoria, contexto y el núcleo del filtro HTML sin artefactos ignorados.
- `python3 -I -B tests/run-suite.py linux` requiere Linux x86_64, Bubblewrap sin privilegios y sockets de loopback. Ejecuta aislamiento, edición de copia, gateway, concurrencia y cancelación SSE.
- `python3 -I -B tests/run-suite.py opencode` verifica versión y SHA-256 de los binarios de calificación en `.fase1`. Ejecuta edición revisada, calificación del supervisor e integración de gateway, contexto y webfetch bajo Bubblewrap. Los hashes corresponden a los binarios locales calificados. Si un build produce bytes distintos se requiere recalificarlo, aunque coincida la versión.
- Para preparar el checkout previo al build, verificar el tag `v2.3.2` contra `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` y exportar ese SHA con `git archive` a un directorio nuevo. Usar Bun 1.4.4 del [release oficial](https://github.com/oven-sh/bun/releases/tag/bun-v1.4.4). Los comandos observados de instalación congelada y build están en [PRUEBAS.md](docs/PRUEBAS.md). No se repitió la construcción completa en esta iteración. El perfil no descarga nada.
- El benchmark HTML requiere el checkout preparado con dependencias. La prueba física requiere el GGUF y llama.cpp existentes. OpenRouter queda fuera de las suites deterministas.

El comando `inject-context --max-context-bytes` acepta 128–16384 bytes para el JSON compacto de memoria, incluido su salto de línea. El supervisor conserva entradas en orden de relevancia, omite duplicados y se salta entradas que no caben. Las instrucciones fijas y la consulta quedan fuera de ese presupuesto. El procesamiento previo rechaza sobres de entrada por encima de 64 KiB.

## Reanudar una tarea con OpenCode

En el mismo workspace y con el estado de sesión conservado, reutilizar `opencode --standalone run --session ID "siguiente paso"`. El ID aparece en los eventos JSON del run anterior. La regresión verifica que un proceso nuevo recupera el resultado de una herramienta ya completada sin ejecutarla otra vez. Una herramienta interrumpida sigue necesitando verificar el estado antes de repetirla.

El resultado de `tool.execute.after` de `webfetch` no incluye una consulta explícita de relevancia. F7.3 conserva el filtro por duplicados y aplaza la selección por secciones. El siguiente trabajo sobre contexto es probar una consulta explícita autorizada y una reserva compartida cuando haya dos fuentes integrables.

## CI en Ubuntu 24.04

Si el job Linux falla en el arranque de Bubblewrap con `Failed RTM_NEWADDR`, comprobar el valor de `kernel.apparmor_restrict_unprivileged_userns`, la versión de Bubblewrap y la carga del perfil oficial `bwrap-userns-restrict`. El workflow lo carga desde el paquete de Ubuntu cuando la restricción está activa. Los tests siguen ejecutándose como usuario normal. La nueva ejecución remota está pendiente de publicación autorizada.

El run posterior a `810af0c` superó AppArmor y falló al iniciar Python. F4 ahora usa el constructor del supervisor para conservar los montajes de bibliotecas del host. Al publicar, verificar las rutas `sandbox runtime` del job Linux y el resultado de ambos jobs. [Run de referencia](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/45864416809)
