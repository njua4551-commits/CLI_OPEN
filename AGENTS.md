# Instrucciones para Codex y Agentes Desarrolladores

## Directiva vigente · Prioridad sobre el roadmap

Prioriza estabilizar CLI_OPEN antes de continuar el roadmap.

Audita y corrige los fallos detectados: límites del gateway, streaming, concurrencia, compatibilidad de APIs, conectividad segura del sandbox, edición real de código, CI y pruebas reproducibles.

Después valida un modelo local real y prepara la integración remota segura con presupuestos y autorización explícita.

Conserva F0–F7, todas las capacidades originales de OpenCode y las protecciones existentes. No elimines límites de seguridad: hazlos configurables y verificables. No dupliques componentes.

Trabaja por módulos pequeños, con pruebas y regresiones después de cada cambio. Actualiza la documentación y crea checkpoints Git revisados. No declares completada una función sin evidencia real.

Pospón nuevas funcionalidades, incluido Computer Use, hasta estabilizar lo fundamental.

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

## Mapa documental (no crear duplicados)

- Estado y checkpoint: `ESTADO.md`. Reanudación: `CONTINUAR.md`. Plan/puertas: `PLAN_PARA_CODEX.md` (equivale a ROADMAP). Arquitectura/ADRs: `docs/DECISIONES.md` (equivale a ARCHITECTURE). Pruebas/evidencia: `docs/PRUEBAS.md` (equivale a AUDIT). Cambios: `docs/CAMBIOS.md`. Matriz F7: `docs/MATRIZ_F7.md`. Resumen técnico: `INFORME_TECNICO.md`.
- No crear `PROJECT_STATE.md`, `ARCHITECTURE.md`, `ROADMAP.md` ni `AUDIT.md`: ya existen los equivalentes anteriores.
- Último checkpoint verificado: `26aea30` (rama `fase-1`, sincronizada con `origin/main`).
- Verificado: F0–F7, núcleo OpenCode V2, aislamiento bubblewrap, supervisor/broker/gateway, presupuestos, cancelación, gateway con streaming/concurrencia acotada/alias exactos, edición aislada en subdirectorios, memoria persistente, envoltura de contexto no confiable.
- Pendiente de prueba real: inferencia con modelo local físico, autorización remota de presupuesto (D07), concurrencia bajo carga con clientes HTTP reales, adaptación F7.2 (Repo Map).

## Autonomía dentro de la fase aprobada

- Crear, editar y organizar archivos del proyecto, ejecutar builds, pruebas y validaciones, instalar dependencias previamente autorizadas, corregir errores, repetir pruebas y hacer commits locales. Agrupar tareas relacionadas y resolver decisiones técnicas menores dentro de la arquitectura aprobada.
- Push autorizado de forma permanente por el usuario («push siempre») al cierre de cada iteración: `git push origin fase-1:main` sin `--force`. No publicar etiquetas, releases ni paquetes sin autorización específica.
- Solicitar autorización para permisos administrativos, cambios en el sistema operativo, acciones destructivas, publicación de etiquetas/releases, cambios en la arquitectura principal, servicios de pago o una nueva fase. El push de commits a `origin/main` ya está autorizado. Respetar los permisos efectivos del entorno.
- Actualizar `ESTADO.md`, `CONTINUAR.md`, `docs/DECISIONES.md`, `docs/CAMBIOS.md` y `docs/PRUEBAS.md` tras cada hito. Reutilizar código y evidencia del mismo SHA y entorno, y consultar fragmentos pertinentes para evitar investigaciones y consumo de tokens innecesarios.
