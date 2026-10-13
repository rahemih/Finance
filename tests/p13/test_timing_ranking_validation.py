from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.best_trading_time import TimingWindowAssessment
from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_ranking import OpportunityRankingResult, RankedOpportunity
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate
from packages.timing_opportunity.scenario_engine import ScenarioFrame, ScenarioSet
from packages.timing_opportunity.session_calendar import SessionContext
from packages.timing_opportunity.validation import (
    TimingRankingValidationBundle,
    TimingRankingValidationError,
    TimingRankingValidationPolicy,
    validate_timing_ranking,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/timing-ranking-validation-policy.json"


class TimingRankingValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = TimingRankingValidationPolicy.from_path(POLICY_PATH)
        self.candidate = OpportunityCandidate(
            candidate_id="a" * 64,
            window_id="window-validation",
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
            source_dataset_versions=("p13h-fixture-v1",),
        )
        self.session = SessionContext(
            timestamp_ns=1,
            calendar_version="P13-A-UTC-BASELINE-V1",
            market_kind="CRYPTO_SPOT",
            weekday_utc=0,
            minute_of_day_utc=840,
            is_market_open=True,
            active_sessions=("EUROPE", "US"),
            overlap_count=2,
            state="OVERLAP",
        )
        self.timing = TimingWindowAssessment(
            window_id=self.candidate.window_id,
            asset_id=self.candidate.asset_id,
            strategy_id=self.candidate.strategy_id,
            timeframe=self.candidate.timeframe,
            regime_label=self.candidate.regime_label,
            session_labels=self.candidate.session_labels,
            sample_count=self.candidate.sample_count,
            mean_edge_bps=170,
            uncertainty_bps=30,
            adjusted_edge_bps=self.candidate.adjusted_edge_bps,
            timing_class=self.candidate.timing_class,
            usable=True,
        )
        self.ranking = OpportunityRankingResult(
            ranked=(RankedOpportunity(1, self.candidate),),
            excluded_candidate_ids=(),
        )
        self.no_trade = NoTradeDecision(self.candidate.candidate_id, "TIMING_ELIGIBLE", ())
        self.expiry = ExpiryNoChaseAssessment(
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
        self.scenarios = ScenarioSet(
            candidate_id=self.candidate.candidate_id,
            state="CONDITIONAL_SCENARIOS",
            upstream_expiry_state="ACTIVE",
            frames=(
                ScenarioFrame("1" * 64, self.candidate.candidate_id, "CONTINUATION", ("A",)),
                ScenarioFrame("2" * 64, self.candidate.candidate_id, "DETERIORATION", ("B",)),
                ScenarioFrame("3" * 64, self.candidate.candidate_id, "INVALIDATION", ("C",)),
            ),
            block_reason=None,
        )

    def bundle(self) -> TimingRankingValidationBundle:
        return TimingRankingValidationBundle(
            session=self.session,
            timing=self.timing,
            candidate=self.candidate,
            ranking=self.ranking,
            no_trade=self.no_trade,
            expiry=self.expiry,
            scenarios=self.scenarios,
        )

    def test_canonical_integrated_fixture_passes(self) -> None:
        report = validate_timing_ranking(self.bundle(), policy=self.policy)
        self.assertEqual(report.state, "PASS")
        self.assertEqual(report.candidate_id, self.candidate.candidate_id)
        self.assertEqual(report.check_codes, self.policy.required_check_codes)

    def test_session_timing_mismatch_fails_closed(self) -> None:
        bundle = replace(self.bundle(), session=replace(self.session, active_sessions=("ASIA",)))
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(bundle, policy=self.policy)

    def test_timing_candidate_metric_mismatch_fails_closed(self) -> None:
        bundle = replace(self.bundle(), candidate=replace(self.candidate, adjusted_edge_bps=139))
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(bundle, policy=self.policy)

    def test_ranking_gap_or_missing_subject_fails_closed(self) -> None:
        gap = OpportunityRankingResult(
            ranked=(RankedOpportunity(2, self.candidate),),
            excluded_candidate_ids=(),
        )
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(replace(self.bundle(), ranking=gap), policy=self.policy)
        missing = OpportunityRankingResult(ranked=(), excluded_candidate_ids=())
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(replace(self.bundle(), ranking=missing), policy=self.policy)

    def test_non_eligible_ranked_candidate_fails_closed(self) -> None:
        bad_candidate = replace(
            self.candidate,
            eligible=False,
            scanner_state="OBSERVE_ONLY",
            timing_class="WEAK",
        )
        ranking = OpportunityRankingResult(
            ranked=(RankedOpportunity(1, bad_candidate),),
            excluded_candidate_ids=(),
        )
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(replace(self.bundle(), ranking=ranking), policy=self.policy)

    def test_no_trade_identity_or_reason_inconsistency_fails_closed(self) -> None:
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(
                replace(self.bundle(), no_trade=replace(self.no_trade, candidate_id="c" * 64)),
                policy=self.policy,
            )
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(
                replace(self.bundle(), no_trade=replace(self.no_trade, reason_codes=("BAD",))),
                policy=self.policy,
            )

    def test_expiry_no_trade_coherence_fails_closed(self) -> None:
        no_trade = NoTradeDecision(self.candidate.candidate_id, "NO_TRADE", ("HIGH_EVENT_RISK",))
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(
                replace(self.bundle(), no_trade=no_trade, expiry=replace(self.expiry, state="ACTIVE")),
                policy=self.policy,
            )

    def test_scenario_expiry_coherence_fails_closed(self) -> None:
        with self.assertRaises(TimingRankingValidationError):
            validate_timing_ranking(
                replace(self.bundle(), scenarios=replace(self.scenarios, upstream_expiry_state="EXPIRED")),
                policy=self.policy,
            )

    def test_policy_rejects_probability_risk_or_execution_authority(self) -> None:
        self.assertFalse(self.policy.validation_is_probability)
        self.assertFalse(self.policy.position_sizing_in_scope)
        self.assertFalse(self.policy.risk_approval_in_scope)
        self.assertFalse(self.policy.execution_authority)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")
        raw = POLICY_PATH.read_text(encoding="utf-8").replace(
            '"validation_is_probability": false',
            '"validation_is_probability": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(TimingRankingValidationError):
                TimingRankingValidationPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
