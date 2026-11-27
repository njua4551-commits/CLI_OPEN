import assert from "node:assert/strict"
import { randomUUID } from "node:crypto"
import { access, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"
import { Database } from "bun:sqlite"

const cli = resolve(process.argv[2])
const root = await mkdtemp(join(tmpdir(), "responses-"))
const work = join(root, "work")
const token = randomUUID()
const secret = randomUUID()
const forbidden = randomUUID()
const model = "fixture"
const ledger = join(root, "task.sqlite")
const sessionDatabase = join(root, "session.sqlite")
let requests = 0
let completed = false
let stalled = false
let disconnected = false
let interruption = false
let interruptedResult = false
const effect = join(work, "effect.txt")
const shellPID = join(work, "shell.pid")
const editPath = join(work, "edit.txt")
let editProbe: { call: string; expected: RegExp } | undefined
let holdToolInput = false
let recoveringToolInput = false
const mcpTool = "probe_append"
let mcpProbe: { id: string; directory: string; resumed: boolean; complete: boolean } | undefined

function events(chunks: object[]) {
  return chunks.map(chunk => "data: " + JSON.stringify(chunk) + "\n\n").join("")
}

function response(id: string, output: object[], chunks: object[], reportUsage = true) {
  const header = { id, model, output: [] }
  return new Response(events([
    { type: "response.created", response: header },
    ...chunks,
    { type: "response.completed", response: { ...header, status: "completed", output,
      ...(reportUsage ? { usage: { input_tokens: 13, output_tokens: 7, total_tokens: 20 } } : {}) } },
  ]), { headers: { "content-type": "text/event-stream" } })
}

function toolCalls(id: string, items: { id: string; arguments: string }[]) {
  return response(id, items, items.flatMap((item, output_index) => [
    { type: "response.output_item.added", output_index, item: { ...item, arguments: "" } },
    { type: "response.function_call_arguments.delta", item_id: item.id, output_index, delta: item.arguments },
    { type: "response.function_call_arguments.done", item_id: item.id, output_index, arguments: item.arguments },
    { type: "response.output_item.done", output_index, item },
  ]))
}

const upstream = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  async fetch(request) {
    assert.equal(new URL(request.url).pathname, "/v1/responses")
    assert.equal(request.headers.get("authorization"), null)
    const body = await request.json()
    requests++
    assert.equal(body.model, model)
    assert.equal(body.store, false)
    assert.equal(body.stream, true)
    const id = "resp_" + requests
    if (body.instructions === "partial") {
      return new Response(events([{ type: "response.created", response: { id, model } }]),
        { headers: { "content-type": "text/event-stream" } })
    }
    if (body.instructions === "http error") return new Response(null, { status: 503 })
    if (body.instructions === "stall") {
      stalled = true
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(events([{ type: "response.created", response: { id, model } }])))
        },
        cancel() { disconnected = true },
      }), { headers: { "content-type": "text/event-stream" } })
    }
    const results = body.input.filter((item: { type: string }) => item.type === "function_call_output")
    if (holdToolInput && body.tools?.some((tool: { name: string }) => tool.name === "shell")) {
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(events([
            { type: "response.created", response: { id, model, output: [] } },
            { type: "response.output_item.added", output_index: 0, item: {
              type: "function_call", id: "fc_before", call_id: "call_before", name: "shell", arguments: "",
            } },
          ])))
        },
      }), { headers: { "content-type": "text/event-stream" } })
    } else if (recoveringToolInput) {
      assert(!body.tools?.some((tool: { name: string }) => tool.name === "shell"))
    } else if (mcpProbe) {
      const result = results.find((item: { call_id: string }) => item.call_id === mcpProbe!.id)
      const offered = body.tools?.some((tool: { name: string }) => tool.name === mcpTool)
      if (result) {
        assert.match(JSON.stringify(result), mcpProbe.complete
          ? /Synthetic append completed/ : /interrupted|aborted|Connection closed/i)
        if (mcpProbe.resumed && !mcpProbe.complete) assert(!offered, "The denied MCP tool was advertised")
      } else if (offered && !mcpProbe.resumed) {
        return toolCalls(id, [{ type: "function_call", id: "fc_" + mcpProbe.id,
          call_id: mcpProbe.id, name: mcpTool, arguments: "{}" }])
      } else if (mcpProbe.resumed && body.tools?.some((tool: { name: string }) => tool.name === "read")) {
        assert.fail("MCP recovery request omitted the persisted tool result")
      }
    } else if (editProbe && (results.length || body.tools?.some((tool: { name: string }) => tool.name === "edit"))) {
      const callID = "call_" + editProbe.call
      if (!results.length) {
        return toolCalls(id, [{ type: "function_call", id: "fc_" + editProbe.call, call_id: callID, name: "edit",
          arguments: JSON.stringify({ path: "edit.txt", oldString: "original", newString: "replacement" }) }])
      }
      const result = results.find((item: { call_id: string }) => item.call_id === callID)
      assert.match(JSON.stringify(result), editProbe.expected)
    } else if (interruption && (results.length || body.tools?.some((tool: { name: string }) => tool.name === "shell"))) {
      if (!results.length) {
        const item = { type: "function_call", id: "fc_effect", call_id: "call_effect", name: "shell",
          arguments: JSON.stringify({ command: 'printf "%s\\n" "$$" > shell.pid; printf "%s\\n" "$OPENCODE_SESSION_ID" >> effect.txt; exec sleep 15' }) }
        return toolCalls(id, [item])
      }
      const result = results.find((item: { call_id: string }) => item.call_id === "call_effect")
      assert.match(JSON.stringify(result), /interrupted|aborted/i)
      interruptedResult = true
    } else if (results.length) {
      const allowed = results.find((item: { call_id: string }) => item.call_id === "call_allowed")
      const denied = results.find((item: { call_id: string }) => item.call_id === "call_denied")
      assert(JSON.stringify(allowed).includes(secret))
      assert.match(JSON.stringify(denied), /permission|denied|reject/i)
      assert(!JSON.stringify(body).includes(forbidden))
      completed = true
    } else if (body.tools?.some((tool: { name: string }) => tool.name === "read")) {
      assert(!JSON.stringify(body).includes(secret))
      const items = ["allowed", "denied"].map(path => ({
        type: "function_call", id: "fc_" + path, call_id: "call_" + path, name: "read",
        arguments: JSON.stringify({ path: path + ".txt", offset: 1, limit: 1 }),
      }))
      return toolCalls(id, items)
    }
    const text = results.length ? (interruption ? "Effect uncertain. Review before repeating." : secret) : "Fixture title"
    const item = { type: "message", id: "msg_" + requests, role: "assistant",
      content: [{ type: "output_text", text, annotations: [] }] }
    return response(id, [item], [
      { type: "response.output_item.added", output_index: 0, item: { ...item, content: [] } },
      { type: "response.output_text.delta", output_index: 0, content_index: 0, item_id: item.id, delta: text },
      { type: "response.output_item.done", output_index: 0, item },
    ], body.instructions !== "no usage")
  },
})

const child = Bun.spawn(["/usr/bin/python3", "-I", "-B", resolve(import.meta.dir, "../implementacion/gateway"),
  "--port", String(upstream.port), "--model", model, "--listen", "0", "--responses", "--task-budget",
  "48", "480000", "24576", "--task-state", ledger, "--task-id", "responses_fixture", "--create-task"], {
  env: { PATH: "/usr/bin:/bin", CLI_OPEN_GATEWAY_TASK_TOKEN: token }, stdout: "pipe", stderr: "inherit",
})
try {
  const reader = child.stdout.getReader()
  const { value } = await reader.read()
  const line = new TextDecoder().decode(value)
  assert.match(line, /^LISTEN \d+\n/)
  const port = Number(line.trim().split(" ")[1])
  const baseURL = `http://127.0.0.1:${port}/v1`
  const payload = { model, stream: true, input: [{ type: "message", role: "user", content: "fixture" }] }
  function post(body: object, authorization = token, path = "/responses", signal?: AbortSignal) {
    return fetch(baseURL + path, { method: "POST", headers: {
      "content-type": "application/json", Authorization: "Bearer " + authorization,
    }, body: JSON.stringify(body), signal })
  }
  assert.equal((await post(payload, "wrong")).status, 401)
  assert.equal((await post(payload, token, "/chat/completions")).status, 502)
  assert.equal((await post({ ...payload, previous_response_id: "unapproved" })).status, 502)
  assert.equal(requests, 0)
  await mkdir(work)
  await writeFile(join(work, "allowed.txt"), secret + "\n")
  await writeFile(join(work, "denied.txt"), forbidden + "\n")
  const config = {
    permissions: [{ action: "*", resource: "*", effect: "deny" },
      { action: "read", resource: "allowed.txt", effect: "allow" },
      { action: "edit", resource: "other-synthetic-file.txt", effect: "allow" }],
    providers: { fixture: {
      package: "@opencode/ai/providers/openai",
      settings: { baseURL, apiKey: token, transport: "http" },
      models: { fixture: { capabilities: { tools: true }, limit: { context: 16000, output: 128 },
        settings: { store: false } } },
    } },
  }
  function spawnSession(prompt: string, session?: string, action?: "shell" | "edit" | typeof mcpTool) {
    return Bun.spawn([cli, "--standalone", "run", "--model", "fixture/fixture", "--format", "json",
      ...(session ? ["--session", session] : []),
      prompt],
    { cwd: work, stdout: "pipe", stderr: "pipe", env: {
    PATH: "/usr/bin:/bin", HOME: root, XDG_DATA_HOME: join(root, "data"), XDG_CONFIG_HOME: join(root, "config"),
    XDG_STATE_HOME: join(root, "state"), XDG_CACHE_HOME: join(root, "cache"),
    OPENCODE_DB: sessionDatabase,
    OPENCODE_CONFIG_CONTENT: JSON.stringify({ ...config,
      permissions: action ? [
        ...config.permissions, { action, resource: action === "edit" ? "edit.txt" : "*", effect: "allow" },
      ] : config.permissions,
      ...(mcpProbe ? { mcp: { servers: { probe: { type: "local",
        command: ["/usr/bin/python3", "-I", "-B", join(import.meta.dir, "fase6-d07-mcp-server.py"), mcpProbe.directory],
        protocol: "legacy", codemode: false,
      } } } } : {}),
    }), OPENCODE_DISABLE_MODELS_FETCH: "true",
    OPENCODE_CONFIG_PROJECT_DISABLE: "true", OPENCODE_DISABLE_FILEWATCHER: "true",
    } })
  }
  async function finish(run: ReturnType<typeof spawnSession>) {
    const timer = setTimeout(() => run.kill("SIGKILL"), 30_000)
    try {
      const [code, output, errors] = await Promise.all([
        run.exited, new Response(run.stdout).text(), new Response(run.stderr).text(),
      ])
      assert.equal(code, 0, errors || output)
      return output
    } finally {
      clearTimeout(timer)
    }
  }
  async function runSession(session?: string) {
    const run = spawnSession(session ? "Repeat the policy from the completed read." : "Read the allowed synthetic file.", session)
    const timer = setTimeout(() => run.kill("SIGKILL"), 30_000)
    try {
      const [code, output, errors] = await Promise.all([
        run.exited, new Response(run.stdout).text(), new Response(run.stderr).text(),
      ])
      assert.equal(code, 0, errors || output)
      assert(completed && output.includes(secret), output + errors)
      assert(!output.includes(forbidden))
      return output.split("\n").filter(line => line.startsWith("{")).map(line => JSON.parse(line))
    } finally {
      clearTimeout(timer)
    }
  }
  const first = await runSession()
  const session = first.find(event => event.type === "tool_use")?.sessionID
  assert.equal(typeof session, "string")
  const beforeResume = requests
  const resumed = await runSession(session)
  assert(!resumed.some(event => event.type === "tool_use"))
  assert.equal(requests, beforeResume + 1)
  holdToolInput = true
  const beforeDispatch = spawnSession("Prepare a shell call.", undefined, "shell")
  const beforeOutput = Promise.all([new Response(beforeDispatch.stdout).text(), new Response(beforeDispatch.stderr).text()])
  const persistedTool = (status: string, callID = "call_before") => {
    const db = new Database(sessionDatabase, { readonly: true })
    try {
      return db.query<{ session_id: string; executed: number | null; error: string | null }, [string, string]>(
        `SELECT session_id, json_extract(part.value, '$.executed') AS executed,
                json_extract(part.value, '$.state.error.type') AS error
         FROM session_message, json_each(data, '$.content') AS part
         WHERE json_extract(part.value, '$.id')=?
           AND json_extract(part.value, '$.state.status')=?`,
      ).get(callID, status)
    } finally {
      db.close()
    }
  }
  let pendingSession: string | undefined
  try {
    for (let attempt = 0; attempt < 200 && !pendingSession && beforeDispatch.exitCode === null; attempt++) {
      pendingSession = persistedTool("streaming")?.session_id
      if (!pendingSession) await Bun.sleep(50)
    }
    if (!pendingSession) {
      const db = new Database(sessionDatabase, { readonly: true })
      try {
        assert.fail(JSON.stringify(db.query(
          `SELECT json_extract(part.value, '$.id') AS id, json_extract(part.value, '$.state.status') AS status
           FROM session_message, json_each(data, '$.content') AS part
           WHERE json_extract(part.value, '$.type')='tool' ORDER BY session_message.time_created DESC LIMIT 6`,
        ).all()))
      } finally {
        db.close()
      }
    }
    await assert.rejects(access(effect), { code: "ENOENT" })
  } finally {
    beforeDispatch.kill("SIGKILL")
    await beforeDispatch.exited
    await beforeOutput
    holdToolInput = false
  }
  recoveringToolInput = true
  const beforeRecovery = await finish(spawnSession("Report the incomplete call.", pendingSession))
  recoveringToolInput = false
  assert(!beforeRecovery.includes('"type":"tool_use"'))
  assert.deepEqual(persistedTool("error"), { session_id: pendingSession, executed: 0, error: "aborted" })
  await assert.rejects(access(effect), { code: "ENOENT" })
  interruption = true
  const active = spawnSession("Run the synthetic effect once.", undefined, "shell")
  const observed = Promise.all([new Response(active.stdout).text(), new Response(active.stderr).text()])
  let interruptedSession = ""
  let processPath = ""
  try {
    for (let attempt = 0; attempt < 200 && !interruptedSession && active.exitCode === null; attempt++) {
      interruptedSession = (await readFile(effect, "utf8").catch(error => {
        if (error.code !== "ENOENT") throw error
        return ""
      })).trim()
      if (!interruptedSession) await Bun.sleep(50)
    }
    const pid = (await readFile(shellPID, "utf8")).trim()
    assert.match(pid, /^[1-9]\d*$/)
    processPath = "/proc/" + pid
    await access(processPath)
  } finally {
    active.kill("SIGKILL")
    await active.exited
  }
  const diagnostics = (await observed).join("\n")
  assert.match(interruptedSession, /^ses_/, diagnostics)
  const processExists = () => access(processPath).then(() => true, error => {
    if (error.code === "ENOENT") return false
    throw error
  })
  for (let attempt = 0; attempt < 40 && await processExists(); attempt++) await Bun.sleep(50)
  assert.equal(await processExists(), false, "Shell process survived OpenCode termination")
  const recovery = spawnSession("Report the interrupted operation without repeating it.", interruptedSession)
  const recoveryTimer = setTimeout(() => recovery.kill("SIGKILL"), 30_000)
  try {
    const [code, output, errors] = await Promise.all([
      recovery.exited, new Response(recovery.stdout).text(), new Response(recovery.stderr).text(),
    ])
    assert.equal(code, 0, errors || output)
    assert(interruptedResult, output + errors)
    assert.match(output, /Effect uncertain/)
    assert(!output.includes('"type":"tool_use"'))
    assert.equal(await readFile(effect, "utf8"), interruptedSession + "\n")
  } finally {
    clearTimeout(recoveryTimer)
  }
  interruptedResult = false
  const beforeShellResume = requests
  const allowedRecovery = await finish(spawnSession("Report the prior operation.", interruptedSession, "shell"))
  assert(interruptedResult, allowedRecovery)
  assert(!allowedRecovery.includes('"type":"tool_use"'))
  assert.equal(requests, beforeShellResume + 1)
  assert.equal(await readFile(effect, "utf8"), interruptedSession + "\n")
  interruption = false
  for (const probe of [
    { call: "edit_denied", content: "original\n", expected: /permission|denied|reject/i },
    { call: "edit_conflict", content: "original original\n", expected: /expected exactly one/i, allow: true },
    { call: "edit_stale", content: "external revision\n", expected: /could not find oldString/i, allow: true },
    { call: "edit_completed", content: "original\r\nkeep\r\n", expected: /Edited .*1 replacement/i, allow: true,
      changed: "replacement\r\nkeep\r\n" },
  ]) {
    editProbe = probe
    await writeFile(editPath, probe.content)
    const output = await finish(spawnSession("Request the synthetic edit.", undefined, probe.allow ? "edit" : undefined))
    assert.equal(await readFile(editPath, "utf8"), probe.changed ?? probe.content)
    if (probe.changed || probe.call === "edit_denied") {
      const edit = output.split("\n").filter(line => line.startsWith("{")).map(line => JSON.parse(line))
        .find(event => typeof event.sessionID === "string")
      assert.equal(typeof edit?.sessionID, "string", output)
      await writeFile(editPath, "original\r\nexternal revision\r\n")
      const before = requests
      const resumed = await finish(spawnSession("Report the prior edit result.", edit.sessionID, "edit"))
      assert(!resumed.includes('"type":"tool_use"'))
      assert.equal(requests, before + 1)
      assert.equal(await readFile(editPath, "utf8"), "original\r\nexternal revision\r\n")
    }
  }
  editProbe = undefined
  for (const phase of ["before", "uncertain", "complete"]) {
    const directory = join(root, "mcp-" + phase)
    const id = "call_mcp_" + phase
    const complete = phase === "complete"
    await mkdir(directory)
    mcpProbe = { directory, id, complete, resumed: false }
    if (phase !== "before") await writeFile(join(directory, "allow-effect"), "")
    if (complete) await writeFile(join(directory, "allow-reply"), "")
    const run = spawnSession("Run the synthetic MCP tool.", undefined, mcpTool)
    let sessionID: string | undefined
    if (complete) {
      const output = await finish(run)
      assert(output.includes('"type":"tool_use"'), output)
      sessionID = persistedTool("completed", id)?.session_id
    } else {
      const output = Promise.all([new Response(run.stdout).text(), new Response(run.stderr).text()])
      const marker = join(directory, phase === "before" ? "calls" : "effects")
      try {
        for (let attempt = 0; attempt < 200 && run.exitCode === null; attempt++) {
          const reached = await Bun.file(marker).exists()
          sessionID = persistedTool("running", id)?.session_id
          if (reached && sessionID) break
          await Bun.sleep(50)
        }
        assert(await Bun.file(marker).exists(), "MCP server did not reach the expected barrier")
        assert.equal(persistedTool("running", id)?.session_id, sessionID, "MCP call did not remain active")
      } finally {
        run.kill("SIGKILL")
        await run.exited
        await output
      }
    }
    assert.match(sessionID ?? "", /^ses_/)
    mcpProbe.resumed = true
    const before = requests
    const output = await finish(spawnSession("Report the prior MCP result.", sessionID, complete ? mcpTool : undefined))
    assert(!output.includes('"type":"tool_use"'))
    assert.equal(requests, before + 1)
    assert.equal(await readFile(join(directory, "calls"), "utf8"), "call\n")
    if (phase === "before") await assert.rejects(access(join(directory, "effects")), { code: "ENOENT" })
    else assert.equal(await readFile(join(directory, "effects"), "utf8"), "effect\n")
    if (!complete) assert.match(persistedTool("error", id)?.error ?? "", /^(aborted|tool\.execution)$/)
  }
  mcpProbe = undefined
  assert.match(await (await post({ ...payload, instructions: "no usage" })).text(), /response.completed/)
  assert.equal((await post({ ...payload, model: "unapproved" })).status, 502)
  for (const instructions of ["partial", "http error"]) {
    const result = await post({ ...payload, instructions })
    assert.match(await result.text(), /gateway_error/)
  }
  const controller = new AbortController()
  const pending = await post({ ...payload, instructions: "stall" }, token, "/responses", controller.signal)
  for (let attempt = 0; !stalled && attempt < 20; attempt++) await Bun.sleep(50)
  assert(stalled)
  controller.abort()
  await pending.body?.cancel().catch(() => {})
  for (let attempt = 0; !disconnected && attempt < 20; attempt++) await Bun.sleep(50)
  assert(disconnected, "Responses cancellation did not reach upstream")
  const before = requests
  assert.equal((await post({ ...payload, max_output_tokens: 513 })).status, 502)
  assert.equal(requests, before)

  const db = new Database(ledger, { readonly: true })
  try {
    const count = db.query<{ count: number }, [string]>("SELECT count(*) AS count FROM operation WHERE status=?")
    for (let attempt = 0; attempt < 40 && count.get("cancelled")?.count !== 2; attempt++) await Bun.sleep(50)
    assert.equal(count.get("cancelled")?.count, 2)
    assert.equal(count.get("uncertain")?.count, 2)
    assert.equal(count.get("complete")?.count, requests - 4)
    assert.equal(db.query("SELECT count(*) AS count FROM operation WHERE prompt_tokens=13 AND completion_tokens=7").get().count,
      requests - 5)
    assert.equal(db.query("SELECT count(*) AS count FROM operation WHERE status='complete' AND prompt_tokens IS NULL AND completion_tokens IS NULL").get().count, 1)
  } finally {
    db.close()
  }
  console.log("PASS Responses: pre-dispatch abort, shell cleanup, edit recovery, permissions, SSE and SQLite usage")
} finally {
  child.kill()
  await child.exited
  await upstream.stop(true)
  await rm(root, { recursive: true, force: true })
}
