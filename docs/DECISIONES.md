# Technical decisions

- **D01 · Engine and scope.** OpenCode supplies the existing CLI, TUI, sessions, and extensions. Codex develops the project. Keep the original clone in place and use a separate copy for tests. The core is outside the change scope.
- **D02 · P-1 base.** Qualify `v2.3.2` at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. Advancement depends on qualification results. [Official release](https://github.com/anomalyco/opencode/releases/tag/v2.3.2)
- **D03 · Continuity.** The containing directory has its own Git repository, excluding `upstream/` and temporary `.fase1/`. Start at `ESTADO.md`. Preserve milestone rationale, changes, and evidence in `docs/`, and request review of any evidence that conflicts with an approved decision.
- **D04 · Baseline.** Reuse CI build and lifecycle tests. Keep `dev:live` out of the private session because it connects to the existing service. Verify flags against the exact binary.
- **D05 · Public repository.** The user chose `https://github.com/njua4551-commits/CLI_OPEN.git` for `origin`. Verify references and contents before publication. Preserve remote history and use a normal push when authorized.
- **D06 · Autonomy.** Routine actions and local commits are authorized within the active phase. Publication requires authorization. [Agent instructions](../AGENTS.md)
- **D07 · P-1 inference.** Use deterministic tests against a synthetic loopback API and a separately authorized OpenRouter test with `openai/gpt-oss-20b:free`. Use a USD 0 budget, synthetic fixtures, zero fallback, and `OPENROUTER_API_KEY` from the environment. Physical inference remained pending at this checkpoint. Treat Kaggle as an explicit remote destination. [Model and pricing](https://openrouter.ai/openai/gpt-oss-20b%3Afree/pricing)
- **D08 · Integration test.** Use the compiled CLI and its OpenAI-compatible provider. The fixture simulates the provider and decoy only. OpenCode runs native tools against synthetic files with private configuration.
- **D09 · Phase 2 gate.** The user approved Phase 2 to start automatically on P-1 acceptance. That authorization ended before Phase 3.
- **D10 · Proposed substitution.** `liquid/lfm-3-1.7b:free` had an endpoint with tool support and zero input and output price. Replacing the model in D07 required approval. [Endpoint catalog](https://openrouter.ai/api/v1/models/liquid/lfm-3-1.7b:free/endpoints)
- **D11 · Approved substitution.** Pin `liquid/lfm-3-1.7b:free` after approval and a price and tool preflight. If it becomes unavailable, record an active free candidate with tools and strong task capabilities. Keep inputs synthetic and disable paid fallback.
- **D12 · P0 supervisor.** Use Python's standard library for the minimal entry point. PLAN exposes two declared local operations. The supervisor owns policy independently of user input. OpenCode remains pinned for integration.
- **D13 · DIAG broker.** Reuse MCP stdio and the pinned client's legacy negotiation. Use Linux standard-library interfaces with a bounded catalog, no path parameters, and no external commands. Prioritize Linux x86_64 and preserve contracts for later Windows and macOS backends.
- **D14 · MCP integration.** Qualify discovery with the actual CLI and a synthetic provider. Accept and discard transport metadata. Limit arguments to an empty object.
- **D15 · Initial Linux isolation.** Test mandatory Bubblewrap namespaces and explicit mounts with synthetic data before connecting the product runtime. Product writes require complete qualification.
- **D16 · DIAG policy.** Use trusted configuration and disable project configuration. The built-in `skill` tool may appear in the catalog despite denied invocation. Verify authorization at invocation too.
- **D17 · Qualification launcher.** The supervisor runs a fixed Bubblewrap fixture and fails closed if the backend is missing, rejects namespaces, or times out. Doctor reports the effective environment. F5 started on a synthetic copy separate from the original.
- **D18 · Transactional review.** Prepare explicit changes in a disposable copy. Run validation and editing under Bubblewrap, reject stale diffs, and keep originals outside the edit path. Reuse the pinned native editing tools.
- **D19 · Native editing and Git publication.** OpenCode runs `write` on the copy. The supervisor verifies bytes and scope, binds approval to the base, and publishes a commit to a separate ref transactionally. Preserve the active index and worktree.
- **D20 · Initial gateway.** Start product inference with external routes disabled. Authorize spending and destination independently of editing.
- **D21 · First P3 adapter.** The local gateway makes a non-streaming HTTP request to a fixed loopback IP and explicit model. Disable proxies, redirects, credentials, and retries. At this checkpoint the transport was separate from the CLI. Physical local inference requires evidence beyond a loopback endpoint.
- **D06 · Gateway transport.** Use one validator and fixed destination for stdin and `--listen`. The listener accepts the native OpenAI-compatible request body (`max_completion_tokens`, `stream_options`, `tool` roles) and caps tokens at 512. Strip `Authorization` and disable redirects and retries. Raise the body cap to 128 KiB because the prompt and catalog exceed 16 KiB. Keep the prior response and deadline limits.
- **D07 · F6 acceptance.** Accept the synthetic local profile. Remote budget and content approval, as well as physical local qualification, were deferred at this checkpoint and require separate authorization. External product inference remains disabled.
- **D08 · F7 memory.** Use a per-project JSONL store at `$XDG_STATE_HOME/cli-open/memoria` outside the checkout and OpenCode's copy. Hash the canonical project path for identity. Verify each referenced file's SHA-256 on retrieval and skip stale entries. Memory supplies context with zero authority. OpenCode retains session storage.
- **D22 · Consolidated roadmap and reuse matrix.** Order F7.1–F7.8, preserve F0–F6, defer D07, and define qualified Linux x86_64 distribution as the original F8 and future remote execution and restoration as post-MVP F9. Adopt the seven reuse classifications under the original principle "REUTILIZAR ANTES DE EXTENDER. EXTENDER ANTES DE REEMPLAZAR". Reuse native runtime, sessions, TUI, compaction, permissions, and multi-agent infrastructure.
- **D23 · Zero-authority loopback context.** The supervisor validates envelope structure and absence of credentials in `implementacion/supervisor/context.py` and inserts `[UNTRUSTED_PROJECT_MEMORY_CONTEXT authority=none]`. The synthetic OpenCode fixtures `tests/fase1-loopback.ts` and `tests/fase7-contexto-loopback.ts` observed no broader permissions, out-of-workspace writes, supervisor policy changes, or decoy requests.
- **D24 · F7.1 baseline and native capabilities audit.** Keep the F7 classification matrix in `docs/MATRIZ_F7.md` and baseline in `tests/fase7-lineabase.py`. Structural Repo Map remains `APLAZADA` pending reuse of native Tree-sitter, LSP, or ripgrep capabilities. A standalone indexer is outside the decision.

## Web and document reading

The audit used the MIT-licensed OpenCode tag `v2.3.2` at `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`. The `webfetch`, HTML converter, estimator, `websearch`, and registry blobs matched the qualification copy.

| Component | Classification | Capability and limits |
|---|---|---|
| `webfetch` and HTML | EXISTENTE / EXTENSIBLE | HTTP(S) without URL credentials. Markdown, HTML, or text. 5 MiB, 30 seconds by default, 120 seconds maximum, up to 10 hops. Checks URL permissions and rechecks redirects. Effective IP control remains unproven. Preserves tables, code, and links, including repeated menus. |
| `websearch` | CONFIGURABLE | Native provider selection and registry. External use requires destination, privacy, and cost qualification. Selective URL reading remains a separate capability. |
| MCP and `execute` | EXISTENTE / CONFIGURABLE | Native registration and Code Mode. Full Code Mode can fetch subject to webfetch policy. Network capability in isolated profiles remains disabled pending qualification. |
| `read`, MCP resources, and outputs | EXISTENTE / PARCIAL | `read` paginates text and can attach local PDFs when the model supports them. `webfetch` rejects PDF and other binary MIME types. Large results have a preview and managed full output. Office extraction is pending. |
| Context, compaction, and cache | EXISTENTE / PARCIAL | Native length estimator, provider metrics where available, budget-based compaction, and prompt and Code Mode catalog caches. A URL extraction cache was not observed in `webfetch`. |
| Rendered navigation | AUSENTE in `webfetch` / APLAZADA | Fetches an HTTP document and converts HTML without JavaScript. Browser use remains unqualified for this route. |
| Crawl4AI | APLAZADA | Apache-2.0. Markdown, `fit_markdown`, BM25, and deterministic pruning. Playwright increases process and memory use. First test local filtering and preserve links, signatures, code, and tables. Reserve rendering for content inaccessible via plain HTML. [Source](https://github.com/unclecode/crawl4ai) · [Filters](https://docs.crawl4ai.com/core/fit-markdown/) |
| MarkItDown | APLAZADA | MIT. Local HTML, CSV, and document conversion. Separate extras for PDF, DOCX, XLSX, and PPTX. Consider Office and text PDF with local streams, decompression, time, and memory limits, and plugins disabled. Fidelity and overhead remain unmeasured. [MarkItDown](https://github.com/microsoft/markitdown) |
| Web2MD | DESCARTADA as a dependency | Markdown, CLI/MCP, and authenticated Chrome bridge. Duplicates native HTML conversion and expands privacy exposure. Integration license and consumption are unverified. [Web2MD](https://web2md.org/) |
| Firecrawl and Tavily | APLAZADA | Review implementation license, costs, destination, and data handling before comparing external retrieval and extraction. [Firecrawl](https://docs.firecrawl.dev/) · [Tavily](https://docs.tavily.com/) |

The optional deterministic candidate runs after authorized retrieval. The Effect SDK's `tool.execute.after` hook can modify a completed result before normalization. Qualification requires preserving full output, preview, provenance, and Code Mode budget enforcement. Reuse `Token.estimate`, model context limits, and managed storage. Use verifiable rules for repeated blocks. Future query-based selection should preserve whole sections, URLs and anchors, label partial output, and allow further retrieval. A future cache would require canonical URL, options, permission scope, expiration, invalidation, and size limits.

External retrieval requires qualification of source, effective destination, DNS, redirects, private network blocking, byte, page, and time bounds, and immunity to changes in permissions or tools from retrieved instructions. Keep Bubblewrap and restricted egress. Treat results as tool data with provenance and no authority. Use synthetic cases for secrets, parsers, compressed files, and adversarial content. The HTML baseline only verifies visible text retention and script exclusion.

## D07 · Native OpenCode Console access

Console is **EXISTENTE** in OpenCode. Free access from the independent gateway is **BLOCKED** by the access policy. The supervised route requires an admitted integration and qualification of authentication, destination, and budgets. SSE cancellation is **EXTENSIBLE** through downstream disconnect detection and upstream closure within current concurrency limits. [Console API](https://opencode.ai/docs/console/api/inference/)

## Web reading · Conservative compression (EXTENSIBLE)

The opt-in adapter uses the pinned Promise SDK hook `tool.execute.after`. It modifies the two normalized fields with the same successful HTML-to-Markdown `webfetch` text and preserves metadata, the original call, and permissions. It collapses runs of at least three identical paragraphs or link lines, keeps the first, records the count, and preserves surrounding order. Individual positions within a repeated run may be lost. The filter skips results above 256 KiB UTF-8, bounding work and memory without a separate timer.

Headings and unique sections are preserved. Lexical selection and BM25 await a relevance query, because omission can remove technical requirements. Noncontiguous duplicates and unique navigation or promotional blocks remain intact. Network controls, permissions, and managed output remain native. The filter performs no I/O and the content remains a tool result. Disable the plugin to restore original output. Crawl4AI and MarkItDown remain deferred candidates for rendering, structural extraction, and Office or text PDF. Neither was installed or measured.

### D24 · Partial path discovery

In the pinned engine, ripgrep-backed glob and grep, paginated read, compaction, session events, and output limits are **EXISTENTE**. Plugins and hooks are **EXTENSIBLE**. Agent configuration and discovery are **CONFIGURABLE**. Tree-sitter highlighting is **PARCIAL**. A public symbol/reference API and LSP service were not observed, so structural mapping stays **APLAZADA**. The stash preserves a separate AST/regex extraction and storage proposal.

The partial feature reuses ripgrep and selects lexical path matches without running project files or reading bodies for the listing. Names are recomputed per query with exclusions and without symlink traversal. Existing memory invalidation applies to notes. The envelope divides available bytes between paths and notes. Shared session budgets and the dependency graph remain pending.

### D07 · Native OAuth and loopback task reservation

Native ChatGPT OAuth is **EXISTENTE** in OpenCode v2.3.2. The gateway is **EXTENSIBLE** for local admission. The opt-in profile uses a separate ephemeral credential, cumulative listener budget, and retained reservations on failure. Input bytes have no guaranteed token equivalence. A listener represents one task. The approved ChatGPT route and usage reconciliation remain deferred. Later decisions qualify persistent deadlines and local restart.

### D07 · Task lifetime and conservative reconciliation

The authenticated listener exits at its task deadline. Authentication and route and body validation precede reservation, which precedes dispatch. Earlier errors consume no task budget. After reservation, the maximum stays consumed on success, failure, truncation, disconnection, or cancellation. Disable retries. A new task requires a new token and explicit budget. The local SSE contract remains stable. Reconciliation by actual usage and remote authorization remain pending.

### D07 · Durable task ledger

Use standard-library SQLite, an exclusive file lock, one private file per task, and explicit creation. The supervisor selects the file, ID, and profile. The ledger grants zero authority and stores no prompts, authentication tokens, or headers. Keep reservations through every state transition and store provider-reported usage separately. Close the task to new operations if reported output exceeds the reservation. A restart never reconstructs or retries a previous operation. The host clock and state directory are trusted dependencies.

### D07 · Native Responses on private loopback

Use a separate Responses listener profile. The client and provider retain native items and events. The gateway supports text and stateless function calls over SSE to a fixed route. The `response.completed` event verifies identity and records reported usage. Errors, early EOF, and incomplete responses preserve the reservation and mark it uncertain. The fixture's OpenAI key is ephemeral and independent of OAuth. External routing remains disabled.

### D07.3 · Native recovery and the ChatGPT boundary

Tool records and session resumption are existing capabilities. OpenCode publishes the call before starting the tool. Recovery converts streaming or running calls to interruption errors and preserves terminal results. Policy for the new run is configurable. An interruption error cannot establish whether a write reached disk. Exactly-once execution remains unproven for arbitrary mutating tools. Retain native storage and the gateway reservation ledger.

Native OAuth exists in the pinned engine. OpenCode documents account connection and model selection. The pinned implementation uses direct HTTP for ChatGPT sign-in and a separate destination for legacy Codex sign-in. CLI_OPEN uses a separate network namespace and a loopback gateway with an ephemeral task token. Direct transport would bypass gateway reservations, deadlines, usage accounting, and destination controls. Exposing credentials to the process that shares an environment with tools would increase the exposure. Defer the optional mode until an official route preserves network isolation, permissions, credentials, and budget. Account model availability and live inference remain unverified. [OpenCode providers](https://opencode.ai/docs/providers/#chatgpt)

### D07.3 · Synthetic MCP

Native MCP discovery, dispatch, and permission checks are existing capabilities. The fixture uses OpenCode's local stdio transport and two temporary-file barriers around a single append. It exercises the existing Responses and Bubblewrap profile. An interrupted or closed MCP transport cannot identify whether the server committed an effect. Preserve the native error and inspect the target state before authorizing a new mutating call.

### D07.3 · Permission barrier and publication boundary

The native session permission API is **EXISTENTE**. The Responses fixture reuses its pending request list, session interrupt, and one-time or reject reply. The synthetic MCP service records dispatch independently of the OpenCode session. Only a new call ID can represent the explicit equivalent follow-up. Native policy still applies to it.

The supervisor's copy and separate Git review ref are **EXISTENTE**. The publication fixture reuses the final source verification callback. The exact native edit validation-to-write interval and a supervised restart spanning both the runtime and its inference budget still require qualification.

### D07.4 · Composed launcher qualification

Reopen one native session and one existing task ledger after the supervisor launcher exits. Keep the current permission policy independent of persisted operation records. Record whether an old tool result was complete, denied, or uncertain before authorizing any new action. The fixture models recovery using the existing namespace and mount builder. Product task ownership, independent protection of trusted state, and graceful user-driven resumption require their own qualification.

Native edit's permission preview is computed from source contents before the approval completes. The pinned engine applies its remaining match and no-op checks to that snapshot. The write helper's lock coordinates engine writes and reads the BOM, but does not compare the full current contents with the preview snapshot. Keep native editing against live source outside the qualified CLI_OPEN edit path. The existing disposable-copy, source-verification, and separate Git-ref boundary avoids applying edits to the live worktree. Any upstream change needs its own approval and a controlled conflict regression. A last-moment reread alone cannot guarantee an atomic comparison with arbitrary external writers.

### D07.4 · Native ChatGPT boundary

Native subscription sign-in is **EXISTENTE**. The pinned local APIs expose the native method and can prepare and cancel the browser flow in an empty profile. The current authenticated gateway is **EXTENSIBLE** for qualified synthetic Responses. Real D07 remains **BLOCKED** until an official provider integration can keep OAuth and external network access on a trusted side and preserve Bubblewrap, destination validation, deadlines, cancellation, and the durable ledger. Native workspace/environment drivers warrant an interface audit before a possible simulated integration. An endpoint override by itself does not isolate credentials or tools. [OpenCode providers](https://opencode.ai/docs/providers/#chatgpt)

### F8.3 · Adaptive Tool Selection & Lazy Activation

Reuse native catalog and invocation, Code Mode schema lookup, agent filters, skill dispatch, permissions, MCP connection lifecycle, and context compaction. Treat model visibility, schema inclusion, and process startup as independently measurable. F8.0 establishes repeatable cost and outcome metrics. F8.1 supplies bounded admission and lifecycle ownership for optional activation. Parallel activation or worker expansion waits for F8.2. Manual activation and trusted policy remain authoritative. A standalone tool chooser or sidecar model is outside the proposed implementation. [Roadmap](../PLAN_PARA_CODEX.md#f83--adaptive-tool-selection--lazy-activation-proposed)

### D07.5 · Bind reviewed edits to source version

An approval binds the source file signature as well as the existing content hash. The signature includes device, inode, file mode, size, mtime, and ctime. Final verification reuses the same bounded, no-follow snapshot. The version stays internal to preserve the public review fields. Existing approval tokens require a fresh review. Source verification precedes the Git ref transaction, which publishes to a separate review ref. Arbitrary filesystem writers do not participate in that transaction, so this is optimistic verification with no live-worktree mutation. Direct native edits on concurrently mutable source remain outside the qualified flow.

### D07.5 · Disposable edit handoff

Keep the native editor in the existing private copy and scope its edit permission to the requested files. Reuse the bounded, no-follow snapshot on staged results after the worker exits. Construct a diff only when these bytes match the proposal that Git publication will use. Final source verification and separate-ref publication remain in the trusted supervisor. Native in-place edits outside CLI_OPEN are outside this containment.

### D07.5 · Native browser handoff

Reuse the native integration API to prepare and observe the official OAuth attempt. Pass the authorization destination directly to the selected Brave executable with its usual profile. Keep OpenCode state in a temporary profile with all tool permissions denied. Verification uses only integration and model metadata. Account recognition does not qualify real inference or the supervised transport.

### D07.6 · Scope of stop and search recovery

Unwind the actual supervisor command on SIGTERM so its subprocess and disposable workspace contexts run cleanup. A stopped review emits no approval. If an apply command stops near Git publication, inspect the review ref before authorizing any retry. Uncatchable termination and production ownership of a separately trusted task ledger are distinct cases. Keep native I/O instrumentation in tests and retain the result-persistence checks for the pinned native reader.

### D07.6 · Opt-in native OAuth continuity

Use OpenCode's native XDG data storage in a new profile under a user-selected private directory. Retain it only after successful consent and metadata verification. Never mount it into the supervised tool namespace or use it as gateway authentication. A failed diagnostic discards the new profile.

### D07.7 · Ledger restart admission

Reject a symlink as the immediate task-state directory before opening its ledger. The directory remains a trusted host deployment requirement. Restart may rotate the task bearer independently of the ledger, while the task identity, budget, and deadline continue to bind the persisted rows. The supervisor-owned service boundary is still required to qualify production recovery with protected state.

### F8 · Preliminary measurement boundary

Use a test-only allowlist of synthetic fixtures for independent measurement. Identify sampled processes by PID and birth time for CPU accounting. Report sampled aggregate RSS and launcher accounting separately. Keep the governor, concurrency defaults, production permissions, and F8 entry gate unchanged.

### D07.8 · Embedded workspace driver audit

The pinned OpenCode Effect SDK is **EXTENSIBLE** through `CreateOptions.workspaceProviders`. Its embedded host registers drivers, and `Environment` routes workspace-bound file operations and child spawning through the selected driver. The normal CLI registry is empty. Local MCP also has its own local driver path, and the embedded host starts the native suspended-session recovery sweep during initialization. The native service documents at-least-once recovery, so admission through the same budget by itself cannot guarantee that uncertain effects stay unrepeated. A trusted host proof must demonstrate coverage of every enabled execution path and defer execution until the current task policy and uncertainty have been reconciled. Passing an authenticated gateway credential into the current shared OpenCode and tool namespace fails the required separation.

### D07.9 · Gate the native recovery sweep before admission

Use the Effect SDK layer replacement to decorate the pinned `SessionRestart` service. The adapter holds the whole sweep, including its background recovery work, and gates the supplied workspace driver's lifecycle with the same deferred admission. Only the trusted admission code receives the session lookup before release. Rejection and interruption close the SDK scope. Production use requires a dedicated native database, a trusted configuration with other startup dispatch paths disabled, and an exclusive task owner that validates identity, permissions, and uncertainty before release. The SDK sweep is global to its database and retains its at-least-once semantics.
