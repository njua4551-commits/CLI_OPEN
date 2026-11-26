"""Test the authenticated task listener with a synthetic provider."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading

GATEWAY = Path(__file__).resolve().parents[1] / "implementacion/gateway"
TOKEN = secrets.token_urlsafe(32)
PRIVATE_FIELD = "synthetic_private_request_field"
REQUEST = json.dumps({"messages": [{"role": "user", "content": "fixture"}],
                      "model": "fixture", "max_tokens": 8}).encode()


@contextmanager
def listener(upstream, *budget, token=TOKEN, seconds=120, expires=False, extra=(), with_process=False,
             rejected=False):
    env = {**os.environ, "CLI_OPEN_GATEWAY_TASK_TOKEN": token, "CLI_OPEN_GATEWAY_TIMEOUT_SECONDS": "10"}
    command = [sys.executable, "-I", "-B", str(GATEWAY), "--port", str(upstream),
               "--listen", "0", "--model", "fixture", "--task-budget", *map(str, budget),
               "--task-seconds", str(seconds)]
    command.extend(extra)
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            line = process.stdout.readline()
            if not token or rejected:
                assert process.wait(timeout=5) == 1 and not line
                yield None
            else:
                assert line.startswith(b"LISTEN "), line
                port = int(line.split()[1])
                yield (port, process) if with_process else port
                if expires:
                    assert process.wait(timeout=5) == 124
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            logs = process.stderr.read()
            assert not token or token.encode() not in logs
            assert PRIVATE_FIELD.encode() not in logs


def request(port, token=TOKEN, body=REQUEST, path="/v1/chat/completions"):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        headers = {"Authorization": "Bearer " + token} if token else {}
        connection.request("POST", path, body, headers)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def main():
    traffic = []
    started = threading.Event()
    disconnected = threading.Event()

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            traffic.append((self.path, self.headers.get("Authorization")))
            if body["stream"]:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                scenario = body["messages"][0]["content"]
                if scenario in ("partial", "complete"):
                    self.wfile.write(b'data: {"model":"fixture","choices":[]}\n\n')
                    if scenario == "complete":
                        self.wfile.write(b"data: [DONE]\n\n")
                    return
                self.wfile.flush()
                started.set()
                self.connection.settimeout(6)
                try:
                    if not self.rfile.read(1):
                        disconnected.set()
                except TimeoutError:
                    pass
                return
            # Failed upstream calls must keep their reservation.
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as provider:
        thread = threading.Thread(target=provider.serve_forever, daemon=True)
        thread.start()
        try:
            upstream = provider.server_port
            with listener(upstream, 1, 1000, 64, token=""):
                pass
            with listener(upstream, 1, 1000, 64) as port:
                assert request(port, token="") == 401
                assert request(port, token="wrong") == 401
                assert request(port, path="/other") == 502
                assert request(port, body=b"[]") == 502
                assert request(port, body=json.dumps({PRIVATE_FIELD: 1}).encode()) == 502
                assert not traffic
                with ThreadPoolExecutor(max_workers=2) as pool:
                    statuses = list(pool.map(lambda _: request(port), range(2)))
                assert sorted(statuses) == [429, 502], statuses
                assert request(port) == 429
            assert traffic == [("/v1/chat/completions", None)], traffic

            with listener(upstream, 4, len(REQUEST), 64) as port:
                assert request(port) == 502
                assert request(port) == 429
            with listener(upstream, 4, 1000, 8) as port:
                assert request(port) == 502
                assert request(port) == 429
            assert traffic == [("/v1/chat/completions", None)] * 3, traffic
            stream = json.loads(REQUEST)
            stream["stream"] = True
            headers = {"Authorization": "Bearer " + TOKEN}

            with listener(upstream, 1, 1000, 64) as port:
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream), headers)
                    assert started.wait(3)
                    client.sock.shutdown(socket.SHUT_RDWR)
                assert disconnected.wait(1), "cancelled task left upstream open"
                assert request(port) == 429, "cancelled task returned its reservation"

            started.clear()
            disconnected.clear()
            with listener(upstream, 1, 1000, 64, seconds=2, expires=True) as port:
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream), headers)
                    assert started.wait(1)
                    response = client.getresponse()
                    assert response.status == 200
                    assert not response.read()
                assert disconnected.wait(1), "expired task left upstream open"

            stream["messages"][0]["content"] = "partial"
            with listener(upstream, 1, 1000, 64) as port:
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream), headers)
                    response = client.getresponse()
                    assert b'"error"' in response.read(), "truncated SSE was accepted"
                assert request(port) == 429
            stream["messages"][0]["content"] = "complete"
            replacement = secrets.token_urlsafe(32)
            with listener(upstream, 1, 1000, 64, token=replacement) as port:
                assert request(port) == 401
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream),
                                   {"Authorization": "Bearer " + replacement})
                    response = client.getresponse()
                    assert b"data: [DONE]" in response.read()
                assert request(port, token=replacement) == 429
            assert traffic == [("/v1/chat/completions", None)] * 7, traffic
        finally:
            provider.shutdown()
            thread.join(timeout=2)
    print("PASS D07 local authentication, reservations, cancellation, deadline and SSE completion")


if __name__ == "__main__":
    main()
