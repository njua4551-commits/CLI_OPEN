"""Exercise the production read task with a deterministic loopback provider."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
from pathlib import Path
import sqlite3
import runpy
import signal
import subprocess
import sys
import tempfile
from threading import Event, Thread
import time

ROOT = Path(__file__).resolve().parents[1]
MARKER = "isolated-native-result"


class Provider(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.path == "/v1/chat/completions"
        assert self.headers.get("Authorization") is None
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        messages = body["messages"]
        last_user = max((index for index, entry in enumerate(messages) if entry["role"] == "user"), default=-1)
        results = [entry for entry in messages[last_user + 1:] if entry["role"] == "tool"]
        if results:
            assert MARKER in results[0]["content"]
            self.server.observed = True
            if self.server.stall:
                self.server.at_result.set()
                self.server.release.wait(10)
                if self.server.stall != "pause":
                    return
            delta, finish = {"content": "Read confirmed."}, "stop"
        elif body.get("tools"):
            delta, finish = {"tool_calls": [{"index": 0, "id": "call_read", "type": "function",
                "function": {"name": "read", "arguments": '{"path":"input.txt"}'}}]}, "tool_calls"
            delta["tool_calls"][0]["id"] += str(last_user)
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
                       "--port", str(server.server_port), "--model", "fixture", "--seconds", "75"]
            token = secrets.token_urlsafe(32)
            env = {**os.environ, "CLI_OPEN_TASK_RECOVERY_TOKEN": token}
            report = json.loads(subprocess.check_output(command, timeout=55, env=env))
            assert report["task"] == "read_fixture" and report["reads"] == 1
            assert MARKER in report["result"] and server.observed
            with sqlite3.connect(state / "task.sqlite") as db:
                session, workspace, raw_binding = db.execute("SELECT * FROM task_owner").fetchone()
                assert (session, workspace) == (report["session"], report["workspace"])
                assert db.execute("PRAGMA user_version").fetchone() == (2,)
                binding = json.loads(raw_binding)
                assert binding["source"] == str(source)
                assert binding["scope"] == "read:input.txt"
                assert binding["native_database"] == [
                    str(state / "native.sqlite"), (state / "native.sqlite").stat().st_dev,
                    (state / "native.sqlite").stat().st_ino,
                ]
                assert len(binding["policy"]) == 64
                assert db.execute("SELECT expires FROM task").fetchone() == (report["expires"],)
                count, = db.execute("SELECT count(*) FROM operation WHERE status='complete'").fetchone()
                assert 2 <= count < 8
                original_operations = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                original_task = db.execute("SELECT * FROM task").fetchall()
                original_credentials = db.execute("SELECT count(*) FROM listener_credential").fetchone()
            recover = [*command, "--recover"]
            wrong_task = recover.copy()
            wrong_task[wrong_task.index("read_fixture")] = "wrong_task"
            wrong_file = recover.copy()
            other = root / "other.txt"
            other.write_bytes(source.read_bytes())
            wrong_file[wrong_file.index(str(source))] = str(other)
            for denied, auth in ((wrong_task, env), (wrong_file, env),
                                 (recover, {**env, "CLI_OPEN_TASK_RECOVERY_TOKEN": secrets.token_urlsafe(32)})):
                rejected = subprocess.run(denied, capture_output=True, timeout=5, env=auth)
                assert rejected.returncode == 1 and not rejected.stdout
            with sqlite3.connect(state / "task.sqlite") as db:
                assert db.execute("SELECT count(*) FROM listener_credential").fetchone() == original_credentials
                assert db.execute("SELECT * FROM operation ORDER BY id").fetchall() == original_operations
            native = state / "native.sqlite"
            with sqlite3.connect(native) as db:
                assert db.execute("SELECT permission FROM session_v2").fetchall() == [(None,)]
                db.execute("UPDATE session_v2 SET permission = ?",
                           (json.dumps([{"action": "read", "resource": "input.txt", "effect": "deny"}]),))
            revoked = subprocess.run(recover, capture_output=True, timeout=5, env=env)
            assert revoked.returncode == 1 and not revoked.stdout
            with sqlite3.connect(native) as db:
                db.execute("UPDATE session_v2 SET permission = NULL, workspace_id = 'wrk_fixture_wrong'")
            wrong_workspace = subprocess.run(recover, capture_output=True, timeout=5, env=env)
            assert wrong_workspace.returncode == 1 and not wrong_workspace.stdout
            with sqlite3.connect(native) as db:
                db.execute("UPDATE session_v2 SET id = 'ses_fixture_wrong', workspace_id = ?", (report["workspace"],))
            wrong_session = subprocess.run(recover, capture_output=True, timeout=5, env=env)
            assert wrong_session.returncode == 1 and not wrong_session.stdout
            with sqlite3.connect(native) as db:
                db.execute("UPDATE session_v2 SET id = ?", (report["session"],))
            replacement = state / "different-native.sqlite"
            original_native = state / "original-native.sqlite"
            replacement.write_bytes(native.read_bytes())
            replacement.chmod(0o600)
            native.rename(original_native)
            replacement.rename(native)
            try:
                changed = subprocess.run(recover, capture_output=True, timeout=5, env=env)
                assert changed.returncode == 1 and not changed.stdout
            finally:
                original_native.replace(native)
            resumed = json.loads(subprocess.check_output(recover, timeout=55, env=env))
            assert all(resumed[key] == report[key] for key in ("task", "session", "workspace", "expires"))
            assert resumed["reads"] == 1 and MARKER in resumed["result"]
            with sqlite3.connect(state / "task.sqlite") as db:
                updated = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                assert 2 <= len(updated) - len(original_operations)
                assert updated[:len(original_operations)] == original_operations
                assert db.execute("SELECT * FROM task").fetchall() == original_task
                assert db.execute("SELECT count(*) FROM listener_credential").fetchone() == (original_credentials[0] + 1,)
            missing = recover.copy()
            missing[missing.index(str(state))] = str(root / "missing-state")
            missing_result = subprocess.run(missing, capture_output=True, timeout=5, env=env)
            assert missing_result.returncode == 1 and not (root / "missing-state").exists()

            for name, content in (("corrupt-state", b"synthetic invalid SQLite"),
                                  ("incomplete-init", b"")):
                invalid_state = root / name
                invalid_state.mkdir(mode=0o700)
                invalid_ledger = invalid_state / "task.sqlite"
                invalid_ledger.write_bytes(content)
                invalid_ledger.chmod(0o600)
                invalid = recover.copy()
                invalid[invalid.index(str(state))] = str(invalid_state)
                result = subprocess.run(invalid, capture_output=True, timeout=5, env=env)
                assert result.returncode == 1 and not result.stdout
                assert invalid_ledger.read_bytes() == content

            with sqlite3.connect(state / "task.sqlite") as db:
                limit, = db.execute("SELECT request_limit FROM task").fetchone()
                db.executemany("INSERT INTO operation (input_bytes, output_limit, status) VALUES (1, 1, 'complete')",
                               [()] * (limit - len(updated)))
                exhausted_operations = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                assert len(exhausted_operations) == limit
            exhausted = subprocess.run(recover, capture_output=True, timeout=5, env=env)
            assert exhausted.returncode == 1 and not exhausted.stdout
            with sqlite3.connect(state / "task.sqlite") as db:
                assert db.execute("SELECT * FROM operation ORDER BY id").fetchall() == exhausted_operations
                assert db.execute("SELECT count(*) FROM listener_credential").fetchone() == (original_credentials[0] + 1,)
                db.execute("DELETE FROM operation WHERE id > ?", (updated[-1][0],))
                db.execute("UPDATE task SET started = started - 120, expires = expires - 120")
                expired_task = db.execute("SELECT * FROM task").fetchone()
            expired = subprocess.run(recover, capture_output=True, timeout=5, env=env)
            assert expired.returncode == 1 and not expired.stdout
            with sqlite3.connect(state / "task.sqlite") as db:
                assert db.execute("SELECT * FROM task").fetchone() == expired_task
                assert db.execute("SELECT * FROM operation ORDER BY id").fetchall() == updated
                assert db.execute("SELECT count(*) FROM listener_credential").fetchone() == (original_credentials[0] + 1,)

            duplicate = subprocess.run(command, capture_output=True, timeout=5)
            assert duplicate.returncode == 1 and not duplicate.stdout
            assert source.read_text() == MARKER + "\n"

            server.stall = True
            interrupted = root / "interrupted"
            command[command.index(str(state))] = str(interrupted)
            process_helpers = runpy.run_path(str(ROOT / "tests/fase6-d07-restart.py"))
            with subprocess.Popen(command, stdout=subprocess.PIPE, env=env) as supervisor:
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
                assert subprocess.run([*command, "--recover"], capture_output=True,
                                      timeout=5, env=env).returncode == 1
                assert db.execute("SELECT * FROM operation ORDER BY id").fetchall() == reserved

            server.at_result.clear()
            server.release.clear()
            server.stall = "pause"
            paused = root / "completed-gateway-interruption"
            command[command.index(str(interrupted))] = str(paused)
            with subprocess.Popen(command, stdout=subprocess.PIPE, env=env) as supervisor:
                try:
                    assert server.at_result.wait(30)
                    tracked = process_helpers["descendants"](supervisor.pid)
                    native_pids = [pid for pid in tracked
                                   if b"/task_run.ts" in Path(f"/proc/{pid}/cmdline").read_bytes()]
                    assert len(native_pids) == 1, native_pids
                    host_pid = native_pids[0]
                    process = os.pidfd_open(host_pid)
                    try:
                        assert process_helpers["processes"]()[host_pid][1] == tracked[host_pid]
                        signal.pidfd_send_signal(process, signal.SIGSTOP)
                    finally:
                        os.close(process)

                    def stopped():
                        return process_helpers["processes"]().get(host_pid, (None, None, None))[2] in {"T", "t"}

                    process_helpers["wait_until"](stopped, 3, "native host did not suspend")
                    server.release.set()

                    def gateway_settled():
                        with sqlite3.connect(paused / "task.sqlite") as db:
                            return not db.execute("SELECT 1 FROM operation WHERE status != 'complete'").fetchone()

                    process_helpers["wait_until"](gateway_settled, 5, "gateway did not record completion")
                    with sqlite3.connect(paused / "native.sqlite") as db:
                        claim, = db.execute("SELECT time_suspended FROM session_v2").fetchone()
                        assert claim is not None
                    with sqlite3.connect(paused / "task.sqlite") as db:
                        task_row = db.execute("SELECT * FROM task").fetchone()
                        before = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                        native_ids = db.execute("SELECT session, workspace FROM task_owner").fetchone()
                        listener_count = db.execute("SELECT count(*) FROM listener_credential").fetchone()
                    competitor = subprocess.run([*command, "--recover"], capture_output=True, timeout=5, env=env)
                    assert competitor.returncode == 1 and not competitor.stdout
                    with sqlite3.connect(paused / "task.sqlite") as db:
                        assert db.execute("SELECT count(*) FROM listener_credential").fetchone() == listener_count
                    supervisor.send_signal(signal.SIGTERM)
                    assert supervisor.wait(timeout=5) == 143
                    assert not supervisor.stdout.read()
                finally:
                    if supervisor.poll() is None:
                        supervisor.kill()
                    server.release.set()
            process_helpers["wait_until"](cleaned_up, 5, "paused native host survived cancellation")
            server.stall = False
            started = time.monotonic()
            restart = json.loads(subprocess.check_output([*command, "--recover"], timeout=55, env=env))
            print(json.dumps({"production_read_restart_seconds": round(time.monotonic() - started, 3)}))
            assert (restart["session"], restart["workspace"]) == native_ids
            assert restart["expires"] == task_row[-2] and MARKER in restart["result"]
            with sqlite3.connect(paused / "native.sqlite") as db:
                claim, outcome = db.execute("SELECT time_suspended, idle_outcome FROM session_v2").fetchone()
                assert claim is None and outcome == "succeeded"
            with sqlite3.connect(paused / "task.sqlite") as db:
                assert db.execute("SELECT * FROM task").fetchone() == task_row
                after = db.execute("SELECT * FROM operation ORDER BY id").fetchall()
                assert after[:len(before)] == before and len(after) > len(before)
        finally:
            server.shutdown()
            thread.join()
    print("PASS production task: owned ledger, authenticated gateway, native session and isolated read; terminal reopen, suspended read restart and uncertain denial")


if __name__ == "__main__":
    main()
