"""Carga real de clientes HTTP contra la concurrencia acotada del gateway.

Usa http.client (no el CLI) con hilos independientes contra el listener de
loopback y un endpoint sintético que mide la concurrencia efectiva. Verifica
que el límite configurado no se excede, que todas las respuestas llegan y que
el timeout por entorno se aplica sin bloqueos ni fallback.
"""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

GATEWAY = Path(__file__).resolve().parents[1] / "implementacion" / "gateway"
MODEL = "concurrency-model"
REQUEST = {"model": MODEL, "messages": [{"role": "user", "content": "load"}], "max_tokens": 8}
DELAY = 0.10


class Fixture:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.requests = 0
        self.delay = DELAY
        self.stream = False

    def enter(self):
        with self.lock:
            self.active += 1
            self.requests += 1
            self.peak = max(self.peak, self.active)

    def leave(self):
        with self.lock:
            self.active -= 1


def chunks(model, stream):
    if not stream:
        body = json.dumps({
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "usage": {"cost": 0},
        }).encode()
        return [(body, "application/json")]
    events = []
    for index, text in enumerate(("ok", "")):
        events.append(json.dumps({
            "model": model,
            "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": "stop" if index else None}],
            "usage": {"cost": 0} if index else {},
        }))
    payload = "".join(f"data: {event}\n\n" for event in events) + "data: [DONE]\n\n"
    return [(payload.encode(), "text/event-stream")]


def serve_fixture(fixture):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            fixture.enter()
            try:
                self.rfile.read(int(self.headers["Content-Length"]))
                time.sleep(fixture.delay)
                for body, content_type in chunks(MODEL, fixture.stream):
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                    self.wfile.flush()
            except BrokenPipeError:
                pass  # The upstream timeout fixture intentionally closes its socket.
            finally:
                fixture.leave()
                self.close_connection = True

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def start_gateway(port, limit, timeout, **settings):
    env = {
        **os.environ,
        "CLI_OPEN_GATEWAY_MAX_CONCURRENCY": str(limit),
        "CLI_OPEN_GATEWAY_TIMEOUT_SECONDS": str(timeout),
        **settings,
    }
    child = subprocess.Popen([
        sys.executable, "-I", "-B", str(GATEWAY), "--port", str(port),
        "--model", MODEL, "--listen", "0",
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, text=True)
    line = child.stdout.readline().strip()
    assert line.startswith("LISTEN "), line
    return child, int(line.split()[1])


def post(port, request):
    return raw_post(port, json.dumps(request).encode())


def raw_post(port, body, **headers):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        connection.request("POST", "/v1/chat/completions", body, {
            "Content-Type": "application/json", "Connection": "close", **headers,
        })
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def load(port, request, clients):
    with ThreadPoolExecutor(max_workers=clients) as pool:
        return list(pool.map(lambda _: post(port, request), range(clients)))


def check_validation(upstream, fixture):
    child, gateway = start_gateway(upstream, 1, 5, CLI_OPEN_GATEWAY_CLIENT_IDLE_SECONDS="1",
                                   CLI_OPEN_GATEWAY_PARSE_SECONDS="2")
    try:
        before = fixture.requests
        address = ("127.0.0.1", gateway)
        with socket.create_connection(address, timeout=3) as idle:
            start = time.monotonic()
            assert idle.recv(1) == b""
            assert 0.75 < time.monotonic() - start < 1.8
        with socket.create_connection(address, timeout=3) as drip:
            start = time.monotonic()
            for char in (b"P", b"O", b"S", b"T", b" "):
                drip.sendall(char)
                time.sleep(0.43)
            assert drip.recv(1) == b""
            assert time.monotonic() - start < 2.8

        def admitted(body, **headers):
            expires = time.monotonic() + 2
            while time.monotonic() < expires:
                status, response = raw_post(gateway, body, **headers)
                if status != 503:
                    return status, response
                time.sleep(0.02)
            raise AssertionError("gateway did not release its HTTP worker slot")

        for stream in (False, True):
            for number in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
                data = json.dumps({**REQUEST, "stream": stream}).encode()
                data = data[:-1] + b',"response_format":{"nested":[' + number + b']}}'
                status, _ = admitted(data)
                assert status == 502, (stream, number, status)
        for body in (b"+1\r\nx\r\n0\r\n\r\n", b"0x1\r\nx\r\n0\r\n\r\n",
                     b"1;a=b\r\nx\r\n0\r\n\r\n", b"1\r\nx!!0\r\n\r\n",
                     b"0\r\nX-Synthetic: yes\r\n\r\n"):
            status, _ = admitted([body], **{"Transfer-Encoding": "chunked"})
            assert status == 502, (body, status)
        assert fixture.requests == before, (fixture.requests, before)
        data = json.dumps(REQUEST).encode()
        chunked = f"{len(data):x}\r\n".encode() + data + b"\r\n0\r\n\r\n"
        assert admitted([chunked], **{"Transfer-Encoding": "chunked"})[0] == 200
    finally:
        child.terminate()
        child.wait(timeout=5)


def main():
    fixture = Fixture()
    server, thread = serve_fixture(fixture)
    upstream = server.server_port
    child = None
    try:
        child, gateway = start_gateway(upstream, 2, 5)

        results = load(gateway, REQUEST, 12)
        assert len(results) == 12
        assert set(status for status, _ in results) <= {200, 503}
        successes = [body for status, body in results if status == 200]
        assert len(successes) >= 2, len(successes)
        assert all(json.loads(body)["choices"][0]["message"]["content"] == "ok" for body in successes)
        assert all(b"concurrency" in body for status, body in results if status == 503)
        assert fixture.requests == len(successes), (fixture.requests, len(successes))
        assert fixture.peak == 2, fixture.peak

        fixture.stream = True
        fixture.peak = 0
        stream_request = {**REQUEST, "stream": True}
        results = load(gateway, stream_request, 2)
        assert all(status == 200 for status, _ in results)
        assert all(b"data: [DONE]" in body for _, body in results)
        assert fixture.peak <= 2, fixture.peak
        fixture.stream = False
        child.terminate()
        child.wait(timeout=5)

        # Saturación: el exceso se rechaza con 503 sin encolar hilos.
        fixture.peak = 0
        fixture.requests = 0
        fixture.delay = 1.0
        child, gateway = start_gateway(upstream, 2, 10)
        burst = load(gateway, REQUEST, 10)
        statuses = [status for status, _ in burst]
        assert statuses.count(200) >= 2, statuses
        assert statuses.count(503) >= 1, statuses
        assert set(statuses) == {200, 503}, statuses
        for status, body in burst:
            if status == 503:
                assert b"concurrency" in body, body
            else:
                assert json.loads(body)["choices"][0]["message"]["content"] == "ok"
        assert fixture.peak == 2, fixture.peak
        assert fixture.requests == statuses.count(200), fixture.requests
        fixture.delay = 0
        assert post(gateway, REQUEST)[0] == 200
        child.terminate()
        child.wait(timeout=5)

        fixture.peak = 0
        fixture.requests = 0
        fixture.delay = 2.0
        child, gateway = start_gateway(upstream, 2, 1)
        started = time.monotonic()
        status, body = post(gateway, REQUEST)
        elapsed = time.monotonic() - started
        assert status == 502, status
        assert json.loads(body)["error"]
        assert 0.9 <= elapsed < 1.9, elapsed
        child.terminate()
        child.wait(timeout=5)
        child = None
        fixture.delay = 0
        check_validation(upstream, fixture)
        print("PASS idle clients, absolute HTTP parsing deadline, chunk framing and strict JSON")
        print("PASS fase6 concurrencia: 12+2+10 clientes HTTP reales, limite 2, 503 y timeout 1s")
    finally:
        if child is not None:
            child.kill()
            child.wait(timeout=5)
        server.shutdown()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
