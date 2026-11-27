"""Streaming, stateless Responses subset for the authenticated loopback profile."""
import json

FIELDS = {
    "model", "input", "instructions", "tools", "tool_choice", "store", "stream",
    "max_output_tokens", "parallel_tool_calls", "temperature", "top_p", "text", "reasoning", "prompt_cache_key", "include",
}
ITEM_TYPES = {"message", "function_call", "function_call_output", "reasoning"}
EVENT_TYPES = {
    "response.created", "response.in_progress", "response.output_item.added",
    "response.output_item.done", "response.content_part.added", "response.content_part.done",
    "response.output_text.delta", "response.output_text.done",
    "response.function_call_arguments.delta", "response.function_call_arguments.done",
    "response.completed", "response.incomplete", "response.failed", "error",
}
TERMINAL_ERRORS = {"response.incomplete", "response.failed", "error"}
ITEM_FIELDS = {
    "message": {"type", "role", "content", "id", "status", "phase"},
    "function_call": {"type", "id", "call_id", "name", "arguments", "namespace"},
    "function_call_output": {"type", "call_id", "output"},
    "reasoning": {"type", "id", "summary", "encrypted_content"},
}


def text_content(content):
    return isinstance(content, str) or isinstance(content, list) and all(
        isinstance(part, dict) and part.get("type") in ("input_text", "output_text")
        and isinstance(part.get("text"), str) for part in content
    )


def parse(raw, model, max_tokens):
    body = json.loads(raw)
    if not isinstance(body, dict) or body.keys() - FIELDS or body.get("model") != model:
        raise ValueError("unsupported Responses request")
    if body.get("stream") is not True or body.get("store", False) is not False:
        raise ValueError("Responses requires streaming without server storage")
    cache_key = body.get("prompt_cache_key", "")
    included = body.get("include", [])
    if not isinstance(cache_key, str) or len(cache_key) > 256 or not isinstance(included, list) or any(
        entry != "reasoning.encrypted_content" for entry in included
    ):
        raise ValueError("unsupported Responses cache or include option")
    if not isinstance(body.get("instructions", ""), str) or type(body.get("parallel_tool_calls", False)) is not bool:
        raise ValueError("invalid Responses options")
    choice = body.get("tool_choice", "auto")
    if choice not in ("auto", "none", "required") and (
        not isinstance(choice, dict) or choice.keys() != {"type", "name"}
        or choice["type"] != "function" or not isinstance(choice["name"], str)
    ):
        raise ValueError("unsupported Responses tool choice")
    for field, keys in (("text", {"verbosity"}), ("reasoning", {"effort", "summary"})):
        value = body.get(field, {})
        if not isinstance(value, dict) or value.keys() - keys or not all(isinstance(v, str) for v in value.values()):
            raise ValueError("unsupported Responses generation option")
    for field, maximum in (("temperature", 2), ("top_p", 1)):
        if field in body and (type(body[field]) not in (int, float) or not 0 <= body[field] <= maximum):
            raise ValueError("invalid Responses sampling")
    tokens = body.get("max_output_tokens", max_tokens)
    if type(tokens) is not int or not 1 <= tokens <= max_tokens:
        raise ValueError("invalid Responses output limit")
    items = body.get("input")
    tools = body.get("tools", [])
    if not isinstance(items, list) or not 1 <= len(items) <= 128 or not isinstance(tools, list) or len(tools) > 64:
        raise ValueError("invalid Responses input or tools")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("type"), str) or item["type"] not in ITEM_TYPES:
            raise ValueError("unsupported Responses input item")
        if item.keys() - ITEM_FIELDS[item["type"]]:
            raise ValueError("unsupported Responses input fields")
        if item["type"].startswith("function_call") and not isinstance(item.get("call_id"), str):
            raise ValueError("invalid function call identifier")
        if item["type"] == "message":
            if item.get("role") not in ("system", "developer", "user", "assistant"):
                raise ValueError("invalid Responses message role")
            if not text_content(item.get("content")):
                raise ValueError("only text message content is supported")
        elif item["type"] == "function_call_output" and not text_content(item.get("output")):
            raise ValueError("only text tool results are supported")
        elif item["type"] == "function_call" and not all(isinstance(item.get(key), str)
                                                         for key in ("name", "arguments")):
            raise ValueError("invalid function call")
    if any(not isinstance(tool, dict) or tool.get("type") != "function"
           or not isinstance(tool.get("name"), str) for tool in tools):
        raise ValueError("only function tools are supported")
    body["store"] = False
    body["max_output_tokens"] = tokens
    return body


def relay(response, model, sink, cancelled, max_bytes, check_usage):
    if response.status != 200 or response.getheader("Content-Type", "").split(";")[0].strip() != "text/event-stream":
        raise ValueError("upstream rejected Responses stream")
    frame = []
    total = 0
    identifier = None
    while not cancelled.is_set():
        line = response.readline(max_bytes - total + 1)
        if not line:
            break
        total += len(line)
        if total > max_bytes:
            raise ValueError("response too large")
        frame.append(line)
        if line not in (b"\n", b"\r\n"):
            continue
        fields = [part.rstrip(b"\r\n") for part in frame]
        data = [part[5:].lstrip() for part in fields if part.startswith(b"data:")]
        if not data:
            frame.clear()
            continue
        event = json.loads(b"\n".join(data))
        kind = event.get("type") if isinstance(event, dict) else None
        names = [part[6:].strip() for part in fields if part.startswith(b"event:")]
        if not isinstance(kind, str) or kind not in EVENT_TYPES or names not in ([], [kind.encode("ascii")]):
            raise ValueError("invalid Responses event")
        if kind in TERMINAL_ERRORS:
            raise ValueError("Responses upstream did not complete")
        if kind == "response.created":
            header = event.get("response")
            if (identifier is not None or not isinstance(header, dict)
                    or header.get("model") != model or not isinstance(header.get("id"), str)):
                raise ValueError("invalid Responses identity")
            identifier = header["id"]
        if identifier is None:
            raise ValueError("Responses stream missing creation event")
        if kind == "response.completed":
            final = event.get("response")
            if (not isinstance(final, dict) or final.get("id") != identifier or final.get("model") != model
                    or final.get("status") != "completed"):
                raise ValueError("invalid Responses completion")
            usage = final.get("usage")
            if usage is not None:
                check_usage(usage)
            counts = (usage.get("input_tokens"), usage.get("output_tokens")) if usage else (None, None)
            sink(b"".join(frame))
            return "complete", counts if all(type(n) is int and 0 <= n < 2**31 for n in counts) else (None, None)
        sink(b"".join(frame))
        frame.clear()
    if cancelled.is_set():
        return "cancelled", (None, None)
    raise ValueError("truncated Responses stream")
