import io
import json
from pathlib import Path
import platform
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = runpy.run_path(str(ROOT / "implementacion/supervisor/workspace.py"))


def request(operation="replace", name="fixture.txt", text="after\n"):
    return {"operation": operation, "path": name, "text": text}


@unittest.skipUnless(platform.system() == "Linux", "Linux workspace backend")
class WorkspaceTest(unittest.TestCase):
    def test_schema_rejects_unauthorized_paths_and_operations(self):
        for edit in (request(name="../fixture.txt"), request(name="/fixture.txt"),
                     request(name=".hidden.txt"), request(operation="execute")):
            with self.assertRaises(ValueError):
                WORKSPACE["parse_request"](io.BytesIO(json.dumps({"edits": [edit]}).encode()))

    def test_diff_reports_missing_final_newlines(self):
        difference = WORKSPACE["review_diff"]("fixture.txt", (None, "before"), "after")
        self.assertIn("-before\n\\ No newline at end of file\n", difference)
        self.assertIn("+after\n\\ No newline at end of file\n", difference)

    def test_source_change_aborts_review_and_discards_copy(self):
        for changed in ("replace", "create"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                source = Path(directory)
                target = source / "fixture.txt"
                if changed == "replace":
                    target.write_text("before\n")
                staging = []

                def command(_backend, _mounts, _program, *, writable_workspace):
                    staging.append(writable_workspace)
                    return ["mock-backend"]

                def run(*_args, **_kwargs):
                    target.write_text("concurrent change\n")
                    return subprocess.CompletedProcess(["mock-backend"], 0)

                with patch("shutil.which", return_value="/usr/bin/bwrap"), patch("subprocess.run", side_effect=run):
                    with self.assertRaisesRegex(ValueError, "concurrently"):
                        WORKSPACE["review"](source, [request(operation=changed)], command)
                self.assertEqual(target.read_text(), "concurrent change\n")
                self.assertFalse(staging[0].exists())

    def test_link_and_validation_failure_leave_original_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            target = source / "fixture.txt"
            target.write_text("before\n")
            (source / "link.txt").symlink_to(target)
            with patch("shutil.which", return_value="/usr/bin/bwrap"):
                with self.assertRaisesRegex(ValueError, "without links"):
                    WORKSPACE["review"](source, [request(name="link.txt")], None)
            def command(*_args, writable_workspace):
                staging.append(writable_workspace)
                return ["mock-backend"]
            staging = []
            with patch("shutil.which", return_value="/usr/bin/bwrap"), patch(
                "subprocess.run", return_value=subprocess.CompletedProcess(["mock-backend"], 1)
            ):
                with self.assertRaisesRegex(ValueError, "discarded"):
                    WORKSPACE["review"](source, [request()], command)
            self.assertEqual(target.read_text(), "before\n")
            self.assertFalse(staging[0].exists())


if __name__ == "__main__":
    unittest.main()
