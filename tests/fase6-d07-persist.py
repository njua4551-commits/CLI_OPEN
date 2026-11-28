"""Verify that loopback task reservations survive process failure and restart."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import runpy
import sqlite3
import stat
import tempfile
import threading
from unittest.mock import patch
from uuid import uuid4

FIXTURE = runpy.run_path(str(Path(__file__).with_name("fase6-d07-budget.py")))
HEADERS = {"Authorization": "Bearer " + FIXTURE["TOKEN"]}


def verify_initialization_rollback(directory):
    path = Path(directory) / "incomplete.sqlite"
    ledger = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                "implementacion/gateway/task_ledger.py"))
    with patch.object(ledger["time"], "time", side_effect=(100, 102)):
        try:
            with ledger["Ledger"].open(path, "expired", (1, 1000, 8, "fixture", 12345), 1,
                                       create=True, owner=("ses_fixture", "wrk_fixture"),
                                       credential=b"fixture"):
                raise AssertionError("expired initialization admitted")
        except ValueError as error:
            assert "expired" in str(error)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT name FROM sqlite_schema").fetchall() == []
        assert db.execute("PRAGMA user_version").fetchone() == (0,)


def main():
    with tempfile.TemporaryDirectory() as directory:
        verify_initialization_rollback(directory)
    started = threading.Event()
    disconnected = threading.Event()

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream" if message["stream"] else "application/json")
            self.end_headers()
            usage = {"prompt_tokens": 3, "completion_tokens": 2}
            if not message["stream"]:
                scenario = message["messages"][0]["content"]
                result = {"model": "fixture", "choices": []}
                if scenario != "unreported":
                    if scenario == "overrun":
                        usage["completion_tokens"] = 9
                    result["usage"] = usage
                self.wfile.write(json.dumps(result).encode())
            elif message["messages"][0]["content"] == "reported":
                event = json.dumps({"model": "fixture", "choices": [], "usage": usage})
                self.wfile.write(f"data: {event}\n\ndata: [DONE]\n\n".encode())
            else:
                self.wfile.flush()
                started.set()
                self.connection.settimeout(5)
                try:
                    if not self.rfile.read(1):
                        disconnected.set()
                except ConnectionResetError:
                    disconnected.set()
                except TimeoutError:
                    pass

        def log_message(self, *args):
            pass

    with tempfile.TemporaryDirectory() as temporary, ThreadingHTTPServer(("127.0.0.1", 0), Provider) as provider:
        thread = threading.Thread(target=provider.serve_forever, daemon=True)
        thread.start()
        path = Path(temporary) / "task.sqlite"
        state = ("--task-state", str(path), "--task-id", "fixture_task")
        settings = (provider.server_port, 3, 1000, 24)

        def operations():
            with closing(sqlite3.connect(path)) as db:
                return db.execute(
                    "SELECT status, output_limit, prompt_tokens, completion_tokens FROM operation ORDER BY id"
                ).fetchall()

        stream = json.loads(FIXTURE["REQUEST"])
        stream["stream"] = True
        try:
            with FIXTURE["listener"](*settings, extra=state, rejected=True):
                pass
            with FIXTURE["listener"](*settings, extra=(*state, "--create-task")) as port:
                assert FIXTURE["request"](port) == 200
                assert stat.S_IMODE(path.stat().st_mode) == 0o600
                with FIXTURE["listener"](*settings, extra=state, rejected=True):
                    pass
            assert operations() == [("complete", 8, 3, 2)]
            with FIXTURE["listener"](*settings, extra=("--task-state", str(path), "--task-id", "other"),
                                     rejected=True):
                pass
            linked = path.parent / "linked"
            linked.symlink_to(path.parent, target_is_directory=True)
            with FIXTURE["listener"](*settings, extra=("--task-state", str(linked / path.name),
                                                       "--task-id", "fixture_task"), rejected=True):
                pass
            nested = path.parent / "nested"
            nested.mkdir(mode=0o700)
            alias = linked / nested.name / "new.sqlite"
            with FIXTURE["listener"](*settings, extra=("--task-state", str(alias), "--task-id",
                                                       "nested", "--create-task"), rejected=True):
                pass
            assert not alias.exists()
            missing = path.parent / "missing" / path.name
            with FIXTURE["listener"](*settings, extra=("--task-state", str(missing),
                                                       "--task-id", "fixture_task"), rejected=True):
                pass
            with FIXTURE["listener"](provider.server_port, 4, 1000, 24, extra=state, rejected=True):
                pass
            with FIXTURE["listener"](*settings, extra=(*state, "--create-task"), rejected=True):
                pass
            with FIXTURE["listener"](*settings, extra=state, with_process=True) as (port, gateway):
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream), HEADERS)
                    assert started.wait(3)
                    assert operations()[-1] == ("reserved", 8, None, None)
                    gateway.kill()
                    gateway.wait(timeout=5)
                assert disconnected.wait(2)
            rotated = uuid4().hex
            with FIXTURE["listener"](*settings, extra=state, token=rotated) as port:
                assert operations()[-1] == ("uncertain", 8, None, None)
                recorded = operations()
                assert FIXTURE["request"](port) == 401
                assert operations() == recorded
                stream["messages"][0]["content"] = "reported"
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream),
                                   {"Authorization": "Bearer " + rotated})
                    assert b"data: [DONE]" in client.getresponse().read()
                assert FIXTURE["request"](port, token=rotated) == 429
            assert operations() == [("complete", 8, 3, 2), ("uncertain", 8, None, None), ("complete", 8, 3, 2)]

            owned_path = Path(temporary) / "owned.sqlite"
            owned_state = ("--task-state", str(owned_path), "--task-id", "owned")
            owner = (*owned_state, "--task-owner", "ses_fixture", "wrk_fixture")
            first_credential, next_credential = uuid4().hex, uuid4().hex
            budget = (provider.server_port, 1, 1000, 8)
            started.clear()
            disconnected.clear()
            stream["messages"][0]["content"] = "stall"
            with FIXTURE["listener"](*budget, extra=(*owner, "--create-task"),
                                     token=first_credential, with_process=True) as (port, gateway):
                with FIXTURE["listener"](*budget, extra=owner, token=next_credential, rejected=True):
                    pass
                with closing(HTTPConnection("127.0.0.1", port, timeout=5)) as client:
                    client.request("POST", "/v1/chat/completions", json.dumps(stream),
                                   {"Authorization": "Bearer " + first_credential})
                    assert started.wait(3)
                    gateway.kill()
                    gateway.wait(timeout=5)
                assert disconnected.wait(2)
            with closing(sqlite3.connect(owned_path)) as db:
                original_task = db.execute("SELECT * FROM task").fetchone()
            for profile, token in (
                (owner, first_credential),
                (owned_state, next_credential),
                ((*owned_state, "--task-owner", "ses_other", "wrk_fixture"), next_credential),
                ((*owned_state, "--task-owner", "ses_fixture", "wrk_other"), next_credential),
            ):
                with FIXTURE["listener"](*budget, extra=profile, token=token, rejected=True):
                    pass
            with closing(sqlite3.connect(owned_path)) as db:
                assert db.execute("SELECT status FROM operation").fetchall() == [("reserved",)]
            with FIXTURE["listener"](*budget, extra=owner, token=next_credential) as port:
                assert FIXTURE["request"](port, token=first_credential) == 401
                assert FIXTURE["request"](port, token=next_credential) == 429
            with FIXTURE["listener"](*budget, extra=owner, token=first_credential, rejected=True):
                pass
            with closing(sqlite3.connect(owned_path)) as db:
                assert db.execute("SELECT * FROM task").fetchone() == original_task
                assert db.execute("SELECT count(*) FROM listener_credential").fetchone() == (2,)
                assert db.execute("SELECT status FROM operation").fetchall() == [("uncertain",)]
                db.execute("UPDATE task_owner SET session = 'corrupt'")
                db.commit()
            with FIXTURE["listener"](*budget, extra=owner, token=uuid4().hex, rejected=True):
                pass

            policy_path = Path(temporary) / "policy.sqlite"
            policy = ("--task-state", str(policy_path), "--task-id", "policy")
            with FIXTURE["listener"](*settings, extra=(*policy, "--create-task")) as port:
                payload = json.loads(FIXTURE["REQUEST"])
                for scenario in ("unreported", "overrun"):
                    payload["messages"][0]["content"] = scenario
                    assert FIXTURE["request"](port, body=json.dumps(payload).encode()) == 200
                assert FIXTURE["request"](port) == 429
            with closing(sqlite3.connect(policy_path)) as db:
                assert db.execute("SELECT prompt_tokens, completion_tokens FROM operation ORDER BY id").fetchall() == [
                    (None, None), (3, 9),
                ]
            with FIXTURE["listener"](*settings, extra=policy, rejected=True):
                pass

            race_path = Path(temporary) / "race.sqlite"
            race = ("--task-state", str(race_path), "--task-id", "race")
            with FIXTURE["listener"](provider.server_port, 1, 1000, 8, extra=(*race, "--create-task")) as port:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    assert sorted(pool.map(lambda _: FIXTURE["request"](port), range(2))) == [200, 429]

            closed = ("--task-state", str(Path(temporary) / "closed.sqlite"), "--task-id", "closed")
            with FIXTURE["listener"](*settings, extra=(*closed, "--create-task"), seconds=1, expires=True):
                pass
            with FIXTURE["listener"](*settings, extra=closed, seconds=1, rejected=True):
                pass

            path.write_bytes(b"database corrupted")
            with FIXTURE["listener"](*settings, extra=state, rejected=True):
                pass
        finally:
            provider.shutdown()
            thread.join(timeout=2)
    print("PASS D07 persisted reservation, crash recovery, usage, expiry and corruption rejection")


if __name__ == "__main__":
    main()
