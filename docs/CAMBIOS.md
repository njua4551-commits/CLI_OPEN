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
