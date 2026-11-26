"""Inferencia real a través del gateway con un modelo local físico (CPU).

Requiere un binario `llama-server` y un GGUF locales. Sin ellos la prueba se
omite para no romper la regresión. Con ambos, valida chat, streaming y llamada
a herramienta a través del gateway OpenAI-compatible, sin red externa.
"""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "implementacion" / "gateway"
RUNTIME = Path(os.environ.get("CLI_OPEN_LLAMA_SERVER", "/tmp/opencode/llama/llama-b12753/llama-server"))
MODEL = Path(os.environ.get("CLI_OPEN_LOCAL_MODEL", "/tmp/opencode/models/llama-3.2-1b-instruct-q4_k_m.gguf"))
ALIAS = "local-llama-3.2-1b"
TIMEOUT = 120


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wait_ready(port, child, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise AssertionError("llama-server terminó durante el arranque")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise AssertionError("llama-server no quedó listo")


def start_gateway(upstream):
    child = subprocess.Popen([
        sys.executable, "-I", "-B", str(GATEWAY), "--port", str(upstream),
        "--model", ALIAS, "--listen", "0",
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    line = child.stdout.readline().strip()
    assert line.startswith("LISTEN "), line
    return child, int(line.split()[1])


def post(port, request, raw=False):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=TIMEOUT)
    try:
        connection.request("POST", "/v1/chat/completions", json.dumps(request).encode(),
                           {"Content-Type": "application/json", "Connection": "close"})
        response = connection.getresponse()
        body = response.read()
        return response.status, body if raw else json.loads(body)
    finally:
        connection.close()


def main():
    if not RUNTIME.is_file() or not MODEL.is_file():
        print("SKIP fase6 modelo local: falta llama-server o el GGUF")
        return

    port = free_port()
    log = open("/tmp/opencode/llama-server.log", "wb")
    llama = subprocess.Popen([
        str(RUNTIME), "-m", str(MODEL), "--host", "127.0.0.1", "--port", str(port),
        "-c", "2048", "-t", "2", "--jinja", "--alias", ALIAS,
    ], stdout=subprocess.DEVNULL, stderr=log)
    gateway = None
    try:
        wait_ready(port, llama)
        gateway, listen = start_gateway(port)

        status, reply = post(listen, {
            "model": ALIAS,
            "messages": [{"role": "user", "content": "Responde solo con la palabra OK."}],
            "max_tokens": 16,
            "temperature": 0,
        })
        assert status == 200, reply
        assert reply["model"] == ALIAS, reply.get("model")
        text = reply["choices"][0]["message"]["content"].strip()
        assert text, "respuesta vacía"

        status, stream = post(listen, {
            "model": ALIAS,
            "messages": [{"role": "user", "content": "Cuenta del 1 al 3."}],
            "max_tokens": 24,
            "temperature": 0,
            "stream": True,
        }, raw=True)
        assert status == 200, stream
        assert b"data: [DONE]" in stream, stream[:300]
        events = [line for line in stream.splitlines() if line.startswith(b"data: ")]
        assert len(events) >= 2, events

        status, tool = post(listen, {
            "model": ALIAS,
            "messages": [{"role": "user", "content": "Lee el archivo sample.txt usando la herramienta."}],
            "max_tokens": 64,
            "temperature": 0,
            "tools": [{
                "type": "function",
                "function": {
                    "name": "leer_archivo",
                    "description": "Lee un archivo del proyecto",
                    "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}},
                                   "required": ["ruta"]},
                },
            }],
            "tool_choice": {"type": "function", "function": {"name": "leer_archivo"}},
        })
        assert status == 200, tool
        calls = tool["choices"][0]["message"].get("tool_calls") or []
        assert calls and calls[0]["function"]["name"] == "leer_archivo", calls
        print("PASS fase6 modelo local: chat, streaming y tool call reales por el gateway")
    finally:
        if gateway is not None:
            gateway.terminate()
            gateway.wait(timeout=10)
        llama.terminate()
        try:
            llama.wait(timeout=10)
        except subprocess.TimeoutExpired:
            llama.kill()
            llama.wait(timeout=5)
        log.close()


if __name__ == "__main__":
    main()
