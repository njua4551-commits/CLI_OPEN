"""Run a physical-model read fixture inside the supervisor's private network."""
import json
import os
from pathlib import Path
import runpy
import secrets
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = runpy.run_path(str(Path(__file__).with_name("fase6-modelo-local.py")))
CLI = ROOT / ".fase1/opencode/packages/cli/dist/cli-linux-x64/bin/opencode"


def session(root, port, filename):
    alias = FIXTURE["ALIAS"]
    config = {
        "permissions": [
            {"action": "*", "resource": "*", "effect": "deny"},
            {"action": "read", "resource": "sample.txt", "effect": "allow"},
        ],
        "agents": {"fixture": {
            "mode": "primary",
            "system": "Use read with the requested path, offset 1, and limit 1. "
                      "After the tool response, copy the first line into your plain-text answer.",
            "steps": 2,
        }},
        "providers": {"fixture": {
            "package": "@opencode/ai/providers/openai-compatible",
            "settings": {"baseURL": f"http://127.0.0.1:{port}/v1", "apiKey": "fixture"},
            "models": {alias: {"capabilities": {"tools": True}, "settings": {"temperature": 0}}},
        }},
    }
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root),
        **{f"XDG_{name}_HOME": str(root / name.lower())
           for name in ("STATE", "CONFIG", "DATA", "CACHE")},
        "OPENCODE_CONFIG_CONTENT": json.dumps(config),
        **{f"OPENCODE_{flag}": "true" for flag in (
            "CONFIG_PROJECT_DISABLE", "DISABLE_CLAUDE_CODE",
            "DISABLE_MODELS_FETCH", "DISABLE_FILEWATCHER",
        )},
    }
    try:
        result = subprocess.run([
            "/fixture/opencode", "--standalone", "run", "--model", f"fixture/{alias}",
            "--agent", "fixture", "--format", "json", f"What are the three words in {filename}?",
        ], env=env, cwd=root / "work", capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as error:
        raise AssertionError(f"session timed out: {(error.stdout or b'')[-2400:]!r}") from error
    events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    if not events:
        raise AssertionError(result.stderr[-2000:])
    assert result.returncode == 0, (result.stderr[-1200:], events[-3:])
    return [(event.get("type"), event.get("part", {})) for event in events]


def inside(runtime):
    with tempfile.TemporaryDirectory(prefix="agente-local-") as directory:
        root = Path(directory)
        work = root / "work"
        work.mkdir()
        marker = " ".join(secrets.SystemRandom().sample(
            ("apple", "peach", "cherry", "plum", "berry", "orange", "lemon", "mango"), 3,
        ))
        forbidden = f"PRIVATE-{uuid.uuid4().hex[:8]}"
        (work / "sample.txt").write_text(marker + "\n")
        (work / "forbidden.txt").write_text(forbidden + "\n")
        port = FIXTURE["free_port"]()
        with (root / "llama.log").open("w+") as log, subprocess.Popen([
            runtime, "-m", "/fixture/model.gguf",
            "--host", "127.0.0.1", "--port", str(port), "-c", "4096",
            "-t", "2", "--parallel", "1", "-ngl", "0", "--jinja", "--alias", FIXTURE["ALIAS"],
        ], stdout=subprocess.DEVNULL, stderr=log) as llama:
            gateway = None
            try:
                FIXTURE["wait_ready"](port, llama)
                os.environ["CLI_OPEN_GATEWAY_MAX_TOKENS"] = "96"
                gateway, listen = FIXTURE["start_gateway"](port)
                allowed = session(root, listen, "sample.txt")
                denied = session(root, listen, "forbidden.txt")
                assert forbidden not in json.dumps(denied), "denied file contents disclosed"
                checks = (
                    ("lectura autorizada", allowed, any(
                        kind == "tool_use" and part.get("tool") == "read"
                        and part["state"].get("status") == "completed"
                        and marker in part["state"].get("output", "")
                        for kind, part in allowed
                    )),
                    ("respuesta final", allowed, any(
                        kind == "text" and marker in part.get("text", "") for kind, part in allowed
                    )),
                    ("lectura no autorizada rechazada", denied, any(
                        kind == "tool_use" and part.get("tool") == "read"
                        and part["state"].get("status") == "error"
                        and "forbidden.txt" in str(part["state"].get("input", {}))
                        and any(word in part["state"].get("error", "").lower()
                                for word in ("denied", "permission", "reject"))
                        for kind, part in denied
                    )),
                )
                for label, events, passed in checks:
                    print(f"{'PASS' if passed else 'FAIL'} modelo físico: {label}", flush=True)
                    if not passed:
                        print([(kind, part.get("state", part.get("reason", part.get("text"))))
                               for kind, part in events if kind != "step_start"][-6:], file=sys.stderr)
                assert all(passed for _, _, passed in checks), "physical agent fixture failed"
            except Exception:
                log.seek(0, os.SEEK_END)
                log.seek(max(0, log.tell() - 1800))
                print(log.read(), file=sys.stderr)
                raise
            finally:
                for child in (gateway, llama):
                    if child is not None and child.poll() is None:
                        child.terminate()
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)


def main():
    runtime, model = FIXTURE["RUNTIME"].resolve(), FIXTURE["MODEL"].resolve()
    bwrap = shutil.which("bwrap", path="/usr/bin:/bin")
    if not bwrap or not all(path.is_file() for path in (runtime, model, CLI)):
        print("SKIP agente local: falta Bubblewrap, OpenCode, llama-server o GGUF")
        return 77
    supervisor = runpy.run_path(str(ROOT / "implementacion/supervisor/__main__.py"))
    command = supervisor["bubblewrap_command"](bwrap, (
        (runtime.parent, "/fixture/llama"),
        (model, "/fixture/model.gguf"),
        (CLI, "/fixture/opencode"),
        (ROOT / "tests", "/fixture/tests"),
        (ROOT / "implementacion/gateway", "/fixture/implementacion/gateway"),
    ), ["/usr/bin/python3", "-I", "-B", "/fixture/tests/fase6-agente-local.py",
        "--inside", f"/fixture/llama/{runtime.name}"])
    return subprocess.run(command, env={}, timeout=240).returncode


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--inside":
        inside(sys.argv[2])
    else:
        raise SystemExit(main())
