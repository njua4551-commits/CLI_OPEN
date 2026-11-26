"""Bounded, offline-profile request to an OpenAI-compatible loopback endpoint.

Two transports share one validator and one fixed destination:
- stdin: a single JSON request, one response on stdout;
- --listen: a local OpenAI-compatible endpoint for the fixed CLI provider.
No redirects, retries, proxies or alternative providers are used.
"""
import argparse
import os
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import http.client
import json
import re
import signal
import sys

def _env_int(name, default, minimum=1, maximum=None):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        value = default
    if value < minimum:
        value = minimum
    if maximum is not None and value > maximum:
        value = maximum
    return value

MAX_REQUEST = _env_int("CLI_OPEN_GATEWAY_MAX_REQUEST", 131_072, 1024, 1_048_576)
MAX_RESPONSE = _env_int("CLI_OPEN_GATEWAY_MAX_RESPONSE", 65_536, 1024, 1_048_576)
MAX_TOKENS = _env_int("CLI_OPEN_GATEWAY_MAX_TOKENS", 512, 1, 8192)
MAX_MESSAGES = _env_int("CLI_OPEN_GATEWAY_MAX_MESSAGES", 24, 1, 256)
MAX_TOOLS = _env_int("CLI_OPEN_GATEWAY_MAX_TOOLS", 64, 1, 512)
TIMEOUT = _env_int(
    "CLI_OPEN_GATEWAY_TIMEOUT_SECONDS",
    _env_int("CLI_OPEN_GATEWAY_TIMEOUT", 30, 1, 300),
    1, 300,
)
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
REQUEST_FIELDS = {"model", "messages", "max_tokens", "max_completion_tokens", "tools", "stream", "stream_options",
                  "tool_choice", "temperature", "top_p", "frequency_penalty", "presence_penalty", "seed", "stop",
                  "tool_stream", "store", "parallel_tool_calls", "reasoning_effort", "response_format"}
MESSAGE_FIELDS = {"role", "content", "tool_calls", "tool_call_id", "name", "reasoning_content", "refusal"}
ROLES = ("system", "developer", "user", "assistant", "tool")


class Rejected(ValueError):
    pass


def parse_request(data, clamp=False):
    request = json.loads(data)
    if not isinstance(request, dict) or request.keys() - REQUEST_FIELDS:
        raise Rejected(f"unexpected request fields {sorted(request.keys() - REQUEST_FIELDS)}")
    messages = request.get("messages")
    limit = request.get("max_tokens", request.get("max_completion_tokens", MAX_TOKENS))
    if type(limit) is not int or limit < 1 or (limit > MAX_TOKENS and not clamp):
        raise Rejected("invalid token limit")
    request["max_tokens"] = min(limit, MAX_TOKENS)
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise Rejected("invalid message list")
    for message in messages:
        if (
            not isinstance(message, dict) or message.keys() - MESSAGE_FIELDS
            or message.get("role") not in ROLES
        ):
            raise Rejected("invalid message")
        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise Rejected("invalid message content")
        calls = message.get("tool_calls")
        if calls is not None and not isinstance(calls, list):
            raise Rejected("invalid tool calls")
        if message["role"] == "tool" and not isinstance(message.get("tool_call_id"), str):
            raise Rejected("invalid tool result")
    if "tools" in request:
        tools = request["tools"]
        if not isinstance(tools, list) or not 1 <= len(tools) <= MAX_TOOLS:
            raise Rejected("invalid tool list")
        for tool in tools:
            if (
                not isinstance(tool, dict) or set(tool) != {"type", "function"}
                or tool["type"] != "function" or not isinstance(tool["function"], dict)
            ):
                raise Rejected("only function definitions are allowed")
    choice = request.get("tool_choice")
    if choice is not None and not (isinstance(choice, str) or isinstance(choice, dict)):
        raise Rejected("invalid tool choice")
    for field in ("temperature", "top_p", "frequency_penalty", "presence_penalty"):
        if field in request and type(request[field]) not in (int, float):
            raise Rejected("invalid sampling parameter")
    if "seed" in request and type(request["seed"]) is not int:
        raise Rejected("invalid seed")
    if "store" in request and not isinstance(request["store"], bool):
        raise Rejected("invalid store flag")
    if "parallel_tool_calls" in request and not isinstance(request["parallel_tool_calls"], bool):
        raise Rejected("invalid parallel_tool_calls flag")
    if "stop" in request:
        stop = request["stop"]
        if not (isinstance(stop, str) or (isinstance(stop, list) and all(isinstance(item, str) for item in stop))):
            raise Rejected("invalid stop value")
    if "reasoning_effort" in request and not isinstance(request["reasoning_effort"], str):
        raise Rejected("invalid reasoning_effort")
    if "response_format" in request and not isinstance(request["response_format"], dict):
        raise Rejected("invalid response_format")
    if "stream" in request and not isinstance(request["stream"], bool):
        raise Rejected("invalid stream flag")
    options = request.get("stream_options")
    if options is not None and (
        not isinstance(options, dict) or set(options) - {"include_usage"}
        or not isinstance(options.get("include_usage"), bool)
    ):
        raise Rejected("invalid stream options")
    return request


def read_request(source):
    data = source.read(MAX_REQUEST + 1)
    if len(data) > MAX_REQUEST:
        raise Rejected("request too large")
    return parse_request(data)


@contextmanager
def deadline():
    def expired(*_):
        raise TimeoutError("gateway deadline elapsed")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, TIMEOUT)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def check_usage(value):
    if not isinstance(value, dict) or ("cost" in value and (
        type(value["cost"]) not in (int, float) or value["cost"] != 0
    )):
        raise Rejected("unexpected cost in local response")


def model_matches(actual, expected):
    if not isinstance(actual, str) or not isinstance(expected, str):
        return False
    if actual == expected:
        return True
    aliases = [item.strip() for item in os.environ.get("CLI_OPEN_GATEWAY_MODEL_ALIASES", "").split(",") if item.strip()]
    # Explicit, authorized alias pairs only: "alias=canonical".
    for entry in aliases:
        if "=" in entry:
            left, right = (part.strip() for part in entry.split("=", 1))
            if (left == actual and right == expected) or (right == actual and left == expected):
                return True
    return False


def check_json(data, model):
    report = json.loads(data)
    if not isinstance(report, dict) or not model_matches(report.get("model"), model) or not isinstance(report.get("choices"), list):
        raise Rejected("invalid response or unexpected model")
    check_usage(report.get("usage", {}))
    return report


def check_stream(data, model):
    text = data.decode("utf-8")
    seen = 0
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        raw = line[6:].strip()
        if raw == "[DONE]":
            continue
        chunk = json.loads(raw)
        if not isinstance(chunk, dict) or not model_matches(chunk.get("model"), model):
            raise Rejected("invalid stream or unexpected model")
        check_usage(chunk.get("usage") or {})
        seen += 1
    if not seen:
        raise Rejected("empty stream")
    return data


def complete(port, model, request, stream=None):
    if not 1 <= port <= 65535 or not MODEL_NAME.fullmatch(model):
        raise Rejected("invalid loopback port or model")
    forwarded = {key: request[key] for key in ("messages", "tools", "tool_choice", "temperature", "top_p", "stream_options",
                                               "frequency_penalty", "presence_penalty", "seed", "stop", "tool_stream",
                                               "store", "parallel_tool_calls", "reasoning_effort", "response_format") if key in request}
    forwarded["model"] = model
    forwarded["max_tokens"] = request.get("max_tokens", request.get("max_completion_tokens", MAX_TOKENS))
    forwarded["stream"] = request.get("stream", False) if stream is None else stream
    payload = json.dumps(forwarded, allow_nan=False).encode("ascii")
    if len(payload) > MAX_REQUEST:
        raise Rejected("encoded request too large")
    # Fixed host/path, direct connection, no proxy, redirects, retries or provider fallback.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        connection.request("POST", "/v1/chat/completions", payload, {"Content-Type": "application/json"})
        with connection.getresponse() as response:
            if response.status != 200:
                raise Rejected("local endpoint rejected the request")
            content_type = response.getheader("Content-Type", "application/json")
            data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise Rejected("response too large")
    finally:
        connection.close()
    if content_type.split(";")[0].strip() == "text/event-stream":
        check_stream(data, model)
    else:
        check_json(data, model)
    return content_type, data


def complete_streaming(port, model, request, sink):
    """Relay an upstream response to ``sink`` without buffering it whole.

    Validates every SSE event as it arrives and enforces the same size and
    model/cost limits as :func:`complete`. ``sink`` receives raw bytes.
    """
    if not 1 <= port <= 65535 or not MODEL_NAME.fullmatch(model):
        raise Rejected("invalid loopback port or model")
    forwarded = {key: request[key] for key in ("messages", "tools", "tool_choice", "temperature", "top_p", "stream_options",
                                               "frequency_penalty", "presence_penalty", "seed", "stop", "tool_stream",
                                               "store", "parallel_tool_calls", "reasoning_effort", "response_format") if key in request}
    forwarded["model"] = model
    forwarded["max_tokens"] = request.get("max_tokens", request.get("max_completion_tokens", MAX_TOKENS))
    forwarded["stream"] = True
    payload = json.dumps(forwarded, allow_nan=False).encode("ascii")
    if len(payload) > MAX_REQUEST:
        raise Rejected("encoded request too large")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    total = 0
    buffer = b""
    try:
        connection.request("POST", "/v1/chat/completions", payload, {"Content-Type": "application/json"})
        with connection.getresponse() as response:
            if response.status != 200:
                raise Rejected("local endpoint rejected the request")
            content_type = response.getheader("Content-Type", "application/json")
            is_stream = content_type.split(";")[0].strip() == "text/event-stream"
            while True:
                chunk = response.read(4096)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE:
                    raise Rejected("response too large")
                if is_stream:
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.rstrip(b"\r")
                        if not line:
                            continue
                        if not line.startswith(b"data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == b"[DONE]":
                            continue
                        parsed = json.loads(raw)
                        if not isinstance(parsed, dict) or not model_matches(parsed.get("model"), model):
                            raise Rejected("invalid stream or unexpected model")
                        check_usage(parsed.get("usage") or {})
                sink(chunk)
            if is_stream and buffer.strip():
                raise Rejected("truncated stream")
            if is_stream and total == 0:
                raise Rejected("empty stream")
    finally:
        connection.close()
    return content_type


def read_body(handler):
    if handler.headers.get("Transfer-Encoding"):
        if handler.headers["Transfer-Encoding"].lower() != "chunked":
            raise Rejected("unsupported transfer encoding")
        chunks, total = [], 0
        while True:
            line = handler.rfile.readline(1024)
            if not line:
                raise Rejected("truncated chunked request")
            size = int(line.split(b";")[0].strip(), 16)
            if size == 0:
                while handler.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                    pass
                break
            total += size
            if total > MAX_REQUEST:
                raise Rejected("request too large")
            chunk = handler.rfile.read(size)
            if len(chunk) != size:
                raise Rejected("truncated chunked request")
            chunks.append(chunk)
            handler.rfile.read(2)
        return b"".join(chunks)
    length = handler.headers.get("Content-Length", "")
    if not length.isdigit() or not 1 <= int(length) <= MAX_REQUEST:
        raise Rejected("invalid content length")
    data = handler.rfile.read(int(length))
    if len(data) != int(length):
        raise Rejected("truncated request")
    return data


def serve(listen, port, model):
    if not MODEL_NAME.fullmatch(model):
        raise Rejected("invalid model")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def reply(self, status, body=b""):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            try:
                if self.path != "/v1/chat/completions":
                    raise Rejected("unexpected path")
                request = parse_request(read_body(self), clamp=True)
                if request.get("stream") is True:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.end_headers()

                    def sink(data):
                        self.wfile.write(data)
                        self.wfile.flush()

                    try:
                        content_type = complete_streaming(port, model, request, sink)
                    except (Rejected, ValueError, OSError, http.client.HTTPException, RecursionError) as exc:
                        print(f"rejected: {exc!r}", file=sys.stderr, flush=True)
                        try:
                            self.wfile.write(b'data: {"error":"local gateway rejected the request"}\\n\\n')
                            self.wfile.flush()
                        except OSError:
                            pass
                        self.close_connection = True
                        return
                else:
                    content_type, body = complete(port, model, request)
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
            except (Rejected, ValueError, OSError, http.client.HTTPException, RecursionError) as exc:
                print(f"rejected: {exc!r}", file=sys.stderr, flush=True)
                self.reply(502, b'{"error":"local gateway rejected the request"}')
            self.close_connection = True

        def do_GET(self):
            self.reply(405)

        def log_message(self, *_):
            pass

    class _BoundedThreadingHTTPServer(ThreadingHTTPServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._concurrency = threading.BoundedSemaphore(
                _env_int("CLI_OPEN_GATEWAY_MAX_CONCURRENCY", 4, 1, 64)
            )

        def process_request_thread(self, request, client_address):
            self._concurrency.acquire()
            try:
                super().process_request_thread(request, client_address)
            finally:
                self._concurrency.release()

    server = _BoundedThreadingHTTPServer(("127.0.0.1", listen), Handler)
    server.daemon_threads = True
    print(f"LISTEN {server.server_port}", flush=True)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Consulta local y acotada. Sin destinos remotos.")
    parser.add_argument("--port", type=int, required=True, help="Puerto del endpoint IPv4 de loopback")
    parser.add_argument("--model", required=True, help="Identificador exacto del modelo")
    parser.add_argument("--listen", type=int, metavar="PUERTO",
                        help="Sirve un endpoint OpenAI-compatible local (0 elige puerto)")
    args = parser.parse_args()
    if not hasattr(signal, "SIGALRM"):
        print("Gateway local sin calificar en este entorno.", file=sys.stderr)
        return 2
    try:
        if args.listen is not None:
            if not 0 <= args.listen <= 65535:
                raise Rejected("invalid listen port")
            serve(args.listen, args.port, args.model)
            return 0
        with deadline():
            request = read_request(sys.stdin.buffer)
            _, report = complete(args.port, args.model, request, stream=False)
    except (Rejected, ValueError, OSError, http.client.HTTPException, RecursionError):
        print("Consulta local rechazada o fallida. Sin conexión alternativa.", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
