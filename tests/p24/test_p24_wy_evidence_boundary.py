"""P24-WY offline evidence reconciliation boundary checks; no broker or runtime access."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class P24WYEvidenceBoundaryTests(unittest.TestCase):
    def test_checkpoint_does_not_claim_postmerge_pass(self) -> None:
        state = (ROOT / "docs/02-current-state/CURRENT-STATE.md").read_text(encoding="utf-8")
        note = (ROOT / "docs/19-production/P24-WY-SECURITY-POSTMERGE-EVIDENCE-CHECKPOINT.md").read_text(encoding="utf-8")
        self.assertIn("FIN-P24-WY-001", state)
        self.assertIn("POSTMERGE_UNVERIFIED", state)
        self.assertIn("**POSTMERGE_UNVERIFIED**", note)
        self.assertIn("5ac2a04dad1ce2d5603154bfc5b769da82c0beaa", state)
        for required in ("P24-B BLOCKED", "G13 NOT_STARTED", "LIVE_TRADING DISABLED", "AUTO_TRADING DISABLED"):
            self.assertIn(required, state)

    def test_dossier_keeps_all_pre_first_live_fail_closed(self) -> None:
        dossier = json.loads((ROOT / "config/production/production-readiness-dossier.json").read_text(encoding="utf-8"))
        pre = [item for item in dossier["production_prerequisites"] if item["stage"] == "PRE_FIRST_LIVE"]
        self.assertEqual(len(pre), 9)
        self.assertTrue(all(item["satisfied"] is False for item in pre))
        self.assertEqual(dossier["next"]["p24_b"], "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES")
        self.assertEqual(dossier["next"]["g13"], "NOT_STARTED")
        self.assertEqual(dossier["safety"]["live_trading"], "DISABLED")
        self.assertEqual(dossier["safety"]["auto_trading"], "DISABLED")

    def test_catalog_reconciled_without_phase_promotion(self) -> None:
        catalog = (ROOT / "docs/13-tasks/TASK-CATALOG.md").read_text(encoding="utf-8")
        self.assertIn("| FIN-P24-WY-001 |", catalog)
        self.assertIn("POSTMERGE_UNVERIFIED", catalog)
        self.assertIn("PR #521 MERGED", catalog)


if __name__ == "__main__":
    unittest.main()
