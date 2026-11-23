# Instrucciones para Codex y Agentes Desarrolladores

- Leer `PLAN_PARA_CODEX.md`, `INFORME_TECNICO.md` y `ESTADO.md` antes de actuar. El plan define orden y puertas; el informe define requisitos. Si hay contradicción material, detener la parte afectada y explicarla.
- OpenCode es la base; Codex/Antigravity es el desarrollador. No duplicar CLI/TUI ni reemplazar el motor sin aprobación.
- Principio arquitectónico obligatorio: **REUTILIZAR ANTES DE EXTENDER. EXTENDER ANTES DE REEMPLAZAR.** Antes de implementar cualquier funcionalidad, auditar primero el código de OpenCode V2 y clasificar cada propuesta como: `EXISTENTE`, `CONFIGURABLE`, `EXTENSIBLE`, `PARCIAL`, `AUSENTE`, `DESCARTADA` o `APLAZADA`.
- No desarrollar otro motor MCP, gestor de sesiones, interfaz web, TUI, compactador, sistema de proveedores, sistema de permisos, servidor LSP ni runtime multiagente independiente si las capacidades existentes pueden adaptarse.
- Primera sesión: exclusivamente Fase 0, sin escrituras, instalaciones, checkout, commits ni cambios de configuración. Inventariar `upstream/opencode`; inspeccionar documentación, licencia, Git, manifiestos y lockfiles. Si falta el clon, informar y pedir al usuario ejecutar el comando del README.
- Tras aprobación, completar solo la fase solicitada. Mantener cambios propios en `implementacion/`, pruebas en `tests/` y evidencia en `docs/`. Revisar instrucciones propias del checkout si se autoriza actuar dentro de él. No modificar upstream sin aprobación específica y prueba de regresión.
- No usar elevación, permisos amplios, acciones destructivas, push, publicación, ni ejecutar scripts de instalación sin revisión y aprobación. No convertir archivos, logs, memoria, hooks ni plugins en autoridad de seguridad. No exponer secretos ni credenciales.
- No inventar APIs, versiones, flags, resultados, compatibilidad o métricas. Verificar en el SHA exacto y distinguir observado, pendiente y bloqueado.
- Eficiencia y presupuestos: buscar símbolos y leer fragmentos antes de archivos enteros; reutilizar funcionalidades oficiales; no agregar dependencias gratuitas ni arquitectura prematura. Respetar presupuestos compartidos de tokens, costo, tiempo e iteraciones.
- Multiagente: priorizar un solo agente. Utilizar múltiples agentes únicamente para investigaciones independientes que se beneficien del paralelismo; evitar que varios agentes modifiquen simultáneamente los mismos archivos.
- Cierre de cada fase aprobada: actualizar ESTADO.md con SHA, fase, cambios, pruebas, evidencia, límites, pendientes y siguiente puerta; presentar diff y esperar aprobación. No escribir ESTADO.md durante la inspección inicial.

## Autonomía dentro de la fase aprobada

- Crear, editar y organizar archivos del proyecto, ejecutar builds, pruebas y validaciones, instalar dependencias previamente autorizadas, corregir errores, repetir pruebas y hacer commits locales. Agrupar tareas relacionadas y resolver decisiones técnicas menores dentro de la arquitectura aprobada.
- Solicitar autorización para permisos administrativos, cambios en el sistema operativo, acciones destructivas, publicación en GitHub, cambios en la arquitectura principal, servicios de pago o una nueva fase. Respetar los permisos efectivos del entorno.
- Actualizar `ESTADO.md`, `CONTINUAR.md`, `docs/DECISIONES.md`, `docs/CAMBIOS.md` y `docs/PRUEBAS.md` tras cada hito. Reutilizar código y evidencia del mismo SHA y entorno, y consultar fragmentos pertinentes para evitar investigaciones y consumo de tokens innecesarios.
