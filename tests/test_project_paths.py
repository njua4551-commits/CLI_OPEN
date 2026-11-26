import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == "linux" and shutil.which("rg"), "Linux and ripgrep required")
class ProjectPathsTest(unittest.TestCase):
    def test_paths_respect_project_scope_and_share_envelope_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            outside = root / "auth_external.py"
            outside.write_text("outside")
            for name in ("src/auth_handler.py", "src/author.py", "src/auth_credentials.py",
                         "ignored/auth.py", "nested/node_modules/auth.js", "nested/auth.ts"):
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("DO NOT EXECUTE THIS")
            (project / ".gitignore").write_text("ignored/\n")
            (project / "auth_link.py").symlink_to(outside)
            (project / "auth_dir").symlink_to(root, target_is_directory=True)

            def memory(command, *args):
                return subprocess.check_output([
                    sys.executable, "-I", "-B", str(ROOT / "implementacion/memoria"),
                    "--store", str(root / "store"), command, "--project", str(project), *args,
                ], timeout=10)

            memory("add", "--text", "auth requirement", "--files", "src/auth_handler.py")

            def context():
                raw = memory("context", "--query", "auth", "--with-paths", "--max-bytes", "220")
                self.assertLessEqual(len(raw), 220)
                self.assertNotIn(b"DO NOT EXECUTE", raw)
                return json.loads(raw)

            result = context()
            self.assertEqual(result["paths"], ["nested/auth.ts", "src/auth_handler.py"])
            self.assertEqual(result, context())
            self.assertEqual(len(result["entries"]), 1)

            result["paths"] += ["../auth_external.py", "/etc/auth.py", "src/../auth.py", "src/auth_credentials.py"]
            prompt = subprocess.check_output([
                sys.executable, "-I", "-B", str(ROOT / "implementacion/supervisor"),
                "inject-context", "--prompt", "auth", "--envelope", json.dumps(result),
                "--max-context-bytes", "220",
            ], text=True, timeout=10)
            encoded = next(line for line in prompt.splitlines() if line.startswith("{"))
            self.assertLessEqual(len(encoded) + 1, 220)
            self.assertEqual(json.loads(encoded)["paths"], ["nested/auth.ts", "src/auth_handler.py"])
            self.assertIn("authority=none", prompt)

            (project / "src/auth_handler.py").rename(project / "src/auth_new.py")
            (project / "nested/auth.ts").unlink()
            updated = context()
            self.assertEqual(updated["paths"], ["src/auth_new.py"])
            self.assertEqual(updated["entries"], [])
