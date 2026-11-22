# Continuar CLI_OPEN

## Punto de reanudación

El proyecto cerró la **Fase 6 (P3)** para el perfil local sintético. La **Fase 7 está en curso** (módulo 1 de 5 cerrado). Las fases 1–5 se cerraron para los flujos acotados descritos en la evidencia. CachyOS Linux x86_64 es el entorno probado. Arch, Ubuntu, Debian, Fedora, WSL2, Windows y macOS requieren validación propia. Continuar la Fase 7 en el orden aprobado: contexto, enrutador, autocorrección y subagentes.

1. Leer `AGENTS.md`, `PLAN_PARA_CODEX.md`, `INFORME_TECNICO.md` y `ESTADO.md`. Consultar `docs/DECISIONES.md`, `docs/CAMBIOS.md` y `docs/PRUEBAS.md` para decisiones y pruebas ya verificadas.
2. Comprobar `git status -sb` y `git log -1 --oneline`. El remoto del proyecto es [CLI_OPEN](https://github.com/njua4551-commits/CLI_OPEN). El checkout independiente de OpenCode, si está disponible, está en `upstream/upstream/opencode`.
3. **Tarea cerrada:** la CLI fijada se conectó al gateway por el proveedor OpenAI-compatible. `tests/fase6-cli-gateway.ts` demuestra `OpenCode → gateway → endpoint de loopback`, rechazo de costo distinto de cero y endpoint caído sin salida alternativa. El gateway sirve `--listen` con validación de modelo y costo en SSE.
4. **Fase 7 en curso:** memoria cerrada en `implementacion/memoria/`. Siguiente módulo: optimización de contexto en `implementacion/contexto/`. Cada módulo se prueba, documenta y publica antes del siguiente.
5. **Aplazado por D07:** seguimiento de presupuesto remoto, aprobación por contenido y calificación de un modelo físico local. No habilitar inferencia remota de producto sin una autorización nueva. Mantener el perfil local sin salida externa. La Fase 6 requiere una comprobación separada de modelo físico local o una decisión explícita sobre su aplazamiento. Antes de habilitar inferencia remota de producto, probar autorización del contenido, destino, conciliación de costo y denegación cuando el gasto o el destino sean desconocidos. OpenRouter se probó únicamente como fixture sintético de USD 0 en la Fase 1. Actualizar los registros tras cada hito.

## Base técnica y archivos

- Motor y CLI: OpenCode `v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. No editar el núcleo por rutina. La copia compilada y Bun 1.4.4 están en `.fase1/` en el entorno de pruebas. `upstream/` y `.fase1/` están excluidos de Git y pueden faltar en otro equipo. Consultar `ESTADO.md` y `docs/PRUEBAS.md` para reconstruir la base con la instalación, copia y build ya documentados.
- Supervisor y sandbox: `implementacion/supervisor/__main__.py`. PLAN carece de ejecución y escritura. DIAG expone únicamente el broker de solo lectura en `implementacion/broker/__main__.py`.
- Edición: `workspace.py`, `workspace_opencode.ts`, `workspace_worker.py` y `workspace_git.py` bajo `implementacion/supervisor/`. La herramienta nativa escribe en una copia. Una aprobación de revisión puede crear una rama Git separada. La rama activa, el índice y el árbol de trabajo quedan fuera de esa operación. Véase `docs/evidencias/FASE5.md`.
- Gateway actual: `implementacion/gateway/__main__.py`. Acepta JSON por stdin, de una única solicitud a `127.0.0.1`. El fixture está en `tests/fase6-gateway.py` y la evidencia en `docs/evidencias/FASE6.md`.
- Incidencia no bloqueante: `mcp list` puede estar vacío en frío. `--standalone run` sí descubre e invoca el broker en la sesión probada. Véase `docs/evidencias/FASE3.md`.

## Validación focalizada

Usar solo las pruebas afectadas por el cambio. Ya pasaron 440 pruebas upstream, los ocho casos de CLI en loopback, la integración MCP, la calificación Bubblewrap, la edición nativa con publicación Git y el fixture HTTP del gateway. `docs/PRUEBAS.md` registra su alcance, entorno y límites.

```sh
python3 -B -m unittest discover -s tests
python3 -I -B implementacion/supervisor qualify-linux
python3 -I -B tests/fase5-review.py
python3 -I -B tests/fase6-gateway.py
git diff --check
```

Los tres recorridos de aislamiento y transporte requieren un entorno que permita las funciones específicas de Bubblewrap o loopback. Ejecutar el fixture de gateway dentro de una red privada. Si el entorno bloquea sockets o namespaces, registrar el error y conservar PLAN/DIAG. La existencia de Bubblewrap en PATH no acredita aislamiento. No abrir red externa para resolver una prueba local.

Para repetir únicamente el fixture HTTP en la topología Linux ya probada, ejecutar desde la raíz del proyecto:

```sh
bwrap --die-with-parent --unshare-user --unshare-pid --unshare-ipc \
  --unshare-net --unshare-uts --disable-userns \
  --ro-bind /usr /usr --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind "$PWD/implementacion" /implementacion --ro-bind "$PWD/tests" /tests \
  --clearenv --setenv PATH /usr/bin:/bin /usr/bin/python3 -I -B /tests/fase6-gateway.py
```

## Límites de continuidad

No adjuntar secretos al código, logs, prompts ni Git. Las credenciales autorizadas se inyectan en el entorno de la sesión que las necesita. No usar sudo, publicar sin autorización ni cambiar de motor. Priorizar Linux x86_64 y mantener protocolos y componentes portables, con límites de archivos, red, procesos y permisos. Los documentos conservan decisiones y evidencia; las autorizaciones se comprueban en la sesión vigente.
