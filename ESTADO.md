# Estado del proyecto

Fase autorizada y en curso: 1 (P-1). Fase 2 requiere aprobación al cierre.

## Fase 0 cerrada

- Clon oficial existente en `upstream/upstream/opencode`. Historial no superficial, árbol limpio, rama `dev` alineada con la referencia local `origin/dev`, SHA `73a0eae88de47f10068a0f9dc7a743638fa3d830`.
- Licencia MIT. Monorepo con Bun 1.4.4, `bun.lock` y `flake.lock`. La guía documenta `bun install` y `bun dev [directory]`.
- Entorno observado: CachyOS, Linux 7.3.3-1-cachyos, x86_64, Bash 5.3.20, Codex CLI 0.171.0, UID 1000. Sin indicadores WSL en el kernel consultado.
- La inspección inicial terminó sin escrituras. Ninguna plataforma tiene arranque, diagnóstico o escritura aislada calificados.

## Fase 1

- Base seleccionada: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. La publicación oficial del 18 de noviembre de 2026 coincide con el tag local.
- El usuario autorizó Bun 1.4.4 y las dependencias fijadas en `bun.lock`, previa revisión de scripts. Se revisó el postinstall raíz y la ruta de build de CI. Queda por revisar cualquier script de terceros que se vaya a ejecutar.
- Git propio inicializado. El remoto público autorizado es CLI_OPEN. La primera consulta Git al remoto no devolvió ramas ni etiquetas.
- Siguiente acción: registrar y publicar el checkpoint inicial tras verificar su contenido. Después, preparar una copia separada del SHA fijado y completar la revisión previa a la instalación. Véase [PRUEBAS.md](docs/PRUEBAS.md).

## Reanudar el trabajo

Leer `AGENTS.md`, el plan y el informe antes de actuar. Revisar [decisiones](docs/DECISIONES.md), [cambios](docs/CAMBIOS.md), [pruebas](docs/PRUEBAS.md), el estado Git propio y el SHA upstream. Reutilizar la evidencia de la misma revisión y entorno. Revalidar cuando cambien el SHA, el entorno o las entradas de la prueba.

Después de cada hito, actualizar este archivo con la siguiente acción y anotar decisiones, cambios y resultados en su registro correspondiente. Guardar el checkpoint en Git local cuando esté disponible. Los registros aportan contexto y evidencia. Las autorizaciones se comprueban con el usuario y los permisos efectivos de la sesión.
