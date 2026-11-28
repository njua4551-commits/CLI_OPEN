# Continue CLI_OPEN

## Resume point

The D07.3 authorization and reviewed publication checkpoint is `018e34fd7330889108ce7067e6a1d1f8d7a37354` on `fase-1`. The earlier real-client HTTP test checkpoint was `5335b70c2bece3a3d8c0256358e1d16e19c88350` (`5335b70`), following `242c3b1`. The historical public reference was `dfcdd822b358b96f19be2d64c0ad1b61d1404f6a`. Check HEAD and the tracking ref before editing.

Stabilize the gateway, streaming, concurrency, APIs, sandbox, real editing, CI, and reproducible tests before advancing the roadmap. Qualify the real local model and require explicit budgets and authorization for remote integration. Computer Use remains deferred. [Agent instructions](AGENTS.md)

## Documentation map

- Project state (`PROJECT_STATE.md`) is recorded in [ESTADO.md](ESTADO.md).
- Roadmap and governance (`ROADMAP.md`) are recorded in [PLAN_PARA_CODEX.md](PLAN_PARA_CODEX.md).
- Architecture (`ARCHITECTURE.md`) is recorded in [D01–D24](docs/DECISIONES.md) and the [technical report](INFORME_TECNICO.md).
- Changes and test evidence (`AUDIT.md`) are recorded in the [change log](docs/CAMBIOS.md) and [test matrix](docs/PRUEBAS.md).

## Codebase summary

- The gateway in `implementacion/gateway/__main__.py` accepts exact model identifiers or explicit `alias=canonical` entries in `CLI_OPEN_GATEWAY_MODEL_ALIASES`. `_BoundedThreadingHTTPServer` uses `CLI_OPEN_GATEWAY_MAX_CONCURRENCY` (1–64, default 4) and returns 503 at saturation. SSE streams incrementally and reports midstream errors as `{"error":"local gateway rejected the request"}`. Socket timeouts use `CLI_OPEN_GATEWAY_TIMEOUT_SECONDS` (default 30 s, maximum 300 s), with `CLI_OPEN_GATEWAY_TIMEOUT` retained as an alias. The OpenAI-compatible request accepts fields including `reasoning_effort`, `response_format`, `parallel_tool_calls`, `seed`, and `stop`. The historical HTTP burst observed two active requests at a limit of two, ten requests under saturation, and a one-second timeout.
- The supervisor edits an isolated copy. `snapshot` traverses intermediate directories using `openat` and `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`. `MAX_FILE` is 256 KiB. `CODE_EXTENSIONS` covers common programming, markup, and data formats. The path validator rejects absolute paths, empty components, and traversal. The copy can create parent directories. Set `CLI_OPEN_ARTIFACTS` to select artifacts.
- Persistent memory uses JSONL outside the repository and invalidates entries using SHA-256 of referenced files. `implementacion/supervisor/context.py` uses the `[UNTRUSTED_PROJECT_MEMORY_CONTEXT authority=none]` envelope.
- F7.1 keeps its reuse matrix and baseline. The F7.2 gate observed 36 `highlights.scm` files in the pinned checkout and lacked the symbol queries, LSP service, and Tree-sitter runtime needed for structural Repo Map. D24 still requires native reuse. [Reuse matrix](docs/MATRIZ_F7.md)
- `tests/fase6-modelo-local.py` passed chat, streaming, and a tool call with CPU llama.cpp and Llama 3.2 1B Q4_K_M (~771 MiB). The full OpenCode session used the same private loopback and enforced read permissions. The final response remained empty.

## Quick regression commands

Run from the project root.

```sh
# 1. Python unit tests
python3 -B -m unittest discover -s tests

# 2. Linux sandbox qualification
python3 -I -B implementacion/supervisor qualify-linux

# 3. Isolated editing fixtures
python3 -I -B tests/fase5-review.py
python3 -I -B tests/fase5-workspace.py

# 4. HTTP gateway and real-client load fixtures
python3 -I -B tests/fase6-gateway.py
python3 -I -B tests/fase6-concurrencia.py

# 5. Memory and context fixtures
python3 -I -B tests/fase7-memoria.py
python3 -I -B tests/fase7-contexto.py

# 6. F7.1 baseline and F7.2 gate
python3 -I -B tests/fase7-lineabase.py
python3 -I -B tests/fase7-repomap.py

# 7. Git diff hygiene
git diff --check
```

## Next local model gate

Run `python3 -I -B tests/fase6-agente-local.py` with the existing artifacts. The supervisor sets the read policy and isolates OpenCode, llama.cpp, and the gateway on private loopback. Keep HTTP success, model-generated calls, actual reads, and the final response distinct. Reproduce the request after `read` through the same private gateway without OpenCode to diagnose the empty final answer. External web retrieval, real remote inference, and structural Repo Map retain their own gates. [Native audit](docs/DECISIONES.md) · [Test evidence](docs/PRUEBAS.md)

## Proposed remote API fixture

The historical candidate was OpenRouter `google/gemma-4-26b-a4b-it:free` at `google-ai-studio`. Before any run, verify zero price, availability, privacy, quota, and tool compatibility. Obtain explicit approval for the destination and synthetic instructions, read schema, filenames, and tool results. Supply the credential only to the trusted remote component outside Bubblewrap. Keep it out of the repository and chat.

Configure `@opencode/ai/providers/openai-compatible` with alias `fixture`, tools enabled, a private loopback `baseURL` ending in `/v1`, and a dummy local key. The trusted component owns the HTTPS destination and real key. The current gateway forwards to loopback only. `tests/fase1-openrouter.py` shows HTTPS, price verification, and fixed provider selection for Liquid. Bubblewrap channel qualification remains separate.

The proposed fixture uses concurrency one, at most six inference requests, 4096 input and 384 output tokens per request, and a 120-second task deadline with zero retries and fallbacks. Reserve budgets before dispatch. Reject unbudgeted auxiliary calls, unconfirmed quota or price, or any configuration that allows an alternate route. Cancel an upstream request when its client cancels. Verify reported usage and cost or record them as unconfirmed. Verify the input bound for the model before sending.

A and B use a temporary fixture and the physical session's read policy. C repeats synthetic history with roles and matching IDs in `assistant.tool_calls` and `tool.tool_call_id`. Use SSE in A and B for D and reserve the remaining request for controlled stream cancellation. Test transport errors locally. Qualify the fixed-destination channel with a synthetic upstream and verify cancellation, direct-route blocking, redirects, and credentials staying outside the sandbox.

### Historical D07 revalidation

The OpenRouter credential was absent from the effective environment, inspected OpenCode metadata, and inspected startup files. Authenticated quota remains unverified. Supply it to the trusted process through an approved secret mechanism. Limit the authenticated quota check to `GET /api/v1/key` and filter its output.

The initial `python3 -I -B tests/fase6-d07-cancel.py` run left the stalled upstream socket open outside the one-second cancellation window until the five-second timeout. The corrected implementation passes within one second against a synthetic upstream. The authenticated local task profile now has a persistent reservation ledger. These results apply to private loopback.

## OpenCode Console and D07

`opencode/deepseek-v4.1-flash-free` was a candidate for an authorized native session. The catalog advertised tools and zero cost. Console's free chat route is restricted to native OpenCode. Direct provider access bypasses the CLI_OPEN gateway and its budgets. Keep A–D remote blocked until an admitted route preserves authentication, cumulative limits, fixed destination, and Bubblewrap.

## Optional HTML filter

With the pinned OpenCode V2, add the absolute `implementacion/lectura-web` directory to `plugins` in trusted configuration. The existing example is `{"plugins":["/ruta/a/CLI_OPEN/implementacion/lectura-web"]}`. Remove the entry to restore the original Markdown output, or request `html` subject to native permissions and limits. The filtered output preserves headings and unique sections. Keep external retrieval disabled pending qualification.

With F1 artifacts, run `bun tests/lectura-web-lineabase.ts .fase1/opencode baseline` and repeat with `filtered`. The integration fixture takes the OpenCode binary path and runs under Bubblewrap with `--unshare-net`, a temporary HOME, and read-only binary, test, and plugin mounts. Its servers bind to private loopback.

## Reproducible profiles

- `python3 -I -B tests/run-suite.py portable` requires Python 3.11+ and Node.js 18+ and covers unit tests, memory, context, and the HTML filter core.
- `python3 -I -B tests/run-suite.py linux` requires Linux x86_64, unprivileged Bubblewrap, and loopback sockets. It covers isolation, workspace copies, the gateway, HTTP concurrency, cancellation, budgets, and persistence.
- `python3 -I -B tests/run-suite.py opencode` verifies version and SHA-256 for prebuilt artifacts in `.fase1`. It covers reviewed editing, supervisor qualification, gateway integration, Responses recovery, context, and webfetch under Bubblewrap. Requalify any build with different bytes.
- Verify the tag `v2.3.2` resolves to `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1` and export that SHA to a fresh directory with `git archive` before a build. Use Bun 1.4.4. The deterministic profiles never download artifacts. The HTML benchmark needs a prepared checkout, and the physical model fixture needs a GGUF and llama.cpp. OpenRouter is outside these profiles. [Bun release](https://github.com/oven-sh/bun/releases/tag/bun-v1.4.4) · [Build evidence](docs/PRUEBAS.md)

`inject-context --max-context-bytes` accepts 128–16384 bytes for compact memory JSON, including its newline. The supervisor retains entries by relevance, omits duplicates, and skips entries that do not fit. The fixed instructions and query are outside that envelope's budget. The input envelope is limited to 64 KiB before processing.

## Resume an OpenCode session

Use `opencode --standalone run --session ID "siguiente paso"` in the same workspace with the persisted session ID from the previous run's JSON events. The qualification recovered a completed tool result in a fresh process without replaying the tool. Inspect the real state of an interrupted operation before repeating it.

`tool.execute.after` for `webfetch` supplies no explicit relevance query. F7.3 keeps duplicate compression. Section selection requires an authorized query and a shared budget when two sources are ready for integration.

## CI on Ubuntu 24.04

For a Bubblewrap startup failure with `Failed RTM_NEWADDR`, inspect `kernel.apparmor_restrict_unprivileged_userns`, the Bubblewrap version, and the packaged `bwrap-userns-restrict` profile. The workflow loads Ubuntu's official profile when the restriction is active and runs tests as a standard user.

The run after `810af0c` passed AppArmor setup and failed on Python startup. F4 now uses the supervisor's mount builder to preserve host library paths. Inspect the Linux job's `sandbox runtime` paths and both job outcomes after authorized publication. [Reference run](https://github.com/njua4551-commits/CLI_OPEN/actions/runs/45864416809)

## F7.2 path discovery and selective reading

Run `python3 -I -B implementacion/memoria context --project RUTA --query "auth" --with-paths --max-bytes 4096` with ripgrep available. Pass its envelope to `inject-context`. Path hints use at most half of the envelope budget. Adjust the query, then use permission-controlled native `grep` and paginated `read` for relevant lines. Discovery uses on-demand enumeration, respects ripgrep exclusions, avoids symlinks, and rejects results larger than 1 MiB or taking more than five seconds. Sensitive names, hidden paths, and invalid characters are excluded. Memory keeps hash-based invalidation.

Copy only `agents.contexto-selectivo` from `implementacion/contexto/opencode.json` into trusted OpenCode configuration. Run `opencode --standalone run --agent contexto-selectivo` with the injected prompt, an authorized provider, and the existing sandbox. The preset preserves effective permissions. Configure explicit reads where needed. Its 4096-byte target guides selection across memory and tool output. The supervisor enforces the envelope budget independently. Verify the chain with `python3 -I -B tests/run-suite.py opencode`.

## ChatGPT OAuth and D07 local task profiles

Pinned OpenCode and the historically installed CLI 2.4.2 include `Sign in with ChatGPT`. The official flow uses `/connect` and then `/models`. Account access, the available model catalog, and live inference remain unverified through CLI_OPEN. The native login, refresh, and inference flow requires a supervised official transport.

The authenticated loopback listener accepts `--task-budget REQUESTS INPUT_BYTES OUTPUT_TOKENS`. Supply `CLI_OPEN_GATEWAY_TASK_TOKEN` as 32–128 ASCII letters, digits, hyphens, or underscores. The token is ephemeral, task-scoped, and independent of OAuth. The gateway consumes it locally and forwards no authentication header. Use a private listener per task. Reserve the full amount at dispatch, including for failed and cancelled attempts. Input is measured in HTTP bytes, and output is the sum of requested maxima. Set the process deadline with `--task-seconds` (1–300, default 120); expiration exits with status 124 and closes the sockets.

### Persistent reservations

Add `--task-state RUTA --task-id ID` and create the task once with `--create-task`. On recovery, omit that flag and retain the path, ID, upstream port, model, limits, and deadline. Keep the private state directory owned by the supervisor outside agent mounts. The SQLite file uses mode 0600. Missing, invalid, busy, and closed task states prevent startup. Restart preserves the original deadline and reservations, marks open operations uncertain, and dispatches only new requests. Provider-reported usage has its own fields. Durability depends on trusted host time and state. OpenCode owns session and account state.

### Simulated Responses

Run `python3 -I -B tests/run-suite.py opencode`. The fixture uses `@opencode/ai/providers/openai`, HTTP, `--responses`, ephemeral bearer authentication, and the SQLite ledger. The target is fixed to IPv4 loopback at `/v1/responses`. Use a separate task database for each protocol. The ledger binds protocol, model, and port and preserves the deadline and conservative reservations.

The subset accepts text and function calls via SSE with `store=false`. Clients resend history with call and result IDs. Provider-side continuation, hosted tools, binary inputs, WebSocket, and remote compaction are outside the profile. Keep OAuth tokens out of the listener. Real D07 remains blocked pending an admitted official route.

## D07.2 interrupted effect recovery

The Responses fixture kills OpenCode after a file effect and before the tool result, then reopens the session ID with `shell` denied. The provider receives the interrupted result and the effect remains recorded once. Inspect actual state and obtain current authorization before repeating an uncertain effect.

## D07.3 · Continuity

The Responses fixture now holds a native MCP permission request with complete arguments before dispatch, then tests interruption, a one-time grant, and rejection. An uncertain prior effect is kept distinct from a new equivalent call, which is governed by the current native policy. The workspace test changes a source before final Git publication verification and checks that the external contents and mode survive.

Continue with interruption during native filesystem and ripgrep work. The D07.4 probe targets the later result persistence boundary. The native edit validation-to-write interval and a supervisor restart that restores both session and budget still need coverage. The F8 entry gate depends on critical D07.3 qualification. Real remote D07 remains blocked. [Test evidence](docs/PRUEBAS.md#d073--permission-dispatch-and-equivalent-calls-after-an-uncertain-effect)

## D07.4 · Reproduce launcher recovery

Run `python3 -I -B tests/fase6-d07-restart.py` on qualified Linux with the pinned artifacts. The OpenCode suite also runs this fixture. It crashes the synthetic launcher before an active MCP reply and while a separate gateway reservation is open. The second namespace reopens the session and ledger. Continue with the exact native edit write boundary and production task-state ownership qualification before F8. [Lifecycle evidence](docs/PRUEBAS.md#d074--launcher-restart-with-native-session-and-task-budget)

## D07.4 · Resume the native ChatGPT diagnostic

The OpenCode profile tests the native pre-browser step with a clean temporary profile and all tool permissions denied. Account verification requires the user's participation in OpenCode's official browser flow. Keep the native diagnostic separate from supervised CLI_OPEN and obtain explicit authorization before real synthetic inference. Keep OAuth credentials outside the CLI_OPEN gateway and tool environment. [Diagnostic evidence](docs/PRUEBAS.md#d074--native-chatgpt-pre-browser-diagnostics)

## D07.5 · Version-bound review

Generate a fresh review before applying a change if the source bytes, identity, or metadata changed. Old approval tokens predate the version binding and must be regenerated. The review path keeps native editing in a disposable workspace and publishes a separate Git ref. The next gate is a supported correction and regression for the native `edit` preview-to-write interval. [Evidence](docs/PRUEBAS.md#d075--version-bound-workspace-approval)

### User-controlled native browser handoff

From the project root in a Bash terminal, create a private diagnostic profile and run native OpenCode's interactive login. The following function uses the pinned binary, a temporary empty workspace, no inherited API credentials, and a deny-all tool policy. The diagnostic requires native network access for OAuth, independently of the supervised CLI_OPEN sandbox.

```bash
diagnostic_cli="$PWD/.fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode"
diagnostic_dir=$(mktemp -d /tmp/cli-open-native-auth.XXXXXXXX)
native_diagnostic() (
  cd "$diagnostic_dir" || exit 1
  env -i PATH=/usr/bin:/bin HOME="$diagnostic_dir" \
    XDG_CONFIG_HOME="$diagnostic_dir/config" XDG_DATA_HOME="$diagnostic_dir/data" \
    XDG_STATE_HOME="$diagnostic_dir/state" XDG_CACHE_HOME="$diagnostic_dir/cache" \
    OPENCODE_CONFIG_PROJECT_DISABLE=true OPENCODE_DISABLE_MODELS_FETCH=true \
    OPENCODE_CONFIG_CONTENT='{"permissions":[{"action":"*","resource":"*","effect":"deny"}]}' \
    "$diagnostic_cli" --standalone "$@"
)
native_diagnostic auth login openai --method chatgpt-token-sharing
```

Complete consent personally. If the clean terminal cannot open a browser, use the URL printed by OpenCode in your browser. Keep that URL and any credential material private. After OpenCode reports completion, `native_diagnostic models | grep '^openai/'` checks the provider's exposed model list without running an inference prompt. Share only the success or failure status and non-sensitive model names if needed. Keep the temporary profile private and separate from CLI_OPEN. [Official ChatGPT setup](https://opencode.ai/docs/providers/#chatgpt)

### Disposable edit containment

Use `review-workspace` and `apply-workspace` for supervised changes. The native editor receives a private copy and permissions limited to the proposal paths. The host checks exact staged bytes before it issues an approval. Production restart with a separate trusted ledger and native in-flight I/O remain the F8 entry dependencies.

### Brave handoff from Fish

The opt-in native diagnostic opens the authorization page in the installed Brave browser using its usual profile and keeps OpenCode in a fresh private profile. Run it from the project root. Fish can execute the binary directly without Bash functions or any change to shell configuration.

```fish
set -l browser (command -s brave)
if test -z "$browser"
    set browser (command -s brave-browser)
end
if test -n "$browser"
    .fase1/tools/bun-linux-x64-baseline/bun tests/fase6-d07-chatgpt-auth.ts \
        "$PWD/.fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode" "$browser"
end
```

Personally complete the authorization in Brave. The diagnostic checks the native integration and model registry and prints only a completion flag and model IDs. The temporary OpenCode profile is removed when the process exits. The automated OpenCode suite omits the browser argument and stops before consent. Remote D07 remains blocked independently.

### Retain a separate native profile after a new consent

An explicit `--retain` parent keeps a newly created private OpenCode profile after successful consent and native metadata verification. Supply a private directory you own outside the repository. The diagnostic creates a unique child and never selects an existing OpenCode profile. It removes the child if the diagnostic fails. Reusing Brave only opens the official consent page.

```fish
set -l native_parent "$HOME/.local/state/cli-open-native"
mkdir -p -m 700 "$native_parent"
set -l browser (command -s brave)
if test -z "$browser"
    set browser (command -s brave-browser)
end
if test -n "$browser"
    .fase1/tools/bun-linux-x64-baseline/bun tests/fase6-d07-chatgpt-auth.ts \
        "$PWD/.fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode" \
        "$browser" --retain "$native_parent"
end
```

To check a successfully retained profile in a fresh native process, use the exact `nativeProfile` directory printed by the diagnostic. Assign `profile` to that directory and run only the native model listing from the project root.

```fish
env -i PATH=/usr/bin:/bin HOME="$profile" XDG_CONFIG_HOME="$profile/config" \
    XDG_DATA_HOME="$profile/data" XDG_STATE_HOME="$profile/state" XDG_CACHE_HOME="$profile/cache" \
    OPENCODE_CONFIG_PROJECT_DISABLE=true OPENCODE_DISABLE_MODELS_FETCH=true \
    'OPENCODE_CONFIG_CONTENT={"permissions":[{"action":"*","resource":"*","effect":"deny"}]}' \
    .fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode --standalone models | grep '^openai/'
```

This profile belongs to the native diagnostic. Keep it separate from the supervised workspace and gateway. A retained login needs fresh consent because the previous temporary profile was removed. A model list is metadata and does not qualify inference.

### D07.6 recovery commands

Run `python3 -I -B tests/fase5-supervisor-stop.py` for production review teardown and restart, and `python3 -I -B tests/fase6-d07-native-io.py` for the two native search I/O cases. The native search fixture requires a Linux C compiler and builds only a temporary interposer. Keep the F8 gate closed until the production task owner protects the ledger outside the sandbox and the read I/O cases are qualified.

### Bounded F8 measurement preparation

Run `python3 -I -B tests/f8-measure.py context` for the independent memory envelope measurement. Use `search`, `review --runs 1`, or `recovery --runs 1` for pinned Linux fixtures with Bubblewrap available. The JSON separates sampled tree CPU and RSS from launcher accounting. The F8 production gate still requires isolated task ownership and native read I/O. Keep these runs sequential. [Measurement evidence](docs/PRUEBAS.md#f8--bounded-preliminary-measurements)

### D07.8 continuation

Start with the Effect SDK workspace-provider path. Exercise one deterministic native read through a workspace driver with a real isolated worker and the existing authenticated gateway. Check the selected session and task identity, deadline and reservation binding, enabled MCP launch paths, and the embedded startup recovery sweep before adding a production entry point. Use the result-persistence test for native read recovery until there is an observable I/O boundary on the pinned artifact. [Driver evidence](docs/PRUEBAS.md#d078--workspace-driver-and-containment-evidence)

### D07.9 continuation

Run `python3 -I -B tests/d079-sdk-admission.py` for the native startup barrier on the pinned source and Bun artifacts. Wire the trusted admission callback to one supervisor-owned task and the existing ledger and authenticated gateway. Qualify one isolated native read with a restricted driver, then crash at an observable MCP effect. Reopen only after proving ownership and reconciliation against a dedicated native database. An unclassified effect must keep the sweep blocked. [Evidence](docs/PRUEBAS.md#d079--native-sdk-startup-admission)

Run `python3 -I -B tests/fase6-d07-native-io.py --read` for the Linux x86_64 native file-read interruption cases. The default invocation still runs the search cases. Production task ownership and recovery are the remaining F8 entry dependencies. [Read evidence](docs/PRUEBAS.md#d079--native-file-read-syscall-boundary)

Create an opt-in owned listener with `--task-owner SESSION WORKSPACE` alongside the existing persistent gateway flags. Reopen it with the same owner IDs, settings and identity and a new bearer supplied by the trusted supervisor. The focused regression is `python3 -I -B tests/fase6-d07-persist.py`. Connect listener ownership to the SDK's admission callback and keep MCP dispatch closed until the separate worker path and reconciliation are covered. [Gateway evidence](docs/PRUEBAS.md#d079--bound-gateway-admission)

### D07.10 · Production fresh read

Qualify the command with `python3 -I -B tests/d0710-task.py`. The command is `python3 -I -B implementacion/supervisor run-read-task SOURCE --state NEW_PRIVATE_DIRECTORY --identity TASK --port LOCAL_PORT --model MODEL`. The operator authorizes the explicit local destination and source. The prepared SDK stays on the trusted side. Continue with immutable recovery bindings, a restricted MCP launch path, and reconciliation before opening the native restart barrier. [Evidence](docs/PRUEBAS.md#d0710--production-read-task)

For bounded preliminary measurement, run `python3 -I -B tests/f8-measure.py production-read --runs 2`. The fixture includes successful completion and cancellation. The matched native comparison remains behind the production recovery gate.
