from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.signal_intelligence.persian_explainability import PersianSignalExplanation
from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.red_team_challenge import RedTeamChallenge, RedTeamFinding
from packages.signal_intelligence.signal_output_contract import (
    CandidatePriceGeometry,
    SignalOutputContractError,
    SignalOutputPolicy,
    build_signal_output,
)
from packages.signal_intelligence.tp_stop_probability import BarrierPlanContext, TPStopOutcomeProbability
from packages.signal_intelligence.weighted_fusion import FusionRepresentative, WeightedFusionResult
from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/signal-output-contract-policy.json"


def candidate(*, eligible: bool = True) -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id="candidate-1",
        window_id="window-1",
        asset_id="BTC-USD",
        strategy_id="trend-flow-v1",
        timeframe="1h",
        regime_label="TRENDING",
        session_labels=("EUROPE_US_OVERLAP",),
        sample_count=120,
        adjusted_edge_bps=4200,
        timing_class="PREFERRED",
        scanner_state="ELIGIBLE_TIMING_CONTEXT" if eligible else "OBSERVE_ONLY",
        eligible=eligible,
        provenance_sha256=("1" * 64,),
        source_dataset_versions=("dataset-v1",),
    )


def no_trade(*, decision: str = "TIMING_ELIGIBLE", reasons: tuple[str, ...] = ()) -> NoTradeDecision:
    return NoTradeDecision(candidate_id="candidate-1", decision=decision, reason_codes=reasons)


def expiry(*, state: str = "ACTIVE") -> ExpiryNoChaseAssessment:
    return ExpiryNoChaseAssessment(
        candidate_id="candidate-1",
        state=state,
        observed_at_ns=1000,
        expires_at_ns=5000,
        as_of_ns=3000,
        age_ns=2000,
        remaining_ns=2000 if state == "ACTIVE" else 0,
        price_displacement_bps=20,
        maximum_chase_bps=50,
        upstream_no_trade_reason_codes=(),
    )


def fusion(*, direction: int = 1, state: str = "FUSED") -> WeightedFusionResult:
    if state == "FUSED":
        return WeightedFusionResult(
            subject_id="BTC-USD",
            as_of_time_ns=3000,
            state="FUSED",
            signed_score_bps=4200 if direction > 0 else -4200,
            direction=direction,
            representatives=(
                FusionRepresentative("1" * 64, "TECH_TREND", "TECHNICAL", direction, 7000 * direction),
                FusionRepresentative("2" * 64, "FLOW_DELTA", "ORDER_FLOW_LIQUIDITY", direction, 6200 * direction),
            ),
            supporting_groups=("FLOW_DELTA", "TECH_TREND"),
            opposing_groups=(),
            neutral_groups=(),
            source_families=("ORDER_FLOW_LIQUIDITY", "TECHNICAL"),
            excluded_expired_evidence_ids=("e" * 64,),
            excluded_correlated_evidence_ids=(),
            veto_codes=(),
        )
    return WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state=state,
        signed_score_bps=None,
        direction=0,
        representatives=(),
        supporting_groups=(),
        opposing_groups=(),
        neutral_groups=(),
        source_families=("TIMING_OPPORTUNITY",),
        excluded_expired_evidence_ids=(),
        excluded_correlated_evidence_ids=(),
        veto_codes=("P13_NO_TRADE",) if state == "BLOCKED" else (),
    )


def qualification(*, state: str = "QUALIFIED", probability: int | None = 7200) -> ProbabilityUncertaintyQualification:
    return ProbabilityUncertaintyQualification(
        prediction_id="b" * 64,
        empirical_probability_bps=probability,
        sample_count=120,
        success_count=86,
        state=state,
        sample_support="STRONG" if state == "QUALIFIED" else "INSUFFICIENT",
        confidence_level_bps=9500,
        confidence_interval_lower_bps=6300 if probability is not None else None,
        confidence_interval_upper_bps=7950 if probability is not None else None,
        interval_half_width_bps=825 if probability is not None else None,
        regime_similarity_bps=8300,
        regime_dissimilarity_bps=1700,
        regime_uncertainty_bps=800,
        overall_uncertainty_bps=800 if state == "QUALIFIED" else 10000,
        dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",) if state == "QUALIFIED" else ("INSUFFICIENT_CALIBRATION_DATA",),
        regime_evidence_id="c" * 64,
    )


def barrier(*, direction: int = 1, asset: str = "BTC-USD") -> BarrierPlanContext:
    return BarrierPlanContext(
        subject_id=asset,
        strategy_id="trend-flow-v1",
        timeframe="1h",
        regime_label="TRENDING",
        session_label="EUROPE_US_OVERLAP",
        direction=direction,
        target_distance_bps=300,
        stop_distance_bps=150,
        evaluation_horizon_steps=12,
        outcome_definition_sha256="d" * 64,
    )


def outcomes(q: ProbabilityUncertaintyQualification, *, state: str = "CALIBRATED_TP_STOP") -> TPStopOutcomeProbability:
    calibrated = state == "CALIBRATED_TP_STOP"
    return TPStopOutcomeProbability(
        model_id="d" * 64,
        upstream_qualification_id=q.qualification_id,
        as_of_time_ns=3000,
        state=state,
        tp_first_probability_bps=6500 if calibrated else None,
        stop_first_probability_bps=2500 if calibrated else None,
        neither_probability_bps=1000 if calibrated else None,
        sample_count=60,
        tp_first_count=39,
        stop_first_count=15,
        neither_count=6,
        general_empirical_probability_bps=q.empirical_probability_bps,
        general_overall_uncertainty_bps=q.overall_uncertainty_bps,
        outcome_definition_sha256="d" * 64,
    )


def explanation(f: WeightedFusionResult, q: ProbabilityUncertaintyQualification | None, o: TPStopOutcomeProbability | None) -> PersianSignalExplanation:
    return PersianSignalExplanation(
        subject_id=f.subject_id,
        as_of_time_ns=f.as_of_time_ns,
        fusion_id=f.fusion_id,
        fusion_state=f.state,
        fusion_direction=f.direction,
        qualification_id=q.qualification_id if q is not None else None,
        tp_stop_prediction_id=o.prediction_id if o is not None else None,
        summary_fa="خلاصه تحلیلی",
        supporting_factors_fa=("عامل تأییدکننده: TECH_TREND",),
        opposing_factors_fa=(),
        neutral_factors_fa=(),
        veto_factors_fa=("دلیل منع: P13_NO_TRADE",) if f.state == "BLOCKED" else (),
        probability_fa="72.00٪" if q is not None and q.empirical_probability_bps is not None else None,
        uncertainty_fa="8.00٪" if q is not None else None,
        tp_stop_fa="TP/Stop" if o is not None else None,
        evidence_quality_fa="کیفیت شواهد",
        empirical_probability_bps=q.empirical_probability_bps if q is not None else None,
        overall_uncertainty_bps=q.overall_uncertainty_bps if q is not None else None,
        tp_first_probability_bps=o.tp_first_probability_bps if o is not None else None,
        stop_first_probability_bps=o.stop_first_probability_bps if o is not None else None,
        neither_probability_bps=o.neither_probability_bps if o is not None else None,
    )


def challenge(f: WeightedFusionResult, e: PersianSignalExplanation, q: ProbabilityUncertaintyQualification | None, o: TPStopOutcomeProbability | None, *, disposition: str = "CLEAR") -> RedTeamChallenge:
    findings: tuple[RedTeamFinding, ...]
    if disposition == "CLEAR":
        findings = ()
    elif disposition == "CAUTION":
        findings = (RedTeamFinding("OPPOSING_EVIDENCE", "CAUTION", "شواهد مخالف وجود دارد."),)
    else:
        findings = (RedTeamFinding("UPSTREAM_BLOCKED", "REJECT", "منع قطعی برقرار است."),)
    return RedTeamChallenge(
        subject_id=f.subject_id,
        as_of_time_ns=f.as_of_time_ns,
        fusion_id=f.fusion_id,
        qualification_id=q.qualification_id if q is not None else None,
        tp_stop_prediction_id=o.prediction_id if o is not None else None,
        explanation_id=e.explanation_id,
        disposition=disposition,
        findings=findings,
        empirical_probability_bps=q.empirical_probability_bps if q is not None else None,
        overall_uncertainty_bps=q.overall_uncertainty_bps if q is not None else None,
        tp_first_probability_bps=o.tp_first_probability_bps if o is not None else None,
        stop_first_probability_bps=o.stop_first_probability_bps if o is not None else None,
    )


def geometry(*, short: bool = False) -> CandidatePriceGeometry:
    return CandidatePriceGeometry(
        price_scale=100,
        reference_price_scaled=100000,
        entry_low_scaled=99500,
        entry_high_scaled=100500,
        entry_anchor_scaled=100000,
        invalidation_price_scaled=102000 if short else 98000,
        geometry_version_sha256="f" * 64,
    )


class SignalOutputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SignalOutputPolicy.from_path(POLICY_PATH)

    def build(
        self,
        *,
        direction: int = 1,
        no_trade_decision: str = "TIMING_ELIGIBLE",
        expiry_state: str = "ACTIVE",
        challenge_disposition: str = "CLEAR",
        fusion_state: str = "FUSED",
        uncertainty_state: str = "QUALIFIED",
        outcome_state: str = "CALIBRATED_TP_STOP",
        price_geometry: CandidatePriceGeometry | None = None,
        eligible: bool = True,
    ):
        f = fusion(direction=direction, state=fusion_state)
        if fusion_state == "FUSED":
            q = qualification(state=uncertainty_state, probability=7200 if uncertainty_state == "QUALIFIED" else None)
            o = outcomes(q, state=outcome_state)
            b = barrier(direction=direction)
        else:
            q = None
            o = None
            b = None
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o, disposition=challenge_disposition)
        return build_signal_output(
            policy=self.policy,
            candidate=candidate(eligible=eligible),
            no_trade=no_trade(decision=no_trade_decision, reasons=("HIGH_EVENT_RISK",) if no_trade_decision == "NO_TRADE" else ()),
            expiry=expiry(state=expiry_state),
            fusion=f,
            uncertainty=q,
            barrier=b,
            outcomes=o,
            explanation=e,
            challenge=ch,
            geometry=price_geometry,
        )

    def test_hard_no_trade_maps_to_no_trade(self) -> None:
        result = self.build(no_trade_decision="NO_TRADE", challenge_disposition="REJECT")
        self.assertEqual(result.action, "NO_TRADE")
        self.assertIn("HIGH_EVENT_RISK", result.action_reason_codes)
        self.assertIsNone(result.entry_low_scaled)

    def test_expired_or_no_chase_maps_to_wait(self) -> None:
        self.assertEqual(self.build(expiry_state="EXPIRED").action, "WAIT")
        self.assertEqual(self.build(expiry_state="NO_CHASE").action, "WAIT")

    def test_red_team_reject_maps_to_no_trade(self) -> None:
        result = self.build(challenge_disposition="REJECT")
        self.assertEqual(result.action, "NO_TRADE")

    def test_red_team_caution_maps_to_wait(self) -> None:
        result = self.build(challenge_disposition="CAUTION")
        self.assertEqual(result.action, "WAIT")

    def test_insufficient_probability_or_outcomes_map_to_wait(self) -> None:
        self.assertEqual(self.build(uncertainty_state="INSUFFICIENT_CALIBRATION_DATA", outcome_state="INSUFFICIENT_UPSTREAM_CALIBRATION").action, "WAIT")
        self.assertEqual(self.build(outcome_state="INSUFFICIENT_TP_STOP_DATA").action, "WAIT")

    def test_clear_long_emits_deterministic_geometry(self) -> None:
        result = self.build(price_geometry=geometry())
        self.assertEqual(result.action, "LONG")
        self.assertEqual(result.entry_low_scaled, 99500)
        self.assertEqual(result.entry_high_scaled, 100500)
        self.assertEqual(result.invalidation_price_scaled, 98000)
        self.assertEqual(result.candidate_stop_scaled, 98500)
        self.assertEqual(result.candidate_target_scaled, 103000)
        self.assertEqual(result.empirical_probability_bps, 7200)
        self.assertEqual(result.overall_uncertainty_bps, 800)
        self.assertEqual(result.tp_first_probability_bps, 6500)

    def test_clear_short_emits_deterministic_geometry(self) -> None:
        result = self.build(direction=-1, price_geometry=geometry(short=True))
        self.assertEqual(result.action, "SHORT")
        self.assertEqual(result.candidate_stop_scaled, 101500)
        self.assertEqual(result.candidate_target_scaled, 97000)

    def test_directional_signal_requires_geometry(self) -> None:
        with self.assertRaises(SignalOutputContractError):
            self.build()

    def test_wait_or_no_trade_forbids_geometry(self) -> None:
        with self.assertRaises(SignalOutputContractError):
            self.build(expiry_state="EXPIRED", price_geometry=geometry())

    def test_candidate_identity_mismatch_fails_closed(self) -> None:
        f = fusion()
        q = qualification()
        o = outcomes(q)
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o)
        with self.assertRaises(SignalOutputContractError):
            build_signal_output(
                policy=self.policy,
                candidate=candidate(),
                no_trade=NoTradeDecision(candidate_id="other", decision="TIMING_ELIGIBLE", reason_codes=()),
                expiry=expiry(),
                fusion=f,
                uncertainty=q,
                barrier=barrier(),
                outcomes=o,
                explanation=e,
                challenge=ch,
                geometry=geometry(),
            )

    def test_barrier_context_mismatch_fails_closed(self) -> None:
        f = fusion()
        q = qualification()
        o = outcomes(q)
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o)
        with self.assertRaises(SignalOutputContractError):
            build_signal_output(
                policy=self.policy,
                candidate=candidate(),
                no_trade=no_trade(),
                expiry=expiry(),
                fusion=f,
                uncertainty=q,
                barrier=barrier(asset="ETH-USD"),
                outcomes=o,
                explanation=e,
                challenge=ch,
                geometry=geometry(),
            )

    def test_directionally_incoherent_geometry_fails_closed(self) -> None:
        bad = replace(geometry(), invalidation_price_scaled=100000)
        with self.assertRaises(SignalOutputContractError):
            self.build(price_geometry=bad)

    def test_signal_identity_is_deterministic_and_content_sensitive(self) -> None:
        first = self.build(price_geometry=geometry())
        second = self.build(price_geometry=geometry())
        self.assertEqual(first.signal_id, second.signal_id)
        changed = self.build(direction=-1, price_geometry=geometry(short=True))
        self.assertNotEqual(first.signal_id, changed.signal_id)

    def test_payload_has_no_risk_sizing_leverage_or_execution_authority(self) -> None:
        payload = self.build(price_geometry=geometry()).payload()
        self.assertIsNone(payload["risk_approval"])
        self.assertIsNone(payload["position_size"])
        self.assertIsNone(payload["leverage"])
        self.assertIsNone(payload["execution_command"])


if __name__ == "__main__":
    unittest.main()
