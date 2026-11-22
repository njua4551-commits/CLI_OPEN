# Fase 4 — Calificación Linux

Entorno observado: CachyOS Linux x86_64, OpenCode v2.3.2 en `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. Los resultados son de una topología sintética. Arch, Ubuntu, Debian, Fedora y las demás plataformas requieren validación propia.

| Frontera | Evidencia |
|---|---|
| Archivos | El probe de Bubblewrap escribió en el montaje autorizado. Los montajes de control permanecieron intactos ante rutas absolutas, traversal y enlaces. El runtime de la prueba integrada montó la CLI, el broker y los fixtures de prueba como solo lectura y usó `/tmp` privado. |
| Red y credenciales | El probe no llegó al listener del host. La CLI usó solo el simulador en el loopback privado. Se vació el entorno del namespace y el señuelo del servicio OpenCode recibió cero solicitudes. |
| Procesos | El probe anterior observó que el hijo dejó de escribir tras el timeout. SIGINT cerró el stream durante una sesión aislada. Al finalizar no quedaron procesos con los argumentos esperados de la CLI, servidor ni broker en el namespace. |
| Configuración y extensiones | Con `OPENCODE_CONFIG_PROJECT_DISABLE=true` y configuración confiable inyectada, un archivo de proyecto que permitía todas las herramientas y declaraba un MCP adicional no alteró el catálogo observado. El plugin local de prueba no creó su marcador. |
| Herramientas | El proveedor simulado vio `diag_environment` y `skill`. El primero devolvió el diagnóstico previsto. Las solicitudes sintéticas de `skill` y de escritura fuera del workspace devolvieron errores sin contenido. El archivo de escritura no se creó. No aparecieron herramientas de shell, edición o red en el catálogo. |
| PLAN y degradación | El supervisor conserva PLAN y DIAG. Con Bubblewrap ausente del PATH, el doctor siguió reportando PLAN sin ejecución ni escritura y aislamiento no verificado. |

## Reproducción focalizada

Desde la raíz del proyecto, con Bubblewrap, Bun y el artefacto fijado ya disponibles:

```bash
bwrap --die-with-parent --unshare-user --unshare-pid --unshare-ipc \
  --unshare-net --unshare-uts --disable-userns \
  --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib /lib64 \
  --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind "$PWD/.fase1" /fase1 --ro-bind "$PWD/tests" /tests \
  --ro-bind "$PWD/implementacion" /implementacion \
  --clearenv --setenv PATH /usr/bin:/bin \
  /usr/bin/timeout 45 /fase1/tools/bun-linux-x64-baseline/bun \
  /tests/fase1-loopback.ts /fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode \
  /implementacion/supervisor --qualification
```

La prueba devuelve `PASS diag`, `PASS cancel`, `PASS restricted catalog, unapproved plugin and process cleanup` y `PASS standalone decoy: 0 requests`. El diseño de montajes para otras distribuciones aún debe ejecutarse allí.

## Límites de la calificación

`mcp list` en frío sigue siendo una observación de la consulta de inventario. La sesión calificada sí descubrió, invocó y obtuvo el resultado del broker. Consultar [Fase 3](FASE3.md) para el análisis del registro en memoria.

El montaje escribible del probe y la sesión compilada se calificaron en pruebas distintas. La sesión de OpenCode se lanzó desde el fixture, fuera del punto de entrada de producto del supervisor. Falta calificar un lanzador de supervisor que use esta frontera y comprobar la degradación ante un fallo de arranque del backend. La autorización condicional de Fase 5 sigue sin activarse.
