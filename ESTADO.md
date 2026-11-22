# Estado del proyecto

Fases 1 (P-1), 2 (P0) y 3 (P1) completadas. Fase 4 (P2) en curso para Linux x86_64.

## Fase 0 cerrada

- Clon oficial existente en `upstream/upstream/opencode`. Historial no superficial, árbol limpio, rama `dev` alineada con la referencia local `origin/dev`, SHA `73a0eae88de47f10068a0f9dc7a743638fa3d830`.
- Licencia MIT. Monorepo con Bun 1.4.4, `bun.lock` y `flake.lock`. La guía documenta `bun install` y `bun dev [directory]`.
- Entorno observado: CachyOS, Linux 7.3.3-1-cachyos, x86_64, Bash 5.3.20, Codex CLI 0.171.0, UID 1000. Sin indicadores WSL en el kernel consultado.
- La inspección inicial terminó sin escrituras. Ninguna plataforma tiene arranque, diagnóstico o escritura aislada calificados.

## Fase 1

- Base seleccionada: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. La publicación oficial del 18 de noviembre de 2026 coincide con el tag local.
- El usuario autorizó Bun 1.4.4 y las dependencias fijadas en `bun.lock`, previa revisión de scripts. Se revisó el postinstall raíz y la ruta de build de CI. Queda por revisar cualquier script de terceros que se vaya a ejecutar.
- Git propio inicializado. El checkpoint inicial `cf7e0f9` se publicó en `origin/main` mediante push normal tras verificar el índice y las referencias remotas.
- Copia separada del SHA fijado en `.fase1/opencode`. El binario oficial de Bun 1.4.4 está en `.fase1/tools` y pasó la verificación SHA-256.
- Dependencias congeladas instaladas dentro de Bubblewrap con `--ignore-scripts`. El lockfile coincide con el SHA fijado.
- Build de CLI Linux x86_64 completado con `OPENCODE_VERSION=2.3.2`. El artefacto reporta `opencode v2.3.2` y ofrece `--standalone` y `--server`.
- El smoke test del servicio compilado y la prueba de terminación standalone pasaron en Bubblewrap con red privada. Pasaron también 23 pruebas no interactivas de upstream.
- La calificación usa una API simulada en loopback y, por separado, OpenRouter con el modelo fijo `liquid/lfm-3-1.7b:free` y presupuesto de USD 0. La inferencia física local queda pendiente fuera de esta puerta. No hay modelo ni runtime de inferencia local instalado para retirar.
- Pasaron los ocho casos de CLI contra el simulador de chat y el señuelo recibió cero solicitudes en modo standalone. Las 440 pruebas anteriores y la invocación MCP sintética conservan su evidencia.

- OpenRouter confirmó costo USD 0 en las dos respuestas de la prueba final. Pasaron los argumentos de la herramienta y la devolución del marcador sintético. La prueba remota usó directamente la API; la CLI se calificó con loopback.

## Fase 2

- Supervisor mínimo en `implementacion/supervisor` con `doctor` y `plan`. Sin dependencias adicionales. OpenCode conserva su función de motor y su CLI original.
- El doctor identifica entorno, arquitectura, shell configurada, WSL y elevación. Reporta el aislamiento como no verificado. `PLAN` rechaza comandos y escrituras.
- Pruebas automatizadas aprobadas en CachyOS x86_64. Las rutas macOS, Windows y WSL quedan pendientes de ejecución en sus entornos.
- PLAN se mantiene separado de la entrada explícita DIAG.

## Fase 3

- Broker MCP local de solo lectura con cinco consultas tipadas, entrada y salida limitadas, y auditoría sin argumentos ni valores. Se comprobó con pruebas Python y con el SDK MCP instalado en el checkout fijado.
- Prioridad Linux x86_64. Probado en CachyOS; Arch, Ubuntu, Debian, Fedora, WSL2, macOS y Windows quedan pendientes de validación propia.
- La CLI compilada descubrió e invocó el broker desde una sesión privada. El proveedor simulado recibió el resultado y el señuelo recibió cero solicitudes. [Evidencia](docs/evidencias/FASE3.md)

## Fase 4

- Se inició la calificación en CachyOS x86_64. La prueba sintética Bubblewrap verificó escritura en el montaje permitido, rechazo en montajes protegidos, traversal y enlaces, red privada, entorno limpio y fin de la carga hija tras timeout.
- Siguiente acción: calificar la frontera con la sesión completa de OpenCode, incluido el control de extensiones y configuraciones no aprobadas. WORKSPACE sigue deshabilitado y el doctor conserva el estado de aislamiento no verificado.

## Reanudar el trabajo

Leer `AGENTS.md`, el plan y el informe antes de actuar. Revisar [decisiones](docs/DECISIONES.md), [cambios](docs/CAMBIOS.md), [pruebas](docs/PRUEBAS.md), el estado Git propio y el SHA upstream. Reutilizar la evidencia de la misma revisión y entorno. Revalidar cuando cambien el SHA, el entorno o las entradas de la prueba.

Después de cada hito, actualizar este archivo con la siguiente acción y anotar decisiones, cambios y resultados en su registro correspondiente. Guardar el checkpoint en Git local cuando esté disponible. Los registros aportan contexto y evidencia. Las autorizaciones se comprueban con el usuario y los permisos efectivos de la sesión.
