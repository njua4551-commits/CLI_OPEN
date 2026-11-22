# Fase 6 — Inicio

Comienza con la selección de la interfaz del gateway y el contrato de rechazo por defecto. La primera salida autorizada deberá ser una prueba sintética y separada del workspace. La sesión de revisión de Fase 5 sigue usando loopback privado.

- Seleccionar el destino, modelo y presupuesto antes de cada solicitud. Usar un permiso de inferencia separado del de edición.
- Requerir aprobación del contenido y limitar destino, concurrencia y tiempo. Corroborar el precio y conciliar el costo reportado; detenerse ante un valor desconocido.
- El perfil local utilizará solamente un endpoint expresamente autorizado. La calificación física local sigue pendiente y no tiene fallback remoto.
- Reutilizar el transporte compatible con OpenAI de OpenCode. Probar primero la denegación de destinos no aprobados, indisponibilidad, presupuesto agotado y ausencia de fallback.

## Checkpoint de continuidad

El adaptador de [gateway](../../implementacion/gateway/__main__.py) acepta una solicitud por stdin. Usa `127.0.0.1` y `/v1/chat/completions`, con puerto y modelo elegidos explícitamente, hasta 512 tokens de salida, 16 KiB de solicitud, 64 KiB de respuesta y 10 segundos de plazo. Rechaza un costo distinto de cero cuando el adaptador lo reporta. Un endpoint local sin campo de costo puede responder. Esta regla no se aplica a un proveedor remoto.

Pasó el [fixture HTTP](../../tests/fase6-gateway.py) en un namespace de red privado. Quedan la conexión desde OpenCode, el seguimiento de presupuesto remoto y su control de aprobación por contenido. No se habilitó inferencia remota de producto ni se calificó un runtime de inferencia física local.
