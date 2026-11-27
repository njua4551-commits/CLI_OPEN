export function events(chunks: object[]) {
  return chunks.map(chunk => "data: " + JSON.stringify(chunk) + "\n\n").join("")
}

export function response(model: string, id: string, output: object[], chunks: object[], reportUsage = true) {
  const header = { id, model, output: [] }
  return new Response(events([
    { type: "response.created", response: header },
    ...chunks,
    { type: "response.completed", response: { ...header, status: "completed", output,
      ...(reportUsage ? { usage: { input_tokens: 13, output_tokens: 7, total_tokens: 20 } } : {}) } },
  ]), { headers: { "content-type": "text/event-stream" } })
}

export function toolCalls(model: string, id: string, items: { id: string; arguments: string }[]) {
  return response(model, id, items, items.flatMap((item, output_index) => [
    { type: "response.output_item.added", output_index, item: { ...item, arguments: "" } },
    { type: "response.function_call_arguments.delta", item_id: item.id, output_index, delta: item.arguments },
    { type: "response.function_call_arguments.done", item_id: item.id, output_index, arguments: item.arguments },
    { type: "response.output_item.done", output_index, item },
  ]))
}
