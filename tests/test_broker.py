import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "implementacion" / "supervisor"


def request(method, identifier=None, **params):
    message = {"jsonrpc": "2.0", "method": method, "params": params}
    if identifier is not None:
        message["id"] = identifier
    return json.dumps(message).encode() + b"\n"


HANDSHAKE = request("initialize", 1, protocolVersion="2025-11-25") + request("notifications/initialized")
TOOLS = {"cpu", "memory", "storage", "processes", "environment"}


@unittest.skipUnless(platform.system() == "Linux", "Linux backend required")
class BrokerTest(unittest.TestCase):
    def run_broker(self, data):
        return subprocess.run(
            [sys.executable, "-B", str(SUPERVISOR), "diag"],
            input=data, capture_output=True, timeout=10, check=False,
            env={**os.environ, "DIAG_PRIVATE_FIXTURE": "never-return-this-value"},
        )

    def test_catalog_and_all_diagnostics(self):
        names = sorted(TOOLS)
        payload = HANDSHAKE + request("tools/list", 2)
        for index, name in enumerate(names, 3):
            payload += request("tools/call", index, name=name, arguments={})
        process = self.run_broker(payload)
        self.assertEqual(process.returncode, 0, process.stderr)
        rows = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["result"]["protocolVersion"], "2025-11-25")
        tools = rows[1]["result"]["tools"]
        self.assertEqual({tool["name"] for tool in tools}, TOOLS)
        self.assertTrue(all(not tool["inputSchema"]["additionalProperties"] for tool in tools))
        result = {
            name: json.loads(row["result"]["content"][0]["text"])
            for name, row in zip(names, rows[2:], strict=True)
        }
        for tool, row in zip(sorted(tools, key=lambda item: item["name"]), rows[2:], strict=True):
            values = row["result"]["structuredContent"]
            self.assertEqual(set(tool["outputSchema"]["required"]), set(values))
            self.assertEqual(values, result[tool["name"]])
        self.assertGreater(result["cpu"]["logical_cpus"], 0)
        self.assertGreater(result["memory"]["total_bytes"], 0)
        self.assertGreater(result["storage"]["total_bytes"], 0)
        self.assertGreaterEqual(result["processes"]["visible_processes"], 1)
        self.assertEqual(result["environment"]["system"], "Linux")
        self.assertEqual(result["environment"]["profile"], "DIAG")
        self.assertNotIn(b"never-return-this-value", process.stdout + process.stderr)
        self.assertEqual(process.stderr.count(b"outcome=ok"), 5)
        self.assertLess(max(map(len, process.stdout.splitlines())), 8192)

    def test_denies_unknown_actions_paths_invalid_params_and_uninitialized_calls(self):
        payload = request("tools/call", 9, name="cpu") + HANDSHAKE
        payload += request("tools/call", 2, name="execute", arguments={"command": "marker"})
        payload += request("tools/call", 3, name="storage", arguments={"path": "/etc/passwd"})
        payload += request("tools/call", 4, name="cpu", arguments=[])
        payload += request("resources/read", 5, uri="file:///etc/passwd")
        payload += request("tools/call", 6, name="processes", arguments={"limit": 5000})
        process = self.run_broker(payload)
        self.assertEqual(process.returncode, 0)
        errors = {
            row["id"]: row["error"]["code"]
            for row in map(json.loads, process.stdout.splitlines()) if "error" in row
        }
        self.assertEqual(errors, {9: -32002, 2: -32602, 3: -32602, 4: -32602, 5: -32601, 6: -32602})
        self.assertNotIn(b"/etc/passwd", process.stdout + process.stderr)
        self.assertNotIn(b"marker", process.stdout + process.stderr)
        self.assertEqual(process.stderr.count(b"outcome=denied"), 4)

    def test_malformed_and_oversize_frames(self):
        process = self.run_broker(b"{bad\n" + b"x" * 8193 + b"\n")
        self.assertEqual(process.returncode, 1)
        rows = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual([row["error"]["code"] for row in rows], [-32700, -32600])


if __name__ == "__main__":
    unittest.main()
