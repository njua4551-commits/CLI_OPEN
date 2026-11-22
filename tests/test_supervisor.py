import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "implementacion" / "supervisor"


class SupervisorTest(unittest.TestCase):
    def run_supervisor(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, "-B", str(SUPERVISOR), *args],
            cwd=cwd,
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

    def test_plan_denies_command_execution_and_writes(self):
        with tempfile.TemporaryDirectory() as workdir:
            marker = Path(workdir) / "marker"
            payload = "from pathlib import Path; Path('marker').touch()"
            for args in (
                ("execute", sys.executable, "-c", payload),
                ("write", "marker", "contents"),
                ("plan", "--execute", payload),
                ("plan", "diag"),
            ):
                result = self.run_supervisor(*args, cwd=workdir)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(marker.exists())
            result = self.run_supervisor("plan", cwd=workdir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PLAN activo", result.stdout)
            self.assertEqual(list(Path(workdir).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
