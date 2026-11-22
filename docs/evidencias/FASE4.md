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
python3 -I -B implementacion/supervisor qualify-linux
```

El supervisor monta el binario, Bun, el fixture y la implementación como solo lectura. El comando es fijo y no acepta programas o argumentos arbitrarios. Si el backend falla, sale con error y conserva PLAN y DIAG. La prueba negativa observada en el entorno restringido fue un error NETLINK_ROUTE al configurar loopback.

La prueba devuelve `PASS diag`, `PASS cancel`, `PASS restricted catalog, unapproved plugin and process cleanup` y `PASS standalone decoy: 0 requests`. El diseño de montajes para otras distribuciones aún debe ejecutarse allí.

## Límites de la calificación

Incidencia no bloqueante de inventario: `mcp list` en frío puede devolver una lista vacía. La sesión calificada sí descubrió, invocó y obtuvo el resultado del broker. Consultar [Fase 3](FASE3.md) para el análisis del registro en memoria.

La calificación corresponde a la topología sintética del supervisor en Linux. El montaje escribible se ejercitó como una copia desechable al inicio de la Fase 5. No se habilitó todavía un comando de producto WORKSPACE.
