import hashlib
import io
import json
import os
from pathlib import Path
import platform
import runpy
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = runpy.run_path(str(ROOT / "implementacion/supervisor/workspace.py"))
WORKSPACE_GIT = runpy.run_path(str(ROOT / "implementacion/supervisor/workspace_git.py"))


def request(operation="replace", name="fixture.txt", text="after\n"):
    return {"operation": operation, "path": name, "text": text}


@unittest.skipUnless(platform.system() == "Linux", "Linux workspace backend")
class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        artifacts = Path(temporary.name)
        # The mocked launcher never executes these placeholders.
        for relative in ("tools/bun-linux-x64-baseline/bun",
                         "opencode/packages/cli/dist/cli-linux-x64/bin/opencode"):
            binary = artifacts / relative
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.touch()
        environment = patch.dict(os.environ, {"CLI_OPEN_ARTIFACTS": str(artifacts)})
        environment.start()
        self.addCleanup(environment.stop)

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
                    target.chmod(0o640)
                    return subprocess.CompletedProcess(["mock-backend"], 0)

                with patch("shutil.which", return_value="/usr/bin/bwrap"), patch("subprocess.run", side_effect=run):
                    with self.assertRaisesRegex(ValueError, "concurrently"):
                        WORKSPACE["review"](source, [request(operation=changed)], command)
                self.assertEqual(target.read_text(), "concurrent change\n")
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
                self.assertFalse(staging[0].exists())

    def test_concurrent_source_change_before_publication_preserves_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            target = source / "fixture.txt"
            target.write_text("before\n")
            git = WORKSPACE_GIT["git"]
            git(source, "init", "-b", "main")
            git(source, "add", "fixture.txt")
            git(source, "commit", "-m", "Synthetic base")
            base = WORKSPACE_GIT["base_commit"](source)
            edits = [request()]
            changes = [{
                "path": "fixture.txt", "operation": "replace",
                "before_sha256": hashlib.sha256(b"before\n").hexdigest(),
                "before_version": WORKSPACE["signature"](target.stat()),
            }]
            approval = WORKSPACE_GIT["approval"](source, base, changes, edits)

            def change_before_final_verification(root, approved_changes):
                target.chmod(0o640)
                WORKSPACE["verify_sources"](root, approved_changes)

            with self.assertRaisesRegex(WORKSPACE["SourceChanged"], "before publication"):
                WORKSPACE_GIT["publish"](source, base, edits, changes, approval, change_before_final_verification)
            self.assertEqual(target.read_bytes(), b"before\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
            self.assertEqual(git(source, "diff", "--cached", "--name-only"), b"")
            self.assertEqual(git(source, "for-each-ref", "refs/heads/cli-open/"), b"")
            self.assertEqual(WORKSPACE_GIT["base_commit"](source), base)

    def test_final_verification_rejects_equal_bytes_on_replaced_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            target = source / "fixture.txt"
            target.write_bytes(b"before\r\n")
            changes = [{
                "path": target.name,
                "before_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "before_version": WORKSPACE["signature"](target.stat()),
            }]
            WORKSPACE["verify_sources"](source, changes)
            replacement = source / "replacement.txt"
            replacement.write_bytes(target.read_bytes())
            replacement.replace(target)
            with self.assertRaisesRegex(WORKSPACE["SourceChanged"], "before publication"):
                WORKSPACE["verify_sources"](source, changes)
            self.assertEqual(target.read_bytes(), b"before\r\n")
            alternate = source / "alternate.txt"
            alternate.write_bytes(target.read_bytes())
            target.unlink()
            target.symlink_to(alternate)
            with self.assertRaisesRegex(ValueError, "without links"):
                WORKSPACE["verify_sources"](source, changes)
            self.assertTrue(target.is_symlink())
            self.assertEqual(alternate.read_bytes(), b"before\r\n")

    def test_final_verification_rejects_source_hard_link_added_after_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            target = source / "fixture.txt"
            content = b"before\n"
            target.write_bytes(content)
            changes = [{
                "path": target.name,
                "before_sha256": hashlib.sha256(content).hexdigest(),
                "before_version": WORKSPACE["signature"](target.stat()),
            }]
            WORKSPACE["verify_sources"](source, changes)
            alternate = source / "alternate.txt"
            alternate.hardlink_to(target)
            with self.assertRaisesRegex(ValueError, "without links"):
                WORKSPACE["verify_sources"](source, changes)
            self.assertTrue(target.samefile(alternate))
            self.assertEqual(target.read_bytes(), content)

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

    def test_review_rejects_changed_or_linked_output_after_worker(self):
        for mutation in ("different-bytes", "symlink", "hardlink"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                source = Path(directory)
                target = source / "fixture.txt"
                target.write_bytes(b"before\r\n")
                target.chmod(0o640)
                copies = []

                def command(*_args, writable_workspace):
                    copies.append(writable_workspace)
                    return ["mock-backend"]

                def run(*_args, **_kwargs):
                    staged = copies[0] / target.name
                    staged.unlink()
                    if mutation == "symlink":
                        staged.symlink_to(target)
                    elif mutation == "hardlink":
                        linked = copies[0] / "linked.txt"
                        linked.write_bytes(b"after\n")
                        staged.hardlink_to(linked)
                    else:
                        staged.write_bytes(b"unreviewed\n")
                    return subprocess.CompletedProcess(["mock-backend"], 0)

                with patch("shutil.which", return_value="/usr/bin/bwrap"), patch("subprocess.run", side_effect=run):
                    with self.assertRaises(WORKSPACE["IsolatedEditFailed"]):
                        WORKSPACE["review"](source, [request()], command)
                self.assertEqual(target.read_bytes(), b"before\r\n")
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
                self.assertFalse(copies[0].exists())


if __name__ == "__main__":
    unittest.main()
