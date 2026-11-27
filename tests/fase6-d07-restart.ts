import assert from "node:assert/strict"
import { randomUUID } from "node:crypto"
import { mkdir, readFile, writeFile } from "node:fs/promises"
import { join } from "node:path"
import { Database } from "bun:sqlite"
import { events, response, toolCalls } from "./responses-fixture"

const [cli, stage] = process.argv.slice(2)
assert(stage === "start" || stage === "resume")
const starting = stage === "start"
const root = "/work"
const cwd = join(root, "project")
const mcp = join(root, "mcp")
const privateState = join(root, "budget")
const ledger = join(privateState, "task.sqlite")
const sessionDB = join(root, "session.sqlite")
const token = randomUUID()
const model = "fixture"
const readID = "call_restart_read"
const activeID = "call_restart_active"
const deniedID = "call_restart_denied"
const approvedID = "call_restart_approved"
const marker = "restart-fixture-readable"
const forbidden = "restart-fixture-private"
const limit = 12
let phase = starting ? "read" : "recover"
let requestCount = 0

function inspect<T>(path: string, query: string): T[] {
  const db = new Database(path, { readonly: true })
  try { return db.query(query).all() as T[] } finally { db.close() }
}

const upstream = Bun.serve({
  hostname: "127.0.0.1",
  port: starting ? 0 : Number(await readFile(join(root, "upstream-port"), "utf8")),
  async fetch(request) {
    assert.equal(new URL(request.url).pathname, "/v1/responses")
    assert.equal(request.headers.get("authorization"), null)
    const body = await request.json()
    assert(!JSON.stringify(body).includes(forbidden))
    const id = "resp_" + stage + "_" + ++requestCount
    if (body.instructions === "hold") {
      return new Response(new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode(events([{ type: "response.created", response: { id, model } }])))
        },
      }), { headers: { "content-type": "text/event-stream" } })
    }
    const results = body.input.filter((item: { type: string }) => item.type === "function_call_output")
    const result = (callID: string) => results.find((item: { call_id: string }) => item.call_id === callID)
    const offered = (name: string) => body.tools?.some((tool: { name: string }) => tool.name === name)
    function call(name: string, callID: string, args: object) {
      return toolCalls(model, id, [{ type: "function_call", id: "fc_" + callID,
        call_id: callID, name, arguments: JSON.stringify(args) }])
    }
    if (phase === "read" && offered("read") && !result(readID)) {
      return call("read", readID, { path: "allowed.txt" })
    }
    if (phase === "effect" && offered("probe_append")) {
      assert(JSON.stringify(result(readID)).includes(marker))
      return call("probe_append", activeID, { label: "synthetic" })
    }
    if (phase === "recover" && offered("read")) {
      assert(JSON.stringify(result(readID)).includes(marker))
      assert.match(JSON.stringify(result(activeID)), /aborted|interrupted/i)
      assert(!offered("probe_append"))
      if (!result(deniedID)) return call("probe_append", deniedID, { label: "different" })
      assert.match(JSON.stringify(result(deniedID)), /permission|denied|not found|not available/i)
    }
    if (phase === "authorize" && offered("read")) {
      assert.match(JSON.stringify(result(activeID)), /aborted|interrupted/i)
      assert.match(JSON.stringify(result(deniedID)), /permission|denied|not found|not available/i)
      assert(offered("probe_append"))
      if (!result(approvedID)) return call("probe_append", approvedID, { label: "different" })
      assert.match(JSON.stringify(result(approvedID)), /Synthetic append completed/)
    }
    const item = { type: "message", id: "msg_" + id, role: "assistant",
      content: [{ type: "output_text", text: !offered("read") && !results.length ? "Fixture title"
        : phase === "recover" ? "Recovered without replay."
          : phase === "authorize" ? "Explicit operation completed." : marker, annotations: [] }] }
    return response(model, id, [item], [
      { type: "response.output_item.added", output_index: 0, item: { ...item, content: [] } },
      { type: "response.output_text.delta", output_index: 0, content_index: 0, item_id: item.id,
        delta: item.content[0].text },
      { type: "response.output_item.done", output_index: 0, item },
    ])
  },
})

if (starting) {
  await mkdir(cwd)
  await mkdir(mcp)
  await mkdir(privateState, { mode: 0o700 })
  await writeFile(join(root, "upstream-port"), String(upstream.port))
  await writeFile(join(cwd, "allowed.txt"), marker)
  await writeFile(join(cwd, "denied.txt"), forbidden)
  await writeFile(join(mcp, "allow-effect"), "")
}
const gateway = Bun.spawn(["/usr/bin/python3", "-I", "-B", "/implementacion/gateway",
  "--port", String(upstream.port), "--model", model, "--listen", "0", "--responses", "--task-budget",
  String(limit), "240000", "6144", "--task-state", ledger, "--task-id", "restart_fixture",
  ...(starting ? ["--create-task"] : [])], {
  env: { PATH: "/usr/bin:/bin", CLI_OPEN_GATEWAY_TASK_TOKEN: token }, stdout: "pipe", stderr: "inherit",
})
try {
  const reader = gateway.stdout.getReader()
  const { value } = await reader.read()
  const line = new TextDecoder().decode(value)
  assert.match(line, /^LISTEN \d+\n$/)
  const baseURL = "http://127.0.0.1:" + line.trim().split(" ")[1] + "/v1"
  function post(instructions: string, bearer = token) {
    return fetch(baseURL + "/responses", {
      method: "POST", headers: { "content-type": "application/json", Authorization: "Bearer " + bearer },
      body: JSON.stringify({ model, stream: true, instructions, input: [{ type: "message", role: "user",
        content: "Synthetic budget probe" }] }), signal: AbortSignal.timeout(25_000),
    })
  }
  function run(session?: string, allowMcp = false) {
    const permissions = [{ action: "*", resource: "*", effect: "deny" },
      { action: "read", resource: "allowed.txt", effect: "allow" },
      ...(allowMcp ? [{ action: "probe_append", resource: "*", effect: "allow" }] : [])]
    return Bun.spawn([cli, "--standalone", "run", "--model", "fixture/fixture", "--format", "json",
      ...(session ? ["--session", session] : []), "Run the synthetic restart step."], {
      cwd, stdout: "pipe", stderr: "inherit", env: {
        PATH: "/usr/bin:/bin", HOME: root, XDG_DATA_HOME: join(root, "data"), XDG_STATE_HOME: join(root, "state"),
        XDG_CACHE_HOME: join(root, "cache"), XDG_CONFIG_HOME: join(root, "config"), OPENCODE_DB: sessionDB,
        OPENCODE_DISABLE_MODELS_FETCH: "true", OPENCODE_CONFIG_PROJECT_DISABLE: "true",
        OPENCODE_DISABLE_FILEWATCHER: "true",
        OPENCODE_CONFIG_CONTENT: JSON.stringify({ permissions,
          providers: { fixture: { package: "@opencode/ai/providers/openai",
            settings: { baseURL, apiKey: token, transport: "http" },
            models: { fixture: { capabilities: { tools: true }, limit: { context: 16000, output: 128 },
              settings: { store: false } } } } },
          mcp: { servers: { probe: { type: "local", protocol: "legacy", codemode: false,
            command: ["/usr/bin/python3", "-I", "-B", "/tests/fase6-d07-mcp-server.py", mcp,
              starting ? "synthetic" : "different"] } } },
        }),
      },
    })
  }
  async function finish(child: ReturnType<typeof run>) {
    const [status, output] = await Promise.all([child.exited, new Response(child.stdout).text()])
    assert.equal(status, 0, output)
    return output
  }
  const operations = () => inspect<{ status: string }>(ledger, "SELECT * FROM operation ORDER BY id")
  const toolState = (id: string) => inspect<{ session_id: string; status: string }>(sessionDB, `
    SELECT session_id, json_extract(part.value, '$.state.status') AS status
    FROM session_message, json_each(data, '$.content') AS part
    WHERE json_extract(part.value, '$.id') = '${id}'`)[0]
  if (starting) {
    const output = await finish(run())
    assert(output.includes(marker))
    const read = toolState(readID)
    assert.equal(read.status, "completed")
    phase = "effect"
    const active = run(read.session_id, true)
    for (let attempt = 0; attempt < 160 && active.exitCode === null; attempt++) {
      if (await Bun.file(join(mcp, "effects")).exists() && toolState(activeID)?.status === "running") break
      await Bun.sleep(50)
    }
    assert.equal(await readFile(join(mcp, "effects"), "utf8"), "effect\n")
    assert.deepEqual(toolState(activeID), { session_id: read.session_id, status: "running" })
    const held = await post("hold")
    assert.equal(held.status, 200)
    assert.equal(operations().at(-1)?.status, "reserved")
    await writeFile(join(root, "session-id"), read.session_id)
    await writeFile(join(root, "ready"), "")
    await active.exited
    assert.fail("The supervisor was not interrupted while the operation was active")
  } else {
    assert.equal(operations().at(-1)?.status, "uncertain")
    assert.equal((await post("unauthorized", randomUUID())).status, 401)
    assert.equal(requestCount, 0)
    const session = await readFile(join(root, "session-id"), "utf8")
    const output = await finish(run(session))
    assert.match(output, /Recovered without replay/)
    assert(!output.includes(forbidden))
    assert.deepEqual(toolState(readID), { session_id: session, status: "completed" })
    assert.deepEqual(toolState(activeID), { session_id: session, status: "error" })
    assert.deepEqual(toolState(deniedID), { session_id: session, status: "error" })
    assert.equal(await readFile(join(mcp, "calls"), "utf8"), "call\n")
    assert.equal(await readFile(join(mcp, "effects"), "utf8"), "effect\n")
    phase = "authorize"
    await writeFile(join(mcp, "allow-reply"), "")
    assert.match(await finish(run(session, true)), /Explicit operation completed/)
    assert.deepEqual(toolState(activeID), { session_id: session, status: "error" })
    assert.deepEqual(toolState(deniedID), { session_id: session, status: "error" })
    assert.deepEqual(toolState(approvedID), { session_id: session, status: "completed" })
    assert.equal(await readFile(join(mcp, "calls"), "utf8"), "call\ncall\n")
    assert.equal(await readFile(join(mcp, "effects"), "utf8"), "effect\neffect\n")
    phase = "budget"
    for (let slots = operations().length; slots < limit; slots++) {
      const probe = await post("budget probe")
      assert.equal(probe.status, 200)
      assert.match(await probe.text(), /response.completed/)
    }
    const before = requestCount
    assert.equal(operations().length, limit)
    assert.equal((await post("exhausted")).status, 429)
    assert.equal(requestCount, before)
  }
} finally {
  gateway.kill()
  await gateway.exited
  await upstream.stop(true)
}
