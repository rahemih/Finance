from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.persian_explainability import (
    PersianExplainabilityError,
    PersianExplainabilityPolicy,
    explain_signal_fa,
)
from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.tp_stop_probability import TPStopOutcomeProbability
from packages.signal_intelligence.weighted_fusion import FusionRepresentative, WeightedFusionResult


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/persian-explainability-policy.json"


def representative(*, group: str, family: str, direction: int, score: int, digit: str) -> FusionRepresentative:
    return FusionRepresentative(
        evidence_id=digit * 64,
        independence_group=group,
        source_family=family,
        direction=direction,
        adjusted_signed_bps=score,
    )


def fused() -> WeightedFusionResult:
    reps = (
        representative(group="TECH_TREND", family="TECHNICAL", direction=1, score=7000, digit="1"),
        representative(group="FLOW_DELTA", family="ORDER_FLOW_LIQUIDITY", direction=1, score=6000, digit="2"),
        representative(group="MACRO_GROWTH", family="FUNDAMENTAL_MACRO", direction=-1, score=-3000, digit="3"),
        representative(group="NEWS_CONFIRMED", family="NEWS_SENTIMENT", direction=0, score=0, digit="4"),
    )
    return WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state="FUSED",
        signed_score_bps=2500,
        direction=1,
        representatives=reps,
        supporting_groups=("TECH_TREND", "FLOW_DELTA"),
        opposing_groups=("MACRO_GROWTH",),
        neutral_groups=("NEWS_CONFIRMED",),
        source_families=("TECHNICAL", "ORDER_FLOW_LIQUIDITY", "FUNDAMENTAL_MACRO", "NEWS_SENTIMENT"),
        excluded_expired_evidence_ids=("e" * 64,),
        excluded_correlated_evidence_ids=("f" * 64, "a" * 64),
        veto_codes=(),
    )


def blocked() -> WeightedFusionResult:
    return WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state="BLOCKED",
        signed_score_bps=None,
        direction=0,
        representatives=(),
        supporting_groups=(),
        opposing_groups=(),
        neutral_groups=(),
        source_families=("TIMING_OPPORTUNITY",),
        excluded_expired_evidence_ids=(),
        excluded_correlated_evidence_ids=(),
        veto_codes=("P13_NO_TRADE", "STALE_EVIDENCE"),
    )


def insufficient() -> WeightedFusionResult:
    return WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state="INSUFFICIENT_EVIDENCE",
        signed_score_bps=None,
        direction=0,
        representatives=(),
        supporting_groups=(),
        opposing_groups=(),
        neutral_groups=("MEMORY_ANALOG",),
        source_families=("MARKET_MEMORY",),
        excluded_expired_evidence_ids=("e" * 64,),
        excluded_correlated_evidence_ids=(),
        veto_codes=(),
    )


def uncertainty(*, state: str = "QUALIFIED", probability: int | None = 7000, overall: int = 900) -> ProbabilityUncertaintyQualification:
    return ProbabilityUncertaintyQualification(
        prediction_id="b" * 64,
        empirical_probability_bps=probability,
        sample_count=100,
        success_count=70,
        state=state,
        sample_support="STRONG" if state == "QUALIFIED" else "INSUFFICIENT",
        confidence_level_bps=9500,
        confidence_interval_lower_bps=6100 if probability is not None else None,
        confidence_interval_upper_bps=7800 if probability is not None else None,
        interval_half_width_bps=850 if probability is not None else None,
        regime_similarity_bps=8000,
        regime_dissimilarity_bps=2000,
        regime_uncertainty_bps=900,
        overall_uncertainty_bps=overall,
        dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",) if state == "QUALIFIED" else ("INSUFFICIENT_CALIBRATION_DATA",),
        regime_evidence_id="c" * 64,
    )


def outcomes(
    *,
    upstream_id: str,
    state: str = "CALIBRATED_TP_STOP",
    general_probability: int | None = 7000,
    overall: int = 900,
) -> TPStopOutcomeProbability:
    calibrated = state == "CALIBRATED_TP_STOP"
    return TPStopOutcomeProbability(
        model_id="d" * 64,
        upstream_qualification_id=upstream_id,
        as_of_time_ns=3000,
        state=state,
        tp_first_probability_bps=6000 if calibrated else None,
        stop_first_probability_bps=3000 if calibrated else None,
        neither_probability_bps=1000 if calibrated else None,
        sample_count=50,
        tp_first_count=30,
        stop_first_count=15,
        neither_count=5,
        general_empirical_probability_bps=general_probability,
        general_overall_uncertainty_bps=overall,
        outcome_definition_sha256="e" * 64,
    )


class PersianExplainabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PersianExplainabilityPolicy.from_path(POLICY_PATH)

    def test_blocked_state_preserves_veto_and_has_no_probability(self) -> None:
        result = explain_signal_fa(policy=self.policy, fusion=blocked())
        self.assertEqual(result.fusion_state, "BLOCKED")
        self.assertIn("منع قطعی", result.summary_fa)
        self.assertEqual(result.veto_factors_fa, ("دلیل منع: P13_NO_TRADE", "دلیل منع: STALE_EVIDENCE"))
        self.assertIsNone(result.probability_fa)
        self.assertIsNone(result.empirical_probability_bps)

    def test_insufficient_evidence_has_no_probability(self) -> None:
        result = explain_signal_fa(policy=self.policy, fusion=insufficient())
        self.assertEqual(result.fusion_state, "INSUFFICIENT_EVIDENCE")
        self.assertIn("کافی نیست", result.summary_fa)
        self.assertIsNone(result.probability_fa)
        self.assertIn("شواهد منقضی کنارگذاشته‌شده: 1", result.evidence_quality_fa)

    def test_directional_fused_requires_uncertainty_and_outcomes(self) -> None:
        with self.assertRaises(PersianExplainabilityError):
            explain_signal_fa(policy=self.policy, fusion=fused())

    def test_qualification_lineage_mismatch_fails_closed(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id="f" * 64)
        with self.assertRaises(PersianExplainabilityError):
            explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)

    def test_general_probability_mismatch_fails_closed(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id=q.qualification_id, general_probability=6900)
        with self.assertRaises(PersianExplainabilityError):
            explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)

    def test_overall_uncertainty_mismatch_fails_closed(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id=q.qualification_id, overall=901)
        with self.assertRaises(PersianExplainabilityError):
            explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)

    def test_qualified_explanation_renders_exact_values_in_persian(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id=q.qualification_id)
        result = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)
        self.assertIn("70.00٪", result.probability_fa or "")
        self.assertIn("95.00٪", result.uncertainty_fa or "")
        self.assertIn("61.00٪", result.uncertainty_fa or "")
        self.assertIn("78.00٪", result.uncertainty_fa or "")
        self.assertIn("60.00٪", result.tp_stop_fa or "")
        self.assertIn("30.00٪", result.tp_stop_fa or "")
        self.assertIn("10.00٪", result.tp_stop_fa or "")
        self.assertEqual(result.empirical_probability_bps, 7000)
        self.assertEqual(result.overall_uncertainty_bps, 900)

    def test_supporting_opposing_and_neutral_groups_are_deterministic(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id=q.qualification_id)
        result = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)
        self.assertEqual(result.supporting_factors_fa, ("عامل تأییدکننده: FLOW_DELTA", "عامل تأییدکننده: TECH_TREND"))
        self.assertEqual(result.opposing_factors_fa, ("عامل مخالف: MACRO_GROWTH",))
        self.assertEqual(result.neutral_factors_fa, ("عامل خنثی: NEWS_CONFIRMED",))

    def test_insufficient_upstream_is_described_without_invented_probability(self) -> None:
        q = uncertainty(state="INSUFFICIENT_CALIBRATION_DATA", probability=None, overall=10000)
        o = outcomes(
            upstream_id=q.qualification_id,
            state="INSUFFICIENT_UPSTREAM_CALIBRATION",
            general_probability=None,
            overall=10000,
        )
        result = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)
        self.assertIn("کافی نیست", result.probability_fa or "")
        self.assertIsNone(result.empirical_probability_bps)
        self.assertIsNone(result.tp_first_probability_bps)

    def test_explanation_identity_is_deterministic_and_content_sensitive(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id=q.qualification_id)
        first = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)
        second = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o)
        self.assertEqual(first.explanation_id, second.explanation_id)
        q2 = uncertainty(overall=901)
        o2 = outcomes(upstream_id=q2.qualification_id, overall=901)
        changed = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q2, outcomes=o2)
        self.assertNotEqual(first.explanation_id, changed.explanation_id)

    def test_payload_has_no_final_action_risk_or_execution_authority(self) -> None:
        q = uncertainty()
        o = outcomes(upstream_id=q.qualification_id)
        payload = explain_signal_fa(policy=self.policy, fusion=fused(), uncertainty=q, outcomes=o).payload()
        self.assertFalse(payload["probability_mutated"])
        self.assertFalse(payload["uncertainty_mutated"])
        self.assertIsNone(payload["final_signal_action"])
        self.assertIsNone(payload["risk_approval"])
        self.assertIsNone(payload["position_size"])
        self.assertIsNone(payload["execution_command"])

    def test_policy_rejects_llm_numeric_probability_mutation_and_final_action(self) -> None:
        original = POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"llm_freeform_numeric_authority": false', '"llm_freeform_numeric_authority": true'),
            original.replace('"probability_mutation_allowed": false', '"probability_mutation_allowed": true'),
            original.replace('"final_signal_action_in_scope": false', '"final_signal_action_in_scope": true'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(PersianExplainabilityError):
                    PersianExplainabilityPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
