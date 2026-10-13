from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.best_trading_time import (
    BestTradingTimePolicy,
    TimingWindowEvidence,
    assess_timing_window,
)
from packages.timing_opportunity.opportunity_scanner import (
    OpportunityScanInput,
    OpportunityScannerError,
    OpportunityScannerPolicy,
    scan_opportunities,
)


ROOT = Path(__file__).resolve().parents[2]
BEST_POLICY_PATH = ROOT / "config/timing-opportunity/best-trading-time-policy.json"
SCANNER_POLICY_PATH = ROOT / "config/timing-opportunity/opportunity-scanner-policy.json"
HASH_A = "a" * 64
HASH_B = "b" * 64


class OpportunityScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.best_policy = BestTradingTimePolicy.from_path(BEST_POLICY_PATH)
        self.policy = OpportunityScannerPolicy.from_path(SCANNER_POLICY_PATH)

    def assessment(
        self,
        *,
        window_id: str,
        mean_edge_bps: int,
        uncertainty_bps: int = 20,
        sample_count: int = 40,
        market_open: bool = True,
        asset_id: str = "BTC-USD",
    ):
        return assess_timing_window(
            TimingWindowEvidence(
                window_id=window_id,
                asset_id=asset_id,
                strategy_id="trend-v1",
                timeframe="1h",
                regime_label="ALIGNED_BULLISH",
                session_labels=("EUROPE", "US"),
                sample_count=sample_count,
                mean_edge_bps=mean_edge_bps,
                uncertainty_bps=uncertainty_bps,
                market_open=market_open,
            ),
            policy=self.best_policy,
        )

    def item(self, assessment, *, digest: str = HASH_A):
        return OpportunityScanInput(
            assessment=assessment,
            provenance_sha256=(digest,),
            source_dataset_versions=("p13b-v1",),
        )

    def test_preferred_and_standard_are_eligible(self) -> None:
        result = scan_opportunities(
            (
                self.item(self.assessment(window_id="preferred", mean_edge_bps=180)),
                self.item(self.assessment(window_id="standard", mean_edge_bps=80)),
            ),
            policy=self.policy,
        )
        self.assertEqual(len(result.eligible_candidate_ids), 2)
        self.assertTrue(all(item.scanner_state == "ELIGIBLE_TIMING_CONTEXT" for item in result.candidates))

    def test_weak_is_observe_only(self) -> None:
        result = scan_opportunities(
            (self.item(self.assessment(window_id="weak", mean_edge_bps=10)),),
            policy=self.policy,
        )
        self.assertEqual(len(result.observe_only_candidate_ids), 1)
        self.assertFalse(result.candidates[0].eligible)
        self.assertEqual(result.candidates[0].scanner_state, "OBSERVE_ONLY")

    def test_closed_and_insufficient_are_ineligible(self) -> None:
        result = scan_opportunities(
            (
                self.item(self.assessment(window_id="closed", mean_edge_bps=200, market_open=False)),
                self.item(self.assessment(window_id="insufficient", mean_edge_bps=200, sample_count=5)),
            ),
            policy=self.policy,
        )
        self.assertEqual(len(result.ineligible_candidate_ids), 2)
        self.assertTrue(all(item.scanner_state == "INELIGIBLE_CONTEXT" for item in result.candidates))

    def test_input_order_does_not_change_result(self) -> None:
        items = (
            self.item(self.assessment(window_id="b", mean_edge_bps=150, asset_id="ETH-USD"), digest=HASH_B),
            self.item(self.assessment(window_id="a", mean_edge_bps=130, asset_id="BTC-USD")),
        )
        self.assertEqual(
            scan_opportunities(items, policy=self.policy),
            scan_opportunities(tuple(reversed(items)), policy=self.policy),
        )

    def test_candidate_identity_is_lineage_sensitive(self) -> None:
        assessment = self.assessment(window_id="lineage", mean_edge_bps=150)
        first = scan_opportunities((self.item(assessment, digest=HASH_A),), policy=self.policy)
        second = scan_opportunities((self.item(assessment, digest=HASH_B),), policy=self.policy)
        self.assertNotEqual(first.candidates[0].candidate_id, second.candidates[0].candidate_id)

    def test_duplicate_canonical_candidate_fails_closed(self) -> None:
        item = self.item(self.assessment(window_id="duplicate", mean_edge_bps=150))
        with self.assertRaises(OpportunityScannerError):
            scan_opportunities((item, item), policy=self.policy)

    def test_invalid_lineage_and_usability_mismatch_fail_closed(self) -> None:
        assessment = self.assessment(window_id="bad", mean_edge_bps=150)
        with self.assertRaises(OpportunityScannerError):
            scan_opportunities(
                (
                    OpportunityScanInput(
                        assessment=assessment,
                        provenance_sha256=("not-a-sha",),
                        source_dataset_versions=("p13b-v1",),
                    ),
                ),
                policy=self.policy,
            )
        tampered = replace(assessment, usable=False)
        with self.assertRaises(OpportunityScannerError):
            scan_opportunities((self.item(tampered),), policy=self.policy)

    def test_policy_rejects_ranking_probability_or_execution_scope(self) -> None:
        self.assertFalse(self.policy.opportunity_ranking_in_scope)
        self.assertFalse(self.policy.hard_no_trade_authority)
        self.assertFalse(self.policy.signal_expiry_in_scope)
        self.assertFalse(self.policy.signal_probability_in_scope)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

        raw = SCANNER_POLICY_PATH.read_text(encoding="utf-8").replace(
            '"opportunity_ranking_in_scope": false',
            '"opportunity_ranking_in_scope": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(OpportunityScannerError):
                OpportunityScannerPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
