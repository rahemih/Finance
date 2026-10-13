from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate
from packages.timing_opportunity.scenario_engine import (
    ScenarioEngineError,
    ScenarioEnginePolicy,
    build_scenarios,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/scenario-engine-policy.json"


class ScenarioEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ScenarioEnginePolicy.from_path(POLICY_PATH)
        self.candidate = OpportunityCandidate(
            candidate_id="a" * 64,
            window_id="window-1",
            asset_id="BTC-USD",
            strategy_id="trend-v1",
            timeframe="1h",
            regime_label="ALIGNED_BULLISH",
            session_labels=("EUROPE", "US"),
            sample_count=64,
            adjusted_edge_bps=140,
            timing_class="PREFERRED",
            scanner_state="ELIGIBLE_TIMING_CONTEXT",
            eligible=True,
            provenance_sha256=("b" * 64,),
            source_dataset_versions=("p13g-fixture-v1",),
        )
        self.eligible = NoTradeDecision(
            candidate_id=self.candidate.candidate_id,
            decision="TIMING_ELIGIBLE",
            reason_codes=(),
        )
        self.active = ExpiryNoChaseAssessment(
            candidate_id=self.candidate.candidate_id,
            state="ACTIVE",
            observed_at_ns=100,
            expires_at_ns=300,
            as_of_ns=200,
            age_ns=100,
            remaining_ns=100,
            price_displacement_bps=10,
            maximum_chase_bps=20,
            upstream_no_trade_reason_codes=(),
        )

    def test_active_context_generates_three_conditional_frames(self) -> None:
        result = build_scenarios(self.candidate, self.eligible, self.active, policy=self.policy)
        self.assertEqual(result.state, "CONDITIONAL_SCENARIOS")
        self.assertIsNone(result.block_reason)
        self.assertEqual(
            tuple(frame.scenario_kind for frame in result.frames),
            ("CONTINUATION", "DETERIORATION", "INVALIDATION"),
        )
        self.assertEqual(len({frame.scenario_id for frame in result.frames}), 3)

    def test_identical_inputs_are_deterministic(self) -> None:
        first = build_scenarios(self.candidate, self.eligible, self.active, policy=self.policy)
        second = build_scenarios(self.candidate, self.eligible, self.active, policy=self.policy)
        self.assertEqual(first, second)

    def test_expired_and_no_chase_are_non_actionable(self) -> None:
        for state in ("EXPIRED", "NO_CHASE"):
            assessment = replace(self.active, state=state)
            result = build_scenarios(self.candidate, self.eligible, assessment, policy=self.policy)
            self.assertEqual(result.state, "NON_ACTIONABLE")
            self.assertEqual(result.frames, ())
            self.assertEqual(result.block_reason, state)

    def test_upstream_no_trade_is_non_actionable_and_non_bypassable(self) -> None:
        no_trade = NoTradeDecision(
            candidate_id=self.candidate.candidate_id,
            decision="NO_TRADE",
            reason_codes=("HIGH_EVENT_RISK",),
        )
        blocked = replace(
            self.active,
            state="BLOCKED_BY_NO_TRADE",
            upstream_no_trade_reason_codes=("HIGH_EVENT_RISK",),
        )
        result = build_scenarios(self.candidate, no_trade, blocked, policy=self.policy)
        self.assertEqual(result.state, "NON_ACTIONABLE")
        self.assertEqual(result.frames, ())
        self.assertEqual(result.block_reason, "BLOCKED_BY_NO_TRADE")

    def test_candidate_identity_mismatch_fails_closed(self) -> None:
        with self.assertRaises(ScenarioEngineError):
            build_scenarios(
                self.candidate,
                replace(self.eligible, candidate_id="c" * 64),
                self.active,
                policy=self.policy,
            )
        with self.assertRaises(ScenarioEngineError):
            build_scenarios(
                self.candidate,
                self.eligible,
                replace(self.active, candidate_id="d" * 64),
                policy=self.policy,
            )

    def test_upstream_decision_state_inconsistency_fails_closed(self) -> None:
        with self.assertRaises(ScenarioEngineError):
            build_scenarios(
                self.candidate,
                NoTradeDecision(self.candidate.candidate_id, "NO_TRADE", ("DEGRADED_DATA",)),
                self.active,
                policy=self.policy,
            )
        with self.assertRaises(ScenarioEngineError):
            build_scenarios(
                self.candidate,
                self.eligible,
                replace(self.active, state="BLOCKED_BY_NO_TRADE"),
                policy=self.policy,
            )

    def test_unknown_expiry_state_fails_closed(self) -> None:
        with self.assertRaises(ScenarioEngineError):
            build_scenarios(
                self.candidate,
                self.eligible,
                replace(self.active, state="UNKNOWN"),
                policy=self.policy,
            )

    def test_policy_rejects_probability_target_sizing_risk_or_execution_scope(self) -> None:
        self.assertFalse(self.policy.scenario_probability_in_scope)
        self.assertFalse(self.policy.confidence_score_in_scope)
        self.assertFalse(self.policy.price_target_in_scope)
        self.assertFalse(self.policy.position_sizing_in_scope)
        self.assertFalse(self.policy.risk_approval_in_scope)
        self.assertFalse(self.policy.execution_authority)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")
        raw = POLICY_PATH.read_text(encoding="utf-8").replace(
            '"scenario_probability_in_scope": false',
            '"scenario_probability_in_scope": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(ScenarioEngineError):
                ScenarioEnginePolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
