from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.no_trade import (
    NoTradeContext,
    NoTradeError,
    NoTradePolicy,
    evaluate_no_trade,
)
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/no-trade-policy.json"


class NoTradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = NoTradePolicy.from_path(POLICY_PATH)

    def candidate(
        self,
        *,
        candidate_id: str = "a" * 64,
        timing_class: str = "PREFERRED",
        scanner_state: str = "ELIGIBLE_TIMING_CONTEXT",
        eligible: bool = True,
    ) -> OpportunityCandidate:
        return OpportunityCandidate(
            candidate_id=candidate_id,
            window_id="window-1",
            asset_id="BTC-USD",
            strategy_id="trend-v1",
            timeframe="1h",
            regime_label="ALIGNED_BULLISH",
            session_labels=("EUROPE", "US"),
            sample_count=80,
            adjusted_edge_bps=150,
            timing_class=timing_class,
            scanner_state=scanner_state,
            eligible=eligible,
            provenance_sha256=("a" * 64,),
            source_dataset_versions=("p13c-v1",),
        )

    def test_clean_eligible_context_remains_timing_eligible(self) -> None:
        result = evaluate_no_trade(NoTradeContext(self.candidate()), policy=self.policy)
        self.assertEqual(result.decision, "TIMING_ELIGIBLE")
        self.assertEqual(result.reason_codes, ())

    def test_non_eligible_context_is_no_trade(self) -> None:
        candidate = self.candidate(
            timing_class="WEAK",
            scanner_state="OBSERVE_ONLY",
            eligible=False,
        )
        result = evaluate_no_trade(NoTradeContext(candidate), policy=self.policy)
        self.assertEqual(result.decision, "NO_TRADE")
        self.assertEqual(result.reason_codes, ("CANDIDATE_NOT_ELIGIBLE",))

    def test_each_governed_context_veto_is_hard_no_trade(self) -> None:
        fields = (
            ("contradictory_evidence", "CONTRADICTORY_EVIDENCE"),
            ("degraded_data", "DEGRADED_DATA"),
            ("high_event_risk", "HIGH_EVENT_RISK"),
            ("poor_liquidity", "POOR_LIQUIDITY"),
            ("excessive_spread", "EXCESSIVE_SPREAD"),
            ("stale_evidence", "STALE_EVIDENCE"),
            ("extreme_uncertainty", "EXTREME_UNCERTAINTY"),
        )
        for field, code in fields:
            with self.subTest(field=field):
                context = replace(NoTradeContext(self.candidate()), **{field: True})
                result = evaluate_no_trade(context, policy=self.policy)
                self.assertEqual(result.decision, "NO_TRADE")
                self.assertEqual(result.reason_codes, (code,))

    def test_multiple_veto_reasons_follow_policy_order(self) -> None:
        result = evaluate_no_trade(
            NoTradeContext(
                self.candidate(),
                contradictory_evidence=True,
                high_event_risk=True,
                excessive_spread=True,
                stale_evidence=True,
            ),
            policy=self.policy,
        )
        self.assertEqual(
            result.reason_codes,
            (
                "CONTRADICTORY_EVIDENCE",
                "HIGH_EVENT_RISK",
                "EXCESSIVE_SPREAD",
                "STALE_EVIDENCE",
            ),
        )

    def test_candidate_state_eligibility_mismatch_fails_closed(self) -> None:
        with self.assertRaises(NoTradeError):
            evaluate_no_trade(
                NoTradeContext(replace(self.candidate(), eligible=False)),
                policy=self.policy,
            )

    def test_identical_inputs_are_deterministic(self) -> None:
        context = NoTradeContext(self.candidate(), degraded_data=True, poor_liquidity=True)
        self.assertEqual(
            evaluate_no_trade(context, policy=self.policy),
            evaluate_no_trade(context, policy=self.policy),
        )

    def test_policy_preserves_downstream_ownership(self) -> None:
        self.assertFalse(self.policy.signal_expiry_computation_in_scope)
        self.assertFalse(self.policy.signal_probability_in_scope)
        self.assertFalse(self.policy.portfolio_risk_budget_computation_in_scope)
        self.assertFalse(self.policy.position_sizing_in_scope)
        self.assertFalse(self.policy.risk_approval_in_scope)
        self.assertFalse(self.policy.execution_authority)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_policy_rejects_risk_budget_or_execution_authority(self) -> None:
        raw = POLICY_PATH.read_text(encoding="utf-8").replace(
            '"portfolio_risk_budget_computation_in_scope": false',
            '"portfolio_risk_budget_computation_in_scope": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(NoTradeError):
                NoTradePolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
