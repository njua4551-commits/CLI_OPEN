import assert from "node:assert/strict"
import { randomUUID } from "node:crypto"
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises"
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
let requests = 0
let completed = false
let stalled = false
let disconnected = false

function events(chunks: object[]) {
  return chunks.map(chunk => "data: " + JSON.stringify(chunk) + "\n\n").join("")
}

function response(id: string, output: object[], chunks: object[]) {
  const header = { id, model, output: [] }
  return new Response(events([
    { type: "response.created", response: header },
    ...chunks,
    { type: "response.completed", response: { ...header, status: "completed", output,
      usage: { input_tokens: 13, output_tokens: 7, total_tokens: 20 } } },
  ]), { headers: { "content-type": "text/event-stream" } })
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
    if (results.length) {
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
      return response(id, items, items.flatMap((item, output_index) => [
        { type: "response.output_item.added", output_index, item: { ...item, arguments: "" } },
        { type: "response.function_call_arguments.delta", item_id: item.id, output_index, delta: item.arguments },
        { type: "response.function_call_arguments.done", item_id: item.id, output_index, arguments: item.arguments },
        { type: "response.output_item.done", output_index, item },
      ]))
    }
    const text = results.length ? secret : "Fixture title"
    const item = { type: "message", id: "msg_" + requests, role: "assistant",
      content: [{ type: "output_text", text, annotations: [] }] }
    return response(id, [item], [
      { type: "response.output_item.added", output_index: 0, item: { ...item, content: [] } },
      { type: "response.output_text.delta", output_index: 0, content_index: 0, item_id: item.id, delta: text },
      { type: "response.output_item.done", output_index: 0, item },
    ])
  },
})

const child = Bun.spawn(["/usr/bin/python3", "-I", "-B", resolve(import.meta.dir, "../implementacion/gateway"),
  "--port", String(upstream.port), "--model", model, "--listen", "0", "--responses", "--task-budget",
  "12", "120000", "6144", "--task-state", ledger, "--task-id", "responses_fixture", "--create-task"], {
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
      { action: "read", resource: "allowed.txt", effect: "allow" }],
    providers: { fixture: {
      package: "@opencode/ai/providers/openai",
      settings: { baseURL, apiKey: token, transport: "http" },
      models: { fixture: { capabilities: { tools: true }, limit: { context: 16000, output: 128 },
        settings: { store: false } } },
    } },
  }
  async function runSession(session?: string) {
    const run = Bun.spawn([cli, "--standalone", "run", "--model", "fixture/fixture", "--format", "json",
      ...(session ? ["--session", session] : []),
      session ? "Repeat the policy from the completed read." : "Read the allowed synthetic file."],
    { cwd: work, stdout: "pipe", stderr: "pipe", env: {
    PATH: "/usr/bin:/bin", HOME: root, XDG_DATA_HOME: join(root, "data"), XDG_CONFIG_HOME: join(root, "config"),
    XDG_STATE_HOME: join(root, "state"), XDG_CACHE_HOME: join(root, "cache"),
    OPENCODE_CONFIG_CONTENT: JSON.stringify(config), OPENCODE_DISABLE_MODELS_FETCH: "true",
    OPENCODE_CONFIG_PROJECT_DISABLE: "true", OPENCODE_DISABLE_FILEWATCHER: "true",
    } })
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
    for (let attempt = 0; attempt < 20 &&
         !db.query("SELECT 1 FROM operation WHERE status='cancelled'").get(); attempt++) await Bun.sleep(50)
    const totals = db.query("SELECT status, count(*) AS count FROM operation GROUP BY status").all()
    assert(totals.some((row: any) => row.status === "complete" && row.count >= 2))
    assert(totals.some((row: any) => row.status === "uncertain" && row.count === 2))
    assert(totals.some((row: any) => row.status === "cancelled" && row.count === 1))
    assert.equal(db.query("SELECT count(*) AS count FROM operation WHERE prompt_tokens=13 AND completion_tokens=7").get().count,
      requests - 3)
  } finally {
    db.close()
  }
  console.log("PASS Responses native tool cycle, deny, SSE, cancellation and persisted usage")
} finally {
  child.kill()
  await child.exited
  await upstream.stop(true)
  await rm(root, { recursive: true, force: true })
}
