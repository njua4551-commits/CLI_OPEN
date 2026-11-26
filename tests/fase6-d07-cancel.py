"""Qualify upstream cancellation against a stalled synthetic SSE server."""
from contextlib import closing
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import runpy
import socket
import threading

FIXTURE = runpy.run_path(str(Path(__file__).with_name("fase6-concurrencia.py")))


def main():
    streaming = threading.Event()
    disconnected = threading.Event()

    class Upstream(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.flush()
            streaming.set()
            self.connection.settimeout(8)
            try:
                if not self.rfile.read(1):
                    disconnected.set()
            except TimeoutError:
                pass

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        gateway = None
        try:
            gateway, port = FIXTURE["start_gateway"](server.server_port, 1, 5)
            with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=3)) as client:
                client.request("POST", "/v1/chat/completions",
                               json.dumps({**FIXTURE["REQUEST"], "stream": True}))
                assert streaming.wait(3), "synthetic upstream did not start"
                client.sock.shutdown(socket.SHUT_RDWR)
            if disconnected.wait(1):
                print("PASS D07: downstream cancellation closed the stalled upstream within 1 s")
                return 0
            assert disconnected.wait(6), "gateway did not close the upstream after its timeout"
            print("FAIL D07: upstream outlived the 1 s cancellation limit and closed at socket timeout")
            return 1
        finally:
            if gateway is not None:
                gateway.terminate()
                gateway.wait(timeout=5)
            server.shutdown()
            thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
