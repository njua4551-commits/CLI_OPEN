"""Exercise the production read task with a deterministic loopback provider."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import runpy
import signal
import subprocess
import sys
import tempfile
from threading import Event, Thread

ROOT = Path(__file__).resolve().parents[1]
MARKER = "isolated-native-result"


class Provider(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.path == "/v1/chat/completions"
        assert self.headers.get("Authorization") is None
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        results = [entry for entry in body["messages"] if entry["role"] == "tool"]
        if results:
            assert MARKER in results[0]["content"]
            self.server.observed = True
            if self.server.stall:
                self.server.at_result.set()
                self.server.release.wait(10)
                return
            delta, finish = {"content": "Read confirmed."}, "stop"
        elif body.get("tools"):
            delta, finish = {"tool_calls": [{"index": 0, "id": "call_read", "type": "function",
                "function": {"name": "read", "arguments": '{"path":"input.txt"}'}}]}, "tool_calls"
        else:
            delta, finish = {"content": "Fixture title"}, "stop"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for payload, reason in (({"role": "assistant", **delta}, None), ({}, finish)):
            chunk = dict(id="fixture", object="chat.completion.chunk", model="fixture", created=1,
                         choices=[dict(index=0, delta=payload, finish_reason=reason)])
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, *_):
        pass


def main():
    with tempfile.TemporaryDirectory() as directory, ThreadingHTTPServer(("127.0.0.1", 0), Provider) as server:
        server.observed = False
        server.stall = False
        server.at_result, server.release = Event(), Event()
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            root = Path(directory)
            source = root / "source.txt"
            source.write_text(MARKER + "\n")
            state = root / "private"
            command = [sys.executable, "-I", "-B", str(ROOT / "implementacion/supervisor"), "run-read-task",
                       str(source), "--state", str(state), "--identity", "read_fixture",
                       "--port", str(server.server_port), "--model", "fixture"]
            report = json.loads(subprocess.check_output(command, timeout=55))
            assert report["task"] == "read_fixture" and report["reads"] == 1
            assert MARKER in report["result"] and server.observed
            with sqlite3.connect(state / "task.sqlite") as db:
                assert db.execute("SELECT * FROM task_owner").fetchone() == (report["session"], report["workspace"])
                assert db.execute("SELECT expires FROM task").fetchone() == (report["expires"],)
                count, = db.execute("SELECT count(*) FROM operation WHERE status='complete'").fetchone()
                assert 2 <= count <= 8
            duplicate = subprocess.run(command, capture_output=True, timeout=5)
            assert duplicate.returncode == 1 and not duplicate.stdout
            assert source.read_text() == MARKER + "\n"

            server.stall = True
            interrupted = root / "interrupted"
            command[command.index(str(state))] = str(interrupted)
            process_helpers = runpy.run_path(str(ROOT / "tests/fase6-d07-restart.py"))
            with subprocess.Popen(command, stdout=subprocess.PIPE) as supervisor:
                try:
                    assert server.at_result.wait(30)
                    tracked = process_helpers["descendants"](supervisor.pid)
                    assert len(tracked) >= 2
                    with sqlite3.connect(interrupted / "task.sqlite") as db:
                        pending = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                        assert pending[-1][3] == "reserved"
                    supervisor.send_signal(signal.SIGTERM)
                    assert supervisor.wait(timeout=5) == 143
                    assert not supervisor.stdout.read()
                finally:
                    if supervisor.poll() is None:
                        supervisor.kill()
                    server.release.set()

            def cleaned_up():
                current = process_helpers["processes"]()
                return all(pid not in current or current[pid][1] != birth or current[pid][2] == "Z"
                           for pid, birth in tracked.items())

            process_helpers["wait_until"](cleaned_up, 5, "managed child survived cancellation")
            with sqlite3.connect(interrupted / "task.sqlite") as db:
                reserved = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                assert [row[:3] for row in reserved] == [row[:3] for row in pending]
                assert reserved[-1][3] in {"reserved", "cancelled", "failed"}
                assert subprocess.run(command, capture_output=True, timeout=5).returncode == 1
                assert db.execute("SELECT * FROM operation ORDER BY id").fetchall() == reserved
        finally:
            server.shutdown()
            thread.join()
    print("PASS production task: owned ledger, authenticated gateway, native session and isolated read")


if __name__ == "__main__":
    main()
