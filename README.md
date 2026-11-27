# CLI_OPEN quickstart with Codex

## 1. Prepare the full checkout

Extract the ZIP, open a terminal in `Agente_OpenCode`, and run the following command with Git and internet access.

```sh
git clone --recurse-submodules https://github.com/anomalyco/opencode.git upstream/opencode
```

The package includes `upstream/`. The command downloads the full Git history and any declared submodules without installing dependencies. If the clone already exists, verify its origin and status. The initial review selects and qualifies a specific tag or commit.

## 2. Open Codex from this folder

Check `codex --help` and `codex --version` for the options below.

```sh
codex --sandbox read-only --ask-for-approval on-request
```

Paste the contents of `INICIAR_CODEX.txt`. When using a remote service, exclude secrets and data that must stay local.

## 3. Advance by phase

Review the Phase 0 evidence before authorizing Phase 1. Keep write access scoped and preserve the original repository while testing its interfaces.

## Files

- AGENTS.md: Codex instructions.
- PLAN_PARA_CODEX.md: phases, limits, and acceptance criteria.
- INFORME_TECNICO.md: architecture, audit, and backlog.
- ESTADO.md: project continuity.
- upstream/opencode/: clone from Step 1.

## Optional real local model test

The test runs on CPU. Check for at least 8 GiB of available RAM and 2 GiB of temporary storage. The download is about 800 MiB.

```sh
mkdir -p /tmp/opencode/llama /tmp/opencode/models
curl -L --fail -o /tmp/opencode/llama/llama.tar.gz \
  https://github.com/ggml-org/llama.cpp/releases/download/b12753/llama-b12753-bin-ubuntu-x64.tar.gz
curl -L --fail -o /tmp/opencode/models/llama-3.2-1b-instruct-q4_k_m.gguf \
  https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf
tar -xzf /tmp/opencode/llama/llama.tar.gz -C /tmp/opencode/llama
python3 -I -B tests/fase6-modelo-local.py
```

The test runs `llama-server` with two CPU threads and validates chat, SSE streaming, and tool calls through the gateway. It requires no system-wide service.

**Original ZIP limitations.** The upstream download was unavailable when the ZIP was assembled, so the archive omitted the upstream checkout. The original packaging step included no build or agent test. Consult `ESTADO.md` for subsequent qualification.
