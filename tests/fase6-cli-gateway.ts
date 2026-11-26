import assert from "node:assert/strict"
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"

const binary = resolve(process.argv[2] ?? "")
const gateway = resolve(import.meta.dir, "..", "implementacion", "gateway")
const model = "synthetic"
const marker = "F6_CLI_OK"
const root = await mkdtemp(join(tmpdir(), "fase6-cli-gateway-"))
const workspace = join(root, "fixture")
const state = join(root, "state", "opencode")
let requests: { path: string; body: any; authorization: string | null }[] = []
let cost = 0
let decoyRequests = 0

function stream(delta: object, finish: string) {
  const chunk = (value: object, reason: string | null) => ({
    id: "fixture", object: "chat.completion.chunk", created: 1, model,
    choices: [{ index: 0, delta: value, finish_reason: reason }],
    ...(reason ? { usage: { cost } } : {}),
  })
  return new Response([
    chunk({ role: "assistant", ...delta }, null), chunk({}, finish),
  ].map(value => `data: ${JSON.stringify(value)}\n\n`).join("") + "data: [DONE]\n\n", {
    headers: { "content-type": "text/event-stream" },
  })
}

const upstream = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  async fetch(request) {
    const body = await request.json()
    requests.push({
      path: new URL(request.url).pathname, body,
      authorization: request.headers.get("authorization"),
    })
    const results = body.messages.filter((message: { role: string }) => message.role === "tool")
    if (body.messages.some((message: { role: string; content: unknown }) =>
      message.role === "user" && JSON.stringify(message.content).includes("Synthetic fixture: resume"))) {
      assert.equal(results.length, 1, "the completed tool result should appear once")
      assert(JSON.stringify(results[0]).includes("FIRST_ONLY"))
      return stream({ content: "FIXTURE_RESUMED" }, "stop")
    }
    if (!body.tools?.length && !results.length) return stream({ content: "Synthetic title" }, "stop")
    if (results.length) {
      const content = results.map((message: { content: string }) => message.content).join("\n")
      assert(content.includes("FIRST_ONLY"), content)
      return stream({ content: marker }, "stop")
    }
    return stream({ tool_calls: [{
      index: 0, id: "call_read", type: "function",
      function: { name: "read", arguments: JSON.stringify({ path: "sample.txt" }) },
    }] }, "tool_calls")
  },
})

const decoy = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  fetch() { decoyRequests++; return Response.json({ error: "decoy" }, { status: 500 }) },
})

const child = Bun.spawn([
  "/usr/bin/python3", "-I", "-B", gateway,
  "--port", String(upstream.port), "--model", model, "--listen", "0",
], { stdout: "pipe", stderr: "inherit" })
const reader = child.stdout.getReader()
let buffered = ""
while (!buffered.includes("\n")) {
  const { value, done } = await reader.read()
  assert(!done, "gateway exited before listening")
  buffered += new TextDecoder().decode(value)
}
const gatewayPort = Number(buffered.split("\n")[0].replace("LISTEN ", ""))
assert(Number.isInteger(gatewayPort) && gatewayPort > 0)

async function run(label: string, timeout = 30000, allowKill = false, sessionID?: string) {
  requests = []
  const process = Bun.spawn([
    binary, "--standalone", "run", "--model", "fixture/synthetic", "--format", "json",
    ...(sessionID ? ["--session", sessionID] : []),
    `Synthetic fixture: ${label}`,
  ], {
    cwd: workspace, stdout: "pipe", stderr: "pipe",
    env: {
      HOME: root, PATH: "/usr/bin:/bin", XDG_STATE_HOME: join(root, "state"),
      XDG_CONFIG_HOME: join(root, "config"), XDG_DATA_HOME: join(root, "data"),
      XDG_CACHE_HOME: join(root, "cache"), OPENCODE_CONFIG_CONTENT: config,
      OPENCODE_VERSION: "2.3.2", OPENCODE_DISABLE_MODELS_FETCH: "true",
      OPENCODE_DISABLE_FILEWATCHER: "true",
    },
  })
  const output = new Response(process.stdout).text()
  const errors = new Response(process.stderr).text()
  const timer = setTimeout(() => process.kill("SIGKILL"), timeout)
  try {
    const exit = await process.exited
    const stdout = await output
    const stderr = await errors
    assert(allowKill || exit !== 137, `fixture hit the watchdog: ${stderr || stdout}`)
    return { exit, stdout, stderr }
  } finally {
    clearTimeout(timer)
    process.kill()
    await process.exited
  }
}

const config = JSON.stringify({
  providers: {
    fixture: {
      package: "@opencode/ai/providers/openai-compatible",
      settings: { baseURL: `http://127.0.0.1:${gatewayPort}/v1`, apiKey: "fixture" },
      models: { [model]: { capabilities: { tools: true } } },
    },
    decoy: {
      package: "@opencode/ai/providers/openai-compatible",
      settings: { baseURL: new URL("v1", decoy.url).toString(), apiKey: "fixture" },
      models: { [model]: { capabilities: { tools: true } } },
    },
  },
})

try {
  await mkdir(state, { recursive: true })
  await mkdir(workspace)
  await writeFile(join(workspace, "sample.txt"), "FIRST_ONLY\nSECOND_ONLY\n")

  const success = await run("success")
  assert.equal(success.exit, 0, success.stderr || success.stdout)
  assert(success.stdout.includes(marker), success.stdout)
  const bounded = requests.filter(item =>
    item.body.tools?.length || item.body.messages.some((message: { role: string }) => message.role === "tool"))
  assert.equal(bounded.length, 2, JSON.stringify(requests))
  assert(requests.every(item => item.path === "/v1/chat/completions"))
  assert(requests.every(item => item.body.model === model && item.body.stream === true))
  assert(requests.every(item => item.authorization === null), "gateway forwarded credentials")
  assert(requests.every(item => item.body.max_tokens <= 512))
  assert.equal(decoyRequests, 0)
  console.log("PASS CLI -> gateway -> loopback with tool result, no credentials, no decoy")

  const events = success.stdout.split("\n").filter(line => line.startsWith("{")).map(line => JSON.parse(line))
  const sessionID = events.find(event => event.type === "tool_use")?.sessionID
  assert.equal(typeof sessionID, "string")
  const resumed = await run("resume", 30000, false, sessionID)
  assert.equal(resumed.exit, 0, resumed.stderr || resumed.stdout)
  assert(resumed.stdout.includes("FIXTURE_RESUMED"), resumed.stdout)
  assert(!resumed.stdout.includes('"type":"tool_use"'), resumed.stdout)
  assert.equal(requests.length, 1)
  assert.equal(decoyRequests, 0)
  console.log("PASS native session resumes in a new CLI process without repeating the read")

  cost = 0.001
  const charged = await run("cost", 8000, true)
  assert.notEqual(charged.exit, 0, charged.stdout)
  assert(!charged.stdout.includes(marker))
  assert.equal(decoyRequests, 0)
  console.log("PASS non-zero cost rejected without fallback")
  cost = 0

  await upstream.stop(true)
  const down = await run("down", 8000, true)
  assert.notEqual(down.exit, 0, down.stdout)
  assert(!down.stdout.includes(marker))
  assert.equal(decoyRequests, 0)
  console.log("PASS endpoint down rejected without fallback")
} finally {
  child.kill()
  await child.exited
  await upstream.stop(true)
  await decoy.stop(true)
  await rm(root, { recursive: true, force: true })
}
