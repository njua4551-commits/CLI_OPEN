# Pruebas y evidencia

| Hito | Comprobación | Resultado |
|---|---|---|
| Fase 0 | Git, licencia, manifiesto, lockfiles, guía de contribución y entorno | Inventario completado. Véase [ESTADO.md](../ESTADO.md). |
| Fijación de P-1 | `git rev-parse 'v2.3.2^{commit}'` y commit asociado al release oficial | Coinciden en `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. |
| Revisión estática | Manifiesto raíz, `fix-node-pty.ts`, acción `setup-bun`, workflow `check-test.yml` y build de CLI en el tag | CI instala con lockfile congelado. El postinstall ajusta el bit de ejecución de helpers locales de node-pty. El manifiesto confía en esbuild, node-pty, protobufjs y electron. El build limpia su salida y puede descargar activos de Bun incluso con `--skip-install`. |
| Prerrequisitos | Consulta del PATH y `git init -b fase-1` | Bun y Ollama no resuelven en PATH. Git devolvió `.git/hooks/: Read-only file system`. La inicialización y el checkpoint quedaron bloqueados. |
| Integridad del clon | `git --no-optional-locks status --short --branch` y `git rev-parse HEAD` | Árbol limpio en `dev`, SHA `73a0eae88de47f10068a0f9dc7a743638fa3d830`. |
| Git propio y remoto | `git init -b fase-1` con autorización específica y `git ls-remote --symref` | Repositorio propio inicializado. CLI_OPEN respondió correctamente y no devolvió ramas ni etiquetas. |

## Pendiente

1. Preparar copia exacta del tag y verificarla. Revisar los scripts de terceros que vayan a ejecutarse, instalar Bun 1.4.4 localmente y aplicar `bun install --frozen-lockfile` con el lockfile fijado.
2. Ejecutar desde `packages/cli` los comandos de CI `bun run script/build.ts --single --skip-install` y `bun run script/service-smoke.ts`. Verificar versión y opciones del artefacto.
3. Verificar identidad y conexiones de un servidor privado frente a un servicio señuelo, lectura sintética y ciclo de vida de procesos hijos. Probar MCP sintético aprobado.
4. Calificar un modelo local con argumento inválido, ruta Windows escapada, ruta Unicode, lectura acotada, respuesta grande, llamadas múltiples, cancelación y fallo recuperable. Comprobar que la caída local no desencadena inferencia remota.

Build, arranque, llamadas a herramientas, MCP, cancelación y aislamiento efectivo siguen sin resultados de ejecución.
