"""One bounded, offline-profile request to an OpenAI-compatible loopback endpoint."""
import argparse
from contextlib import contextmanager
import http.client
import json
import re
import signal
import sys

MAX_REQUEST = 16_384
MAX_RESPONSE = 65_536
MAX_TOKENS = 512
TIMEOUT = 10
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")


class Rejected(ValueError):
    pass


def read_request(source):
    data = source.read(MAX_REQUEST + 1)
    if len(data) > MAX_REQUEST:
        raise Rejected("request too large")
    request = json.loads(data)
    if not isinstance(request, dict) or request.keys() - {"messages", "max_tokens", "tools"}:
        raise Rejected("unexpected request fields")
    messages = request.get("messages")
    limit = request.get("max_tokens")
    if type(limit) is not int or not 1 <= limit <= MAX_TOKENS:
        raise Rejected("invalid token limit")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 12:
        raise Rejected("invalid message list")
    for message in messages:
        if (
            not isinstance(message, dict) or set(message) != {"role", "content"}
            or message["role"] not in ("system", "user", "assistant")
            or not isinstance(message["content"], str)
        ):
            raise Rejected("invalid message")
    if "tools" in request:
        tools = request["tools"]
        if not isinstance(tools, list) or not 1 <= len(tools) <= 8:
            raise Rejected("invalid tool list")
        for tool in tools:
            if (
                not isinstance(tool, dict) or set(tool) != {"type", "function"}
                or tool["type"] != "function" or not isinstance(tool["function"], dict)
            ):
                raise Rejected("only function definitions are allowed")
    return request


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


def complete(port, model, request):
    if not 1 <= port <= 65535 or not MODEL_NAME.fullmatch(model):
        raise Rejected("invalid loopback port or model")
    payload = json.dumps({**request, "model": model, "stream": False}, allow_nan=False).encode("ascii")
    if len(payload) > MAX_REQUEST:
        raise Rejected("encoded request too large")
    # Fixed host/path, direct connection, no proxy, redirects, retries or provider fallback.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        with deadline():
            connection.request("POST", "/v1/chat/completions", payload, {"Content-Type": "application/json"})
            with connection.getresponse() as response:
                if response.status != 200:
                    raise Rejected("local endpoint rejected the request")
                data = response.read(MAX_RESPONSE + 1)
                if len(data) > MAX_RESPONSE:
                    raise Rejected("response too large")
    finally:
        connection.close()
    report = json.loads(data)
    if not isinstance(report, dict) or report.get("model") != model or not isinstance(report.get("choices"), list):
        raise Rejected("invalid response or unexpected model")
    usage = report.get("usage", {})
    if not isinstance(usage, dict) or ("cost" in usage and (
        type(usage["cost"]) not in (int, float) or usage["cost"] != 0
    )):
        raise Rejected("unexpected cost in local response")
    return report


def main():
    parser = argparse.ArgumentParser(description="Consulta local y acotada. Sin destinos remotos.")
    parser.add_argument("--port", type=int, required=True, help="Puerto del endpoint IPv4 de loopback")
    parser.add_argument("--model", required=True, help="Identificador exacto del modelo")
    args = parser.parse_args()
    if not hasattr(signal, "SIGALRM"):
        print("Gateway local sin calificar en este entorno.", file=sys.stderr)
        return 2
    try:
        request = read_request(sys.stdin.buffer)
        report = json.dumps(complete(args.port, args.model, request), ensure_ascii=True, allow_nan=False)
    except (ValueError, OSError, http.client.HTTPException, RecursionError):
        print("Consulta local rechazada o fallida. Sin conexión alternativa.", file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
