# Estado del proyecto

Fase 6 (P3) cerrada para el perfil local sintético. Fase 7 en curso.

## Cerrado

- Fases 0 a 5 cerradas para los flujos acotados de `docs/PRUEBAS.md` y `docs/evidencias/`. Entorno calificado: CachyOS Linux x86_64.
- Base: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`, sin cambios en el núcleo. Copia, Bun 1.4.4 y binario Linux en `.fase1/`, excluidos de Git.
- Gateway local en `implementacion/gateway/__main__.py`: modo stdin de una solicitud y modo `--listen` OpenAI-compatible. Destino fijo `127.0.0.1`, sin proxy, redirecciones, reintentos ni proveedor alternativo; límites de cuerpo, tokens, respuesta y plazo; costo distinto de cero rechazado.

## Fase 6 cerrada

- `bun tests/fase6-cli-gateway.ts RUTA_AL_BINARIO` pasó: la CLI completó una llamada a herramienta a través del gateway, no se reenvió la credencial, un costo `0.001` fue rechazado y un endpoint caído no produjo salida alternativa.
- Aceptación verificada en el perfil local sintético: destino y límites fijados, sin ruta remota alternativa y sin fallback ante fallo local.
- El modelo físico local y el presupuesto remoto se aplazan por decisión explícita (D07). La inferencia remota de producto sigue deshabilitada.

## Fase 7 en curso

- Módulo 1 cerrado: memoria persistente por proyecto con recuperación selectiva e invalidación automática. `tests/fase7-memoria.py` pasó.
- Módulo 2 iniciado: `memoria context` recupera entradas vigentes y relevantes dentro de un límite de bytes, con un sobre de autoridad nula.
- Siguiente acción: probar una sesión sintética de OpenCode donde el supervisor incorpore ese sobre como datos no confiables, sin modificar permisos ni enviar datos fuera de loopback.

## Reanudar el trabajo

Leer `AGENTS.md`, `PLAN_PARA_CODEX.md`, `INFORME_TECNICO.md` y `CONTINUAR.md` antes de actuar. Revisar [decisiones](docs/DECISIONES.md), [cambios](docs/CAMBIOS.md), [pruebas](docs/PRUEBAS.md), el estado Git y el SHA fijado. Reutilizar la evidencia de la misma revisión y entorno.

Después de cada hito, actualizar este archivo con la siguiente acción y anotar decisiones, cambios y resultados en su registro. Guardar el checkpoint en Git local; publicar solo con autorización. Los registros aportan contexto y evidencia.
