# Cambios

## 2026-11-21 · Continuidad y base de la Fase 1

- `ESTADO.md` registra el cierre de Fase 0, el SHA seleccionado y el procedimiento de reanudación.
- `docs/DECISIONES.md`, `docs/CAMBIOS.md` y `docs/PRUEBAS.md` conservan los hitos y su evidencia.
- `.gitignore` excluye el clon, el área temporal de pruebas y los directorios privados del entorno.
- La autorización específica permitió inicializar Git propio en `fase-1`. Se ampliaron las exclusiones a dependencias, archivos de entorno y claves comunes.
- Se configuró `origin` y se publicó `cf7e0f9` en `main`. La copia y Bun se guardaron bajo `.fase1/`, excluida del repositorio.
- Se instalaron las dependencias fijadas únicamente en la copia separada, con scripts de instalación deshabilitados.
- `AGENTS.md` registra la autonomía dentro de cada fase aprobada y las acciones que requieren autorización.
- Se generó la CLI Linux x86_64 en el área excluida `.fase1/`.
- Se registraron las pruebas de servicio, sesión no interactiva y terminación standalone en `docs/PRUEBAS.md`.
- Se publicó `8abba6a` en `origin/main` tras revisar los cinco archivos del checkpoint. Se adaptaron el plan, el informe y los registros al alcance revisado de inferencia de P-1.
- Se registraron los resultados de replay HTTP, MCP sintético, herramientas y resolución de servidor. No había un modelo o runtime de inferencia instalado que retirar.
- El checkpoint revisado `5ec7fa4` se publicó en `origin/main` mediante fast-forward. Se añadió `tests/fase1-loopback.ts` para los ocho casos y el señuelo. El núcleo permanece intacto.
- El checkpoint `d0dee98` se revisó y se publicó en `origin/main` mediante fast-forward.
- Se registró la autenticación correcta y el bloqueo de disponibilidad del modelo fijado.
- Se actualizó el modelo en el plan y el informe, se añadió `tests/fase1-openrouter.py` y se registró el cierre de Fase 1.
- Se añadieron `implementacion/supervisor/__main__.py` y `tests/test_supervisor.py` para el doctor y el perfil PLAN de Fase 2.
- Se añadió `implementacion/broker/__main__.py` con cinco consultas de solo lectura, una entrada DIAG explícita en el supervisor y pruebas de catálogo, rechazo y límites.
- Se adaptó el sobre MCP del broker y se añadió la prueba focalizada de integración CLI con DIAG. Se inició P2 con `tests/fase4-linux.py`.
- Se añadió un recorrido de calificación de OpenCode y el broker en Bubblewrap y una prueba de degradación con Bubblewrap ausente del PATH. [Evidencia](evidencias/FASE4.md)
- Se incorporó `qualify-linux` al supervisor, la prueba inicial de copia y diff en `tests/fase5-workspace.py`, y el registro de la incidencia no bloqueante de inventario MCP.
