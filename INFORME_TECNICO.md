# Informe de mejoras y fases de implementación

## Agente CLI multiplataforma sobre OpenCode V2

**Versión del documento:** 2.1 — ejecución coordinada con Codex  
**Base de análisis:** informe unificado anterior, propuesta auditada y revisión v3 adjunta.  
**Fecha de corte de las referencias recibidas:** 21 de noviembre de 2026.  
**Estado:** plan de diseño; no representa una implementación ejecutada ni una certificación de seguridad.

## 1. Propósito y decisión

Este informe convierte las mejoras propuestas para el agente CLI multiplataforma en un plan de trabajo gradual. La propuesta es reutilizar OpenCode V2 como interfaz y motor de sesión, manteniéndolo como upstream y evitando modificar su núcleo al comienzo. El valor propio se construirá en una capa separada: launcher/supervisor, broker de operaciones tipadas, gateway de modelos, memoria/contexto y validadores.

La primera decisión no es qué tecnología usar para todos los componentes, sino comprobar que OpenCode puede integrarse de forma segura sin un fork. Por eso se añade una fase previa de prueba de integración. Si esa prueba falla por una limitación concreta de las APIs públicas, se reduce el alcance o se compara Codex CLI antes de comprometerse a modificar el núcleo.

**Recomendación principal:** empezar con un prototipo pequeño, sin privilegios y con inferencia local; avanzar a diagnóstico, aislamiento, edición y automatización únicamente cuando cada frontera haya pasado sus pruebas.

## 2. Alcance del primer producto

El objetivo es que la persona use una CLI coherente en Linux, macOS, Windows y WSL2, sin que el modelo adivine comandos ni obtenga permisos por cambiar de agente. La capacidad efectiva depende del SO y del backend de aislamiento; si no se comprueba, el sistema debe degradarse y explicar por qué.

### Incluido inicialmente

- Selección y fijación de una versión V2 del motor.
- Diagnóstico del entorno y presentación clara del perfil activo.
- Herramientas del host limitadas, tipadas y de solo lectura.
- Trabajo de código en una copia aislada, solo después de validar el sandbox.
- Uso de modelos locales como opción inicial y acceso remoto únicamente por gateway autorizado.
- Validación objetiva, diff revisable, evidencia y límites de costo/tiempo.

### Fuera del MVP

- Shell privilegiada o administración autónoma irrestricta del sistema operativo.
- Cambios automáticos de servicios, red, permisos, registro o disco del host.
- Uso silencioso de sesiones autenticadas de navegador.
- Ejecución de tareas programadas que deban actuar sin aprobación.
- Modificaciones amplias del núcleo de OpenCode antes de demostrar que son necesarias.

## 3. Mejoras que se incorporan

### 3.1 Prueba de integración antes de construir

Hacer un spike de alcance corto para comprobar cómo se inicia OpenCode V2 desde un supervisor, cuáles son las configuraciones efectivas, qué llamadas auxiliares realiza, cómo se conectan MCP y los proveedores y qué puede cancelarse. Confirmar si el gateway puede ser el único camino a modelos remotos y si la ejecución completa puede quedar dentro de la frontera de aislamiento.

**Resultado esperado:** una decisión con evidencia: seguir con OpenCode sin fork, ajustar el diseño, reducir alcance o comparar un motor alternativo. No iniciar plugins ni automatizaciones a gran escala hasta cerrar esta fase.

### 3.2 Separación explícita de fronteras

El supervisor inicia OpenCode y las herramientas aprobadas dentro de un sandbox o VM verificados. El gateway y el broker son fronteras lógicas separadas, con autenticación según el transporte y permisos mínimos. No requieren daemons independientes en el MVP. El broker ofrece acciones predefinidas —por ejemplo, resumen de disco o consulta de estado de un servicio autorizado—, nunca una operación genérica de ejecución de comandos.

El modelo solicita; el supervisor comprueba el permiso, el alcance y el presupuesto; el backend autorizado ejecuta o rechaza. Un plugin, una instrucción del proyecto, un archivo de memoria o un resultado MCP no pueden modificar esa política.

~~~mermaid
flowchart LR
  U[Usuario] --> S[Supervisor confiable]
  S --> P[Política y presupuesto protegidos]
  S --> X[Sandbox o VM comprobados]
  subgraph X[Entorno aislado]
    O[OpenCode y extensiones aprobadas]
    O --> W[Workspace de trabajo]
    O --> V[Validadores autorizados]
  end
  O --> G[Gateway autenticado]
  O --> B[Cliente del broker]
  B --> H[Broker de diagnóstico limitado]
  H --> R[Consultas permitidas del host]
  O --> M[Recuperación de memoria y contexto]
  M --> O
  G --> L[Modelo local]
  G --> E[Proveedor remoto aprobado]
~~~

La memoria solo puede aportar contexto a la sesión. No hay una conexión de memoria a las políticas o al presupuesto. El gateway no necesita acceso al workspace; el broker no recibe shell arbitraria; el supervisor verifica cada solicitud.

### 3.3 Memoria persistente con procedencia y vencimiento

La revisión propone SQLite con FTS5 como implementación inicial, siempre que se compruebe su disponibilidad en cada build. Guardar la base fuera de los archivos que el agente pueda editar directamente y exponerla mediante una interfaz validada. La memoria será por usuario y proyecto, inspeccionable, exportable y borrable.

Tipos de registro recomendados:

| Tipo | Contenido mínimo | Invalidación o cierre |
|---|---|---|
| Proyecto | Raíz, lenguajes, estructura y revisión de referencia | Cambio de raíz o configuración relevante |
| Decisión | Decisión, motivo, fecha, referencia y estado | Sustitución explícita |
| Hallazgo | Problema, solución, evidencia y versión | Cambio en archivos o dependencias relacionadas |
| Tarea | Objetivo, progreso, pasos, presupuesto y estado | Cierre o cancelación |
| Evidencia | Resultado, referencia, fecha y hash opcional | Cambio en las entradas de validación |

Reglas: no guardar secretos ni historiales completos; mantener procedencia; separar hechos verificados de hipótesis; recuperar pocos elementos pertinentes; invalidar o revalidar tras cambios; nunca tratar una memoria como permiso o evidencia actual sin verificarla. La reanudación de una tarea debe comprobar nuevamente proyecto, commit, diff y operaciones pendientes para no repetir una escritura incierta.

### 3.4 Contexto y recuperación progresiva

Reducir la carga al modelo sin perder información necesaria:

1. Inventariar archivos y buscar términos o símbolos.
2. Leer fragmentos pertinentes con referencias de archivo/líneas.
3. Consultar referencias estructurales si existe un indexador confiable.
4. Leer un archivo completo solo cuando haga falta.
5. Guardar resultados extensos fuera del contexto y retornar un resumen con referencias.

Excluir por defecto binarios, dependencias generadas, secretos y directorios de salida. La caché debe estar ligada a la identidad del proyecto, contenido y parámetros de consulta; invalidarse al cambiar esos datos. Los estados del host no deben reutilizarse como actuales sin nueva comprobación. La caché de lectura local no es lo mismo que la caché facturada por un proveedor.

No se debe asumir que OpenCode permite interceptar todos los puntos de compactación o armado del contexto. El spike debe comprobar las APIs disponibles. Si no existe una API pública para una función, se ofrece recuperación mediante herramientas propias y límites de gateway, sin prometer control completo del contexto interno.

### 3.5 Enrutamiento de modelos y esfuerzo separados de permisos

El supervisor podrá elegir modelo y esfuerzo mediante reglas propias, pero el perfil de razonamiento nunca cambia permisos. El gateway valida destino, consentimiento, presupuesto, concurrencia y uso antes de cada petición.

| Perfil de esfuerzo | Uso orientativo | Restricción |
|---|---|---|
| FAST | Clasificación, búsqueda y lectura sencilla | Modelo local probado con herramientas; resultado acotado |
| BALANCED | Depuración o cambio pequeño | Mismos permisos; presupuesto de tarea controlado |
| DEEP | Problema de varias partes o fallo repetido | Solo con presupuesto y evidencia de progreso |
| REVIEW | Revisión de plan o diff sensible | Solo lectura y propuesta; no aplica cambios |

Estos perfiles son conceptos de la capa propia, no nombres de parámetros universales. Cada adaptador de proveedor debe traducir solo capacidades que haya comprobado. Si el proveedor no admite el esfuerzo solicitado, seleccionar un modelo compatible o detenerse; no suponer que la API lo aplicó.

Distinguir inferencia local física, servidor remoto autogestionado y API de terceros. Un túnel o proxy no vuelve local a un modelo que está corriendo en otra máquina. El modo local estricto no transmite datos. En modo remoto autorizado, usar un destino configurado y probado; ante caída o error, no cambiar silenciosamente de proveedor.

El presupuesto se comparte entre agente principal, subagentes y llamadas auxiliares. Reservar antes de enviar, limitar concurrencia, asentar el uso medido y reconciliar solicitudes interrumpidas antes de repetir. Si se desconoce precio, uso o estado de facturación, detener la escalada remota.

### 3.6 Validación y autocorrección acotadas

El ciclo propuesto es: objetivo y contrato → plan acotado → acción autorizada y aislada → validación determinista → presentar evidencia o clasificar el fallo. Reintentar solo ante un fallo recuperable y una estrategia distinta; no desactivar pruebas, ampliar permisos ni alterar el objetivo para forzar un resultado positivo.

Clasificar errores de sintaxis, pruebas, entorno, permisos, conectividad y presupuesto. Detenerse inmediatamente ante falta de autorización, aislamiento no comprobado, violación de política o ejecución cuyo resultado sea incierto. Una operación de escritura con estado desconocido requiere reconciliación, no repetición automática.

Los números iniciales —por ejemplo, máximo de pasos, reintentos o llamadas remotas— son límites de laboratorio que deben decidirse y medirse. No son una promesa de rendimiento.

### 3.7 Experiencia y estado visibles

Mostrar al usuario el perfil activo, sistema operativo efectivo, estado verificado del sandbox, tipo de destino de inferencia, presupuesto disponible y motivo de cualquier parada. Una opción remota es transversal a PLAN/DIAG/WORKSPACE y no eleva permisos.

Perfiles operativos:

- **PLAN:** plan y conversación; sin ejecución.
- **DIAG:** consultas tipadas de solo lectura por broker.
- **WORKSPACE:** edición y pruebas dentro de un entorno aislado verificado.
- **REMOTE:** permiso independiente para inferencia externa, sujeto a datos aprobados y presupuesto.

No mostrar “sandbox activo” solo porque un binario exista. El estado inicial debe ser “no verificado” hasta pasar pruebas de ejecución.

## 4. Estrategia para el repositorio de OpenCode

1. Usar el repositorio oficial como upstream y fijar una versión V2 concreta, con lockfile y esquema correspondiente.
2. Mantener launcher, gateway, broker, políticas, memoria y validadores en módulos propios separados del núcleo, aunque se utilice un fork de GitHub para desarrollar y colaborar.
3. Mantener la configuración y las políticas de confianza fuera de los archivos que el agente puede editar.
4. Calificar primero una ruta vertical mínima: OpenCode → endpoint explícito → lectura de un workspace sintético → evidencia. Usar un servidor simulado en loopback para resultados deterministas y OpenRouter con un modelo gratuito fijo para la inferencia real de P-1.
5. Añadir herramientas e integración MCP solo cuando su frontera y permisos estén probados.
6. Considerar un fork solo si el spike demuestra una limitación indispensable no resoluble con APIs públicas. Registrar el parche, pruebas y estrategia de sincronización con upstream.

La IA puede acelerar el scaffolding, los adaptadores y las pruebas; no puede reemplazar la revisión de cambios ni las pruebas negativas de aislamiento. El criterio de aceptación es comportamiento observado, no que el código compile o que el modelo afirme que respetó la política.

## 5. Fases, entregables y puertas de decisión

| Fase | Objetivo y entregables | Criterio para avanzar |
|---|---|---|
| **P-1: Spike de integración** | Arranque supervisado de OpenCode V2; API simulada y prueba sintética de inferencia en OpenRouter; configuración efectiva; MCP, cancelación, llamadas auxiliares y APIs disponibles | Se demuestra una ruta sin modificar el núcleo con alcance claro, o se documenta el bloqueo y se compara Codex/reduce alcance |

Para P-1, el endpoint simulado y OpenRouter se seleccionan por separado. OpenRouter queda restringido a `liquid/lfm-3-1.7b:free`, precio verificado de USD 0, datos sintéticos y credencial `OPENROUTER_API_KEY` inyectada desde fuera del repositorio. Se detiene la prueba si falla el destino o falta una condición de costo o autenticación. Usar la configuración de proveedores de OpenCode como punto de integración. La selección futura podrá declarar Ollama, llama.cpp u otro endpoint compatible con OpenAI. Un servidor autogestionado en Kaggle se considera remoto y requiere aprobación como destino independiente. La inferencia física local queda pendiente y esta prueba acotada conserva las puertas de la Fase 6 para uso remoto del producto.
| **P0: Base segura** | Versiones fijadas, launcher/doctor, usuario estándar, modo PLAN y configuración local restrictiva | Identifica SO efectivo, shell y elevación; no expone secretos ni ejecuta acciones de host |
| **P1: Broker de lectura** | Broker autenticado con catálogo pequeño de diagnósticos, límites y auditoría | Rechaza recursos y parámetros no autorizados; no tiene método genérico de shell |
| **P2: Aislamiento por plataforma** | Sandbox o VM para OpenCode, plugins, herramientas y procesos hijos; pruebas de rutas, red y terminación | Escritura fuera del workspace y red no autorizada fallan. Si no pasa, permanece en PLAN/DIAG |
| **P3: Gateway y presupuesto** | Un destino remoto configurado, credenciales fuera de OpenCode, consentimiento, presupuesto y registro compartidos | No hay ruta directa alternativa; presupuesto desconocido o agotado deniega la petición |
| **P4: Trabajo en workspace** | Copia aislada, edición autorizada, diff, validadores aprobados y control de cambios concurrentes | Pruebas ejecutadas dentro del sandbox; diff y evidencia revisables; se detectan cambios obsoletos |
| **P4a: Memoria y contexto** | SQLite/FTS5, recuperación selectiva, retención, invalidación y controles de acceso | No hay secretos ni fuga entre proyectos; reanuda tareas revalidando estado; se mide reducción de contexto |
| **P4b: Enrutamiento adaptativo** | Perfiles de esfuerzo, selección por reglas y límites compartidos | Adaptadores probados; sin escalada silenciosa, permisos adicionales o gasto fuera de presupuesto |
| **P4c: Autocorrección** | Clasificación de fallos, replanificación y límites de intentos | Se detiene al no haber progreso o ante estado incierto; no modifica políticas ni deshabilita pruebas |
| **P5: Automatización y paralelismo** | Subagentes de lectura, worktrees, cron de diagnóstico y MCP adicionales | Sin duplicados, colisiones ni ampliación de privilegios; las aprobaciones pendientes detienen tareas |
| **P6: Distribución** | Instalación repetible, binarios firmados, actualizaciones, rollback y doctor por plataforma | Instalación y rollback se validan en los SO objetivo; la actualización repite la calificación del sandbox |

### Orden de prioridad

P-1 → P0 → P1 → P2 → P4 local; P3 en paralelo cuando se necesite inferencia remota.  
P4a, P4b y P4c se añaden después de que la ruta segura de workspace sea estable. P5 y P6 son posteriores.

**Puerta crítica:** no habilitar escritura automatizada antes de aprobar P2. La inferencia remota y la escritura son permisos independientes; que P3 apruebe no implica que WORKSPACE esté habilitado.

## 6. Plan de pruebas por plataforma

Usar fixtures sintéticos, sin credenciales personales. Calificar Linux, macOS, Windows nativo en PowerShell/CMD y WSL2 por separado. Añadir arquitecturas ARM cuando se vayan a distribuir.

### Pruebas de seguridad obligatorias

- Ausencia o fallo del backend de aislamiento conduce a modo PLAN/DIAG, no a ejecución libre.
- Bloqueo de rutas absolutas fuera del workspace, traversal, symlinks/junctions y rutas UNC no permitidas.
- Bloqueo de conexiones directas a proveedores cuando solo se autoriza el gateway.
- Ningún subagente, plugin, proceso hijo, prueba o servidor MCP puede ampliar permisos.
- Un log o archivo con instrucciones maliciosas no cambia políticas ni provoca acciones.
- El timeout termina también los procesos hijos; si no se puede confirmar, la tarea queda en estado incierto.
- El endpoint local caído no dispara una API remota sin autorización.
- Presupuesto agotado o uso desconocido detiene nuevas llamadas.
- Cambios concurrentes o diff obsoleto impiden integrar el resultado.
- La validación fallida no se reporta como éxito; la falta de evidencia se declara como pendiente.

### Medición de valor

Comparar OpenCode base y extensión con el mismo modelo, herramientas, fixtures y límites. Registrar éxito verificado, costo por tarea exitosa, tokens incluyendo auxiliares, latencia, fallos, aprobaciones, reintentos y resultados de seguridad. Usar mediana y percentiles cuando haya muestra suficiente. No prometer un porcentaje de ahorro antes de medir una línea base comparable.

## 7. Decisiones técnicas todavía abiertas

Las siguientes selecciones son provisionales y deben cerrarse después del spike:

- Lenguaje del supervisor y broker; Go es una opción, no un requisito.
- Gateway propio o producto existente; comprobar cuotas, streaming, cancelación, límites y compatibilidad con herramientas.
- Disponibilidad de FTS5 en cada paquete de SQLite y estrategia de respaldo/retención.
- Transporte autenticado local para broker y gateway en cada SO.
- Backend de aislamiento mantenido para macOS y Windows, y tratamiento de montajes WSL2.
- APIs V2 realmente disponibles para plugins, compactación, contexto y cancelación.

No introducir un servicio específico no acordado como backend remoto. Configurar un endpoint aprobado, verificar TLS/autenticación y probar sus capacidades; si no pasa, conservar el modo local o detenerse.

## 8. Riesgos y controles

| Riesgo | Control propuesto |
|---|---|
| Modificar demasiado el núcleo | Spike P-1; extensiones fuera del core; fork solo con bloqueo demostrado |
| Falsa sensación de aislamiento | Estado “no verificado” hasta pruebas; degradación segura por SO |
| Memoria obsoleta o contaminada | Procedencia, invalidación, límites de recuperación; no es fuente de permisos |
| Filtración a proveedor remoto | Gateway obligatorio, minimización, aprobación y modo local estricto |
| Presupuesto inexacto | Reserva compartida, reconciliación y denegación si el uso es desconocido |
| Plugins, pruebas o MCP no confiables | Inventario cerrado, versiones fijadas, sandbox y red restringida |
| Reintento de escritura incierta | Estado explícito desconocido y reconciliación antes de repetir |
| Complejidad prematura | Un flujo vertical por vez; medir antes de añadir memoria, agentes o cron |

## 9. Cambios aplicados frente a la revisión v3

- Se convirtió la conexión de memoria con políticas en una recuperación de contexto hacia la sesión: la memoria nunca autoriza herramientas ni altera presupuesto.
- El destino remoto se describe como endpoint autorizado genérico; no se presupone un servicio no definido.
- Se separó el permiso REMOTE de los perfiles de ejecución PLAN, DIAG y WORKSPACE.
- Se elevó el spike de integración a fase P-1, antes de construir plugins o elegir tecnología del supervisor.
- Se presentan Go, LiteLLM, SQLite/FTS5 y los límites de reintentos como elecciones por validar, no como requisitos ya demostrados.
- Se añadió una condición de parada explícita: si el aislamiento no está verificado, no se habilita escritura automatizada.

## 10. Conclusión

La ruta recomendada es reutilizar el repo oficial de OpenCode V2 como upstream, mantener las capas propias separadas y demostrar primero que la integración puede funcionar sin parches al núcleo. Las mejoras de memoria, contexto, selección de esfuerzo y autocorrección son valiosas, pero pertenecen a etapas posteriores y solo se justifican si reducen costo o mejoran continuidad sin empeorar calidad ni seguridad.

El criterio de éxito no es que la CLI se ejecute en varios sistemas operativos. Es que cada plataforma anuncie con precisión lo que puede hacer, mantenga las operaciones dentro de su frontera, respete límites y deje evidencia comprobable. Si no puede demostrarlo, debe detenerse o degradarse, no improvisar.

## 11. Procedencia y fuentes anteriores

Este plan deriva del informe unificado anterior, la “Propuesta de Agente CLI Multiplataforma v2 Auditada” y el “Informe definitivo v3” adjunto. Los datos históricos se conservan como antecedentes. En esta revisión se consultó el repositorio oficial, su changelog y reportes públicos sobre el servidor V2; no se compiló ni ejecutó el código y no se verificaron todos los enlaces históricos.

Referencias oficiales citadas en los documentos de origen:

- OpenCode: [changelog V2](https://opencode.ai/changelog), [configuración](https://opencode.ai/docs/config/), [permisos](https://opencode.ai/docs/permissions/), [políticas](https://opencode.ai/docs/policies/), [plugins](https://opencode.ai/docs/build/plugins/), [MCP](https://opencode.ai/docs/mcp-servers/), [migración V1](https://opencode.ai/docs/migrate-v1/).
- Claude Code: [hooks](https://code.claude.com/docs/en/hooks), [subagentes](https://code.claude.com/docs/en/sub-agents), [sandboxing](https://code.claude.com/docs/en/sandboxing).
- DeepSeek Harness: [repositorio](https://github.com/deepseek-ai/deepseek-harness), [arquitectura](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md), [subsistemas](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/).
- Codex CLI: [repositorio](https://github.com/openai/codex), [sandboxing](https://learn.chatgpt.com/docs/sandboxing), [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox).

---

**Nota:** este documento es un plan técnico. No instala, configura ni certifica el agente. Antes de ejecutar fases, fijar la versión V2 y validar cada integración y backend en el entorno objetivo.


## 12. Decisión de implementación: partir del código de GitHub

**Repositorio upstream:** https://github.com/anomalyco/opencode

Usaremos un clon completo del repositorio oficial como upstream. Un fork remoto se creará únicamente con autorización explícita cuando resulte necesario. Tener un fork de GitHub no obliga a alterar el núcleo: inicialmente se conserva upstream intacto y se desarrollan componentes propios en módulos separados. No se reimplementa el motor de agentes ni la interfaz de terminal. La versión exacta se decidirá tras evaluar releases V2 y sus regresiones; registrar tag, SHA, herramientas de compilación y lockfile. No trabajar directamente sobre una rama `dev` cambiante como base de producción.

### 12.1 Arranque del trabajo

```bash
git clone https://github.com/anomalyco/opencode.git
cd opencode
git remote -v
git tag --list 'v2*'
```

Después de elegir un tag real con documentación y artefactos compatibles, registrar su SHA y crear una rama de integración desde ese commit. Al crear el fork propio, conservar `upstream` apuntando al repositorio oficial y `origin` al fork. No inventar URL del fork ni instrucciones de build: leer README, CONTRIBUTING, manifiestos, lockfile y workflows del commit seleccionado antes de ejecutarlas. Registrar requisitos y resultados del build base en `docs/BASELINE.md`. Revisar licencia y avisos antes de distribuir.

### 12.2 Inventario de reutilización

| Capacidad | Decisión | Verificación requerida |
|---|---|---|
| CLI/TUI, sesiones y conversación | Reutilizar | Arranque y sesión con fixture |
| Herramientas de código, edición y búsqueda | Reutilizar dentro de aislamiento | Contratos y pruebas negativas |
| Proveedores y streaming | Reutilizar con endpoint restringido | Tool calling, cancelación y uso |
| MCP y plugins | Reutilizar únicamente interfaces verificadas | Compatibilidad exacta de V2 |
| Compactación, skills y subagentes | Reutilizar si están disponibles | Calidad, permisos y consumo |
| Doctor, supervisor y política externa | Desarrollar | Portabilidad y degradación segura |
| Broker de diagnóstico y gateway | Implementar adaptadores mínimos | Catálogo cerrado y destinos autorizados |
| Memoria persistente y evaluación | Añadir después de medir | Aislamiento por proyecto y métricas |

El código fuente es referencia de comportamiento y facilita depuración, no evidencia automática de seguridad. Explorar primero las rutas de CLI, servidor, sesión, herramientas, proveedores, plugins, configuración y tests. En el árbol consultado aparece `packages/core`; los demás nombres y puntos de extensión se deben localizar en el commit seleccionado, no asumir rutas de V1.

### 12.3 Estructura propuesta de componentes propios

```text
agent-project/
  upstream/                 # checkout fijado o submódulo; no copiar dependencias
  supervisor/               # launcher, doctor, política y ciclo de vida
  integrations/             # adaptadores OpenCode V2, MCP, proveedores
  broker/                   # diagnóstico tipado de lectura
  gateway/                  # destino, límites, consentimiento
  memory/                   # contexto persistente (fase posterior)
  tests/                    # fixtures y pruebas de integración/seguridad
  docs/                     # ADR, matriz de compatibilidad, evidencias
  .github/workflows/        # CI del proyecto propio
```

Esta estructura es propuesta, no descripción del repo oficial. Si un módulo oficial permite cubrir una necesidad sin duplicación, reutilizarlo. Si hace falta un parche del núcleo, abrir un issue técnico con reproducción, evaluar extensión pública, aplicar el cambio mínimo y añadir prueba de regresión. Mantener parches pequeños y una rama de actualización de upstream; no fusionar sin repetir CI y las pruebas de aislamiento.

## 13. Correcciones de la auditoría adicional

### 13.1 P-1: propiedad del servidor y perfiles

OpenCode V2 presenta un modelo cliente-servidor y reportes públicos muestran diferencias entre ejecución con servidor de fondo y `--standalone`. Verificar el flag con la ayuda del binario exacto. Lanzar servidor privado y cliente dentro de la frontera correspondiente, con directorios de configuración, estado, caché y datos aislados; no heredar credenciales ni configuración ambiental no aprobada. Comprobar identidad, ciclo de vida, conexiones y procesos hijos. Un PID por sí solo no demuestra confinamiento: comprobar pertenencia a la frontera y acceso efectivo a recursos. Con un servidor externo de prueba ya activo, confirmar que el agente no lo utiliza. El loopback no debe considerarse confiable automáticamente.

Verificar descubrimiento de plugins locales/globales, mecanismos de actualización, proveedores auxiliares, telemetría y conexión MCP. Mantener lista cerrada de componentes y desactivar descubrimiento/instalación no aprobados mediante mecanismos comprobados o aislamiento externo. Las incidencias específicas de permisos citadas en la auditoría adjunta son hipótesis para pruebas de regresión hasta reproducirlas o identificar sus issues y versiones corregidas.

### 13.2 P0/P2: matriz por plataforma

| Entorno | Backend candidato | Si no se verifica |
|---|---|---|
| Linux | Bubblewrap/namespaces o VM | PLAN/DIAG |
| macOS | VM aislada; Seatbelt solo como candidato sujeto a compatibilidad y mantenimiento | PLAN/DIAG |
| Windows nativo | VM o backend de aislamiento nativo evaluado | PLAN/DIAG |
| WSL2 | Entorno Linux aislado, sin acceso no autorizado al host | PLAN/DIAG |

WSL2 por sí solo no constituye sandbox. Una worktree tampoco. Un contenedor solo se acepta tras comprobar montajes, red, usuario y aislamiento. No integrar Codex como segundo motor durante el MVP: evaluar su backend posteriormente si hay un bloqueo demostrado; su configuración no protege automáticamente a OpenCode. La CLI podrá arrancar nativamente en los sistemas objetivo, pero la paridad de escritura no se declara hasta verificar cada backend.

Doctor: detectar SO del host y entorno efectivo, arquitectura, versión de shell, WSL, UTF-8, rutas con espacios y caracteres Unicode, permisos y elevación; en Linux comprobar disponibilidad efectiva de namespaces y restricciones AppArmor; Windows probar CMD, PowerShell 5.1/7, rutas UNC y ConPTY cuando corresponda. No modificar políticas del sistema automáticamente para hacer pasar pruebas.

### 13.3 P1/P3: menor complejidad

Comenzar con un adaptador MCP por stdio para diagnósticos sintéticos o del workspace. Para datos del host, el supervisor inicia un proceso confiable separado y expone solo un catálogo restringido, autenticado según el transporte. Un MCP lanzado dentro del sandbox conserva esa frontera y no adquiere acceso al host por usar stdio. No crear un daemon privilegiado ni shell general. El gateway inicial puede ser un proxy mínimo o estándar evaluado: un destino, límites duros, cancelación, credenciales externas y bloqueo de rutas alternativas. No retrasar el MVP local por contabilidad remota avanzada; REMOTE permanece desactivado hasta superar sus pruebas.

### 13.4 Modelo local y eficiencia

Antes de seleccionar FAST, ejecutar al menos ocho fixtures: argumento inválido, ruta Windows escapada, ruta Unicode, lectura acotada, respuesta grande, llamada múltiple, cancelación y fallo recuperable. Exigir resultados válidos y ausencia de acciones prohibidas en todos los casos críticos; descartar modelos que repitan llamadas sin progreso. Medir tool calling antes de comparar razonamiento. Confirmar estado LSP en el commit elegido; si no está disponible, comenzar con búsqueda y lectura selectiva. No introducir indexación semántica o agentes adicionales sin demostrar un beneficio.

En el prototipo local: mantener un solo modelo compatible, contexto incremental, salida de herramientas limitada, caché invalidable y máximo inicial de tres intentos por fallo recuperable (ajustable tras medición). No confundir un servidor de inferencia remoto propio con ejecución local física.

## 14. Backlog ejecutable en GitHub

| Issue | Entrega | Dependencia | Cierre comprobable |
|---|---|---|---|
| 001 | Fijar release/SHA, build y licencia | Ninguna | Build base reproducible y registro |
| 002 | Inventario de módulos y APIs V2 | 001 | Mapa de código y pruebas mínimas |
| 003 | Sesión privada y perfil limpio | 002 | No reutiliza servidor externo |
| 004 | Modelo local y benchmark inicial | 003 | Ocho fixtures y métricas |
| 005 | Doctor y perfil PLAN | 003 | CI por SO; ejecución denegada |
| 006 | Broker mínimo de lectura | 005 | Validación de esquema y catálogo |
| 007 | Sandbox Linux | 005 | Pruebas negativas y terminación |
| 008 | Calificación macOS, Windows, WSL2 | 007 | Matriz real, degradación explícita |
| 009 | Edición y validación de workspace | 007 (por plataforma calificada) | Diff y pruebas; sin escritura exterior |
| 010 | Gateway opcional con presupuesto | 003, 007 | Sin destinos alternativos |
| 011 | Memoria/contexto y routing | 009 | Comparación objetiva con baseline |
| 012 | Empaquetado y actualizaciones | 008, 009 | Instalación, rollback y regresión |

El gateway remoto no es dependencia del primer MVP local. Las fases P3/P4 pueden ejecutarse en paralelo o invertir su orden para el modo local, sin relajar los controles de escritura. Cada issue debe incluir caso de prueba, criterio de aceptación, alcance, archivos modificados y evidencia. Cada PR debe ser pequeño, pasar CI y recibir revisión humana antes de fusionarse. No permitir a agentes cambiar sus propias políticas, workflows de confianza o reglas de aprobación sin revisión independiente.

## 15. Criterios Go/No-Go y definición de terminado

- **Go para MVP local:** build fijado, servidor privado, modelo calificado, doctor y una sesión de lectura verificable. La escritura requiere además sandbox calificado para esa plataforma.
- **Go para edición:** todas las pruebas negativas críticas pasan; cambios en workspace aislado, diff y validación. Probar también `execute`/Code Mode si existe, directorios externos, plugins, procesos hijos y servidor de fondo con fixtures controlados.
- **Go para remoto:** presupuesto y destinos aprobados, uso contabilizado, sin salida directa alternativa; el modo local no transmite datos.
- **No-Go:** acceso fuera de frontera, permisos ambiguos, servidor no identificado, resultado desconocido, pruebas omitidas o build no reproducible. No anunciar soporte completo por compilar.
- **Entrega final:** binarios o instalación reproducible, matriz de funciones por plataforma, manual, configuración de ejemplo sin secretos, pruebas automatizadas y evidencia de resultados. La CI debe cubrir Linux, macOS y Windows; WSL2 y VM requieren además pruebas reales dedicadas si los runners no las soportan.

## 16. Fuentes adicionales y límites de verificación

Consultadas el 21/11/2026:
- Repositorio oficial: https://github.com/anomalyco/opencode
- Changelog: https://github.com/anomalyco/opencode/blob/dev/CHANGELOG.md
- Instrucciones V2 en el árbol actual: https://github.com/anomalyco/opencode/blob/dev/packages/core/src/plugin/skill/opencode.md
- Reporte de servidor de fondo frente a standalone: https://github.com/anomalyco/opencode/issues/64869
- Reporte de arranque de servidor en Windows: https://github.com/anomalyco/opencode/issues/41746
- Reporte de estado/configuración V1/V2: https://github.com/anomalyco/opencode/issues/47018

Los issues son reportes públicos, no pruebas propias ni garantía de que un defecto afecte a todas las versiones. Las afirmaciones de la auditoría pegada sobre hooks concretos, fallos de políticas y versiones deben verificarse en el SHA seleccionado. No se ha recibido URL de un fork propio, por lo que el informe usa el upstream oficial como referencia y no afirma que se haya creado o modificado un repositorio.

**Próximo paso:** completar primero la Fase 0 del PLAN_PARA_CODEX.md; tras aprobación, ejecutar únicamente los issues 001–004 para establecer una línea base reproducible. No desarrollar toda la arquitectura de una vez.

## 17. Codex development contract

OpenCode supplies the product engine. Codex develops CLI_OPEN. Adding another engine requires approval. `PLAN_PARA_CODEX.md` and `AGENTS.md` define the binding phase order. Develop project modules under `implementacion/`. Preserve the history of `upstream/opencode` and obtain an architectural decision and approval before editing it. Verify OpenCode V2, flags, hooks, routes, and build requirements against the selected SHA. Inspect scripts and lockfiles before installation. Phase 0 stays read-only. Remote Codex uses provider inference. Keep secrets out of it and obtain authorization before adding a provider.

## 18. Consolidated technical architecture and reuse roadmap

### 18.1 Required architecture principle and classifications

**REUSE BEFORE EXTENDING. EXTEND BEFORE REPLACING.**

Audit OpenCode `v2.3.2` at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` and the current CLI_OPEN implementation before writing code. Use the existing classifications.

1. `EXISTENTE` means reuse official functionality directly.
2. `CONFIGURABLE` means use native `opencode.json`, flags, or environment variables.
3. `EXTENSIBLE` means use public APIs, lifecycle hooks, or supported plugins.
4. `PARCIAL` means add the missing logic in the supervisor or adapter layer.
5. `AUSENTE` means justify a loosely coupled module under `implementacion/`.
6. `DESCARTADA` means reject redundant proposals or changes with unacceptable complexity, risk, or insufficient benefit.
7. `APLAZADA` means defer beyond the initial MVP.

### 18.2 Native OpenCode V2 capabilities to audit and reuse

- Code Mode, native `execute`, grouped tool execution, and truncated output handling.
- `read`, `list`, `grep`, and `glob` with byte and line limits.
- MCP transport, discovery, and negotiation. Verify the applicable transport in the pinned engine.
- Native subagents, child sessions (`session`), structured JSON events, and cancellation.
- Git worktrees for isolated branches.
- Automatic compaction and reasoning variants (`thinking`).
- Native TUI, Pair Device, and web server.
- OpenAI-compatible, Ollama, Anthropic, OpenRouter, and local provider support.
- Language-aware formatting and LSP reuse where available. The pinned engine's missing qualified LSP and symbol interfaces for Repo Map remain subject to D24. [Pinned capability matrix](docs/MATRIZ_F7.md)

### 18.3 External references and adoption decisions

These classifications describe the original design. Verify implementation status in the F7 matrix and decision log. [F7 matrix](docs/MATRIZ_F7.md) · [Decisions](docs/DECISIONES.md)

| Reference | Capability | Classification | CLI_OPEN strategy |
|---|---|---|---|
| Cloudflare Code Mode | Dynamic discovery, on-demand schemas, grouped execution | `EXTENSIBLE` / `PARCIAL` | Reuse native `execute` and extend selective discovery and schema access. |
| Aider Repo Map | Tree-sitter, dependency graphs, incremental mapping | `PARCIAL` | Reuse `implementacion/memoria/` and dynamic context budgets. Structural extraction remains subject to D24. |
| Amp deep research | On-demand dependency and code understanding | `CONFIGURABLE` / `PARCIAL` | Use existing search and subagents for sufficiently complex tasks. Reuse a qualified LSP where available. |
| Kilo CLI routing | Model choice by complexity, cost, and latency | `PARCIAL` | Reuse `implementacion/gateway/` and extend only routing policy. |
| Qwen Code compatibility | Ollama, llama.cpp, vLLM, and self-hosted endpoints | `CONFIGURABLE` | Reuse native OpenAI-compatible providers. Keep LiteLLM optional. |
| OpenHands self-correction | Loop and stalled-progress detection, replanning | `PARCIAL` | Use native session and supervisor events. Bound replanning and preserve the existing loop. |
| Antigravity orchestration | Verifying subagents, coordination, and worktrees | `EXISTENTE` / `CONFIGURABLE` | Reuse native agents, child sessions, and worktrees. Start with one agent and delegate only independent work with measured benefit. |
| Goose Recipes | Parameterized, reproducible workflows | `EXISTENTE` / `EXTENSIBLE` | Reuse native skills and commands and keep the existing authoring interface. |
| Kiro Specs | Specifications, design, and acceptance criteria | `EXISTENTE` / `CONFIGURABLE` | Use structured Markdown, project instructions, and skills. |
| Cline headless and governance | Headless CLI, JSON events, CI/CD | `EXISTENTE` / `CONFIGURABLE` | Reuse `opencode run --format json` and the session events. Enforce budgets at the existing supervisor boundary. |
| amux mobile supervision | Remote status, progress, and budgets | `EXTENSIBLE` | Evaluate a limited Pair Device extension using the native session server. |
| Warp Oz asynchronous tasks | Cooperative pause, cancellation, and reconciliation | `PARCIAL` | Integrate safe pause points and state reconciliation with the supervisor and native sessions. |
| Crush TUI performance | Latency, RAM, and CPU | `CONFIGURABLE` | Preserve the native TUI and address measured bottlenecks. |
| Cursor remote executors | Delegation to self-hosted servers | `APLAZADA` | F9 after network and authorization controls qualify. |

### 18.4 Additional proposed improvements

1. **Deterministic tool-output filtering.** Deduplicate repeated lines, count occurrences, group identical errors, retain 5–10 surrounding lines, and redact secret patterns. Keep references to full local logs, preserve critical errors, and mark excerpts with `[TRUNCATED / SUMMARIZED]`.
2. **Recovery.** Prioritize Git, transactional copies, and disposable worktrees. Btrfs snapshots, Snapper, Timeshift, APFS, and System Restore remain disabled by default and classified `APLAZADA` in F9. They require platform qualification and explicit authorization for privileged actions.
3. **Claude Code and Codex hooks.** A lightweight supervisor adapter may interpret standard hook contracts. Keep it disabled by default and require an action allowlist, standard-user execution, a strict deadline, sandboxing, and zero authority over supervisor policy.
4. **Language-aware validation.** Detect Node/TypeScript, Python, Rust, Go, Java, C/C++, and Bash deterministically. Target the existing linters, formatters, and tests to edited files. Obtain approval before installing dependencies.
5. **Read-only scheduled diagnostics.** Reuse `implementacion/broker/` with systemd timers, cron, Task Scheduler, or launchd. Bound frequency, CPU, and report size. Keep operations read-only, inspectable, and user-disableable, without model calls.

### 18.5 Free initial use and provider choice

Detect authorized native OpenCode free models and local Ollama or LM Studio endpoints. Enforce the approved budget. When an allowance is exhausted, report it and let the user configure an authorized API or model. Require authorization before switching endpoints or incurring cost. Keep API keys private and preserve the local loopback restriction.

### 18.6 Security and budget architecture

- The trusted supervisor (`implementacion/supervisor/`) owns policy, profiles (PLAN, DIAG, WORKSPACE), budgeting, and process lifecycle within the qualified scope.
- The DIAG broker (`implementacion/broker/`) exposes five typed, read-only MCP queries.
- Linux Bubblewrap provides private loopback, read-only host mounts, and ephemeral workspace mounts.
- The inference gateway (`implementacion/gateway/`) is the sole model channel for qualified profiles. It enforces destination and bounds, and local profiles reject nonzero cost and disable fallback.
- Persistent project memory (`implementacion/memoria/` and `context.py`) uses JSONL, hash invalidation, and an `authority: none` envelope. Context is untrusted data with zero permission and policy authority.

The design in this report describes intended architecture. Current qualification and gates are recorded in the project state and roadmap. [Project state](ESTADO.md) · [Execution plan](PLAN_PARA_CODEX.md)
