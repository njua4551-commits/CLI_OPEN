# Plan for building CLI_OPEN in modules with Codex

CLI_OPEN is a secure, economical, cross-platform development, reasoning, and diagnostics agent built on OpenCode V2. Codex or Antigravity develops the project.

Version 3.0 defines the phase order, gates, and acceptance criteria. `INFORME_TECNICO.md` defines the technical requirements and architecture.

## Current directive

Stabilize CLI_OPEN before advancing the roadmap. Audit and correct gateway limits, streaming, concurrency, API compatibility, sandbox connectivity, real code editing, CI, and reproducible tests. Then qualify a real local model and prepare secure remote integration with budgets and explicit authorization. Preserve F0–F7, native OpenCode capabilities, and existing protections. Make limits configurable and verifiable. Work in small modules, run focused regressions, update the documentation, and create reviewed Git checkpoints. Require observed evidence before declaring a feature complete. Defer new features, including Computer Use, until the fundamentals are stable. See `AGENTS.md` for the full directive.

## Required architectural principle

**REUSE BEFORE EXTENDING. EXTEND BEFORE REPLACING.**

Before implementation, inspect the pinned OpenCode source (`v2.3.2`, SHA `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`) and CLI_OPEN. Identify existing APIs, plugins, features, and configuration. Exercise the reusable capabilities, identify missing behavior, and choose the smallest maintainable solution that meets quality and safety requirements.

Classify each proposal before acting.

- `EXISTENTE` means reuse directly.
- `CONFIGURABLE` means use native configuration.
- `EXTENSIBLE` means extend public APIs, hooks, or plugins.
- `PARCIAL` means implement the missing increment only.
- `AUSENTE` means evaluate a project module with a specific justification.
- `DESCARTADA` means the proposal lacks sufficient measurable benefit.
- `APLAZADA` means defer beyond the initial MVP.

Reuse native MCP, sessions, web UI, TUI, compaction, providers, permissions, LSP, and multi-agent infrastructure where adaptable.

## How to use this plan

Keep this plan with the project's technical report and identified OpenCode checkout. Ask Codex to read both documents and complete the authorized phase, present results, and wait for approval to advance. Codex develops the product, and OpenCode provides the runtime. Evaluate a different engine only after documenting an indispensable blocker and obtaining approval.

Locate and report the actual checkout path before editing. Preserve the existing checkout location and name.

## Target outcome

Support Linux, macOS, and native Windows, and evaluate WSL2 separately. Start with planning and read-only diagnostics. Enable edits only inside an isolated workspace after qualifying isolation on the operating system in use. Keep the agent within its scoped tools and effective privileges. Local, remote, fast, and deep model profiles share the same permission boundary.

## Safety and development rules

1. Work within the project and identified checkout. Access personal or system directories only when required and authorized.
2. Describe intended files and the reason for editing before making changes. Keep the diff small and present it at the phase review.
3. Use standard-user privileges. Keep operating-system permissions, services, network settings, firewalls, registries, policies, and scheduled tasks outside the prototype's scope.
4. Use named diagnostic actions with typed, bounded inputs and results. Keep host command execution outside the broker.
5. Obtain approval before installing dependencies or changing global settings. Keep keys and tokens out of the repository.
6. Obtain explicit consent before transmitting files, logs, private paths, or project content to an additional external service. A remote Codex session is itself provider processing. Require authorization for fallback from a local provider.
7. Qualify the sandbox with positive and negative tests in the effective environment.
8. Keep capabilities in PLAN/DIAG when isolation fails, permissions are ambiguous, or a result is uncertain. Document the blocker.
9. Preserve the OpenCode core during the prototype. Reconsider only after reproducing and documenting a concrete public API limitation.
10. Present changes, commands, results, limitations, and acceptance evidence before advancing.

Check Git status and existing changes before work. Preserve other contributors' work and leave a reviewable branch or commit for each phase.

## Suggested layout

Adapt this example to the existing workspace. Preserve the downloaded checkout's location.

```text
agente-local/
├── PLAN_PARA_CODEX.md
├── INFORME_TECNICO.md             # requirements and architecture
├── upstream/
│   └── opencode/                   # complete checkout at the pinned version and commit
├── implementacion/                 # project-owned code outside the upstream core
│   ├── supervisor/
│   ├── adapters/
│   ├── broker/
│   ├── gateway/                    # optional, for a later phase
│   └── policy/
├── tests/
│   └── fixtures/                   # synthetic data only
└── docs/
    ├── DECISIONES.md
    ├── MATRIZ_PLATAFORMAS.md
    └── evidencias/
```

Use the directories required by the phase. Inspect how the checkout builds before choosing the supervisor language and interfaces.

## Development phases

### Phase 0 — Read-only inspection

Review this plan and `INFORME_TECNICO.md`. Locate the checkout's Git root, branch, pending changes, license, contribution documents, and build instructions. Record the OS, version, architecture, shell, Codex version, and effective runtime, including whether the environment is native Windows, WSL2, macOS, or Linux. Distinguish assumptions in the report from findings that source and official documentation can verify.

Acceptance requires an inventory, paths, Git status, and the documented build commands. Keep the inspection read-only and leave dependencies and the machine unchanged.

### Phase 1 — Comparative integration test (P-1)

Qualify a specific stable OpenCode V2 release. Record the release, tag or commit, date, official documentation, and changelog. A moving development branch requires a specific justification.

- Start with a clean, private configuration. Use only the server, credentials, and plugins specified for the test.
- Build the checkout and run a read session on a test project.
- Use a synthetic OpenAI-compatible loopback endpoint for deterministic tool calls, long responses, cancellation, and errors.
- The historical authorized OpenRouter test uses `liquid/lfm-3-1.7b:free`, synthetic fixtures, and a USD 0 budget. Verify tool support and zero price before execution. Supply `OPENROUTER_API_KEY` through the environment. Stop on missing authorization or credentials, price changes, or endpoint failure. Disable fallback, alternate models, and hosted tools.
- Track local model inference separately. Preserve explicit configuration for Ollama, llama.cpp, and other endpoints.
- Discover and use MCP through an approved test server. Test cancellation and child-process cleanup.
- Verify configuration, connection routes, available public APIs for extension, policy, logging and cancellation, and the sandbox limits demonstrable on the test system.

Record evidence, failures, and reproduction steps in `docs/evidencias/`. Qualify isolation independently of startup. Defer memory, gateway, scheduling, browser access, and the host broker.

Continue with OpenCode when the supervised session, synthetic transport, authorized inference case, and required APIs pass on the upstream core. Qualify physical local inference separately. Investigate Codex CLI as an alternative only for a documented indispensable blocker and obtain approval before switching. Reduce scope or stop when OpenCode fails the requirements. Preserve existing permissions.

Acceptance requires reproducible evidence and a decision on whether to continue, change engine, or stop.

### Phase 2 — Supervisor, doctor, and PLAN (P0)

After Phase 1 approval, build the minimum supervisor. Detect the OS, architecture, shell, WSL, effective privileges, and declared isolation backend availability. Display the profile and its capability limits. Keep PLAN free of host execution and file changes. Store trusted policies beyond the agent's editing scope.

Acceptance requires correct environment detection, absence of host actions, and an explicit unverified status when isolation cannot be established.

### Phase 3 — Read-only diagnostic broker (P1)

Define a small allowlist of actions, each with validated parameters and bounded output. Authenticate components when required by the transport. Reject out-of-scope actions, paths, parameters, and resources. Record queries without collecting secrets or unnecessary data. Start with synthetic fixtures.

Acceptance requires successful authorized queries, rejection of invalid and out-of-scope requests, and a bounded catalog without a generic host command action.

### Phase 4 — Platform isolation (P2)

Qualify Linux, macOS, native Windows in PowerShell, and WSL2 independently before enabling writes. Qualify CMD separately if required. WSL2 establishes evidence only for its own environment.

- Attempt writes outside the synthetic workspace and verify rejection.
- Cover absolute paths, traversal, symlinks or junctions, and disallowed paths.
- Check network behavior, child processes, timeouts, and cancellation.
- Verify that local configuration, plugins, instructions, and tool results cannot broaden permissions.
- Verify PLAN/DIAG fallback when isolation is missing or fails.

Writes depend on all critical tests passing on the effective platform.

### Phase 5 — Safe workspace editing (P4)

Use a disposable, controlled copy rooted in the authorized workspace. Present a diff before integration and run only approved validators within the same qualified boundary. Reconcile uncertain writes before retrying.

Acceptance requires isolated tests and changes, a reviewable diff, and rejection of writes outside the boundary.

### Phase 6 — Models, gateway, and budget (P3, optional)

Start with a tested local provider such as Ollama or LM Studio after its model passes tool-call tests. Keep local mode free of external transmission. Authorize remote inference separately from editing. Present the proposed outbound content, remove secrets and unnecessary data, and obtain explicit approval before sending. Bound destination, concurrency, deadline, and budget. Stop when provider identity, cost, or results cannot be established. Verify and record adapter capabilities and require authorization for remote escalation.

Acceptance requires verified destination and limits, a local profile with no remote route, and explicit approval before any remote call after local failure.

### Phase 7 — Consolidated roadmap

F7 expands context, efficiency, controlled autonomy, and supervision while retaining the completed F0–F6 scope. Each subphase reuses native capabilities and requires reproducible evidence.

#### F7.1 — Native capabilities audit and baseline

- Audit proposals against native `execute`, subagents, child sessions, worktrees, compaction, reasoning variants, Pair Device, TUI, web UI, and LSP.
- Classify each proposal using the seven established identifiers and establish reproducible test suites and metrics before extending the engine.

#### F7.2 — Selective context and repository understanding (Aider / Amp)

- Integrate existing persistent memory in `implementacion/memoria/`.
- Build incremental structural Repo Map only when Tree-sitter or native OpenCode/LSP symbol graphs can support it.
- Run deep dependency and symbol investigation on demand when the task warrants it.
- Use dynamic context token budgets and selective workspace-change invalidation. Reuse the native engine for indexing and context where available.

#### F7.3 — Code Mode and deterministic output filtering (Cloudflare)

- Reuse native `execute` and retrieve tool schemas on demand.
- Enforce each tool's permissions, isolation, and budget in bundled execution.
- Deduplicate log lines, group equivalent errors, count occurrences, preserve surrounding failure context, and redact secrets.
- Use local caching and invalidation without additional model calls.

#### F7.4 — Models, shared budgets, and providers (Kilo CLI / Qwen Code)

- Route by complexity, availability, latency, privacy, and cost.
- Reuse `implementacion/gateway/` and the native provider manager.
- Qualify OpenAI-compatible endpoints, Ollama, llama.cpp, LM Studio, vLLM, OpenRouter, Groq, and self-hosted servers. LiteLLM remains optional.
- Track shared task budgets for input and output tokens, cost, time, concurrency, and subagents.
- Identify authorized free native models and local endpoints. Display quotas and require authorization before switching to a paid model.
- Complete D07 safety controls before enabling real remote product inference.

#### F7.5 — Controlled autonomy, validation, and recovery (OpenHands / Antigravity)

- Detect loops and stalled progress, classify errors, and bound replanning using observed evidence.
- Run focused tests and the project's compilers, linters, and formatters for the language in use. Dependencies require approval.
- Delegate only justified independent tasks to native child sessions and isolate branches with Git worktrees.
- Review and revert changes transactionally through authorized paths.

#### F7.6 — Reusable automation and governance (Goose / Kiro / Cline)

- Reuse native skills, parameterized commands, and reproducible workflows.
- Use specifications and tasks for complex work.
- Bound headless execution with budgets and track JSON events for CI/CD validation.
- Restrict lightweight adapters for external hooks (Claude Code / Codex) to supervisor policy, time limits, and network controls.

#### F7.7 — Supervision and asynchronous tasks (amux / Warp Oz)

- Extend native Pair Device and web UI where needed to show progress, token usage, remaining budgets, approvals, and subagent state.
- Qualify cooperative pause at safe points, cancellation, and reconciliation.
- Use native schedulers (systemd timers, cron, Task Scheduler, launchd) for read-only DIAG broker jobs without model calls.

#### F7.8 — Compatibility, performance, and security (Crush / OpenCode)

- Improve TUI latency, RAM, and CPU use within the existing framework.
- Preserve Pair Device, TUI, web UI, sessions, plugins, MCP, and LSP.
- Maintain a functional, compatibility, and security regression matrix.

### Stabilization gate for real local sessions and selective reading

- Qualify a permitted read, rejection of an unauthorized read, and a final answer grounded in file contents using OpenCode, the gateway, and llama.cpp inside Bubblewrap's private network namespace.
- Use the HTML baseline and reuse matrix in the test evidence and architecture decisions. Require any opt-in filter to preserve technical fidelity and reduce estimated tokens before integration. [Tests](docs/PRUEBAS.md) · [Decisions](docs/DECISIONES.md)
- Use isolated fixtures until external retrieval qualifies. Web reading and remote inference have separate gates.

### D07 — Real remote product inference (blocked)

Real remote inference requires a verified budget, explicit approval of destination and content, protected credentials, verified privacy, and provider controls that prevent silent fallback. Qualify the supervised transport with a synthetic upstream first. Once credentials, quota, destination, privacy, zero cost, and the fixture are approved, exercise allowed and denied reads, tool-result replay, SSE, and cancellation. Keep Repo Map and Computer Use outside this iteration. [Fixture profile and limits](CONTINUAR.md)

### F8 — Agent Intelligence & Resource Efficiency (Proposed)

**Entry gate.** Finish the critical D07.3 recovery qualifications before starting F8. Keep D07.3 scope and priority, D24's structural extraction gate, and D07's remote inference gate. This section authorizes planning only.

Production review teardown and fresh review after restart are qualified. Native search interruption passes at the ripgrep libc I/O result boundary, and editing remains contained in a disposable workspace. Native read and paginated read pass at the successful positional read syscall boundary. The full production task restart with a separately trusted ledger and authentication state remains open. The F8 entry gate stays closed. [D07.6 evidence](docs/PRUEBAS.md#d076--production-review-stop-and-restart)

The pinned Effect SDK workspace-provider interface is the next D07.8 candidate. Qualify one workspace-backed native tool end to end through the supervisor and authenticated gateway, with the OpenCode host and trusted state outside the Bubblewrap worker. Verify dispatch coverage for enabled capabilities and deny suspended runs until task policy is loaded. [Driver decision](docs/DECISIONES.md#d078--embedded-workspace-driver-audit)

D07.9 qualifies a pre-admission gate around the pinned SDK startup sweep. The opt-in gateway profile binds a persistent budget to one session and workspace and requires a fresh bearer on each listener admission. The gate remains closed for F8 until an exclusive supervisor owner connects the real isolated workspace driver and gateway, reconciles effects before opening the barrier, and passes production restart. [SDK evidence](docs/PRUEBAS.md#d079--native-sdk-startup-admission) · [Native read evidence](docs/PRUEBAS.md#d079--native-file-read-syscall-boundary)

D07.10 connects the existing supervisor, persistent gateway and SDK to a read-only Bubblewrap worker for a fresh task. Recovery admission and effect reconciliation remain the next F8 prerequisites. [Production read evidence](docs/PRUEBAS.md#d0710--production-read-task)

D07.12 qualifies production restart for a suspended read in a dedicated native profile with complete gateway accounting. It retains reservations and denies unresolved work. Production MCP remains the next recovery prerequisite, and the F8 entry gate stays closed. [Production read recovery evidence](docs/PRUEBAS.md#d0712--external-audit-regressions-and-production-read-recovery)

D07.13 qualifies native MCP invocation identity and operation receipts in a composed synthetic fixture. Production admission still requires authorization-bound receipt verification and a regression using the real supervisor. [Native MCP evidence](docs/PRUEBAS.md#d0713--execution-environment-native-mcp-hooks-and-hosted-ci)

**Reference.** jcode master at `d31f9cd9c36ba73ea3b3de66649648c2963a1542`. The README describes swarm messaging and file-change notifications. The harness documents explicit todo prerequisites and distinguishes worker telemetry from inferred activity. Its memory benchmark provides a workload design reference. These are upstream descriptions and artifacts. CLI_OPEN has not run jcode or reproduced its measurements. [Repository](https://github.com/1jehuang/jcode) · [Pinned README](https://github.com/1jehuang/jcode/blob/d31f9cd9c36ba73ea3b3de66649648c2963a1542/README.md) · [Harness documentation](https://github.com/1jehuang/jcode/blob/d31f9cd9c36ba73ea3b3de66649648c2963a1542/docs/HARNESS.md) · [Memory benchmark](https://github.com/1jehuang/jcode/blob/d31f9cd9c36ba73ea3b3de66649648c2963a1542/scripts/bench_headless_memory.py)

**License review.** The pinned jcode and OpenCode roots both carry MIT licenses. Both require preservation of the copyright and permission notice in copies or substantial portions. Treat the source as a design reference. Any later proposal to copy a specific file must first verify its provenance, file-level and dependency licenses, attribution, and suitability for the pinned OpenCode interfaces. No jcode code or dependency is proposed for import here. [jcode license](https://github.com/1jehuang/jcode/blob/d31f9cd9c36ba73ea3b3de66649648c2963a1542/LICENSE) · [OpenCode license](https://github.com/anomalyco/opencode/blob/c0ad18b402eb2827fc1ee71c171b1177b3fc02d1/LICENSE)

Engine evidence below refers to OpenCode v2.3.2 at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`, under `packages/core/src/` unless stated otherwise. The classifications are planning decisions based on source inspection. `EXISTING` means reuse directly, `IMPROVE` means extend a known boundary, `ADD` means a missing project deliverable, `DEFER` means a later gate, and `REJECT` rules out a proposed approach.

| Area | Classification | Evidence and qualification target |
|---|---|---|
| Global CPU, RAM, processes, and tool resources | IMPROVE | CLI_OPEN's supervisor constructs Bubblewrap namespaces, the broker exposes bounded read-only CPU, memory, and process diagnostics, and the gateway limits request admission and lifetime. These are separate limits and observations. Measure the whole task process tree and qualify aggregate CPU, RAM, process count, tool subprocess lifetime, and cleanup under constrained load before proposing enforcement. |
| Adaptive parallelism and agent coordination | IMPROVE | OpenCode has native `tool/plugin/subagent.ts`, `session/subagent-job.ts`, and `session/subagent-depth.ts`. Gateway request concurrency alone cannot represent runnable agents or tool processes. Evaluate admission against native jobs and verified resource headroom. Test backpressure, cancellation, and single-worker fallback. |
| Task dependencies | DEFER | OpenCode has `tool/plugin/todo.ts`, `job.ts`, and `automation.ts`. Their presence does not establish durable prerequisite scheduling. Audit native sequencing and terminal states first. If a gap remains, qualify dependency cycles, failure and cancellation propagation, and restart behavior before proposing an extension. |
| Efficient subagent communication | IMPROVE | Reuse native completion data and parent reporting in `session/subagent-completion.ts` and `session/execution/subagent-report.ts`. Measure smaller result summaries with provenance and bounded size. Preserve permissions, project scope, and enough detail to recover work. |
| Selective memory and context F7.2 | IMPROVE | CLI_OPEN already retrieves memory and paths in `implementacion/memoria/` and validates the untrusted envelope in `implementacion/supervisor/context.py`. The opt-in preset uses native glob, grep, and paginated read. Benchmark fewer repeated reads and better evidence selection. Keep D24 and the envelope's zero authority. |
| Conflicts between agents | IMPROVE | Reuse OpenCode `worktree.ts` and CLI_OPEN's review and source-change checks in `implementacion/supervisor/workspace*.py`. Test concurrent modifications and stale reads across isolated worktrees. Report overlap for review and require an explicit resolution before publication. |
| Cache and token observation | EXISTING | OpenCode has `repository-cache.ts`, `shared-cache.ts`, and provider-reported cache token fields in `session/usage.ts` and `session/stats.ts`. Reuse available counters in the benchmark. Distinguish local cache behavior, provider cache usage, estimates, and actual billing. Record unsupported fields as unavailable. |
| Session hibernation and lifecycle | DEFER | OpenCode has suspended execution recovery in `session/execution/restart.ts` and background jobs in `session/background.ts`. Audit practical idle reclamation separately from resume. Qualify process cleanup, budget continuity, and current permission checks before considering hibernation for quiescent sessions. |
| Comparative benchmarks | ADD | CLI_OPEN has recovery, selective-context, and local token estimate fixtures. Add a repeatable comparison of unmodified OpenCode 2.3.2, current CLI_OPEN, and each candidate after the entry gate. Follow the protocol below. |
| Parallel runtime, scheduler, cache, message bus, or session store | REJECT | Extend verified OpenCode boundaries only when existing interfaces leave a measurable gap. Keep OS isolation, session authority, and remote approval in their existing components. |

**Benchmark protocol.** Pin binary, host and OS, workspace snapshot, model profile or synthetic upstream, fixtures, and starting cache state. Run repeated cold and warm trials at one worker and fixed concurrent workloads. Measure process-tree peak RAM, CPU time, process count, time to first output and completion, successful task rate, recovery and cancellation outcomes, conflict outcomes, and input/output and cache tokens when reported. Report exact bytes and token estimates separately. Report sandbox overhead and resource-control differences when the upstream configuration cannot match CLI_OPEN. Record raw results, failures, run counts, and median and tail latencies. Use local synthetic fixtures first. Set acceptance thresholds from the measured baseline, retain safety regressions, and require independent approval before any remote inference.

**F8.0 preparation.** Compare native OpenCode and CLI_OPEN on the same synthetic search, reviewed edit, bounded validation command, independent tasks, and cancellation/recovery cases. Add candidates one change at a time. Start with one worker and a fixed request budget and deadline. Detect host CPU and RAM at each run. On Linux, size the task tree with PID and start-time tracking. Report sampled peak sum of RSS separately from per-process peak RSS and describe shared-page double counting and missed short-lived processes. Use cgroup v2 counters only when an isolated, delegated task cgroup is available. Count tool dispatches from native session records and requests from the synthetic upstream and ledger. Record model-reported tokens separately from estimates. Measure supervision overhead only where the tool and provider behavior match.

| Initial workload | Existing fixture to reuse | Equivalent comparison boundary |
|---|---|---|
| Search and paginated read | `tests/fase7-contexto-selectivo.ts` | Keep the same corpus, tool policy, synthetic provider, and expected final answer. Hold the selective-context preset constant when comparing launchers. |
| One edit and validation | `tests/fase5-review.py` and `implementacion/supervisor/workspace_opencode.ts` | Use identical disposable copies and exact output bytes. Measure Git review and publication as a separate cost when the native case has no equivalent. |
| Cancellation and partial results | `tests/fase6-d07-responses.ts --read-results` | Hold the same result boundary and compare time from interruption to process exit. Treat this as result-persistence cancellation evidence. |
| Gateway and restart | `tests/fase6-d07-restart.py` | Reuse the synthetic provider and persistent session. Record reservation and descendant cleanup separately from the edit workload. |

These fixtures remain validation workloads until the F8.0 entry gate opens. Run them sequentially and keep existing provider, sandbox, and task boundaries during preparation. The test-only `tests/f8-measure.py` harness can collect bounded preliminary samples under those restrictions. Treat its output as fixture evidence until equivalent production and native workloads are qualified.

**F8.1 preparation.** The current supervisor constructs Bubblewrap namespaces and calls bounded subprocesses. The gateway limits requests and owns cancellation and task deadlines. The read-only DIAG broker reports visible host-level measurements. These mechanisms have no shared per-task CPU, RAM, or process admission budget. Evaluate one admission point at the supervised task launch after F8.0, retain task-scoped cleanup, and avoid changes to host limits or unrelated processes. **F8.2** depends on that enforcement and evidence that bounded parallel work improves task outcomes.

#### F8.3 — Adaptive Tool Selection & Lazy Activation (proposed)

The primary model should choose native tools from task intent. For an ordinary request such as “Analyze my project, find the login problem, fix it and test the result,” start with existing search and read capabilities, edit in the allowed workspace, and run approved validation. Reuse completed results and relevant context, choose the least costly sufficient tool, keep outputs bounded, and escalate only when evidence warrants it. Preserve explicit activation for experimental MCP, provider connections, sensitive actions, and user-specific commands.

| Capability | Classification | Reuse at OpenCode v2.3.2 |
|---|---|---|
| Discovery, descriptions, schema lookup, and invocation | EXISTING | Reuse the native registry in `tool.ts`, the request catalog in `session/model-request.ts`, and Code Mode's catalog and `search` in `codemode/`. |
| Agent-specific exposure, filtering, and conditional availability | EXISTING | Reuse agent definitions, session tool selection and registry transforms. Conditional availability must also be enforced at invocation. |
| Permissions and confirmation | EXISTING | Reuse `permission.ts`, tool-level assertions, and native approval. A model's choice confers zero authority. |
| Skills, plugins, and nested tasks | EXISTING | Reuse on-demand `skill` invocation, plugin lifecycle and hooks, and native subagent jobs. Run one primary agent by default. |
| MCP discovery and activation | IMPROVE | `mcp/index.ts` starts enabled servers and has native connect/disconnect and discovery. Evaluate allowlisted disabled-by-default optional servers through the existing lifecycle. Distinguish owned from shared connections. |
| Context and tool-output budgets | IMPROVE | Reuse native compaction, token/cache accounting, result truncation, and F7.2's selective preset and untrusted memory envelope. Preserve essential tools and provenance. |
| Per-component cost and lifecycle evidence | ADD | Measure visibility, schema exposure, and live process state independently before changing a default. |
| Automatic plugin unloading and optional background indexing | DEFER | Require a supported lifecycle, measured benefit, and a specific need. Preserve manual control and D24. |
| New selection engine, separate permission layer, or extra model call for routing | REJECT | Reuse primary-model selection and the native permission path. Revisit additional model inference only if a controlled comparison justifies it. |

Measure idle and active process counts, process-tree peak RAM and CPU, activation and first-result latency, schema bytes and estimated tokens, repeated calls and results, prompt cache behavior, and task success. Compare native defaults, CLI_OPEN's current profile, and individual candidates with identical synthetic fixtures. Exercise cold/warm activation, concurrent requests for an optional service, disabled or denied tools, unavailable services, deadline and cancellation, retry bounds, explicit activation, and survival of shared services. Verify that catalog filtering changes neither permissions nor essential functionality.

Prioritize schema measurement after F8.0. Optional service activation depends on F8.1 admission and memory-pressure limits, with bounded waiting, cancellation, and deadlines. Any concurrent activation or extra workers also depends on F8.2 qualification. Under pressure, keep the task on sufficient lightweight tools or wait within its deadline. Preserve ownership and reuse already-running components only when their scope and policy match.

### Packaging, distribution, and announced support (previous F8 workstream)

The historical F8 designation in D22 referred to packaging. Keep this workstream and its support scope under this heading. The new F8 proposal does not change the existing packaging commitments.

- Initial target: functional Linux x86_64 on CachyOS, Arch Linux, Ubuntu, Debian, and Fedora.
- Later targets: native Windows, macOS, and WSL2 with dedicated backend qualification.
- Reproducible installers, test containers, and validation without hidden dependencies.

### Phase 9 — Optional post-MVP features

- Self-hosted remote executors (Cursor / Warp Oz).
- Advanced operating-system restoration (Btrfs snapshots, Snapper, Timeshift, APFS, Windows System Restore), disabled by default.
- Advanced distributed infrastructure.

## Benchmarks and acceptance criteria

When relevant, compare unmodified OpenCode, current CLI_OPEN, and CLI_OPEN with the candidate improvement. Measure total tokens and tokens per successful task, cost in USD, model calls, execution time and latency, success rates, retries, CPU, and RAM. Require zero functional or security regressions.

## Delivery priorities

1. Critical work covers integrated memory, selective context and Repo Map, safe inference with budgets, adapted Code Mode, evidence-driven correction, language-aware validation, deterministic log filtering, OpenCode compatibility, and a functional Linux package.
2. High priority covers local and authorized free providers, justified deep investigation, adaptive coordination, recovery, and Pair Device supervision.
3. Require measured benefit for Recipes/Specs, hook adapters, advanced headless execution, scheduled diagnostics, and interface optimizations.
4. Defer OS-level restoration, remote executors, and distributed infrastructure.

## Dividing Codex work

Use a reviewable branch or commit for each approved phase. Parallel investigation may cover independent engine modules. Keep one writer per module. At phase close, record files, commands, results, limits, risks, and evidence for the next gate. Maintain architecture and decisions, and pause affected work when the pinned implementation contradicts a material premise. Review `git diff` before approving the checkpoint.

## Original Codex bootstrap prompt

```text
Lee PLAN_PARA_CODEX.md y INFORME_TECNICO.md de esta carpeta. Localiza el repositorio completo descargado y reporta su ruta, versión, estado Git y documentación de construcción.

En esta primera tarea haz solo la Fase 0 y prepara la calificación de la Fase 1. No edites archivos, no instales dependencias, no ejecutes acciones que cambien el sistema, no uses privilegios y no envíes datos a proveedores remotos. Usa OpenCode como base elegida; verifica versión, SHA, interfaces y fuentes oficiales. No cambies de motor sin autorización. Distingue los hechos verificados de las hipótesis del informe.

Devuélveme el inventario, la matriz de compatibilidad, los riesgos, las pruebas exactas de la Fase 1 y sus criterios para avanzar o detenerse. Espera mi aprobación antes de cambiar archivos o iniciar la implementación.
```

After approving inspection, explicitly authorize the next phase. The original wording is “Implementa solo la Fase 1 aprobada; no comiences la Fase 2”. Use the same pattern for subsequent phases.

## Starting Codex with bounded access

Start from the folder containing the plan and checkout with read-only access and approval on request.

```bash
codex --sandbox read-only --ask-for-approval on-request
```

Check `codex --version` and `codex --help` for the installed flags. After approval for a phase that needs edits, use workspace-scoped writes and retain approvals.

On Windows, start with PowerShell or Windows Terminal. Treat WSL2 as a separate Linux environment and keep the checkout in its filesystem when possible. Qualify macOS and Linux on their respective operating systems.

## Official references to verify before each phase

- Codex CLI and changelog. [CLI](https://developers.openai.com/codex/cli) · [Changelog](https://developers.openai.com/codex/changelog)
- Sandboxing and approvals. [Sandboxing](https://developers.openai.com/codex/concepts/sandboxing) · [Approvals](https://developers.openai.com/codex/agent-approvals-security)
- Windows and WSL. [Windows sandbox](https://developers.openai.com/codex/windows/windows-sandbox) · [WSL](https://developers.openai.com/codex/windows/wsl)
- Provider configuration and agent instructions. [Advanced configuration](https://developers.openai.com/codex/config-advanced) · [AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md)
- Engine source. [OpenCode upstream](https://github.com/anomalyco/opencode)

Use tests on the effective environment as phase evidence. D07 real inference remains blocked. Reuse the authenticated loopback profile to test admission and conservative reservation. Use native OpenCode OAuth for ChatGPT and qualify an official supervised transport before connecting an account to CLI_OPEN.
