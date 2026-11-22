# Fase 6 — Inicio

Comienza con la selección de la interfaz del gateway y el contrato de rechazo por defecto. La primera salida autorizada deberá ser una prueba sintética y separada del workspace. La sesión de revisión de Fase 5 sigue usando loopback privado.

- Seleccionar el destino, modelo y presupuesto antes de cada solicitud. Usar un permiso de inferencia separado del de edición.
- Requerir aprobación del contenido y limitar destino, concurrencia y tiempo. Corroborar el precio y conciliar el costo reportado; detenerse ante un valor desconocido.
- El perfil local utilizará solamente un endpoint expresamente autorizado. La calificación física local sigue pendiente y no tiene fallback remoto.
- Reutilizar el transporte compatible con OpenAI de OpenCode. Probar primero la denegación de destinos no aprobados, indisponibilidad, presupuesto agotado y ausencia de fallback.
