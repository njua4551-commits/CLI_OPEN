"""Synthetic stdio MCP server with barriers before an append and before its reply."""
import json
from pathlib import Path
import select
import sys
import time

root = Path(sys.argv[1])


def wait_for_release(marker):
    deadline = time.monotonic() + 20
    while not (root / marker).exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(marker)
        # Closing the MCP transport aborts the synthetic operation at the barrier.
        if select.select([sys.stdin], [], [], 0.025)[0]:
            pending = sys.stdin.readline()
            if not pending:
                raise SystemExit(0)
            message = json.loads(pending)
            if message["method"] == "notifications/cancelled":
                raise SystemExit(0)
            if message["method"] == "ping":
                print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": {}}), flush=True)


for line in sys.stdin:
    request = json.loads(line)
    if "id" not in request:
        continue
    method = request["method"]
    if method == "initialize":
        result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "recovery-fixture", "version": "1"}}
    elif method == "tools/list":
        result = {"tools": [{"name": "append", "description": "Append a fixed line to a synthetic file.",
                             "inputSchema": {"type": "object", "properties": {"label": {"type": "string"}},
                                             "required": ["label"], "additionalProperties": False}}]}
    elif method == "tools/call":
        assert request["params"]["name"] == "append"
        assert request["params"]["arguments"] == {"label": "synthetic"}
        with (root / "calls").open("a") as calls:
            calls.write("call\n")
        wait_for_release("allow-effect")
        with (root / "effects").open("a") as effects:
            effects.write("effect\n")
        wait_for_release("allow-reply")
        result = {"content": [{"type": "text", "text": "Synthetic append completed."}]}
    elif method == "ping":
        result = {}
    else:
        raise ValueError(method)
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
