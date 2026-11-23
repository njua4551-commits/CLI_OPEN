# Plan para construir el agente por módulos con Codex

**Propósito:** construir gradualmente CLI_OPEN como un agente de desarrollo, razonamiento y diagnóstico avanzado, seguro, económico y multiplataforma, basado en OpenCode V2 y desarrollado con Codex/Antigravity.

**Versión:** 3.0 — Roadmap estratégico consolidado y definitivo. Este plan gobierna el orden de ejecución, puertas y criterios de aceptación; INFORME_TECNICO.md gobierna requisitos técnicos y arquitectura.

## Directiva vigente (prevalece sobre el orden de este plan)

Prioriza estabilizar CLI_OPEN antes de continuar el roadmap: auditar y corregir límites del gateway, streaming, concurrencia, compatibilidad de APIs, conectividad segura del sandbox, edición real de código, CI y pruebas reproducibles. Después, validar un modelo local real y preparar la integración remota segura con presupuestos y autorización explícita. Conservar F0–F7, las capacidades originales de OpenCode y las protecciones existentes; los límites de seguridad se hacen configurables y verificables, no se eliminan. No duplicar componentes. Módulos pequeños, pruebas y regresiones tras cada cambio, documentación actualizada y checkpoints Git revisados; ninguna función se declara completada sin evidencia real. Posponer nuevas funcionalidades, incluido Computer Use, hasta estabilizar lo fundamental. Texto íntegro en `AGENTS.md`.

## Principio arquitectónico obligatorio

**REUTILIZAR ANTES DE EXTENDER. EXTENDER ANTES DE REEMPLAZAR.**

Antes de implementar cualquier funcionalidad:
1. Inspeccionar el código fuente de la versión fijada de OpenCode (`v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`).
2. Inspeccionar la implementación actual de CLI_OPEN.
3. Identificar funcionalidades, APIs, plugins y configuraciones aprovechables.
4. Comprobar su funcionamiento mediante pruebas.
5. Identificar exclusivamente capacidades faltantes.
6. Seleccionar la solución con menor complejidad y mantenimiento sin comprometer calidad ni seguridad.

Clasificar cada propuesta antes de actuar como:
- `EXISTENTE`: reutilizar directamente sin código adicional.
- `CONFIGURABLE`: resolver mediante configuración nativa.
- `EXTENSIBLE`: ampliar mediante APIs públicas, hooks o plugins.
- `PARCIAL`: implementar exclusivamente el incremento faltante.
- `AUSENTE`: evaluar un módulo propio justificado.
- `DESCARTADA`: no aporta beneficios medibles suficientes.
- `APLAZADA`: posponer fuera del MVP inicial.

No desarrollar otro motor MCP, gestor de sesiones, interfaz web, TUI, compactador, sistema de proveedores, sistema de permisos, servidor LSP ni infraestructura multiagente si las capacidades nativas pueden adaptarse.

## Cómo usar este documento

Coloca este archivo en la carpeta principal que también contiene el repositorio completo de OpenCode y, si lo tienes, INFORME_TECNICO.md. Abre Codex desde esa carpeta y pídele que lea primero este plan y el informe. No le pidas que implemente todo de una vez: debe completar una fase, mostrar resultados y esperar tu aprobación antes de avanzar.

Codex será el **agente que ayuda a programar el proyecto**. Eso no decide por sí solo qué motor usará el producto final. OpenCode es la base elegida por el usuario. Codex CLI es el desarrollador del proyecto, no un segundo motor; solo se evalúa como alternativa si aparece un bloqueo indispensable documentado.

Codex debe localizar el repositorio descargado y reportar su ruta antes de cambiar archivos. No asumas que el repositorio se llama `opencode` ni muevas o sobrescribas archivos para ajustarlo a un ejemplo de este documento.

## Resultado buscado

Construir gradualmente una herramienta CLI que pueda trabajar en Linux, macOS y Windows, con WSL2 evaluado como entorno separado. Debe empezar en modo de planificación y diagnóstico de solo lectura. La edición de archivos solo se habilita dentro de un área de trabajo aislada y después de comprobar el aislamiento en el sistema donde se ejecuta.

El agente no debe recibir una consola irrestricta ni privilegios administrativos. Los perfiles del modelo (local, remoto, rápido o profundo) nunca deben aumentar los permisos del agente.

## Reglas de seguridad y de trabajo

Codex debe cumplir estas reglas durante todas las fases:

1. Trabajar solo dentro de la carpeta del proyecto y del repositorio identificado. No leer ni modificar carpetas personales o del sistema que no sean necesarias.
2. Antes de cualquier edición, informar qué archivos cambiará y por qué. Mantener el diff pequeño y mostrarlo al cerrar cada fase.
3. No ejecutar comandos como administrador, no usar `sudo`, no cambiar permisos, servicios, red, firewall, registro, políticas del sistema ni tareas programadas.
4. No crear una herramienta que ejecute comandos arbitrarios del host. Las acciones de diagnóstico deben tener nombres, entradas y resultados tipados y limitados.
5. No instalar dependencias ni cambiar la configuración global de Codex, OpenCode o del equipo sin pedir autorización. No guardar tokens ni claves en el repositorio.
6. No enviar logs, archivos, rutas privadas ni contenido del proyecto a servicios remotos adicionales sin consentimiento explícito para esa tarea. El uso de Codex con un modelo remoto ya implica procesamiento por su proveedor; no equivale a modo local estricto. No cambiar silenciosamente de proveedor si un modelo local falla.
7. No declarar un sandbox como activo solo porque una herramienta esté instalada. El aislamiento debe tener pruebas positivas y negativas en el entorno efectivo.
8. Si una prueba de aislamiento falla, hay permisos ambiguos o el resultado de una operación es incierto, detenerse. Mantener las capacidades en modo PLAN/DIAG y explicar el bloqueo.
9. No modificar el núcleo de OpenCode ni crear un fork durante el prototipo. Solo reconsiderarlo ante una limitación concreta de una API pública, reproducida y documentada.
10. No continuar a la siguiente fase hasta presentar: cambios, comandos ejecutados, resultados, limitaciones y criterio de aceptación.

Usa Git desde el principio. Antes de trabajar, revisa `git status` y los cambios existentes. No borres ni restaures cambios ajenos. Cada fase debe quedar en una rama o commit revisable.

## Estructura sugerida

Adáptala a la carpeta existente, sin reorganizar el repositorio descargado por iniciativa propia:

```text
agente-local/
├── PLAN_PARA_CODEX.md
├── INFORME_TECNICO.md             # requisitos y arquitectura
├── upstream/
│   └── opencode/                   # checkout completo, versión y commit fijados
├── implementacion/                 # código propio; no mezclar con el núcleo upstream
│   ├── supervisor/
│   ├── adapters/
│   ├── broker/
│   ├── gateway/                    # opcional y posterior
│   └── policy/
├── tests/
│   └── fixtures/                   # datos sintéticos, nunca datos personales
└── docs/
    ├── DECISIONES.md
    ├── MATRIZ_PLATAFORMAS.md
    └── evidencias/
```

No es obligatorio usar estos nombres ni crear todas las carpetas en la primera fase. Primero inspecciona dónde está el repositorio descargado y cómo se construye. La selección del lenguaje del supervisor también queda pendiente hasta evaluar las interfaces reales del motor.

## Fases de trabajo

### Fase 0 — Inspección sin cambios

**Objetivo:** entender qué hay en la carpeta y evitar que Codex trabaje en el lugar equivocado.

- Leer este plan y INFORME_TECNICO.md.
- Localizar la raíz Git del repositorio descargado, la rama, los cambios no confirmados, la licencia, los documentos de contribución y las instrucciones de construcción.
- Registrar sistema operativo, versión, arquitectura, shell, versión de Codex y entorno de ejecución: Windows nativo, WSL2, macOS o Linux.
- Identificar qué parte del informe es una hipótesis y qué se puede comprobar en el código o la documentación oficial.

**Aceptación:** Codex presenta el inventario, las rutas, el estado Git y los comandos de construcción que encontró en los documentos del repositorio. No ha modificado archivos, instalado paquetes ni cambiado la máquina.

### Fase 1 — Prueba comparativa de integración (P-1)

**Objetivo:** calificar el checkout de OpenCode elegido antes de construir módulos propios.

Evalúa una versión estable concreta de OpenCode V2, si existe y cumple los requisitos. Consulta la documentación y el changelog oficiales actuales; anota versión, tag o commit y fecha. No uses una rama de desarrollo cambiante como base sin justificarlo.

Usa el siguiente conjunto pequeño de pruebas sintéticas para OpenCode:

- Arranque desde una configuración limpia y privada, sin reutilizar silenciosamente un servidor, credenciales o plugins globales.
- Construcción y una sesión de lectura sobre un proyecto de prueba.
- Pruebas deterministas de herramientas, respuestas extensas, cancelación y errores con una API compatible con OpenAI simulada en loopback.
- Inferencia real con OpenRouter, modelo fijo `liquid/lfm-3-1.7b:free`, solo fixtures sintéticos y presupuesto máximo de USD 0. Confirmar soporte de herramientas y precio cero antes de ejecutar. Usar `OPENROUTER_API_KEY` inyectada en el entorno y detener la prueba si falta, cambia el precio o falla el endpoint. Deshabilitar fallbacks, modelos alternativos y herramientas alojadas.
- Registrar la inferencia física local como pendiente de validación. Conservar la opción de configurar Ollama, llama.cpp y otros endpoints de forma explícita.
- Descubrimiento y uso de MCP únicamente con un servidor de prueba aprobado.
- Cancelación de una tarea y cierre de procesos secundarios.
- Comprobación de la configuración y de las rutas de conexión utilizadas.
- Revisión de las APIs públicas disponibles para extensión, políticas, configuración, logs y cancelación.
- Confirmación de qué límites del sandbox del propio motor se pueden probar en el sistema actual.

Registra la evidencia, problemas y pasos de reproducción en `docs/evidencias/`. No afirmes que Codex u OpenCode están aislados solo porque la aplicación arranque. No añadas todavía memoria, gateway, cron, navegador ni broker del host.

**Criterio para continuar:**

- Continuar con OpenCode si la sesión supervisada, el transporte simulado, la prueba de inferencia autorizada y las APIs necesarias pasan sin modificar su núcleo. La inferencia física local se calificará en un entorno adecuado y queda fuera de esta puerta.
- Solo si hay un bloqueo indispensable, documentar una comparación con Codex CLI y solicitar aprobación antes de cambiar de motor.
- Reducir el alcance o detenerse si OpenCode no cumple las condiciones; no compensar una integración rota con permisos más amplios.

**Aceptación:** existe un registro reproducible y una decisión justificada de avanzar, cambiar de motor o detenerse. No se ha empezado la arquitectura completa.

### Fase 2 — Base segura: supervisor, doctor y perfil PLAN (P0)

**Objetivo:** hacer visible el entorno y mantener la CLI sin capacidad de ejecutar acciones del host.

- Crear el supervisor mínimo solo después de aprobar el resultado de la Fase 1.
- Detectar sistema operativo efectivo, arquitectura, shell, WSL, permisos/elevación y disponibilidad declarada del backend de aislamiento.
- Mostrar el perfil activo y explicar qué funciones están deshabilitadas y por qué.
- Mantener el perfil PLAN sin ejecución de comandos ni cambios de archivos.
- Guardar las políticas de confianza fuera de los archivos que el agente pueda editar.

**Aceptación:** detecta correctamente el entorno de prueba y no ejecuta acciones del host. Si no puede verificar el aislamiento, lo informa como “no verificado”.

### Fase 3 — Broker de diagnóstico de solo lectura (P1)

**Objetivo:** permitir consultas acotadas sin dar al modelo una shell general.

- Diseñar un catálogo pequeño de acciones permitidas, cada una con parámetros validados y salida limitada.
- Añadir autenticación entre componentes si el transporte la requiere.
- Rechazar acciones, rutas, parámetros o recursos fuera del catálogo.
- Registrar qué consulta se hizo, con límites para no guardar secretos o datos innecesarios.
- Usar fixtures sintéticos para las primeras pruebas.

**Aceptación:** las consultas autorizadas funcionan; acciones desconocidas, parámetros inválidos y rutas fuera del alcance se rechazan. No existe una acción genérica tipo “ejecutar cualquier comando”.

### Fase 4 — Aislamiento por plataforma (P2)

**Objetivo:** probar la frontera de ejecución antes de habilitar escrituras.

Califica cada entorno por separado: Linux, macOS, Windows nativo en PowerShell y WSL2. Prueba CMD aparte si se requiere compatibilidad con CMD; no infieras que funciona porque PowerShell funcione. WSL2 no demuestra aislamiento del host Windows.

Pruebas negativas con datos sintéticos:

- Intentar escribir fuera del área de trabajo y confirmar que se bloquea.
- Probar rutas absolutas, traversal, enlaces simbólicos o junctions y rutas no permitidas.
- Confirmar qué ocurre con red, procesos hijos, tiempos de espera y cancelación.
- Confirmar que una configuración local, plugin, instrucción o respuesta de herramienta no puede ampliar los permisos.
- Verificar que un backend ausente o fallido deja el agente en PLAN/DIAG.

**Aceptación:** todas las pruebas críticas pasan en el sistema específico. Un entorno no calificado no obtiene capacidad de escritura aunque otro sistema sí haya pasado.

### Fase 5 — Edición segura del workspace (P4)

**Objetivo:** permitir cambios de código revisables dentro de una copia aislada.

- Crear o usar una copia de trabajo controlada; nunca editar archivos arbitrarios del host.
- Restringir las operaciones a la raíz de trabajo autorizada.
- Mostrar un diff antes de integrar cambios.
- Ejecutar únicamente validadores permitidos y dentro del mismo límite comprobado.
- Si el estado de una escritura queda incierto, reconciliarlo antes de reintentar.

**Aceptación:** las pruebas y los cambios se ejecutan dentro de la frontera aprobada; el diff es revisable; un intento de escritura fuera de ella falla.

### Fase 6 — Modelos, gateway y presupuesto (P3, opcional)

**Objetivo:** añadir proveedores remotos solo si se necesitan.

- Comenzar con un proveedor local probado, como Ollama o LM Studio, si el modelo supera pruebas de llamadas a herramientas.
- Mantener el modo local como modo que no transmite datos.
- Tratar el permiso para usar un proveedor remoto como un permiso separado de la edición de archivos.
- Antes de enviar datos a un modelo remoto, mostrar qué información se enviará, eliminar secretos y datos no necesarios y pedir aprobación.
- Limitar destino, concurrencia, tiempo y presupuesto. Si el proveedor, costo o resultado no pueden confirmarse, detener las llamadas.
- No implementar escalado remoto silencioso. Las capacidades de cada adaptador deben verificarse y registrarse.

**Aceptación:** el destino y los límites se verifican; el modo local no tiene una ruta remota alternativa; una falla local no dispara una llamada remota sin aprobación.

### Fase 7 — Roadmap estratégico consolidado y definitivo

La Fase 7 actualiza y amplía el alcance de inteligencia, contexto, eficiencia, autonomía y supervisión sin reabrir fases F0–F6 cerradas. Se estructura en subfases ordenadas gobernadas por el principio de reutilización y validación por evidencia:

#### F7.1 — Auditoría y línea base de capacidades nativas
- Auditar todas las propuestas frente a las capacidades nativas de OpenCode V2 (`execute`, subagentes, sesiones hijas, worktrees, compactador, variantes de razonamiento, Pair Device, TUI, Web UI, LSP, etc.).
- Elaborar matriz de clasificación estricta (`EXISTENTE`, `CONFIGURABLE`, `EXTENSIBLE`, `PARCIAL`, `AUSENTE`, `DESCARTADA`, `APLAZADA`).
- Establecer suites de pruebas de referencia y métricas reproducibles previas a extensiones.

#### F7.2 — Contexto inteligente y comprensión de repositorios (Aider / Amp)
- Integrar con la memoria persistente existente (`implementacion/memoria/`).
- Repo Map incremental y estructurado mediante Tree-sitter o grafos de símbolos de OpenCode/LSP.
- Investigación profunda de dependencias y símbolos bajo demanda, activada únicamente cuando la complejidad lo justifique.
- Presupuesto dinámico de tokens para contexto e invalidación selectiva ante cambios del workspace.
- No construir un segundo motor de contexto ni un segundo indexador independiente.

#### F7.3 — Code Mode y optimización determinista de resultados (Cloudflare)
- Reutilizar y adaptar la herramienta `execute` nativa de OpenCode.
- Descubrimiento dinámico y selectivo de herramientas con recuperación de esquemas bajo demanda.
- Ejecución agrupada respetando individualmente permisos, aislamiento y presupuestos.
- Filtrado determinista de logs y salidas: deduplicación de líneas, agrupamiento de errores equivalentes, conteo de ocurrencias, preservación de contexto alrededor de fallos y redacción de secretos.
- Caché e invalidación local sin llamadas adicionales al modelo.

#### F7.4 — Modelos, presupuesto unificado y proveedores (Kilo CLI / Qwen Code)
- Enrutamiento adaptativo de modelos según complejidad, disponibilidad, latencia, privacidad y costo.
- Reutilizar el gateway existente (`implementacion/gateway/`); no duplicar el gestor de proveedores.
- Compatibilidad verificada con endpoints compatibles con OpenAI, Ollama, llama.cpp, LM Studio, vLLM, OpenRouter, Groq y servidores autogestionados sin introducir LiteLLM obligatoriamente.
- Presupuestos compartidos por tarea (tokens de entrada/salida, costo, tiempo, concurrencia, subagentes).
- Experiencia inicial gratuita: detectar y aprovechar modelos gratuitos nativos autorizados de OpenCode y endpoints locales, informando cuotas y sin cambio silencioso a modelos de pago.
- Resolver controles de seguridad de D07 antes de habilitar inferencia real de producto.

#### F7.5 — Autonomía controlada, validación y recuperación (OpenHands / Antigravity)
- Autocorrección guiada por evidencia: detección objetiva de bucles y falta de progreso, clasificación de errores y replanificación acotada.
- Validación automática según lenguaje: compiladores, linters, formateadores y pruebas focalizadas detectadas en el proyecto; sin instalar dependencias automáticamente.
- Coordinación adaptativa de subagentes y sesiones hijas nativas: delegación justificada únicamente para tareas independientes; uso de Git worktrees nativos para aislamiento de ramas.
- Revisión transaccional y reversión de cambios del proyecto sin rutas no autorizadas.

#### F7.6 — Automatización reutilizable y gobernanza (Goose / Kiro / Cline)
- Reutilizar skills nativas, comandos parametrizados y flujos reproducibles.
- Flujos de especificaciones (Specs/Tasks) orientados a tareas complejas sin burocracia para tareas sencillas.
- Ejecución headless gobernada por presupuestos, eventos JSON y validación en CI/CD.
- Compatibilidad controlada con hooks externos (Claude Code / Codex) mediante adaptadores ligeros sujetos a la política del supervisor, tiempo límite y restricciones de red.

#### F7.7 — Supervisión y tareas asíncronas (amux / Warp Oz)
- Ampliación selectiva de Pair Device y la interfaz web original de OpenCode: visualización de progreso, consumo de tokens, presupuestos restantes, aprobaciones y estado de subagentes.
- Tareas asíncronas con pausa cooperativa en puntos seguros, cancelación efectiva y reconciliación de estado.
- Diagnósticos programados de solo lectura mediante planificadores nativos (systemd timers, cron, Task Scheduler, launchd) utilizando el broker DIAG sin consumo de tokens ni acciones destructivas.

#### F7.8 — Compatibilidad integral, rendimiento y seguridad integral (Crush / OpenCode)
- Rendimiento y optimización de latencia, RAM y CPU en la TUI sin reemplazar el framework de OpenCode.
- Conservación estricta de funcionalidades originales (Pair Device, TUI, Web, Sesiones, Plugins, MCP, LSP).
- Matriz integral de compatibilidad y regresión funcional y de seguridad.

### D07 — Puerta de inferencia real de producto (Aplazada)
- Requiere resolver: presupuesto remoto verificado, aprobación explícita de contenido y destino, protección de credenciales, control de proveedores sin fallback silencioso, y privacidad verificada.
- No habilitar inferencia remota de producto hasta superar estos controles específicos.

### Fase 8 — Empaquetado, distribución y soporte anunciado
- Prioridad inicial: Linux x86_64 funcional en CachyOS, Arch Linux, Ubuntu, Debian y Fedora.
- Entornos posteriores: Windows nativo, macOS y WSL2 con calificación de backends dedicados.
- Instaladores reproducibles, contenedores de prueba y validación sin dependencias ocultas.

### Fase 9 — Funcionalidades futuras opcionales (Fuera de MVP)
- Ejecutores remotos autogestionados (estilo Cursor / Warp Oz).
- Mecanismos avanzados de restauración del sistema operativo (Btrfs snapshots, Snapper, Timeshift, APFS, Windows System Restore) deshabilitados por defecto y posteriores al MVP.
- Infraestructura distribuida avanzada.

## Benchmarks y criterios de aceptación

Para cada componente evaluado o extendido, comparar cuando corresponda:
1. **Línea base A:** OpenCode original sin modificaciones.
2. **Línea base B:** CLI_OPEN actual.
3. **Candidato C:** CLI_OPEN con la mejora propuesta.

Métricas verificadas:
- Tokens totales y tokens por tarea resuelta exitosamente.
- Costo medido en USD.
- Número de llamadas al modelo.
- Tiempo de ejecución y latencia.
- Tasa de éxito y reintentos por fallo.
- Consumo de CPU y memoria RAM.
- Regresiones funcionales o de seguridad (0 toleradas).

## Prioridades de entrega

1. **Prioridad crítica:** Memoria persistente integrada, contexto inteligente y Repo Map, inferencia segura con presupuestos, Code Mode adaptado, autocorrección objetiva, validación por lenguaje, filtrado determinista de logs, compatibilidad completa con OpenCode y paquete funcional en Linux.
2. **Prioridad alta:** Compatibilidad de proveedores locales/gratuitos, investigación profunda justificada, coordinación adaptativa de agentes, recuperación de tareas y supervisión mediante Pair Device.
3. **Prioridad condicionada a beneficios medidos:** Recipes/Specs, adaptadores de hooks, headless avanzado, diagnósticos programados periódicos y optimización de interfaces.
4. **Prioridad futura:** Restauración del SO a nivel de sistema, ejecutores remotos e infraestructura distribuida.

## Instrucciones para dividir el trabajo de Codex

- Una fase por solicitud y una rama o commit revisable por fase.
- En tareas grandes, Codex puede hacer investigaciones independientes en paralelo, por ejemplo revisar módulos independientes del motor; solo un agente debe escribir un módulo a la vez.
- Al cerrar una fase, pedir un resumen con: archivos cambiados, comandos ejecutados, resultados, limitaciones, riesgos y la evidencia que permite avanzar.
- Mantener el informe de arquitectura y las decisiones actualizados. Si Codex descubre que una premisa del informe no aplica a la versión real, debe documentar la discrepancia y detener la fase afectada.
- Antes de aprobar, revisar `git diff` y confirmar que ningún cambio salió del alcance.

## Primer mensaje para pegar en Codex

```text
Lee PLAN_PARA_CODEX.md y INFORME_TECNICO.md de esta carpeta. Localiza el repositorio completo descargado y reporta su ruta, versión, estado Git y documentación de construcción.

En esta primera tarea haz solo la Fase 0 y prepara la calificación de la Fase 1. No edites archivos, no instales dependencias, no ejecutes acciones que cambien el sistema, no uses privilegios y no envíes datos a proveedores remotos. Usa OpenCode como base elegida; verifica versión, SHA, interfaces y fuentes oficiales. No cambies de motor sin autorización. Distingue los hechos verificados de las hipótesis del informe.

Devuélveme el inventario, la matriz de compatibilidad, los riesgos, las pruebas exactas de la Fase 1 y sus criterios para avanzar o detenerse. Espera mi aprobación antes de cambiar archivos o iniciar la implementación.
```

Cuando apruebes la inspección, pide explícitamente: “Implementa solo la Fase 1 aprobada; no comiences la Fase 2”. Repite ese patrón para cada fase.

## Cómo iniciar Codex con límites

Desde la carpeta que contiene este plan y el repositorio, comienza en modo de solo lectura con aprobación para solicitudes:

```bash
codex --sandbox read-only --ask-for-approval on-request
```

Comprueba primero `codex --version` y `codex --help`, porque las opciones pueden cambiar entre versiones. Después de aprobar una fase que requiera escribir, cambia solo al permiso de escritura limitado al workspace y conserva las aprobaciones. No uses modos de acceso total ni desactives las solicitudes de aprobación.

En Windows, empieza por PowerShell o Windows Terminal. Si usas WSL2, trátalo como un entorno Linux separado y conserva el repositorio en el filesystem de WSL cuando sea posible. Para afirmar compatibilidad con macOS o Linux hace falta probarlos en esos sistemas, no solo desde Windows.

## Referencias oficiales para verificar antes de cada fase

- Codex CLI y changelog: https://developers.openai.com/codex/cli y https://developers.openai.com/codex/changelog
- Sandbox y aprobaciones: https://developers.openai.com/codex/concepts/sandboxing y https://developers.openai.com/codex/agent-approvals-security
- Sandbox nativo de Windows: https://developers.openai.com/codex/windows/windows-sandbox
- WSL: https://developers.openai.com/codex/windows/wsl
- Proveedores y configuración: https://developers.openai.com/codex/config-advanced
- Instrucciones `AGENTS.md`: https://developers.openai.com/codex/agent-configuration/agents-md
- Repositorio upstream de OpenCode indicado por el informe: https://github.com/anomalyco/opencode

Estas referencias describen capacidades y documentación; no prueban que una integración concreta funcione en tu PC. La evidencia de cada fase debe venir de las pruebas ejecutadas en el entorno indicado.
