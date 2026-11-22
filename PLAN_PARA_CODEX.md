# Plan para construir el agente por módulos con Codex

**Propósito:** usar Codex en la computadora local para evaluar y, si las pruebas lo justifican, construir un agente de desarrollo y diagnóstico multiplataforma, seguro y económico.

**Versión:** 2.1. Este plan gobierna el orden de ejecución; el informe gobierna requisitos técnicos.

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
- Compatibilidad con un modelo local, incluyendo llamadas a herramientas, manejo de respuestas extensas y errores.
- Descubrimiento y uso de MCP únicamente con un servidor de prueba aprobado.
- Cancelación de una tarea y cierre de procesos secundarios.
- Comprobación de la configuración y de las rutas de conexión utilizadas.
- Revisión de las APIs públicas disponibles para extensión, políticas, configuración, logs y cancelación.
- Confirmación de qué límites del sandbox del propio motor se pueden probar en el sistema actual.

Registra la evidencia, problemas y pasos de reproducción en `docs/evidencias/`. No afirmes que Codex u OpenCode están aislados solo porque la aplicación arranque. No añadas todavía memoria, gateway, cron, navegador ni broker del host.

**Criterio para continuar:**

- Continuar con OpenCode si la sesión supervisada, el proveedor local y las APIs necesarias pasan las pruebas sin modificar su núcleo.
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

### Fase 7 — Memoria, contexto y automatización (posterior)

Añadir estas funciones únicamente después de medir una ruta estable de lectura y escritura:

- Memoria inspeccionable por proyecto, con procedencia, retención y eliminación.
- Contexto progresivo: búsqueda, fragmentos pertinentes, salidas acotadas y referencias a archivos.
- Validación automática después de editar, con número de reintentos limitado y detención ante falta de progreso.
- Subagentes solo para tareas independientes. Evita varios agentes escribiendo los mismos archivos y contabiliza su costo.
- Tareas programadas y automatizaciones del host quedan fuera hasta que exista una necesidad concreta, aprobación explícita y pruebas de seguridad específicas.

**Aceptación:** la memoria no autoriza operaciones ni cambia presupuestos; se demuestra que estas funciones mejoran resultados o costo frente a una línea base.

### Fase 8 — Empaquetado y soporte anunciado (P6)

- Documentar instalación, actualización y reversión sin asumir que los sistemas son equivalentes.
- Ejecutar pruebas reales en cada plataforma que se vaya a declarar compatible.
- Publicar una matriz que separe “arranca”, “diagnóstico de solo lectura”, “escritura aislada” y “no probado”.
- No declarar soporte de un sistema solo porque el código compila o porque funciona en WSL2.

**Aceptación:** cada capacidad anunciada tiene evidencia para el entorno y versión probados.

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
