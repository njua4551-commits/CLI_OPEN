"""Test the authenticated task listener with a synthetic provider."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading

GATEWAY = Path(__file__).resolve().parents[1] / "implementacion/gateway"
TOKEN = secrets.token_urlsafe(32)
REQUEST = json.dumps({"messages": [{"role": "user", "content": "fixture"}],
                      "model": "fixture", "max_tokens": 8}).encode()


@contextmanager
def listener(upstream, *budget, token=TOKEN):
    env = {**os.environ, "CLI_OPEN_GATEWAY_TASK_TOKEN": token}
    command = [sys.executable, "-I", "-B", str(GATEWAY), "--port", str(upstream),
               "--listen", "0", "--model", "fixture", "--task-budget", *map(str, budget)]
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            line = process.stdout.readline()
            if not token:
                assert process.wait(timeout=5) == 1 and not line
                yield None
            else:
                assert line.startswith(b"LISTEN "), line
                yield int(line.split()[1])
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


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

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            traffic.append((self.path, self.headers.get("Authorization")))
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
        finally:
            provider.shutdown()
            thread.join(timeout=2)
    print("PASS D07 local authentication, isolated budgets, atomic reservation, no credential forwarding")


if __name__ == "__main__":
    main()
