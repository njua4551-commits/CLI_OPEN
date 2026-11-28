"""Bounded, offline-profile request to an OpenAI-compatible loopback endpoint.

Two transports share one validator and one fixed destination:
- stdin: a single JSON request, one response on stdout;
- --listen: a local OpenAI-compatible endpoint for the fixed CLI provider.
No redirects, retries, proxies or alternative providers are used.
"""
import argparse
import hmac
import os
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import http.client
import json
from pathlib import Path
import re
import runpy
import selectors
import signal
import socket
import sqlite3
import sys
import time

load_json = runpy.run_path(str(Path(__file__).with_name("strict_json.py")))["load"]

UNKNOWN_USAGE = (None, None)


def reported_usage(value):
    if not isinstance(value, dict):
        return UNKNOWN_USAGE
    counts = (value.get("prompt_tokens"), value.get("completion_tokens"))
    return counts if all(type(count) is int and 0 <= count < 2**31 for count in counts) else UNKNOWN_USAGE

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
CLIENT_IDLE = _env_int("CLI_OPEN_GATEWAY_CLIENT_IDLE_SECONDS", 5, 1, 60)
PARSE_TIMEOUT = _env_int("CLI_OPEN_GATEWAY_PARSE_SECONDS", 10, 1, 60)
CHUNK_SIZE = re.compile(rb"[0-9A-Fa-f]{1,8}\r\n")
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
REQUEST_FIELDS = {"model", "messages", "max_tokens", "max_completion_tokens", "tools", "stream", "stream_options",
                  "tool_choice", "temperature", "top_p", "frequency_penalty", "presence_penalty", "seed", "stop",
                  "tool_stream", "store", "parallel_tool_calls", "reasoning_effort", "response_format"}
MESSAGE_FIELDS = {"role", "content", "tool_calls", "tool_call_id", "name", "reasoning_content", "refusal"}
ROLES = ("system", "developer", "user", "assistant", "tool")


class Rejected(ValueError):
    pass


def parse_request(data, clamp=False):
    request = load_json(data)
    if not isinstance(request, dict):
        raise Rejected("request must be a JSON object")
    if request.keys() - REQUEST_FIELDS:
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
def deadline(seconds=TIMEOUT):
    def expired(*_):
        raise TimeoutError("gateway deadline elapsed")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
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
        usage = UNKNOWN_USAGE
    else:
        usage = reported_usage(check_json(data, model).get("usage"))
    return content_type, data, usage


@contextmanager
def cancel_on_disconnect(downstream, upstream):
    finished = threading.Event()
    cancelled = threading.Event()

    def watch(selector):
        while not finished.wait(0.1):
            try:
                if not selector.select(0) or downstream.recv(1, socket.MSG_PEEK):
                    continue
            except OSError:
                pass
            cancelled.set()
            try:
                upstream.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return

    with selectors.DefaultSelector() as selector:
        selector.register(downstream, selectors.EVENT_READ)
        watcher = threading.Thread(target=watch, args=(selector,), daemon=True)
        watcher.start()
        try:
            yield cancelled
        finally:
            finished.set()
            watcher.join()


def complete_streaming(port, model, request, sink, downstream, *, require_done=False, responses=None):
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
    route = "/v1/chat/completions"
    if responses is not None:
        forwarded = request
        route = "/v1/responses"
    payload = json.dumps(forwarded, allow_nan=False).encode("ascii")
    if len(payload) > MAX_REQUEST:
        raise Rejected("encoded request too large")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        connection.connect()
        with cancel_on_disconnect(downstream, connection.sock) as cancelled:
            connection.request("POST", route, payload, {"Content-Type": "application/json"})
            with connection.getresponse() as response:
                if responses is not None:
                    return responses["relay"](response, model, sink, cancelled, MAX_RESPONSE, check_usage)
                return relay_stream(response, model, sink, cancelled, require_done=require_done)
    finally:
        connection.close()


def relay_stream(response, model, sink, cancelled, *, require_done=False):
    total = 0
    buffer = b""
    seen_event = False
    done = False
    usage = UNKNOWN_USAGE
    if response.status != 200:
        raise Rejected("local endpoint rejected the request")
    content_type = response.getheader("Content-Type", "application/json")
    is_stream = content_type.split(";")[0].strip() == "text/event-stream"
    if require_done and not is_stream:
        raise Rejected("expected SSE response")
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
                if require_done and done:
                    raise Rejected("data after stream terminator")
                if raw == b"[DONE]":
                    if require_done and not seen_event:
                        raise Rejected("stream ended without events")
                    done = True
                    continue
                parsed = json.loads(raw)
                if not isinstance(parsed, dict) or not model_matches(parsed.get("model"), model):
                    raise Rejected("invalid stream or unexpected model")
                check_usage(parsed.get("usage") or {})
                if parsed.get("usage") is not None:
                    usage = reported_usage(parsed["usage"])
                seen_event = True
        sink(chunk)
    if cancelled.is_set():
        return "cancelled", UNKNOWN_USAGE
    if is_stream and buffer.strip():
        raise Rejected("truncated stream")
    if is_stream and total == 0:
        raise Rejected("empty stream")
    if require_done and not done:
        raise Rejected("missing stream terminator")
    return "complete", usage if done else UNKNOWN_USAGE


def read_body(handler):
    encodings = handler.headers.get_all("Transfer-Encoding", [])
    lengths = handler.headers.get_all("Content-Length", [])
    if encodings:
        if len(encodings) != 1 or encodings[0].lower() != "chunked" or lengths:
            raise Rejected("unsupported transfer encoding")
        data = bytearray()
        while True:
            line = handler.rfile.readline(11)
            if not CHUNK_SIZE.fullmatch(line):
                raise Rejected("invalid chunk size")
            size = int(line, 16)
            if size == 0:
                if handler.rfile.read(2) != b"\r\n":
                    raise Rejected("unsupported chunk trailer")
                return bytes(data)
            if len(data) + size > MAX_REQUEST:
                raise Rejected("request too large")
            chunk = handler.rfile.read(size)
            if len(chunk) != size or handler.rfile.read(2) != b"\r\n":
                raise Rejected("invalid chunk body")
            data.extend(chunk)
    if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
        raise Rejected("invalid content length")
    length = lengths[0]
    if not 1 <= int(length) <= MAX_REQUEST:
        raise Rejected("invalid content length")
    data = handler.rfile.read(int(length))
    if len(data) != int(length):
        raise Rejected("truncated request")
    return data


class TaskBudget:
    """Reserve local limits before dispatch. Failed or cancelled calls keep their reservation."""

    def __init__(self, token, requests, input_bytes, output_tokens):
        if (not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token)
                or not 1 <= requests <= 64 or not 1 <= input_bytes <= 16 * MAX_REQUEST
                or not 1 <= output_tokens <= 64 * MAX_TOKENS):
            raise Rejected("invalid task profile")
        self.authorization = ("Bearer " + token).encode("ascii")
        self.requests = requests
        self.input_bytes = input_bytes
        self.output_tokens = output_tokens
        self.lock = threading.Lock()
        self.ledger = None

    def allows(self, headers):
        return (len(headers) == 1
                and hmac.compare_digest(headers[0].encode("latin-1"), self.authorization))

    def reserve(self, size, tokens):
        with self.lock:
            if self.ledger is not None:
                return self.ledger.reserve(size, tokens)
            if self.requests == 0 or size > self.input_bytes or tokens > self.output_tokens:
                return None
            self.requests -= 1
            self.input_bytes -= size
            self.output_tokens -= tokens
            return True


def serve(listen, port, model, task=None, responses=None):
    if not MODEL_NAME.fullmatch(model):
        raise Rejected("invalid model")
    route = "/v1/responses" if responses is not None else "/v1/chat/completions"

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def handle(self):
            self.connection.settimeout(CLIENT_IDLE)
            self.parse_expires = time.monotonic() + PARSE_TIMEOUT
            self.parse_timer = threading.Timer(PARSE_TIMEOUT, self.expire_parsing)
            self.parse_timer.daemon = True
            self.parse_timer.start()
            try:
                self.handle_one_request()
            finally:
                self.parse_timer.cancel()

        def expire_parsing(self):
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        def finish_parsing(self):
            self.parse_timer.cancel()
            self.parse_timer.join()
            if time.monotonic() >= self.parse_expires:
                raise TimeoutError("request parsing deadline expired")
            self.connection.settimeout(TIMEOUT)

        def reply(self, status, body=b""):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            operation = None
            outcome, usage = "failed", UNKNOWN_USAGE
            try:
                if task is not None and not task.allows(self.headers.get_all("Authorization", [])):
                    self.close_connection = True
                    self.reply(401, b'{"error":"task authentication required"}')
                    return
                if self.path != route:
                    raise Rejected("unexpected path")
                raw = read_body(self)
                if responses is None:
                    request = parse_request(raw, clamp=task is None)
                    tokens = request["max_tokens"]
                else:
                    request = responses["parse"](raw, model, MAX_TOKENS)
                    tokens = request["max_output_tokens"]
                self.finish_parsing()
                if task is not None:
                    operation = task.reserve(len(raw), tokens)
                    if operation is None:
                        self.close_connection = True
                        self.reply(429, b'{"error":"task budget exhausted"}')
                        return
                if request.get("stream") is True:
                    if responses is not None:
                        outcome = "uncertain"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.end_headers()

                    def sink(data):
                        self.wfile.write(data)
                        self.wfile.flush()

                    try:
                        outcome, usage = complete_streaming(
                            port, model, request, sink, self.connection, require_done=task is not None,
                            responses=responses,
                        )
                    except (Rejected, ValueError, OSError, http.client.HTTPException, RecursionError) as exc:
                        print(f"rejected: {type(exc).__name__}", file=sys.stderr, flush=True)
                        try:
                            message = (b'event: error\ndata: {"type":"error","code":"gateway_error",'
                                       b'"message":"Responses stream incomplete"}\n\n'
                                       if responses is not None else
                                       b'data: {"error":"local gateway rejected the request"}\n\n')
                            self.wfile.write(message)
                            self.wfile.flush()
                        except OSError:
                            pass
                        self.close_connection = True
                        return
                else:
                    content_type, body, usage = complete(port, model, request)
                    outcome = "complete"
                    if operation is not None and task.ledger is not None:
                        task.ledger.finish(operation, outcome, usage)
                        operation = None
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
            except (Rejected, ValueError, OSError, sqlite3.Error, http.client.HTTPException, RecursionError) as exc:
                print(f"rejected: {type(exc).__name__}", file=sys.stderr, flush=True)
                try:
                    self.reply(502, b'{"error":"local gateway rejected the request"}')
                except OSError:
                    pass
            finally:
                self.close_connection = True
                if operation is not None and task.ledger is not None:
                    try:
                        task.ledger.finish(operation, outcome, usage)
                    except (sqlite3.Error, ValueError, OSError):
                        print("task ledger outcome unknown; reservation retained", file=sys.stderr)

        def do_HEAD(self):
            self.close_connection = True
            if self.path != route or task is None or task.ledger is None:
                self.reply(405)
            elif not task.allows(self.headers.get_all("Authorization", [])):
                self.reply(401)
            else:
                self.reply(204)

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

        def _overloaded(self, request):
            body = b'{"error":"gateway concurrency limit reached"}'
            try:
                # Drain briefly before closing so clients can receive the response.
                expires = time.monotonic() + 0.05

                def receive():
                    remaining = expires - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    request.settimeout(remaining)
                    return request.recv(4096)

                head = b""
                while b"\r\n\r\n" not in head and len(head) < 8192:
                    chunk = receive()
                    if not chunk:
                        break
                    head += chunk
                headers, _, payload = head.partition(b"\r\n\r\n")
                length = 0
                for line in headers.split(b"\r\n")[1:]:
                    if line.lower().startswith(b"content-length:"):
                        length = int(line.split(b":", 1)[1].strip() or b"0")
                while len(payload) < min(length, MAX_REQUEST):
                    chunk = receive()
                    if not chunk:
                        break
                    payload += chunk
                request.settimeout(0.05)
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n\r\n" + body
                )
            except (OSError, ValueError):
                pass
            finally:
                try:
                    request.close()
                except OSError:
                    pass

        def process_request(self, request, client_address):
            # Reject before creating a worker thread to prevent an unbounded queue.
            if not self._concurrency.acquire(blocking=False):
                self._overloaded(request)
                return
            try:
                super().process_request(request, client_address)
            except Exception:
                self._concurrency.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                self._concurrency.release()

    with _BoundedThreadingHTTPServer(("127.0.0.1", listen), Handler) as server:
        server.daemon_threads = True
        print(f"LISTEN {server.server_port}", flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Bounded local inference over loopback.")
    parser.add_argument("--port", type=int, required=True, help="IPv4 loopback endpoint port")
    parser.add_argument("--model", required=True, help="Exact model identifier")
    parser.add_argument("--listen", type=int, metavar="PORT",
                        help="Serve a local OpenAI-compatible endpoint (0 selects a port)")
    parser.add_argument("--task-budget", type=int, nargs=3, metavar=("REQUESTS", "INPUT_BYTES", "OUTPUT_TOKENS"),
                        help="Cumulative budget for an authenticated listener (CLI_OPEN_GATEWAY_TASK_TOKEN)")
    parser.add_argument("--task-seconds", type=int, metavar="SECONDS",
                        help="Maximum lifetime of the authenticated listener (1–300, default 120)")
    parser.add_argument("--task-state", type=Path, help="Private SQLite task ledger")
    parser.add_argument("--task-id", help="Verifiable persistent task identity")
    parser.add_argument("--task-owner", nargs=2, metavar=("SESSION", "WORKSPACE"),
                        help="Bind a persistent task to one native session and workspace; rotate credentials on restart")
    parser.add_argument("--create-task", action="store_true", help="Create a new persistent budget")
    parser.add_argument("--responses", action="store_true", help="Enable only Responses SSE on loopback")
    args = parser.parse_args()
    if not hasattr(signal, "SIGALRM"):
        print("The local gateway is unqualified in this environment.", file=sys.stderr)
        return 2
    try:
        task = None
        persistent = args.task_state is not None
        raw_binding = os.environ.get("CLI_OPEN_GATEWAY_TASK_BINDING")
        if raw_binding is not None and (not args.task_owner or not persistent or len(raw_binding) > 8192):
            raise Rejected("invalid supervised binding profile")
        binding = load_json(raw_binding) if raw_binding is not None else None
        if raw_binding is not None and not isinstance(binding, dict):
            raise Rejected("invalid supervised task binding")
        if (persistent != (args.task_id is not None) or (args.create_task or args.task_owner) and not persistent
                or persistent and args.task_budget is None):
            raise Rejected("incomplete task state configuration")
        if args.responses and not persistent:
            raise Rejected("Responses requires a persistent authenticated task")
        responses = runpy.run_path(str(Path(__file__).with_name("responses.py"))) if args.responses else None
        seconds = 120 if args.task_seconds is None else args.task_seconds
        if args.task_seconds is not None and (args.task_budget is None or not 1 <= seconds <= 300):
            raise Rejected("invalid task deadline")
        if args.task_budget is not None:
            if args.listen is None:
                raise Rejected("task profile requires an HTTP listener")
            task = TaskBudget(os.environ.get("CLI_OPEN_GATEWAY_TASK_TOKEN", ""), *args.task_budget)
        if args.listen is not None:
            if not 0 <= args.listen <= 65535:
                raise Rejected("invalid listen port")
            if task is None:
                serve(args.listen, args.port, args.model)
            else:
                try:
                    if persistent:
                        ledger_type = runpy.run_path(str(Path(__file__).with_name("task_ledger.py")))["Ledger"]
                        ledger_model = args.model + "|responses" if args.responses else args.model
                        with ledger_type.open(args.task_state, args.task_id, (*args.task_budget, ledger_model, args.port),
                                              seconds, create=args.create_task, owner=args.task_owner,
                                              credential=task.authorization, binding=binding) as ledger:
                            task.ledger = ledger
                            with deadline(max(0.001, ledger.expires - time.time())):
                                serve(args.listen, args.port, args.model, task, responses)
                    else:
                        with deadline(seconds):
                            serve(args.listen, args.port, args.model, task)
                except TimeoutError:
                    print("Task deadline expired.", file=sys.stderr)
                    return 124
            return 0
        with deadline():
            request = read_request(sys.stdin.buffer)
            _, report, _ = complete(args.port, args.model, request, stream=False)
    except (Rejected, ValueError, OSError, sqlite3.Error, http.client.HTTPException, RecursionError):
        print("Local request rejected or failed. No fallback connection was attempted.", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
