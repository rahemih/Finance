"""Synthetic negative tests for the fail-closed Finance watcher."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from finance_watch import EvidenceError, summarize  # noqa: E402


SHA = "a" * 40
STAMP = "2026-11-17T00:00:00+00:00"


def fixture():
    return {
        "branch": {"commit": {"sha": SHA}},
        "issues": [
            {"number": 491, "title": "P24 Live: prerequisites blocked"},
            {"number": 504, "title": "PR mirrored in issues endpoint", "pull_request": {"url": "x"}},
        ],
        "prs": [{"number": 504, "title": "Blocked: license review"}],
        "runs": {"workflow_runs": [
            {"name": "Governance Verify", "id": 123, "head_sha": SHA,
             "status": "completed", "conclusion": "success",
             "created_at": "2026-11-17T00:00:00Z"}]},
    }


class WatchTests(unittest.TestCase):
    def test_good_main_ci_does_not_mean_complete(self):
        r = summarize(fixture(), STAMP)
        self.assertEqual(r["exact_main_governance"]["status"], "SUCCESS_EXACT_MAIN")
        self.assertEqual(r["open_issue_count"], 1)
        self.assertEqual(r["open_pr_count"], 1)
        self.assertEqual(r["final_completion"], "NOT_VERIFIED")
        self.assertEqual(len(r["potential_blockers"]), 2)

    def test_same_evidence_has_stable_digest(self):
        self.assertEqual(summarize(fixture(), STAMP), summarize(fixture(), STAMP))

    def test_wrong_sha_never_promotes_ci(self):
        p = fixture()
        p["runs"]["workflow_runs"][0]["head_sha"] = "b" * 40
        self.assertEqual(summarize(p, STAMP)["exact_main_governance"]["status"], "NOT_VERIFIED")

    def test_missing_ci_never_promotes_completion(self):
        p = fixture()
        p["runs"]["workflow_runs"] = []
        r = summarize(p, STAMP)
        self.assertEqual(r["exact_main_governance"]["status"], "NOT_VERIFIED")
        self.assertEqual(r["final_completion"], "NOT_VERIFIED")

    def test_failed_ci_is_not_success(self):
        p = fixture()
        p["runs"]["workflow_runs"][0]["conclusion"] = "failure"
        self.assertEqual(summarize(p, STAMP)["exact_main_governance"]["status"], "FAILED_EXACT_MAIN")

    def test_missing_main_fails_closed(self):
        p = fixture()
        p["branch"] = {}
        with self.assertRaises(EvidenceError):
            summarize(p, STAMP)

    def test_pagination_limit_fails_closed(self):
        p = fixture()
        p["prs"] = [{"number": i+1, "title": "x"} for i in range(100)]
        with self.assertRaises(EvidenceError):
            summarize(p, STAMP)

    def test_malformed_item_fails_closed(self):
        p = fixture()
        p["issues"].append({"number": "491", "title": "bad"})
        with self.assertRaises(EvidenceError):
            summarize(p, STAMP)

    def test_unknown_status_remains_unverified(self):
        p = copy.deepcopy(fixture())
        p["runs"]["workflow_runs"][0]["status"] = "queued"
        self.assertEqual(summarize(p, STAMP)["exact_main_governance"]["status"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
