from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.probability_calibration import (
    CalibrationContext,
    CalibrationObservation,
    ProbabilityCalibrationError,
    ProbabilityCalibrationPolicy,
    build_calibration_model,
    calibrate_probability,
)
from packages.signal_intelligence.weighted_fusion import WeightedFusionResult


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/probability-calibration-policy.json"
OUTCOME_DEF = "d" * 64
DATASET = "e" * 64


def context(*, subject: str = "BTC-USD") -> CalibrationContext:
    return CalibrationContext(
        subject_id=subject,
        strategy_id="trend-flow-v1",
        timeframe="1h",
        regime_label="TRENDING",
        session_label="EUROPE_US_OVERLAP",
        outcome_definition_sha256=OUTCOME_DEF,
    )


def observation(
    *,
    score: int = 3000,
    success: bool = True,
    decision_ns: int = 1000,
    observed_ns: int = 1500,
    provenance_digit: str = "1",
    ctx: CalibrationContext | None = None,
) -> CalibrationObservation:
    return CalibrationObservation(
        context=ctx or context(),
        signed_score_bps=score,
        direction=1 if score > 0 else -1,
        success=success,
        decision_as_of_ns=decision_ns,
        outcome_observed_ns=observed_ns,
        source_dataset_version_sha256=DATASET,
        provenance_sha256=provenance_digit * 64,
    )


def fusion(*, subject: str = "BTC-USD", score: int = 3000, state: str = "FUSED") -> WeightedFusionResult:
    return WeightedFusionResult(
        subject_id=subject,
        as_of_time_ns=3000,
        state=state,
        signed_score_bps=score if state == "FUSED" else None,
        direction=(1 if score > 0 else -1) if state == "FUSED" else 0,
        representatives=(),
        supporting_groups=(),
        opposing_groups=(),
        neutral_groups=(),
        source_families=("TECHNICAL", "ORDER_FLOW_LIQUIDITY"),
        excluded_expired_evidence_ids=(),
        excluded_correlated_evidence_ids=(),
        veto_codes=(),
    )


class ProbabilityCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ProbabilityCalibrationPolicy.from_path(POLICY_PATH)
        self.ctx = context()

    def model(self, records: tuple[CalibrationObservation, ...]):
        return build_calibration_model(
            policy=self.policy,
            context=self.ctx,
            training_cutoff_ns=2000,
            calibration_dataset_version_sha256=DATASET,
            observations=records,
        )

    def five_records(self) -> tuple[CalibrationObservation, ...]:
        return (
            observation(success=True, provenance_digit="1"),
            observation(success=True, provenance_digit="2"),
            observation(success=True, provenance_digit="3"),
            observation(success=True, provenance_digit="4"),
            observation(success=False, provenance_digit="5"),
        )

    def test_future_outcome_after_training_cutoff_fails_closed(self) -> None:
        with self.assertRaises(ProbabilityCalibrationError):
            self.model((observation(observed_ns=2001),))

    def test_outcome_before_decision_fails_closed(self) -> None:
        with self.assertRaises(ProbabilityCalibrationError):
            observation(decision_ns=1500, observed_ns=1499)

    def test_mixed_calibration_context_fails_closed(self) -> None:
        with self.assertRaises(ProbabilityCalibrationError):
            self.model((
                observation(),
                observation(ctx=context(subject="ETH-USD"), provenance_digit="2"),
            ))

    def test_duplicate_observation_fails_closed(self) -> None:
        item = observation()
        with self.assertRaises(ProbabilityCalibrationError):
            self.model((item, item))

    def test_model_identity_is_input_order_independent(self) -> None:
        records = self.five_records()
        left = self.model(records)
        right = self.model(tuple(reversed(records)))
        self.assertEqual(left.model_id, right.model_id)
        self.assertEqual(left.observation_ids, right.observation_ids)

    def test_empirical_probability_is_raw_success_frequency(self) -> None:
        model = self.model(self.five_records())
        result = calibrate_probability(model=model, fusion=fusion(), as_of_time_ns=3000)
        self.assertEqual(result.state, "CALIBRATED")
        self.assertEqual(result.probability_bps, 8000)
        self.assertEqual(result.sample_count, 5)
        self.assertEqual(result.success_count, 4)
        self.assertEqual((result.lower_abs_score_bps, result.upper_abs_score_exclusive_bps), (2500, 5000))

    def test_score_bin_boundary_is_deterministic(self) -> None:
        records = tuple(
            observation(score=2499, success=(index < 3), provenance_digit=str(index + 1))
            for index in range(5)
        ) + tuple(
            observation(score=2500, success=(index < 4), provenance_digit=chr(ord("a") + index))
            for index in range(5)
        )
        model = self.model(records)
        low = calibrate_probability(model=model, fusion=fusion(score=2499), as_of_time_ns=3000)
        high = calibrate_probability(model=model, fusion=fusion(score=2500), as_of_time_ns=3000)
        self.assertEqual(low.probability_bps, 6000)
        self.assertEqual(high.probability_bps, 8000)
        self.assertEqual(low.upper_abs_score_exclusive_bps, 2500)
        self.assertEqual(high.lower_abs_score_bps, 2500)

    def test_insufficient_sample_count_returns_explicit_state(self) -> None:
        model = self.model((
            observation(provenance_digit="1"),
            observation(provenance_digit="2"),
            observation(provenance_digit="3"),
            observation(provenance_digit="4"),
        ))
        result = calibrate_probability(model=model, fusion=fusion(), as_of_time_ns=3000)
        self.assertEqual(result.state, "INSUFFICIENT_CALIBRATION_DATA")
        self.assertIsNone(result.probability_bps)
        self.assertEqual(result.sample_count, 4)

    def test_prediction_must_be_after_training_cutoff(self) -> None:
        model = self.model(self.five_records())
        with self.assertRaises(ProbabilityCalibrationError):
            calibrate_probability(model=model, fusion=fusion(), as_of_time_ns=2000)

    def test_only_directional_fused_result_may_be_calibrated(self) -> None:
        model = self.model(self.five_records())
        with self.assertRaises(ProbabilityCalibrationError):
            calibrate_probability(model=model, fusion=fusion(state="BLOCKED"), as_of_time_ns=3000)

    def test_subject_mismatch_fails_closed(self) -> None:
        model = self.model(self.five_records())
        with self.assertRaises(ProbabilityCalibrationError):
            calibrate_probability(model=model, fusion=fusion(subject="ETH-USD"), as_of_time_ns=3000)

    def test_prediction_payload_defers_uncertainty_and_tp_stop(self) -> None:
        model = self.model(self.five_records())
        result = calibrate_probability(model=model, fusion=fusion(), as_of_time_ns=3000)
        payload = result.payload()
        self.assertIsNone(payload["confidence_interval"])
        self.assertIsNone(payload["tp_probability"])
        self.assertIsNone(payload["stop_probability"])

    def test_policy_rejects_priors_smoothing_llm_and_uncertainty(self) -> None:
        original = POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"synthetic_prior_enabled": false', '"synthetic_prior_enabled": true'),
            original.replace('"smoothing_enabled": false', '"smoothing_enabled": true'),
            original.replace('"llm_probability_authority": false', '"llm_probability_authority": true'),
            original.replace('"confidence_interval_in_scope": false', '"confidence_interval_in_scope": true'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ProbabilityCalibrationError):
                    ProbabilityCalibrationPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
