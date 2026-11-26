# Proyecto Agente OpenCode — inicio con Codex

## 1. Preparar el checkout completo

Extrae el ZIP, abre una terminal dentro de `Agente_OpenCode` y ejecuta (requiere Git e Internet):

```sh
git clone --recurse-submodules https://github.com/anomalyco/opencode.git upstream/opencode
```

El directorio `upstream/` está incluido. El comando descarga el historial Git sin `--depth`, además de submódulos declarados, si existen. No instala dependencias. Si ya tienes un clon en esa ruta, no repitas el comando: comprueba su origen y estado. La revisión inicial seleccionará un tag/commit adecuado; el checkout inicial no constituye una versión calificada.

## 2. Abrir Codex desde esta carpeta

Comprueba `codex --help` y `codex --version`. Si la versión admite estas opciones:

```sh
codex --sandbox read-only --ask-for-approval on-request
```

Pega el contenido de `INICIAR_CODEX.txt`. Si Codex usa un servicio remoto, no introduzcas secretos ni datos que no deban procesarse allí.

## 3. Avanzar por fases

Revisa la evidencia de la fase 0 antes de autorizar la fase 1. No habilites escritura general. Conserva el repositorio original intacto mientras se prueban sus interfaces.

## Archivos

- AGENTS.md: reglas para Codex.
- PLAN_PARA_CODEX.md: fases, límites y aceptación.
- INFORME_TECNICO.md: arquitectura, auditoría y backlog.
- ESTADO.md: continuidad del proyecto.
- upstream/opencode/: clon que se obtiene en el paso 1.

## Prueba opcional de modelo local físico

La prueba real usa CPU, no requiere GPU. Comprueba al menos 8 GiB de RAM
disponible y 2 GiB de espacio temporal. Descarga aproximadamente 800 MiB:

```sh
mkdir -p /tmp/opencode/llama /tmp/opencode/models
curl -L --fail -o /tmp/opencode/llama/llama.tar.gz \
  https://github.com/ggml-org/llama.cpp/releases/download/b12753/llama-b12753-bin-ubuntu-x64.tar.gz
curl -L --fail -o /tmp/opencode/models/llama-3.2-1b-instruct-q4_k_m.gguf \
  https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf
tar -xzf /tmp/opencode/llama/llama.tar.gz -C /tmp/opencode/llama
python3 -I -B tests/fase6-modelo-local.py
```

La prueba ejecuta `llama-server` con dos hilos de CPU y valida chat, streaming
SSE y tool call mediante el gateway. No se instala ningún servicio global.

**Límite del paquete:** no incluye los bytes del repositorio oficial porque la descarga no estuvo disponible al prepararlo. No se ha realizado build ni prueba del agente.
