# Fase 3 — Broker de diagnóstico

Se verificó en CachyOS Linux x86_64, con OpenCode v2.3.2 fijado en `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. Arch, Ubuntu, Debian, Fedora, WSL2, Windows nativo y macOS quedan pendientes de pruebas reales. El backend utiliza la biblioteca estándar de Python y las interfaces Linux `/proc` y `statvfs`.

## Uso

Iniciar `python3 -I -B implementacion/supervisor diag` como comando local de MCP **solo** en una sesión DIAG aprobada. El supervisor lanza el broker con un entorno vacío. La siguiente estructura corresponde al esquema V2 y usa rutas de ejemplo. Se verificó mediante una sesión `opencode --standalone run` con configuración privada.

```json
{
  "mcp": {
    "servers": {
      "diag": {
        "type": "local",
        "command": ["/ruta/a/python3", "-I", "-B", "/ruta/al/proyecto/implementacion/supervisor", "diag"],
        "protocol": "legacy",
        "codemode": false
      }
    }
  }
}
```

PLAN no lanza OpenCode ni el broker. Los datos reflejan los recursos visibles al proceso; ejecutar el broker en un namespace no concede visibilidad del host. La conexión usa exclusivamente las tuberías privadas del proceso iniciado. La incorporación de este catálogo a una sesión de producto con IA queda sujeta al aislamiento de esa plataforma.

| Herramienta | Datos devueltos |
|---|---|
| `cpu` | CPU lógicas visibles y carga de 1, 5 y 15 minutos |
| `memory` | RAM total y disponible en bytes según `/proc/meminfo` |
| `storage` | Bytes totales y disponibles para el sistema de archivos raíz visible |
| `processes` | Conteo visible y aviso de truncamiento a 4096 entradas examinadas |
| `environment` | Sistema, arquitectura, indicador de kernel WSL y perfil DIAG |

Todas las herramientas aceptan un objeto vacío. Las salidas tienen esquemas y van en `structuredContent`, con representación textual para clientes compatibles. Cada trama está limitada a 8192 bytes antes del salto de línea. La auditoría en stderr registra solo el nombre del catálogo y el resultado. La API rechaza comandos, rutas, identificadores de procesos, URLs y parámetros desconocidos. Los backends para otros sistemas pueden añadirse detrás del mismo catálogo después de probarse.

## Descubrimiento e invocación

El esquema V2 de este SHA admite `mcp.servers`; el proceso servidor consume `OPENCODE_CONFIG_CONTENT` o la configuración del workspace. El handler de `mcp list` consulta `Mcp.Service.servers()`, que enumera el registro en memoria. La consulta inicial en un servidor privado recién iniciado devolvió una lista vacía. No se estableció por qué la activación todavía no había poblado ese registro. El flujo real de sesión sí ofreció la herramienta `diag_environment` al proveedor simulado.

OpenCode agrega `_meta` al sobre de `tools/call` para la sesión y el progreso. El broker acepta ese objeto y lo descarta antes de ejecutar, preservando el esquema vacío de `arguments`. Se verificó la respuesta `profile=DIAG` y `system=Linux` de la CLI compilada con `bun tests/fase1-loopback.ts RUTA_BINARIO RUTA_SUPERVISOR` en Bubblewrap, con configuración privada, red externa desconectada y el señuelo sin solicitudes.
