"""Regression tests for bounded, non-financial model coding runner."""
from pathlib import Path
import json
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
import governed_coder as g  # noqa: E402

class TaskContractTests(unittest.TestCase):
    def test_verified_task_loads(self):
        task = g.read_task()
        self.assertEqual(task["task_id"], "FIN-P24-WZ-005")
        self.assertEqual(task["mode"], "DEMO_ONLY")
        self.assertEqual(task["max_attempts"], 2)
        self.assertEqual(task["allowed_files"][0], "scripts/dev/doctor.py")

    def test_bad_write_scope_rejected(self):
        obj = g.read_task()
        obj["allowed_files"][0] = ".github/workflows/governance.yml"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaises(g.GuardError):
                g.read_task(path)

    def test_unknown_task_rejected(self):
        obj = g.read_task()
        obj["task_id"] = "FIN-P24-WZ-999"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaises(g.GuardError):
                g.read_task(path)

    def test_no_extra_fields(self):
        obj = g.read_task()
        obj["extra_permission"] = "write_all"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task.json"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaises(g.GuardError):
                g.read_task(path)

    def test_unsafe_diff_path_rejected(self):
        with self.assertRaises(g.GuardError):
            g.validate_paths({"contracts/tasks/FIN-P24-WZ-005.json"}, g.read_task())

    def test_safe_existing_diff_path_accepted(self):
        g.validate_paths({"scripts/dev/doctor.py"}, g.read_task())

    def test_no_model_configuration_is_fail_closed(self):
        with patch.object(g.shutil, "which", return_value=None):
            self.assertEqual(g.invoke_model("safe prompt"),
                             (False, "COPILOT_AUTH_OR_BINARY_MISSING"))

    def test_copilot_restricts_writes_at_tool_permission_layer(self):
        import inspect
        src = inspect.getsource(g.invoke_model)
        self.assertIn("write(scripts/dev/doctor.py)", src)
        self.assertIn("write(tests/foundation/test_dev_doctor.py)", src)
        self.assertIn("--available-tools=edit,view,grep,glob", src)
        self.assertIn("--deny-tool=shell", src)
        self.assertNotIn("--allow-all-tools", src)
        self.assertIn("--model=auto", src)

    def test_prompt_bounds_and_no_shell_instructions(self):
        value = g.prompt(g.read_task(), "FAILED", 1)
        self.assertIn("FIN-P24-WZ-005", value)
        self.assertIn("scripts/dev/doctor.py", value)
        self.assertIn("Never use shell/git/network commands", value)

class RunTests(unittest.TestCase):
    def test_missing_model_does_not_forge_patch(self):
        with tempfile.TemporaryDirectory() as t:
            report = Path(t) / "out.json"
            patch_path = Path(t) / "change.patch"
            with patch.object(g, "git", return_value="a"*40), \
                 patch.object(g, "changed_paths", return_value=set()), \
                 patch.object(g, "run_tests", return_value=(True, "ok")), \
                 patch.object(g, "invoke_model", return_value=(False,"COPILOT_AUTH_OR_BINARY_MISSING")), \
                 patch.object(g, "emit_event"):
                state = g.execute(report, patch_path, g.TASK_PATH)
            self.assertEqual(state["status"], "BLOCKED")
            self.assertFalse(patch_path.exists())
            self.assertFalse(state["live_enabled"])
            self.assertFalse(state["merged"])
            self.assertEqual(state["iterations"], 1)
            self.assertEqual(json.loads(report.read_text())["status"], "BLOCKED")

    def test_successful_patch_requires_review(self):
        with tempfile.TemporaryDirectory() as t:
            report = Path(t) / "out.json"
            patch_path = Path(t) / "change.patch"
            n = [0]
            def paths():
                n[0] += 1
                return set() if n[0] == 1 else {"scripts/dev/doctor.py"}
            with patch.object(g, "git", return_value="b"*40), \
                 patch.object(g, "changed_paths", side_effect=paths), \
                 patch.object(g, "validate_paths"), \
                 patch.object(g, "run_tests", return_value=(True,"ok")), \
                 patch.object(g, "invoke_model", return_value=(True,"COPILOT_DONE")), \
                 patch.object(g, "produce_patch", return_value=(120,"f"*64)), \
                 patch.object(g, "emit_event"):
                state = g.execute(report, patch_path, g.TASK_PATH)
            self.assertEqual(state["status"], "READY_FOR_PR_REVIEW")
            self.assertTrue(state["tests_pass"])
            self.assertEqual(state["independent_review"], "NOT_VERIFIED")
            self.assertEqual(state["patch_sha256"], "f"*64)

    def test_failing_tests_bounded_two_attempts(self):
        with tempfile.TemporaryDirectory() as t:
            report = Path(t) / "report.json"
            with patch.object(g, "git", return_value="c"*40), \
                 patch.object(g, "changed_paths", return_value=set()), \
                 patch.object(g, "validate_paths"), \
                 patch.object(g, "run_tests", return_value=(False, "broken")), \
                 patch.object(g, "invoke_model", return_value=(True,"COPILOT_DONE")), \
                 patch.object(g, "emit_event"):
                state = g.execute(report, Path(t)/"p.patch", g.TASK_PATH)
            self.assertEqual(state["status"], "BLOCKED")
            self.assertEqual(state["iterations"], 2)
            self.assertEqual(state["reason"], "FOUNDATION_TESTS_NOT_GREEN")

    def test_unauthorized_path_prevents_publication(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(g, "git", return_value="d"*40), \
                 patch.object(g, "changed_paths", side_effect=[set(), {".github/workflows/governance.yml"}]), \
                 patch.object(g, "run_tests", return_value=(True, "ok")), \
                 patch.object(g, "invoke_model", return_value=(True,"COPILOT_DONE")), \
                 patch.object(g, "emit_event"):
                state = g.execute(Path(t)/"report.json", Path(t)/"diff.patch", g.TASK_PATH)
            self.assertEqual(state["status"], "BLOCKED")
            self.assertEqual(state["guard_error_type"], "GuardError")
            self.assertFalse((Path(t)/"diff.patch").exists())

if __name__ == "__main__":
    unittest.main()
