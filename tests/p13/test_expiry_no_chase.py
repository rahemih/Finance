from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.expiry_no_chase import (
    ExpiryNoChaseContext,
    ExpiryNoChaseError,
    ExpiryNoChasePolicy,
    assess_expiry_no_chase,
)
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/expiry-no-chase-policy.json"


class ExpiryNoChaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ExpiryNoChasePolicy.from_path(POLICY_PATH)

    def candidate(self, *, eligible: bool = True) -> OpportunityCandidate:
        return OpportunityCandidate(
            candidate_id="a" * 64,
            window_id="window-1",
            asset_id="BTC-USD",
            strategy_id="trend-v1",
            timeframe="1h",
            regime_label="ALIGNED_BULLISH",
            session_labels=("EUROPE", "US"),
            sample_count=80,
            adjusted_edge_bps=150,
            timing_class="PREFERRED" if eligible else "WEAK",
            scanner_state="ELIGIBLE_TIMING_CONTEXT" if eligible else "OBSERVE_ONLY",
            eligible=eligible,
            provenance_sha256=("b" * 64,),
            source_dataset_versions=("p13c-v1",),
        )

    def context(
        self,
        *,
        no_trade: NoTradeDecision | None = None,
        observed_at_ns: int = 1_000,
        expires_at_ns: int = 2_000,
        as_of_ns: int = 1_500,
        price_displacement_bps: int = 40,
        maximum_chase_bps: int = 50,
    ) -> ExpiryNoChaseContext:
        candidate = self.candidate()
        decision = no_trade or NoTradeDecision(
            candidate_id=candidate.candidate_id,
            decision="TIMING_ELIGIBLE",
            reason_codes=(),
        )
        return ExpiryNoChaseContext(
            candidate=candidate,
            no_trade_decision=decision,
            observed_at_ns=observed_at_ns,
            expires_at_ns=expires_at_ns,
            as_of_ns=as_of_ns,
            price_displacement_bps=price_displacement_bps,
            maximum_chase_bps=maximum_chase_bps,
        )

    def test_clean_context_is_active(self) -> None:
        result = assess_expiry_no_chase(self.context(), policy=self.policy)
        self.assertEqual(result.state, "ACTIVE")
        self.assertEqual(result.age_ns, 500)
        self.assertEqual(result.remaining_ns, 500)

    def test_upstream_no_trade_cannot_be_bypassed(self) -> None:
        decision = NoTradeDecision(
            candidate_id="a" * 64,
            decision="NO_TRADE",
            reason_codes=("HIGH_EVENT_RISK",),
        )
        result = assess_expiry_no_chase(
            self.context(no_trade=decision, as_of_ns=3_000, price_displacement_bps=500),
            policy=self.policy,
        )
        self.assertEqual(result.state, "BLOCKED_BY_NO_TRADE")
        self.assertEqual(result.upstream_no_trade_reason_codes, ("HIGH_EVENT_RISK",))

    def test_expiry_boundary_is_fail_closed(self) -> None:
        at_expiry = assess_expiry_no_chase(
            self.context(as_of_ns=2_000),
            policy=self.policy,
        )
        after_expiry = assess_expiry_no_chase(
            self.context(as_of_ns=2_001),
            policy=self.policy,
        )
        self.assertEqual(at_expiry.state, "EXPIRED")
        self.assertEqual(after_expiry.state, "EXPIRED")

    def test_displacement_beyond_explicit_limit_is_no_chase(self) -> None:
        result = assess_expiry_no_chase(
            self.context(price_displacement_bps=51, maximum_chase_bps=50),
            policy=self.policy,
        )
        self.assertEqual(result.state, "NO_CHASE")
        boundary = assess_expiry_no_chase(
            self.context(price_displacement_bps=50, maximum_chase_bps=50),
            policy=self.policy,
        )
        self.assertEqual(boundary.state, "ACTIVE")

    def test_identity_and_decision_reason_consistency_fail_closed(self) -> None:
        mismatch = NoTradeDecision(
            candidate_id="c" * 64,
            decision="TIMING_ELIGIBLE",
            reason_codes=(),
        )
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(self.context(no_trade=mismatch), policy=self.policy)
        invalid_reasons = NoTradeDecision(
            candidate_id="a" * 64,
            decision="TIMING_ELIGIBLE",
            reason_codes=("HIGH_EVENT_RISK",),
        )
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(self.context(no_trade=invalid_reasons), policy=self.policy)

    def test_invalid_temporal_ordering_fails_closed(self) -> None:
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(
                self.context(expires_at_ns=1_000),
                policy=self.policy,
            )
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(
                self.context(as_of_ns=999),
                policy=self.policy,
            )

    def test_basis_point_bounds_fail_closed(self) -> None:
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(
                self.context(price_displacement_bps=10001),
                policy=self.policy,
            )
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(
                self.context(maximum_chase_bps=-1),
                policy=self.policy,
            )

    def test_noneligible_candidate_cannot_be_timing_eligible(self) -> None:
        candidate = self.candidate(eligible=False)
        context = replace(
            self.context(),
            candidate=candidate,
            no_trade_decision=NoTradeDecision(
                candidate_id=candidate.candidate_id,
                decision="TIMING_ELIGIBLE",
                reason_codes=(),
            ),
        )
        with self.assertRaises(ExpiryNoChaseError):
            assess_expiry_no_chase(context, policy=self.policy)

    def test_policy_has_no_universal_threshold_and_preserves_boundaries(self) -> None:
        self.assertFalse(self.policy.universal_expiry_threshold_defined)
        self.assertFalse(self.policy.universal_chase_threshold_defined)
        self.assertFalse(self.policy.upstream_no_trade_bypass_allowed)
        self.assertFalse(self.policy.signal_probability_in_scope)
        self.assertFalse(self.policy.portfolio_risk_in_scope)
        self.assertFalse(self.policy.position_sizing_in_scope)
        self.assertFalse(self.policy.risk_approval_in_scope)
        self.assertFalse(self.policy.execution_authority)

    def test_policy_rejects_universal_chase_threshold(self) -> None:
        raw = POLICY_PATH.read_text(encoding="utf-8").replace(
            '"universal_chase_threshold_defined": false',
            '"universal_chase_threshold_defined": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(ExpiryNoChaseError):
                ExpiryNoChasePolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
