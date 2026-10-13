from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.tp_stop_probability import (
    BarrierPlanContext,
    TPStopObservation,
    TPStopProbabilityError,
    TPStopProbabilityPolicy,
    build_tp_stop_model,
    estimate_tp_stop_probabilities,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/tp-stop-probability-policy.json"
OUTCOME_DEF = "d" * 64
DATASET = "e" * 64


def context(*, subject: str = "BTC-USD", target: int = 300, stop: int = 150) -> BarrierPlanContext:
    return BarrierPlanContext(
        subject_id=subject,
        strategy_id="trend-flow-v1",
        timeframe="1h",
        regime_label="TRENDING",
        session_label="EUROPE_US_OVERLAP",
        direction=1,
        target_distance_bps=target,
        stop_distance_bps=stop,
        evaluation_horizon_steps=12,
        outcome_definition_sha256=OUTCOME_DEF,
    )


def observation(
    *,
    outcome: str = "TP_FIRST",
    decision_ns: int = 1000,
    observed_ns: int = 1500,
    provenance_digit: str = "1",
    ctx: BarrierPlanContext | None = None,
) -> TPStopObservation:
    return TPStopObservation(
        context=ctx or context(),
        outcome=outcome,
        decision_as_of_ns=decision_ns,
        outcome_observed_ns=observed_ns,
        source_dataset_version_sha256=DATASET,
        provenance_sha256=provenance_digit * 64,
    )


def qualification(*, state: str = "QUALIFIED", probability: int | None = 7000) -> ProbabilityUncertaintyQualification:
    return ProbabilityUncertaintyQualification(
        prediction_id="a" * 64,
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
        overall_uncertainty_bps=900 if state == "QUALIFIED" else 10000,
        dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",) if state == "QUALIFIED" else ("INSUFFICIENT_CALIBRATION_DATA",),
        regime_evidence_id="b" * 64,
    )


class TPStopProbabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = TPStopProbabilityPolicy.from_path(POLICY_PATH)
        self.ctx = context()

    def model(self, records: tuple[TPStopObservation, ...]):
        return build_tp_stop_model(
            policy=self.policy,
            context=self.ctx,
            training_cutoff_ns=2000,
            outcome_dataset_version_sha256=DATASET,
            observations=records,
        )

    def ten_records(self) -> tuple[TPStopObservation, ...]:
        labels = ("TP_FIRST",) * 6 + ("STOP_FIRST",) * 3 + ("NEITHER",)
        digits = tuple("123456789a")
        return tuple(
            observation(outcome=label, provenance_digit=digit)
            for label, digit in zip(labels, digits)
        )

    def test_ambiguous_or_unresolved_outcome_fails_closed(self) -> None:
        with self.assertRaises(TPStopProbabilityError):
            observation(outcome="AMBIGUOUS")

    def test_future_outcome_after_training_cutoff_fails_closed(self) -> None:
        with self.assertRaises(TPStopProbabilityError):
            self.model((observation(observed_ns=2001),))

    def test_outcome_before_decision_fails_closed(self) -> None:
        with self.assertRaises(TPStopProbabilityError):
            observation(decision_ns=1500, observed_ns=1499)

    def test_mixed_barrier_plan_context_fails_closed(self) -> None:
        with self.assertRaises(TPStopProbabilityError):
            self.model((
                observation(),
                observation(ctx=context(target=500), provenance_digit="2"),
            ))

    def test_duplicate_observation_fails_closed(self) -> None:
        item = observation()
        with self.assertRaises(TPStopProbabilityError):
            self.model((item, item))

    def test_model_identity_is_input_order_independent(self) -> None:
        records = self.ten_records()
        left = self.model(records)
        right = self.model(tuple(reversed(records)))
        self.assertEqual(left.model_id, right.model_id)
        self.assertEqual(left.observation_ids, right.observation_ids)

    def test_insufficient_upstream_probability_returns_no_tp_stop_probability(self) -> None:
        model = self.model(self.ten_records())
        result = estimate_tp_stop_probabilities(
            model=model,
            qualification=qualification(state="INSUFFICIENT_CALIBRATION_DATA", probability=None),
            as_of_time_ns=3000,
        )
        self.assertEqual(result.state, "INSUFFICIENT_UPSTREAM_CALIBRATION")
        self.assertIsNone(result.tp_first_probability_bps)
        self.assertIsNone(result.stop_first_probability_bps)
        self.assertIsNone(result.neither_probability_bps)

    def test_minimum_outcome_sample_shortfall_is_explicit(self) -> None:
        model = self.model((
            observation(outcome="TP_FIRST", provenance_digit="1"),
            observation(outcome="TP_FIRST", provenance_digit="2"),
            observation(outcome="STOP_FIRST", provenance_digit="3"),
            observation(outcome="NEITHER", provenance_digit="4"),
        ))
        result = estimate_tp_stop_probabilities(
            model=model,
            qualification=qualification(),
            as_of_time_ns=3000,
        )
        self.assertEqual(result.state, "INSUFFICIENT_TP_STOP_DATA")
        self.assertIsNone(result.tp_first_probability_bps)
        self.assertEqual(result.general_empirical_probability_bps, 7000)

    def test_raw_empirical_distribution_is_exact_and_sums_to_scale(self) -> None:
        model = self.model(self.ten_records())
        result = estimate_tp_stop_probabilities(
            model=model,
            qualification=qualification(),
            as_of_time_ns=3000,
        )
        self.assertEqual(result.state, "CALIBRATED_TP_STOP")
        self.assertEqual(result.tp_first_probability_bps, 6000)
        self.assertEqual(result.stop_first_probability_bps, 3000)
        self.assertEqual(result.neither_probability_bps, 1000)
        self.assertEqual(
            result.tp_first_probability_bps + result.stop_first_probability_bps + result.neither_probability_bps,
            10000,
        )

    def test_rounding_distribution_still_sums_to_10000(self) -> None:
        records = (
            observation(outcome="TP_FIRST", provenance_digit="1"),
            observation(outcome="STOP_FIRST", provenance_digit="2"),
            observation(outcome="NEITHER", provenance_digit="3"),
            observation(outcome="TP_FIRST", provenance_digit="4"),
            observation(outcome="STOP_FIRST", provenance_digit="5"),
            observation(outcome="NEITHER", provenance_digit="6"),
        )
        model = self.model(records)
        result = estimate_tp_stop_probabilities(model=model, qualification=qualification(), as_of_time_ns=3000)
        probabilities = (
            result.tp_first_probability_bps,
            result.stop_first_probability_bps,
            result.neither_probability_bps,
        )
        self.assertTrue(all(item is not None for item in probabilities))
        self.assertEqual(sum(item for item in probabilities if item is not None), 10000)

    def test_general_directional_probability_remains_separate(self) -> None:
        model = self.model(self.ten_records())
        result = estimate_tp_stop_probabilities(model=model, qualification=qualification(), as_of_time_ns=3000)
        self.assertEqual(result.general_empirical_probability_bps, 7000)
        self.assertEqual(result.tp_first_probability_bps, 6000)
        self.assertNotEqual(result.general_empirical_probability_bps, result.tp_first_probability_bps)
        self.assertFalse(result.payload()["general_probability_equals_tp_probability"])

    def test_prediction_must_be_after_training_cutoff(self) -> None:
        model = self.model(self.ten_records())
        with self.assertRaises(TPStopProbabilityError):
            estimate_tp_stop_probabilities(model=model, qualification=qualification(), as_of_time_ns=2000)

    def test_policy_rejects_priors_smoothing_llm_and_ambiguous_paths(self) -> None:
        original = POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"synthetic_prior_enabled": false', '"synthetic_prior_enabled": true'),
            original.replace('"smoothing_enabled": false', '"smoothing_enabled": true'),
            original.replace('"llm_probability_authority": false', '"llm_probability_authority": true'),
            original.replace('"ambiguous_path_behavior": "REJECT"', '"ambiguous_path_behavior": "INFER"'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(TPStopProbabilityError):
                    TPStopProbabilityPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
