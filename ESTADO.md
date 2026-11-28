# Project state

The stabilization directive covers gateway limits, streaming, concurrency, APIs, sandbox connectivity, real editing, CI, and reproducible tests. Real local inference and secure remote integration have separate gates. Computer Use remains deferred. [Agent instructions](AGENTS.md)

The historical public reference is `dfcdd822b358b96f19be2d64c0ad1b61d1404f6a`. The real-client HTTP checkpoint is `5335b70c2bece3a3d8c0256358e1d16e19c88350`, following `242c3b1`. The working branch is `fase-1` and tracks `origin/main`.

## Documentation map

- Architecture and decisions D01–D24. [Technical report](INFORME_TECNICO.md) · [Decisions](docs/DECISIONES.md)
- Phase order, acceptance gates, and reuse. [Roadmap](PLAN_PARA_CODEX.md) · [F7 matrix](docs/MATRIZ_F7.md)
- Audit, patches, and qualification. [Changes](docs/CAMBIOS.md) · [Test evidence](docs/PRUEBAS.md)
- Reproduction and next steps. [Continuity](CONTINUAR.md)

## F0–F5 · Qualified on Linux x86_64

The qualification environment was CachyOS Linux x86_64. OpenCode `v2.3.2` at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` supplies the engine. PLAN, the DIAG MCP broker, and Bubblewrap are qualified. The workspace supervisor edits a disposable copy, traverses nested paths through `snapshot` and `openat` with `O_NOFOLLOW` and `O_DIRECTORY`, supports real code extensions with `MAX_FILE` at 256 KiB, and publishes approved changes to a separate Git ref transactionally.

## F6 · Gateway and local inference

The OpenAI-compatible gateway has bounded concurrency via `CLI_OPEN_GATEWAY_MAX_CONCURRENCY`. At saturation it returns HTTP 503 without queueing a worker. `model_matches` accepts exact IDs and explicit `alias=canonical` pairs. `complete_streaming` forwards SSE incrementally, validates lines, and forwards errors before closing. The socket timeout uses `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` with `CLI_OPEN_GATEWAY_TIMEOUT` as a legacy alias. Supported request fields include `frequency_penalty`, `presence_penalty`, `seed`, `stop`, `parallel_tool_calls`, `reasoning_effort`, and `response_format`.

Both the HTTP and CLI fixtures passed. The real-client load in `tests/fase6-concurrencia.py` reached a peak of two concurrent streams at a configured limit of two. It rejected excess clients with 503 and observed the configured one-second timeout.

The physical CPU fixture passed chat, SSE, and tool calls through the gateway using llama.cpp `b12753` and Llama 3.2 1B Instruct Q4_K_M (~771 MiB), with artifacts isolated in `/tmp/opencode`. Check for existing temporary artifacts before considering another download. In the full OpenCode session, the permitted read succeeded and the out-of-scope read was denied. The final response was empty, so full-session qualification remains open. [Test evidence](docs/PRUEBAS.md)

## F7 · Persistent memory and selective context

Project memory uses JSONL outside the repository and invalidates referenced files by SHA-256. Token-aware ranking is covered by `tests/fase7-memoria.py`. The supervisor includes memory in an `authority: none` envelope and verifies its byte limit. The loopback fixture observed no privilege increase. The shared budget across memory, code, web, and tool output remains open.

F7.1 records reuse classifications and a deterministic baseline. The pinned engine has 36 `highlights.scm` grammars and ripgrep. The environment lacked symbol queries, an LSP service, a usable Tree-sitter runtime, and `.wasm` grammars. D24 keeps structural Repo Map blocked. The preserved stash contains an independent AST and regex indexer and was left unapplied. The shipped F7.2 increment discovers paths on demand with ripgrep. The optional `contexto-selectivo` preset qualifies path discovery, matches with line numbers, paginated reading, and a final answer under Bubblewrap. Structural symbol extraction for Python, JS, TS, Java, and C# remains unqualified. [F7 matrix](docs/MATRIZ_F7.md)

The native web audit and isolated HTML baseline are complete. The opt-in HTML filter passed deterministic fixtures. External retrieval, additional format conversion, and relevance-based section selection remain deferred. The latter requires an explicit relevance query. [Decisions](docs/DECISIONES.md) · [Measurements](docs/PRUEBAS.md)

## Reproducibility and CI

GitHub Actions has separate Portable and Linux jobs. The OpenCode profile verifies binary versions and SHA-256 before running. CI qualification of a clean engine build and its artifacts remains open.

Historically, `f74ab48` passed Portable and failed Linux during Bubblewrap loopback setup. The workflow correction loads Ubuntu's packaged AppArmor profile. `810af0c` passed loopback setup and failed Python startup in the separated ELF library layout. The F4 mount change prepared the next remote qualification. [CI evidence](docs/PRUEBAS.md)

## D07 · Local admission and remote inference

**BLOCKED** for real remote inference. The public catalog showed a free Gemma endpoint with tools, but authenticated OpenRouter quota and account access were unverified. Native OpenCode OAuth exists. The effective ChatGPT model catalog and a zero-cost supervised API route for the fixture remain unverified. Free OpenCode Console chat is restricted to its native client. Remote scenarios A–D were not run. The Llama 3.2 1B comparison remains **INCONCLUSIVE**. [Remote fixture plan](CONTINUAR.md)

Early testing passed destination, per-request limits, and local isolation, with **FAIL** for cancellation during stalled SSE. The corrected cancellation regression passed with a synthetic upstream. The authenticated private listener qualifies per-task reservations, cancellation, strict SSE termination, and expiration. Its SQLite ledger preserves reservations and the original deadline on restart, rejects corrupted state, and records reported usage separately.

The opt-in Responses listener uses the existing authenticated ledger against a synthetic upstream under Bubblewrap. Chat Completions remains available in its own profile. The engine's direct native ChatGPT transport has no qualified official interface through the supervised gateway. D07 remains blocked pending that transport and explicit content and destination authorization.

## D07.2 · Partial recovery under Bubblewrap

At public checkpoint `a3fbcf4`, the local fixture recovered a completed read and a shell operation interrupted after an observable effect but before its recorded result. It also tested complete SSE without usage and rejection of an unapproved model. Later D07.3 evidence extends that scope.

## D07.3 · Local recovery qualification

The initial qualification started at `aca792ea24d7b4d1a28e110252465a1c8e3fb95b`, confirmed on GitHub at the time. It distinguished incomplete input, interrupted shell effects, denied edits, stale and ambiguous replacements, and completed results. The native stdio MCP fixture covered interruption before an effect, interruption after an effect but before reply, and recorded completion. The follow-up at `054456c00f8c0fa542853cb870d706806604917c` qualified a distinct equivalent call after a completed result. [Earlier MCP evidence](docs/PRUEBAS.md#d073--native-mcp-interruption-under-bubblewrap)

## D07.3 · Authorization and publication checkpoint

Work started at `054456c00f8c0fa542853cb870d706806604917c` on `fase-1`. The local OpenCode profile passed the pending native MCP permission boundary and equivalent new calls after an uncertain result. The workspace tests passed the concurrent revision check before reviewed Git publication. Active native read/search interruption, the final native edit-write interval, and the full supervisor restart remain open. D07 real remote inference and the F8 entry gate remain blocked. [Test evidence](docs/PRUEBAS.md#d073--permission-dispatch-and-equivalent-calls-after-an-uncertain-effect)

## English engineering migration

The quickstart, bootstrap guidance, agent policy, selective context preset, memory envelope guidance, implementation diagnostics, roadmap, continuity documents, and architectural decisions use English. Spanish input and fixture data are preserved. The earlier runtime benchmark measured 466 estimated tokens before the change and 426 afterward. The current documentation edits do not change those inputs. The technical report's current reuse section and the D07.3 evidence matrix also use English. Earlier report sections and historical change and test entries still contain Spanish. [Benchmark](docs/PRUEBAS.md#english-engineering-text-benchmark)

## Resume work

Read `AGENTS.md`, `CONTINUAR.md`, `ESTADO.md`, and `docs/DECISIONES.md`. Verify Git status and compare HEAD to the public reference, then run the regression commands applicable to the change.

```sh
python3 -B -m unittest discover -s tests
python3 -I -B implementacion/supervisor qualify-linux
python3 -I -B tests/fase6-gateway.py
python3 -I -B tests/fase6-concurrencia.py
python3 -I -B tests/fase7-lineabase.py
python3 -I -B tests/fase7-repomap.py
git diff --check
```

The phase gate and authorized next steps are in the continuity guide. [CONTINUAR.md](CONTINUAR.md)

## D07.4 · Launcher recovery

Starting SHA `d3ec56fbb08742b259a846ddb1b5d97187d03771` on `fase-1`, verified as the public `main` at the start of the work. The composed launcher fixture observed the same OpenCode session and SQLite task after a crash, no automatic MCP effect replay, one newly denied operation, one explicitly authorized new operation, retained reservations and deadline, and cleanup of seven observed descendants. Product task orchestration still requires qualification. The native edit preview probe reproduced a stale overwrite. The read/search result-persistence cases passed. The exact final write interval and interruption during filesystem or ripgrep work remain open, so the F8 entry gate stays closed. [Lifecycle evidence](docs/PRUEBAS.md#d074--launcher-restart-with-native-session-and-task-budget)

## D07.4 · Native ChatGPT diagnostic

The pinned acquisition path passed preparation and cancellation before browser authorization. Account consent, available subscription models, and native inference remain unverified. The supervised gateway has synthetic Responses evidence only. Real D07 remains blocked pending a supported provider and tool isolation boundary with trusted egress and durable task budgeting. [Diagnostic evidence](docs/PRUEBAS.md#d074--native-chatgpt-pre-browser-diagnostics)

## D07.5 · Version-bound supervised editing

Starting SHA `0cd96c733a4f503a5e3c4cce772a402672cf237b`, confirmed on public `main`. The supervisor now checks source identity and metadata in addition to bytes during approval and final publication. The public review report keeps its existing fields and earlier approvals require a fresh review. The native editor still lacks a supported post-approval, pre-write validation hook. Its known overwrite and the production lifecycle with a separately protected budget remain open. F8 stays gated. [Evidence](docs/PRUEBAS.md#d075--version-bound-workspace-approval)

### Disposable edit containment

Starting SHA `a851751e02a7880d0995548b87d0c65a2b2d5107`. The supervised editor operates on a disposable copy with permission only for proposed paths. The host rejects linked or changed output before issuing a review, and preserves version-bound approval and a separate publication ref. Direct native editing still has the stale-preview race. Production restart with separate trusted state and native in-flight I/O cancellation remain open. [Test evidence](docs/PRUEBAS.md#d075--disposable-edit-containment)

### Native ChatGPT account recognition

The user completed native consent in the installed Brave browser. The pinned OpenCode integration reported a connection and exposed 18 OpenAI model IDs in the temporary profile. Native inference was not requested. Supervised D07 remains blocked on the trusted transport. [Test evidence](docs/PRUEBAS.md#d075--brave-account-diagnostic)

## D07.6 · Review stop and native search I/O

Starting SHA `791c2b3e3caa16dfab4cf2a34be8962e61c664e0` was verified on public `main`. Production `review-workspace` passed SIGTERM cleanup and restart as a fresh review. `glob` and literal `grep` passed at their native libc I/O result boundaries. The native reader has only result-persistence evidence. The full supervised session-and-budget restart with trusted state outside the tools remains open. Native edit containment still passes and F8 stays gated. [D07.6 evidence](docs/PRUEBAS.md#d076--production-review-stop-and-restart)

### Native authentication continuity

The previous Brave consent succeeded with 18 exposed model IDs, and that temporary profile has been removed. No credential is currently available to CLI_OPEN from that run. The native diagnostic can now retain a newly created profile in an explicitly selected private directory after fresh user consent and metadata verification. The retained success path awaits that consent. Native inference and supervised D07 remain separate and unqualified.

## D07.7 · Starting point and gateway recovery

The clean initial branch and public tracking reference were at `196c3a98278b46083bf5ec28b31acbc129045cf1`. GitHub Actions confirmed success. The native checkout remains pinned to OpenCode v2.3.2 at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. The gateway passed additional task identity, bearer rotation, and state-directory rejection tests. Full production task ownership and native read I/O qualification still gate F8. Real D07 stays blocked. [Evidence](docs/PRUEBAS.md#d077--gateway-restart-negative-cases)

### F7.2 budget and preliminary F8 measurements

The regression reduced a 1,268-byte envelope to 204 bytes under a 256-byte limit and preserved the memory entry. The independent F8 harness measured context, pinned search, reviewed editing, and composed recovery sequentially on Linux. No full baseline comparison, governor, worker coordination, concurrency adjustment, or automatic tool activation was enabled. [Measurement evidence](docs/PRUEBAS.md#f8--bounded-preliminary-measurements)

## D07.8 preparation and preliminary F8 measurements

Work started at `ea66e91c6a974dfd0777b5a74c375eb308337c6c` on `fase-1`, matching remote `main`. The Repo Map stash remains at `943cc63e`. Published CI succeeded for the starting SHA. [CI run](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/46088689868)

The pinned SDK passed workspace-driver registration and first-tool gating with an in-memory driver. Checkpoint `366a444` adds the late hard-link containment case and makes the native I/O fixture reject unsupported case selectors. The tool trust boundary still requires production integration. Direct editing remains **CONTAINED**. Native read and paginated read interruption at the actual I/O boundary remain unqualified. The standalone gateway and the composed restart fixture are narrower evidence than full production recovery. Supervised remote inference stays blocked. [Driver and containment evidence](docs/PRUEBAS.md#d078--workspace-driver-and-containment-evidence)

Repeated synthetic trials now record variability and sampler CPU. The production F8 gate still requires D07.8 recovery and native read I/O. The next eligible D07.8 task is a deterministic workspace-driver proof using the production gateway and a Bubblewrap worker with separately protected task state. [Measurement evidence](docs/PRUEBAS.md#f8--sampler-overhead-and-trial-variability)

The portable, Linux and pinned OpenCode profiles passed locally. The focused native search I/O fixture and two SDK tests passed independently. The OpenCode profile reproduced the known native edit overwrite and passed its separate result-persistence read cases. [Test evidence](docs/PRUEBAS.md#d078--workspace-driver-and-containment-evidence)

## D07.9 · SDK recovery barrier qualified in isolation

Started at `bfc1185a9b0f4ecf2fb04478340c58ab385ac44f` on `fase-1`, two local commits ahead of confirmed remote `ea66e91c6a974dfd0777b5a74c375eb308337c6c`. Stash `943cc63e` remains preserved. The internal SDK adapter passed startup ordering against a native suspended-session claim. Portable, Linux, OpenCode, and the standalone native search I/O fixture passed. D07.9 production task ownership, separate trusted gateway and state, and the in-flight native file reads remain open. The F8 entry gate remains closed. [Evidence](docs/PRUEBAS.md#d079--native-sdk-startup-admission)

## D07.9 · Native file-read interruption qualified

At base `46377d4`, both native file-read cases passed at successful `pread64` before userspace delivery. Search remains qualified at its libc result boundaries. Full production task ownership and restart with a separate trusted ledger and authentication still block F8. [Evidence](docs/PRUEBAS.md#d079--native-file-read-syscall-boundary)

## D07.9 · Gateway ownership binding qualified

At base `a5382c5`, the standalone gateway passed native ID binding and credential rotation, including recovery of an active reservation after gateway termination. The SDK sweep gate and gateway binding now have separate executable regression coverage. Production ownership still needs one supervisor lifecycle for both components, a restricted workspace driver, and uncertain-MCP reconciliation across a full restart. The F8 entry gate remains closed. [Evidence](docs/PRUEBAS.md#d079--bound-gateway-admission)
