import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "implementacion" / "supervisor"


class SupervisorTest(unittest.TestCase):
    def run_supervisor(self, *args, cwd=None, env=None):
        return subprocess.run(
            [sys.executable, "-B", str(SUPERVISOR), *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_doctor_reports_effective_environment(self):
        result = self.run_supervisor("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["profile"], "PLAN")
        self.assertTrue(report["system"])
        self.assertTrue(report["architecture"])
        self.assertFalse(report["isolation"]["verified"])
        self.assertEqual(report["capabilities"], {"execute": False, "write": False, "remote": False})

    @unittest.skipUnless(platform.system() == "Linux", "Bubblewrap detection is Linux-specific")
    def test_missing_backend_keeps_plan_without_access(self):
        result = self.run_supervisor("doctor", env={**os.environ, "PATH": ""})
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["profile"], "PLAN")
        self.assertEqual(report["isolation"], {"bubblewrap_on_path": False, "verified": False})
        self.assertFalse(report["capabilities"]["write"])
        self.assertFalse(report["capabilities"]["execute"])

    def test_plan_denies_command_execution_and_writes(self):
        with tempfile.TemporaryDirectory() as workdir:
            marker = Path(workdir) / "marker"
            payload = "from pathlib import Path; Path('marker').touch()"
            for args in (
                ("execute", sys.executable, "-c", payload),
                ("write", "marker", "contents"),
                ("plan", "--execute", payload),
                ("plan", "diag"),
                ("plan", "qualify-linux"),
                ("workspace",),
            ):
                result = self.run_supervisor(*args, cwd=workdir)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(marker.exists())
            result = self.run_supervisor("plan", cwd=workdir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PLAN activo", result.stdout)
            self.assertEqual(list(Path(workdir).iterdir()), [])

    def test_inject_context_enforces_zero_authority(self):
        valid_envelope = {
            "authority": "none",
            "source": "project-memory",
            "entries": [{"id": "abcdef0123456789", "text": "Valid memory item"}],
        }
        res = self.run_supervisor("inject-context", "--prompt", "Analyze repo",
                                  "--envelope", json.dumps(valid_envelope))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("[UNTRUSTED_PROJECT_MEMORY_CONTEXT authority=none]", res.stdout)
        self.assertIn("Analyze repo", res.stdout)
        self.assertIn("Valid memory item", res.stdout)

        # Rejection of non-none authority
        invalid_envelope = {
            "authority": "root",
            "source": "project-memory",
            "entries": [],
        }
        res_bad = self.run_supervisor("inject-context", "--prompt", "Test",
                                      "--envelope", json.dumps(invalid_envelope))
        self.assertEqual(res_bad.returncode, 1)
        self.assertIn("autoridad nula", res_bad.stderr)

    def test_inject_context_applies_encoded_budget_and_deduplicates(self):
        envelope = {
            "authority": "none",
            "source": "project-memory",
            "entries": [
                {"id": "0" * 16, "text": "雪" * 100},
                {"id": "1" * 16, "text": "Keep this"},
                {"id": "2" * 16, "text": "Keep this"},
                {"id": "1" * 16, "text": "Duplicate id"},
                {"id": "3" * 16, "text": "Second item"},
            ],
        }
        args = ("inject-context", "--prompt", "Analyze repo", "--envelope", json.dumps(envelope))
        result = self.run_supervisor(*args, "--max-context-bytes", "180")
        self.assertEqual(result.returncode, 0, result.stderr)
        serialized = next(line for line in result.stdout.splitlines() if line.startswith("{"))
        self.assertLessEqual(len(serialized.encode()) + 1, 180)
        self.assertEqual(json.loads(serialized)["entries"], [envelope["entries"][1], envelope["entries"][4]])
        self.assertEqual(self.run_supervisor(*args, "--max-context-bytes", "127").returncode, 1)


if __name__ == "__main__":
    unittest.main()
