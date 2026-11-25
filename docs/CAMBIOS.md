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
- Se añadió `review-workspace`, el trabajador aislado y la cobertura de creación, reemplazo, concurrencia, reversión por descarte y diff. [Evidencia](evidencias/FASE5.md)
- Se sustituyó la escritura propia por la herramienta nativa de OpenCode y se añadió la publicación Git de revisiones aprobadas. Se inició el contrato del gateway de Fase 6.
- Se añadió el adaptador de loopback en `implementacion/gateway/__main__.py`, su fixture HTTP en `tests/fase6-gateway.py` y el punto de reanudación en `CONTINUAR.md`.

## 2026-11-21 · Transporte CLI → gateway de Fase 6

- `implementacion/gateway/__main__.py` añade `--listen`: endpoint OpenAI-compatible local que reutiliza el validador y el destino fijo del modo stdin. Acepta `model`, `max_completion_tokens`, `stream_options` y mensajes con `tool_calls`/rol `tool`; limita `max_tokens` a 512, el cuerpo a 128 KiB y la respuesta a 64 KiB, y valida modelo y costo cero también en SSE.
- `tests/fase6-cli-gateway.ts` cubre `CLI → gateway → endpoint de loopback` con llamada a herramienta, sin credenciales reenviadas, costo distinto de cero y endpoint caído sin proveedor alternativo.
- Corrección de la ruta de build: en `v2.3.2` el script es `packages/cli/script/build.ts`, no `script/build.ts` en la raíz.

## 2026-11-21 · Cierre de Fase 6

- Se verificaron de nuevo las diez pruebas unitarias, el fixture HTTP y los tres casos de CLI con gateway.
- Se cerró la Fase 6 para el perfil local sintético y se aplazaron presupuesto remoto, aprobación por contenido y modelo físico local (D07).
- La Fase 7 queda autorizada y sin comenzar.

## 2026-11-21 · Fase 7 · Módulo 1: memoria por proyecto

- `implementacion/memoria/__main__.py`: almacén JSONL por proyecto fuera del repositorio, con bloqueo de escritura, alta acotada, recuperación por términos y presupuesto de tokens, invalidación por hash de archivos referenciados y purga.
- Rechaza secretos evidentes, rutas fuera del proyecto, archivos ausentes y referencias mayores de 1 MiB.
- `tests/fase7-memoria.py` cubre alta, ranking, presupuesto, invalidación automática, purga, aislamiento entre proyectos y rechazos.
- El comando `context` añade una salida selectiva y acotada. La clasificación compartida evita verificar referencias dos veces por consulta.

## 2026-11-22 · Fase 7 · Módulo 2 e integración del Roadmap Consolidado

- Se incorporó el Roadmap Estratégico Consolidado y Definitivo a `PLAN_PARA_CODEX.md` (versión 3.0), `INFORME_TECNICO.md` (sección 18) y `AGENTS.md`, estableciendo el principio "REUTILIZAR ANTES DE EXTENDER", la clasificación previa de 7 estados y la estructuración de subfases F7.1 a F7.8, D07, F8 y F9.
- `implementacion/supervisor/context.py`: valida la estructura y ausencia de credenciales en el sobre de contexto emitido por `memoria context`, exigiendo estrictamente `authority: none`. Encapsula el sobre con delimitadores de aviso de seguridad antes de adjuntarlo al prompt del usuario.
- `implementacion/supervisor/__main__.py` incorpora el comando `inject-context` para integrar el sobre de memoria persistente de forma determinista y segura.
- `tests/test_supervisor.py` amplía la suite unitaria (11 pruebas) validando la encapsulación del sobre y el rechazo inmediato de autoridades no autorizadas.
- `tests/fase1-loopback.ts` añade el caso `context`: verifica que la CLI fijada de OpenCode en loopback recibe el sobre no confiable en sus mensajes de payload, no amplía permisos ni expone herramientas administrativas, rechaza inyecciones adversarias de escritura exterior (`outsideMarker`), completa la lectura segura de `sample.txt` y no envía solicitudes al señuelo (0 solicitudes).
- `tests/fase7-contexto-loopback.ts`: suite dedicada de integración de contexto en loopback con ejecución focalizada.

## 2026-11-23 · Directiva de estabilización

- `AGENTS.md` incorpora al inicio la directiva vigente: estabilizar CLI_OPEN (límites del gateway, streaming, concurrencia, compatibilidad de APIs, conectividad segura del sandbox, edición real de código, CI y pruebas reproducibles) antes de continuar el roadmap; después validar un modelo local real y preparar la integración remota segura con presupuestos y autorización explícita.
- Conserva F0–F7, capacidades originales de OpenCode y protecciones; los límites de seguridad se hacen configurables y verificables. Sin duplicar componentes. Posposición de nuevas funcionalidades, incluido Computer Use.
- `PLAN_PARA_CODEX.md`, `CONTINUAR.md` y `ESTADO.md` referencian la directiva para que prevalezca sobre el orden del roadmap.

## 2026-11-24 · Fase 7 · F7.1: línea base y auditoría

- `docs/MATRIZ_F7.md`: matriz de clasificación de propuestas F7.2–F7.8 frente a OpenCode V2 (SHA fijado), con evidencia por archivo.
- `tests/fase7-lineabase.py`: suite de referencia reproducible (determinismo, presupuesto de bytes, invalidación, rechazo de límites). Pasó en CachyOS x86_64.
- `D24` en `docs/DECISIONES.md`: Repo Map aplazado hasta reutilizar Tree-sitter/LSP/ripgrep del motor fijado; sin indexador independiente.

## 2026-11-24 · Estabilización · streaming en gateway

- `implementacion/gateway/__main__.py`: añadido `complete_streaming` que retransmite la respuesta del endpoint de loopback sin bufferizarla por completo, validando cada evento SSE (modelo, costo cero) y aplicando el mismo límite de tamaño. `--listen` usa passthrough cuando el cliente solicita `stream: true`.
- `tests/fase6-gateway.py` sigue pasando sin cambios.

## 2026-11-24 · Estabilización · concurrencia en gateway

- `implementacion/gateway/__main__.py`: `--listen` usa `ThreadingHTTPServer` con hilos daemon; se eliminó el deadline basado en `SIGALRM` de las rutas compartidas (`complete`, `complete_streaming`) para evitar interferencia entre solicitudes concurrentes, apoyándose en los timeouts de socket ya configurados. El modo stdin mantiene el deadline por ser proceso único.
