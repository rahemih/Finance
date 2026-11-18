"""Negative tests for the privileged, non-executing patch publisher gate."""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from coder_publish_guard import verify, PublishError

SHA = "a" * 40
FILE = "scripts/dev/doctor.py"
PATCH = (f"diff --git a/{FILE} b/{FILE}\n"
         "index 1111111..2222222 100644\n"
         f"--- a/{FILE}\n+++ b/{FILE}\n"
         "@@ -1 +1 @@\n-a\n+b\n").encode()

def evidence(patch=PATCH):
    return {
        "schema_version": "fin.coder.run.v1",
        "task_id": "FIN-P24-WZ-005",
        "status": "READY_FOR_PR_REVIEW",
        "tests_pass": True,
        "financial_mode": "DEMO_ONLY",
        "live_enabled": False,
        "merged": False,
        "independent_review": "NOT_VERIFIED",
        "iterations": 2,
        "base_sha": SHA,
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "changed_files": [FILE],
    }

class PublisherGateTests(unittest.TestCase):
    def test_safe_diff_can_be_inspected_without_executing(self):
        self.assertEqual(verify(evidence(), PATCH, SHA, [FILE]), [FILE])

    def test_no_unreviewed_tests_are_executed_here(self):
        # Publisher imports no generated test module or other code.
        import inspect
        from coder_publish_guard import execute
        source = inspect.getsource(execute)
        self.assertNotIn("python -m unittest", source)
        self.assertNotIn("shell=True", source)

    def test_wrong_commit_sha_is_rejected(self):
        with self.assertRaises(PublishError):
            verify(evidence(), PATCH, "b"*40, [FILE])

    def test_missing_tests_rejected(self):
        e = evidence()
        e["tests_pass"] = False
        with self.assertRaises(PublishError):
            verify(e, PATCH, SHA, [FILE])

    def test_live_mode_rejected(self):
        e = evidence()
        e["financial_mode"] = "LIVE"
        with self.assertRaises(PublishError):
            verify(e, PATCH, SHA, [FILE])

    def test_wrong_patch_hash_rejected(self):
        e = evidence()
        e["patch_sha256"] = "0"*64
        with self.assertRaises(PublishError):
            verify(e, PATCH, SHA, [FILE])

    def test_other_files_rejected(self):
        with self.assertRaises(PublishError):
            verify(evidence(), PATCH, SHA, ["docs/00-governance/OWNER-GATES.md"])

    def test_chmod_rename_rejected(self):
        data = PATCH + b"old mode 100644\nnew mode 100755\n"
        with self.assertRaises(PublishError):
            verify(evidence(data), data, SHA, [FILE])

    def test_binary_rejected(self):
        data = PATCH + b"GIT binary patch\n"
        with self.assertRaises(PublishError):
            verify(evidence(data), data, SHA, [FILE])

    def test_many_bytes_rejected(self):
        data = PATCH + b"x" * 33000
        with self.assertRaises(PublishError):
            verify(evidence(data), data, SHA, [FILE])

    def test_extra_header_rejected(self):
        data = PATCH + b"diff --git a/.github/workflows/governance.yml b/.github/workflows/governance.yml\n"
        with self.assertRaises(PublishError):
            verify(evidence(data), data, SHA, [FILE])

    def test_review_does_not_self_approve(self):
        e = evidence()
        e["independent_review"] = "APPROVED_BY_SELF"
        with self.assertRaises(PublishError):
            verify(e, PATCH, SHA, [FILE])

if __name__ == "__main__":
    unittest.main()
