// Compress only adjacent copies of a plain paragraph or a line of Markdown links.
const MAX_INPUT = 256 * 1024
const fencePattern = /^ {0,3}(`{3,}|~{3,})(.*)$/u
const plainParagraph = /^\p{L}[^\n<>`\[\]|]+$/u
const linkLine = /^(?:\[[^\[\]\n]+\]\([^\s()]+\)[ \t]*)+$/u

export function compressMarkdown(markdown) {
  if (markdown.length > MAX_INPUT || Buffer.byteLength(markdown) > MAX_INPUT) return markdown

  const blocks = markdown.split("\n\n")
  const output = []
  let fence
  for (let index = 0; index < blocks.length;) {
    const block = blocks[index]
    const eligible = !fence && (plainParagraph.test(block) || linkLine.test(block))
    if (eligible) {
      let end = index + 1
      while (blocks[end] === block) end++
      const count = end - index
      const notice = `[Previous block appears ${count} times in the source.]`
      if (count >= 3 && notice.length < (count - 1) * (block.length + 2)) {
        output.push(block, notice)
        index = end
        continue
      }
    }
    for (const line of block.split("\n")) {
      const match = fencePattern.exec(line)
      if (!match) continue
      const [, marker, tail] = match
      if (!fence) fence = marker
      else if (marker[0] === fence[0] && marker.length >= fence.length && !tail.trim()) fence = undefined
    }
    output.push(block)
    index++
  }
  return output.join("\n\n")
}

export default {
  id: "cli-open.lectura-web",
  async setup(ctx) {
    const registration = await ctx.tool.hook("execute.after", (event) => {
      if (event.tool !== "webfetch" || event.status !== "completed") return
      if (event.input?.format !== undefined && event.input.format !== "markdown") return
      const { content, output } = event.result
      if (!Array.isArray(content) || content.length !== 1 || content[0]?.type !== "text" ||
          typeof content[0].text !== "string" || output?.output !== content[0].text ||
          typeof output.contentType !== "string" ||
          output.contentType.split(";", 1)[0].trim().toLowerCase() !== "text/html") return
      const compressed = compressMarkdown(content[0].text)
      if (compressed === content[0].text) return
      event.result = {
        ...event.result,
        content: [{ ...content[0], text: compressed }],
        output: { ...output, output: compressed },
      }
    })
    return () => registration.dispose()
  },
}
