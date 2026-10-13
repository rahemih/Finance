from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.probability_calibration import CalibratedProbability
from packages.signal_intelligence.probability_uncertainty import (
    ProbabilityUncertaintyError,
    ProbabilityUncertaintyPolicy,
    RegimeSimilarityEvidence,
    qualify_probability_uncertainty,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/probability-uncertainty-policy.json"
MODEL_ID = "a" * 64
FUSION_ID = "b" * 64
OUTCOME_DEF = "c" * 64
PROVENANCE = "d" * 64


def calibrated(
    *,
    sample_count: int = 100,
    success_count: int = 60,
    state: str = "CALIBRATED",
    probability_bps: int | None = 6000,
    as_of_ns: int = 3000,
) -> CalibratedProbability:
    return CalibratedProbability(
        model_id=MODEL_ID,
        fusion_id=FUSION_ID,
        as_of_time_ns=as_of_ns,
        state=state,
        probability_bps=probability_bps,
        sample_count=sample_count,
        success_count=success_count,
        lower_abs_score_bps=2500,
        upper_abs_score_exclusive_bps=5000,
        outcome_definition_sha256=OUTCOME_DEF,
    )


def regime(
    prediction: CalibratedProbability,
    *,
    similarity_bps: int = 9000,
    uncertainty_bps: int = 700,
    source_kind: str = "P12_HISTORICAL_ANALOG",
    as_of_ns: int | None = None,
) -> RegimeSimilarityEvidence:
    return RegimeSimilarityEvidence(
        prediction_id=prediction.prediction_id,
        source_kind=source_kind,
        as_of_time_ns=prediction.as_of_time_ns if as_of_ns is None else as_of_ns,
        similarity_bps=similarity_bps,
        uncertainty_bps=uncertainty_bps,
        source_record_id="regime-match-001",
        provenance_sha256=PROVENANCE,
    )


class ProbabilityUncertaintyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ProbabilityUncertaintyPolicy.from_path(POLICY_PATH)

    def test_probability_is_preserved_and_wilson_interval_contains_it(self) -> None:
        prediction = calibrated()
        result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction),
        )
        self.assertEqual(result.state, "QUALIFIED")
        self.assertEqual(result.empirical_probability_bps, prediction.probability_bps)
        self.assertIsNotNone(result.confidence_interval_lower_bps)
        self.assertIsNotNone(result.confidence_interval_upper_bps)
        assert result.confidence_interval_lower_bps is not None
        assert result.confidence_interval_upper_bps is not None
        self.assertLessEqual(result.confidence_interval_lower_bps, 6000)
        self.assertGreaterEqual(result.confidence_interval_upper_bps, 6000)
        self.assertFalse(result.payload()["probability_mutated"])

    def test_larger_sample_same_rate_narrows_interval(self) -> None:
        small = calibrated(sample_count=20, success_count=12)
        large = calibrated(sample_count=200, success_count=120)
        small_result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=small,
            regime=regime(small, similarity_bps=10000, uncertainty_bps=0),
        )
        large_result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=large,
            regime=regime(large, similarity_bps=10000, uncertainty_bps=0),
        )
        assert small_result.interval_half_width_bps is not None
        assert large_result.interval_half_width_bps is not None
        self.assertLess(large_result.interval_half_width_bps, small_result.interval_half_width_bps)

    def test_sample_support_states_are_deterministic(self) -> None:
        minimum = calibrated(sample_count=5, success_count=3)
        moderate = calibrated(sample_count=20, success_count=12)
        strong = calibrated(sample_count=50, success_count=30)
        self.assertEqual(
            qualify_probability_uncertainty(policy=self.policy, calibrated=minimum, regime=regime(minimum)).sample_support,
            "MINIMUM",
        )
        self.assertEqual(
            qualify_probability_uncertainty(policy=self.policy, calibrated=moderate, regime=regime(moderate)).sample_support,
            "MODERATE",
        )
        self.assertEqual(
            qualify_probability_uncertainty(policy=self.policy, calibrated=strong, regime=regime(strong)).sample_support,
            "STRONG",
        )

    def test_regime_dissimilarity_can_dominate_uncertainty(self) -> None:
        prediction = calibrated()
        result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction, similarity_bps=7000, uncertainty_bps=500),
        )
        self.assertEqual(result.overall_uncertainty_bps, 3000)
        self.assertEqual(result.dominant_uncertainty_sources, ("REGIME_DISSIMILARITY",))

    def test_regime_evidence_uncertainty_can_dominate(self) -> None:
        prediction = calibrated()
        result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction, similarity_bps=9500, uncertainty_bps=4000),
        )
        self.assertEqual(result.overall_uncertainty_bps, 4000)
        self.assertEqual(result.dominant_uncertainty_sources, ("REGIME_EVIDENCE_UNCERTAINTY",))

    def test_statistical_interval_can_dominate(self) -> None:
        prediction = calibrated(sample_count=5, success_count=3)
        result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction, similarity_bps=10000, uncertainty_bps=0),
        )
        self.assertEqual(result.overall_uncertainty_bps, result.interval_half_width_bps)
        self.assertEqual(result.dominant_uncertainty_sources, ("STATISTICAL_INTERVAL",))

    def test_prediction_id_and_as_of_mismatch_fail_closed(self) -> None:
        prediction = calibrated()
        other = calibrated(as_of_ns=3001)
        with self.assertRaises(ProbabilityUncertaintyError):
            qualify_probability_uncertainty(
                policy=self.policy,
                calibrated=prediction,
                regime=regime(other),
            )
        with self.assertRaises(ProbabilityUncertaintyError):
            qualify_probability_uncertainty(
                policy=self.policy,
                calibrated=prediction,
                regime=regime(prediction, as_of_ns=2999),
            )

    def test_unapproved_regime_similarity_source_fails_closed(self) -> None:
        prediction = calibrated()
        with self.assertRaises(ProbabilityUncertaintyError):
            qualify_probability_uncertainty(
                policy=self.policy,
                calibrated=prediction,
                regime=regime(prediction, source_kind="LLM_GUESS"),
            )

    def test_invalid_regime_scales_fail_closed(self) -> None:
        prediction = calibrated()
        with self.assertRaises(ProbabilityUncertaintyError):
            RegimeSimilarityEvidence(
                prediction_id=prediction.prediction_id,
                source_kind="P12_HISTORICAL_ANALOG",
                as_of_time_ns=prediction.as_of_time_ns,
                similarity_bps=10001,
                uncertainty_bps=0,
                source_record_id="bad",
                provenance_sha256=PROVENANCE,
            )

    def test_insufficient_calibration_returns_maximum_uncertainty_without_probability(self) -> None:
        prediction = calibrated(
            sample_count=4,
            success_count=3,
            state="INSUFFICIENT_CALIBRATION_DATA",
            probability_bps=None,
        )
        result = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction),
        )
        self.assertEqual(result.state, "INSUFFICIENT_CALIBRATION_DATA")
        self.assertIsNone(result.empirical_probability_bps)
        self.assertIsNone(result.confidence_interval_lower_bps)
        self.assertEqual(result.sample_support, "INSUFFICIENT")
        self.assertEqual(result.overall_uncertainty_bps, 10000)

    def test_inconsistent_empirical_probability_fails_closed(self) -> None:
        prediction = calibrated(probability_bps=6100)
        with self.assertRaises(ProbabilityUncertaintyError):
            qualify_probability_uncertainty(
                policy=self.policy,
                calibrated=prediction,
                regime=regime(prediction),
            )

    def test_qualification_identity_is_deterministic(self) -> None:
        prediction = calibrated()
        first = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction),
        )
        second = qualify_probability_uncertainty(
            policy=self.policy,
            calibrated=prediction,
            regime=regime(prediction),
        )
        self.assertEqual(first.qualification_id, second.qualification_id)
        self.assertFalse(first.payload()["regime_similarity_is_probability"])
        self.assertIsNone(first.payload()["tp_probability"])
        self.assertIsNone(first.payload()["stop_probability"])

    def test_policy_rejects_probability_mutation_llm_and_execution_authority(self) -> None:
        original = POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"probability_mutation_allowed": false', '"probability_mutation_allowed": true'),
            original.replace('"regime_similarity_is_probability": false', '"regime_similarity_is_probability": true'),
            original.replace('"llm_uncertainty_authority": false', '"llm_uncertainty_authority": true'),
            original.replace('"execution_authority_in_scope": false', '"execution_authority_in_scope": true'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ProbabilityUncertaintyError):
                    ProbabilityUncertaintyPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
