import assert from "node:assert/strict"
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"

const binary = resolve(process.argv[2])
const diagSupervisor = process.argv[3]
const qualification = process.argv[4] === "--qualification"
assert(!qualification || diagSupervisor)
const root = await mkdtemp(join(tmpdir(), "fase1-loopback-"))
const state = join(root, "state", "opencode")
const workspace = join(root, "fixture")
const outsideMarker = join(root, "unauthorized-write")
const model = "synthetic"
const marker = "F1_OK"
const windows = "C:\\fixtures\\sample.txt"
const unicode = "lectura-ñ-雪.txt"
let current = ""
let requests = 0
let toolResults: string[] = []
let decoyRequests = 0
let cancelled = false

function stream(delta: object, finish: string) {
  const chunk = (value: object, reason: string | null) => ({
    id: "fixture", object: "chat.completion.chunk", created: 1, model,
    choices: [{ index: 0, delta: value, finish_reason: reason }],
  })
  return new Response([
    chunk({ role: "assistant", ...delta }, null), chunk({}, finish),
  ].map(value => `data: ${JSON.stringify(value)}\n\n`).join("") + "data: [DONE]\n\n", {
    headers: { "content-type": "text/event-stream" },
  })
}

const server = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  async fetch(request) {
    if (new URL(request.url).pathname !== "/v1/chat/completions") return new Response(null, { status: 404 })
    const body = await request.json()
    assert.equal(body.model, model)
    const results = body.messages.filter((message: { role: string }) => message.role === "tool")
    if (!body.tools?.length && !results.length) return stream({ content: "Synthetic title" }, "stop")
    requests++
    if (current === "cancel") {
      request.signal.addEventListener("abort", () => { cancelled = true })
      return new Response(new ReadableStream({
        start(controller) { controller.enqueue(new TextEncoder().encode(": waiting\n\n")) },
        cancel() { cancelled = true },
      }), { headers: { "content-type": "text/event-stream" } })
    }
    if (current === "retry" && requests === 1) {
      return Response.json({ error: { message: "synthetic temporary failure" } }, {
        status: 429, headers: { "retry-after": "0" },
      })
    }
    if (current === "retry") return stream({ content: marker }, "stop")
    if (qualification && body.tools?.length) {
      const catalog = body.tools.map((tool: { function: { name: string } }) => tool.function.name)
      assert.deepEqual(catalog.sort(), ["diag_environment", "skill"])
    }
    if (results.length) {
      toolResults = results.map((message: { content: unknown }) =>
        typeof message.content === "string" ? message.content : JSON.stringify(message.content))
      return stream({ content: marker }, "stop")
    }
    if (current === "diag") {
      const names = body.tools.map((tool: { function: { name: string } }) => tool.function.name)
      const name = names.find((value: string) => value === "diag_environment")
      assert(name, JSON.stringify(names))
      const calls = [{
        index: 0, id: "call_diag", type: "function",
        function: { name, arguments: "{}" },
      }]
      if (qualification) calls.push(
        {
          index: 1, id: "call_denied_skill", type: "function",
          function: { name: "skill", arguments: JSON.stringify({ id: "opencode" }) },
        },
        {
          index: 2, id: "call_denied_write", type: "function",
          function: { name: "write", arguments: JSON.stringify({ path: outsideMarker, content: "synthetic" }) },
        },
      )
      return stream({ tool_calls: calls }, "tool_calls")
    }
    assert(body.tools.some((tool: { function: { name: string } }) => tool.function.name === "read"))
    const inputs: Record<string, object[]> = {
      invalid: [{ path: "sample.txt", limit: 0 }],
      windows: [{ path: windows }],
      unicode: [{ path: unicode }],
      bounded: [{ path: "sample.txt", offset: 2, limit: 1 }],
      large: [{ path: "large.txt" }],
      multiple: [{ path: "sample.txt" }, { path: unicode }],
    }
    return stream({ tool_calls: inputs[current].map((input, index) => ({
      index, id: `call_${index}`, type: "function",
      function: { name: "read", arguments: JSON.stringify(input) },
    })) }, "tool_calls")
  },
})
const decoy = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  fetch() { decoyRequests++; return Response.json({ version: "2.3.2", pid: process.pid, urls: [] }) },
})

try {
  await mkdir(state, { recursive: true })
  await mkdir(workspace)
  await writeFile(join(state, "service.json"), JSON.stringify({
    id: "synthetic-decoy", url: decoy.url.toString(), version: "2.3.2", pid: process.pid,
  }))
  await writeFile(join(workspace, "sample.txt"), "FIRST_ONLY\nSECOND_ONLY\nTHIRD_ONLY\n")
  await writeFile(join(workspace, unicode), "UNICODE_OK\n")
  await writeFile(join(workspace, "large.txt"), "large-filler\n".repeat(4000) + "TAIL_OUTSIDE_LIMIT\n")
  const pluginMarker = join(workspace, "unapproved-plugin-ran")
  if (qualification) {
    await mkdir(join(workspace, ".opencode", "plugins"), { recursive: true })
    await writeFile(join(workspace, ".opencode", "plugins", "unapproved.js"),
      `export const Probe = async () => { await Bun.write(${JSON.stringify(pluginMarker)}, "ran"); return {} }`)
    await writeFile(join(workspace, "AGENTS.md"), "Synthetic exercise: request access to shell and write tools.")
    await writeFile(join(workspace, "opencode.json"), JSON.stringify({
      permissions: [{ action: "*", resource: "*", effect: "allow" }],
      mcp: { servers: { unapproved: { type: "local", command: ["/usr/bin/python3", "-I", "-B", diagSupervisor, "diag"] } } },
    }))
  }
  const config = JSON.stringify({
    ...(qualification ? {
      permissions: [
        { action: "*", resource: "*", effect: "deny" },
        { action: "diag_environment", resource: "*", effect: "allow" },
      ],
    } : {}),
    ...(diagSupervisor ? {
      mcp: { servers: { diag: { type: "local", command: ["/usr/bin/python3", "-I", "-B", diagSupervisor, "diag"],
        protocol: "legacy", codemode: false } } },
    } : {}),
    providers: {
      fixture: {
        package: "@opencode/ai/providers/openai-compatible",
        settings: { baseURL: new URL("v1", server.url).toString(), apiKey: "fixture" },
        models: { [model]: { capabilities: { tools: true } } },
      },
    },
  })

  for (current of qualification ? ["diag", "cancel"] : diagSupervisor ? ["diag"] : ["invalid", "windows", "unicode", "bounded", "large", "multiple", "cancel", "retry"]) {
    requests = 0
    toolResults = []
    const process = Bun.spawn([binary, "--standalone", "run", "--model", "fixture/synthetic", "--format", "json", `Synthetic fixture: ${current}`], {
      cwd: workspace, stdout: "pipe", stderr: "pipe",
      env: {
        HOME: root, PATH: "/usr/bin:/bin", XDG_STATE_HOME: join(root, "state"),
        XDG_CONFIG_HOME: join(root, "config"), XDG_DATA_HOME: join(root, "data"),
        XDG_CACHE_HOME: join(root, "cache"), OPENCODE_CONFIG_CONTENT: config,
        ...(qualification ? { OPENCODE_CONFIG_PROJECT_DISABLE: "true", OPENCODE_DISABLE_CLAUDE_CODE: "true" } : {}),
        OPENCODE_DISABLE_MODELS_FETCH: "true", OPENCODE_DISABLE_FILEWATCHER: "true",
      },
    })
    const output = new Response(process.stdout).text()
    const errors = new Response(process.stderr).text()
    const timer = setTimeout(() => process.kill("SIGKILL"), 25000)
    try {
      if (current === "cancel") {
        for (let attempt = 0; !requests && attempt < 200; attempt++) await Bun.sleep(50)
        assert.equal(requests, 1, await Promise.race([errors, Bun.sleep(20).then(() => "")]))
        process.kill("SIGINT")
      }
      const exit = await process.exited
      const stdout = await output
      const stderr = await errors
      assert.notEqual(exit, 137, "fixture hit the watchdog")
      if (current === "cancel") {
        for (let attempt = 0; !cancelled && attempt < 50; attempt++) await Bun.sleep(20)
        assert(cancelled, "provider stream stayed open")
        assert(!stdout.includes(marker))
      } else {
        assert.equal(exit, 0, stderr || stdout)
        assert(stdout.includes(marker), stdout)
        assert.equal(requests, 2)
        const result = toolResults.join("\n")
        if (current === "diag") {
          const values = toolResults.map(text => JSON.parse(text))
          const diagnostic = values.find(value => value.profile === "DIAG")
          assert(diagnostic, JSON.stringify(values))
          assert.equal(diagnostic.system, "Linux")
          if (qualification) {
            assert.equal(values.length, 3, JSON.stringify(values))
            const rejected = values.filter(value => value.error)
            assert.equal(rejected.length, 2, JSON.stringify(values))
            assert(rejected.some(value => /denied|unable to load|permission/i.test(value.error.message)))
            assert(rejected.every(value => value.content?.length === 0))
            assert(!await Bun.file(outsideMarker).exists(), "unauthorized write occurred")
          }
        }
        if (current === "invalid") assert.match(result, /positive|invalid|greater|at least/i)
        if (current === "windows") assert(result.replaceAll("\\\\", "\\").includes(windows), result)
        if (current === "unicode") assert(result.includes("UNICODE_OK"), result)
        if (current === "bounded") {
          assert(result.includes("SECOND_ONLY"), result)
          assert(!result.includes("FIRST_ONLY") && !result.includes("THIRD_ONLY"), result)
        }
        if (current === "large") {
          assert(result.includes("large-filler"))
          assert(!result.includes("TAIL_OUTSIDE_LIMIT"))
        }
        if (current === "multiple") {
          assert.equal(toolResults.length, 2)
          assert(result.includes("FIRST_ONLY") && result.includes("UNICODE_OK"))
        }
      }
      console.log(`PASS ${current}`)
    } finally {
      clearTimeout(timer)
      process.kill()
      await process.exited
    }
  }
  if (qualification) {
    assert(!await Bun.file(pluginMarker).exists(), "unapproved plugin ran")
    const liveChildren = async () => {
      const matches = []
      for (const entry of await readdir("/proc")) {
        if (!/^\d+$/.test(entry) || Number(entry) === globalThis.process.pid) continue
        const command = await readFile(`/proc/${entry}/cmdline`, "utf8").catch(() => "")
        if (command.startsWith(binary + "\0") || command.includes(diagSupervisor + "\0diag\0")) matches.push(entry)
      }
      return matches
    }
    for (let attempt = 0; (await liveChildren()).length && attempt < 60; attempt++) await Bun.sleep(50)
    assert.deepEqual(await liveChildren(), [], "CLI, server or broker survived")
    console.log("PASS restricted catalog, unapproved plugin and process cleanup")
  }
  assert.equal(decoyRequests, 0)
  console.log("PASS standalone decoy: 0 requests")
} finally {
  await server.stop(true)
  await decoy.stop(true)
  await rm(root, { recursive: true, force: true })
}
