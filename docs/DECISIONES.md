# Decisiones técnicas

- **D01 · Motor y alcance.** OpenCode aporta CLI, TUI, sesión y extensiones existentes. Codex desarrolla el proyecto. El clon original queda en su ruta actual. Las pruebas usarán una copia separada y el núcleo queda fuera del alcance de cambios.
- **D02 · Base P-1.** `v2.3.2` en `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. La selección fija la revisión a calificar. La decisión de avanzar depende de los resultados. [Release oficial](https://github.com/anomalyco/opencode/releases/tag/v2.3.2)
- **D03 · Continuidad.** Git propio en la carpeta contenedora, excluyendo `upstream/` y el área temporal `.fase1/`. `ESTADO.md` sirve como punto de entrada. Los registros bajo `docs/` conservan justificación, cambios y evidencia por hito. Si aparece evidencia que afecta una decisión aprobada, documentar la discrepancia y solicitar revisión antes de cambiarla.
- **D04 · Baseline.** Reutilizar el build y la prueba de ciclo de vida de CI. Evitar `dev:live` en la sesión privada porque se conecta al servicio existente. Verificar los flags con el binario exacto antes de usarlos.
- **D05 · Repositorio público.** El usuario designó `https://github.com/njua4551-commits/CLI_OPEN.git` como `origin`. Verificar referencias y contenido antes de publicar. Conservar cualquier historial remoto; usar push normal.
- **D06 · Autonomía.** El usuario autorizó acciones rutinarias y commits locales dentro de la fase vigente. Las nuevas publicaciones requieren autorización. Véase [AGENTS.md](../AGENTS.md).
