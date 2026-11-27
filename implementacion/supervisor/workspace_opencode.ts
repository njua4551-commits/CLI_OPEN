// Deterministic OpenCode provider for explicitly supplied workspace edits.
import assert from "node:assert/strict"
import { mkdtemp } from "node:fs/promises"
import { join } from "node:path"

type Edit = { operation: "create" | "replace"; path: string; text: string }
const edits: Edit[] = await Bun.stdin.json()
const model = "workspace-fixture"
const root = await mkdtemp("/tmp/cli-open-editor-")
let written = false

function stream(delta: object, finish: string) {
  const payload = (value: object, reason: string | null) => ({
    id: "workspace-fixture", object: "chat.completion.chunk", created: 1, model,
    choices: [{ index: 0, delta: value, finish_reason: reason }],
  })
  const messages = [payload({ role: "assistant", ...delta }, null), payload({}, finish)]
  return new Response(messages.map(message => `data: ${JSON.stringify(message)}\n\n`).join("") + "data: [DONE]\n\n", {
    headers: { "content-type": "text/event-stream" },
  })
}

const server = Bun.serve({
  hostname: "127.0.0.1", port: 0,
  async fetch(request) {
    if (request.method !== "POST" || new URL(request.url).pathname !== "/v1/chat/completions") {
      return new Response(null, { status: 404 })
    }
    const body = await request.json()
    assert.equal(body.model, model)
    if (body.messages.some((message: { role: string }) => message.role === "tool")) {
      return stream({ content: "Review fixture complete." }, "stop")
    }
    if (!body.tools?.length) return stream({ content: "Workspace review" }, "stop")
    assert(body.tools.some((tool: { function: { name: string } }) => tool.function.name === "write"))
    assert(!written, "fixture received a repeated edit turn")
    written = true
    return stream({ tool_calls: edits.map((edit, index) => ({
      id: `edit_${index}`, index, type: "function",
      function: { name: "write", arguments: JSON.stringify({ path: edit.path, content: edit.text }) },
    })) }, "tool_calls")
  },
})

try {
  const config = {
    permissions: [
      { action: "*", resource: "*", effect: "deny" },
      ...edits.map(({ path }) => ({ action: "edit", resource: path, effect: "allow" })),
    ],
    snapshots: false,
    providers: {
      fixture: {
        package: "@opencode/ai/providers/openai-compatible",
        settings: { baseURL: new URL("v1", server.url).toString(), apiKey: "fixture" },
        models: { [model]: { capabilities: { tools: true } } },
      },
    },
  }
  const child = Bun.spawn([
    "/fixture/opencode", "--standalone", "run", "--model", `fixture/${model}`, "--format", "json",
    "Prepare the explicitly approved edits in the workspace copy.",
  ], {
    cwd: "/work", stdout: "pipe", stderr: "inherit",
    env: {
      HOME: root, PATH: "/usr/bin:/bin", XDG_STATE_HOME: join(root, "state"),
      XDG_CONFIG_HOME: join(root, "config"), XDG_DATA_HOME: join(root, "data"),
      XDG_CACHE_HOME: join(root, "cache"), OPENCODE_CONFIG_CONTENT: JSON.stringify(config),
      OPENCODE_CONFIG_PROJECT_DISABLE: "true", OPENCODE_DISABLE_CLAUDE_CODE: "true",
      OPENCODE_DISABLE_MODELS_FETCH: "true", OPENCODE_DISABLE_FILEWATCHER: "true",
    },
  })
  try {
    const output = await new Response(child.stdout).text()
    assert.equal(await child.exited, 0)
    assert(written && output.includes("Review fixture complete."))
    const validator = Bun.spawn(["/usr/bin/python3", "-I", "-B", "/worker.py"], {
      cwd: "/work", env: {}, stdin: new Blob([JSON.stringify(edits)]), stderr: "inherit",
    })
    assert.equal(await validator.exited, 0)
  } finally {
    child.kill()
    await child.exited
  }
} finally {
  await server.stop(true)
}
