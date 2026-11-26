import assert from "node:assert/strict"
import plugin, { compressMarkdown } from "../implementacion/lectura-web/index.mjs"

const paragraph = "Documentation navigation."
const original = Array(12).fill(paragraph).join("\n\n")
const compressed = compressMarkdown(original)
assert(compressed.length < original.length)
assert.match(compressed, /appears 12 times/)
for (const text of [
  "```markdown\n" + original + "\n```",
  "## Heading\n\n| Col |\n| --- |\n| 雪 |",
  "Large paragraph.\n\n".repeat(20_000),
]) assert.equal(compressMarkdown(text), text)

let hook
let disposed = false
const dispose = await plugin.setup({ tool: { hook: async (name, callback) => {
  assert.equal(name, "execute.after")
  hook = callback
  return { dispose: async () => { disposed = true } }
} } })
const result = {
  content: [{ type: "text", text: original }],
  output: { contentType: "text/html; charset=utf-8", output: original },
  metadata: { fixture: true },
}
const event = { tool: "webfetch", status: "completed", input: { format: "markdown" }, result }
for (const override of [{ tool: "read" }, { status: "error" }, { input: { format: "html" } }]) {
  const ignored = { ...event, ...override }
  hook(ignored)
  assert.equal(ignored.result, result)
}
hook(event)
assert.equal(event.result.content[0].text, compressed)
assert.equal(event.result.output.output, compressed)
assert.equal(event.result.metadata, result.metadata)
await dispose()
assert(disposed)
console.log("PASS webfetch plugin scope, bounded compression and cleanup")
