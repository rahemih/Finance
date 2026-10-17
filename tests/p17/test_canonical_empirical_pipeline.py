from __future__ import annotations

import unittest

from scripts.ci.p17_canonical_empirical_pipeline import build


class CanonicalEmpiricalPipelineTests(unittest.TestCase):
    def test_canonical_p17_modules_drive_empirical_g9(self) -> None:
        evidence = build()
        self.assertEqual(evidence["gate_state"], "PASS_EMPIRICAL_REFERENCE")
        self.assertFalse(evidence["fixture_only"])
        self.assertEqual(
            evidence["canonical_modules_executed"],
            [
                "P17-A_BACKTEST_ENGINE",
                "P17-B_EXECUTION_REALISM",
                "P17-C_INFORMATION_HYGIENE",
                "P17-D_WALK_FORWARD",
                "P17-E_ROBUSTNESS",
                "P17-F_LIQUIDITY_CAPACITY",
                "P17-G_STRATEGY_REGISTRY",
                "P17-H_MODEL_REGISTRY",
                "P17-I_EMPIRICAL_G9",
            ],
        )
        self.assertEqual(len(evidence["workstream_evidence"]), 8)
        self.assertFalse(evidence["production_scale_validation"])
        self.assertFalse(evidence["profitability_guarantee"])
        self.assertFalse(evidence["p19_started"])

    def test_canonical_outputs_are_distinct_content_identities(self) -> None:
        evidence = build()
        ids = {
            evidence["backtest_result_id"],
            evidence["information_hygiene_certificate_id"],
            evidence["walk_forward_certificate_id"],
            evidence["robustness_certificate_id"],
            evidence["capacity_certificate_id"],
            evidence["strategy_registry_id"],
            evidence["model_registry_id"],
            evidence["gate_certificate_id"],
        }
        self.assertEqual(len(ids), 8)
        self.assertTrue(all(len(set(value)) >= 4 for value in ids))


if __name__ == "__main__":
    unittest.main()
