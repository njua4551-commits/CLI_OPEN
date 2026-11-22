"""Exercise the local gateway against a synthetic HTTP server."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading

GATEWAY = Path(__file__).resolve().parents[1] / "implementacion" / "gateway"
MODEL = "test-model"
REQUEST = {"messages": [{"role": "user", "content": "Synthetic fixture"}], "max_tokens": 16}


def main():
    received = []
    control = {"status": 200, "model": MODEL, "cost": 0, "oversize": False}
    class Fixture(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append((self.path, body, self.headers.get("Authorization")))
            payload = json.dumps({
                "model": control["model"],
                "choices": [{"message": {"tool_calls": [{"type": "function", "function": {"name": "fixture"}}]}}],
                "usage": {"cost": control["cost"]},
            }).encode() if not control["oversize"] else b" " * 65537
            self.send_response(control["status"])
            self.send_header("Content-Length", str(len(payload)))
            if control["status"] == 302:
                self.send_header("Location", "/alternate")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    with HTTPServer(("127.0.0.1", 0), Fixture) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port

        def invoke(request, *options):
            return subprocess.run([
                sys.executable, "-I", "-B", str(GATEWAY), "--port", str(port), "--model", MODEL, *options,
            ], input=json.dumps(request).encode(), capture_output=True, check=False, timeout=15)

        try:
            result = invoke({
                **REQUEST, "tools": [{"type": "function", "function": {"name": "fixture", "parameters": {}}}],
            })
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)["choices"][0]["message"]["tool_calls"]
            path, body, credential = received[-1]
            assert (path, body["model"], body["stream"], credential) == ("/v1/chat/completions", MODEL, False, None)
            assert invoke({**REQUEST, "base_url": "https://invalid.example"}).returncode == 1
            assert invoke({**REQUEST, "max_tokens": 513}).returncode == 1
            assert invoke(REQUEST, "--url", "https://invalid.example").returncode == 2
            assert len(received) == 1

            control["status"] = 302
            assert invoke(REQUEST).returncode == 1
            assert len(received) == 2 and received[-1][0] == "/v1/chat/completions"
            control.update(status=200, cost=0.001)
            assert invoke(REQUEST).returncode == 1
            control.update(cost=0, model="unexpected")
            assert invoke(REQUEST).returncode == 1
            control.update(model=MODEL, oversize=True)
            assert invoke(REQUEST).returncode == 1
            assert len(received) == 5
        finally:
            server.shutdown()
            thread.join(timeout=2)
    assert invoke(REQUEST).returncode == 1
    assert len(received) == 5
    print("PASS local tool call, limits, destination, cost, redirect, endpoint failure and no fallback")


if __name__ == "__main__":
    main()
