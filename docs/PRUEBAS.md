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

## Pendiente

1. Revisar cualquier script de instalación de terceros que el build llegue a requerir. Los scripts permanecen deshabilitados.
2. Verificar identidad y conexiones de un servidor privado frente a un servicio señuelo, lectura sintética y ciclo de vida de procesos hijos. Probar una invocación MCP con un servidor sintético aprobado.
3. Calificar un modelo local con argumento inválido, ruta Windows escapada, ruta Unicode, lectura acotada, respuesta grande, llamadas múltiples, cancelación y fallo recuperable. Comprobar que la caída local no desencadena inferencia remota. Los ejecutables `ollama`, `lms` y `llama-server` no aparecen en PATH. Hace falta identificar un modelo y un endpoint existentes o aprobar su provisión local.

La lectura en una sesión con un modelo, la invocación MCP sintética y la calificación de aislamiento siguen pendientes.
