from __future__ import annotations

from pathlib import Path
import unittest

from packages.data_quality import (
    ControlEvidence,
    ControlOutcome,
    EligibilityStatus,
    ProvenanceConfidenceError,
    ProvenanceConfidenceEvaluator,
    ProvenanceConfidencePolicy,
)
from packages.historical_data.feature_materialization import FeatureMaterializationError

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/data-quality/provenance-confidence-policy.json"


def policy() -> ProvenanceConfidencePolicy:
    return ProvenanceConfidencePolicy.from_path(POLICY)


def evidence(
    control_id: str,
    *,
    outcome: ControlOutcome = ControlOutcome.PASS,
    confidence_bps: int = 10000,
    digest_char: str = "a",
) -> ControlEvidence:
    return ControlEvidence(
        control_id=control_id,
        outcome=outcome,
        confidence_bps=confidence_bps,
        evidence_sha256=digest_char * 64,
    )


def full_components(*, confidence_bps: int = 10000) -> tuple[ControlEvidence, ...]:
    return (
        evidence("P07-A", confidence_bps=confidence_bps, digest_char="a"),
        evidence("P07-B", confidence_bps=confidence_bps, digest_char="b"),
        evidence("P07-C", confidence_bps=confidence_bps, digest_char="c"),
        evidence("P07-D", confidence_bps=confidence_bps, digest_char="d"),
    )


class ProvenanceConfidencePolicyTests(unittest.TestCase):
    def test_policy_is_explicit_offline_and_vendor_neutral(self):
        value = policy()
        self.assertEqual(value.policy_version, "p07e-v1")
        self.assertEqual(value.score_scale_bps, 10000)
        self.assertEqual(value.eligibility_min_score_bps, 9000)
        self.assertEqual(sum(value.weights.values()), value.score_scale_bps)
        self.assertEqual(value.production_data_quality_vendor, "NOT_SELECTED")


class ProvenanceConfidenceEvaluationTests(unittest.TestCase):
    def test_complete_pass_above_threshold_is_eligible(self):
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(full_components())
        self.assertEqual(result.status, EligibilityStatus.ELIGIBLE)
        self.assertEqual(result.aggregate_confidence_bps, 10000)
        self.assertEqual(result.missing_controls, ())

    def test_complete_pass_below_threshold_is_ineligible(self):
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(
            full_components(confidence_bps=8000)
        )
        self.assertEqual(result.status, EligibilityStatus.INELIGIBLE)
        self.assertEqual(result.aggregate_confidence_bps, 8000)

    def test_any_explicit_fail_is_ineligible(self):
        components = list(full_components())
        components[2] = evidence(
            "P07-C",
            outcome=ControlOutcome.FAIL,
            confidence_bps=10000,
            digest_char="c",
        )
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(tuple(components))
        self.assertEqual(result.status, EligibilityStatus.INELIGIBLE)

    def test_missing_required_evidence_is_unknown(self):
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(
            full_components()[:-1]
        )
        self.assertEqual(result.status, EligibilityStatus.UNKNOWN)
        self.assertIsNone(result.aggregate_confidence_bps)
        self.assertEqual(result.missing_controls, ("P07-D",))

    def test_duplicate_control_evidence_fails_closed(self):
        with self.assertRaises(ProvenanceConfidenceError):
            ProvenanceConfidenceEvaluator(policy()).evaluate(
                (
                    evidence("P07-A"),
                    evidence("P07-A", digest_char="b"),
                )
            )

    def test_unknown_control_fails_closed(self):
        with self.assertRaises(ProvenanceConfidenceError):
            ProvenanceConfidenceEvaluator(policy()).evaluate(
                full_components() + (evidence("P07-X"),)
            )

    def test_invalid_digest_fails_closed(self):
        with self.assertRaises(ProvenanceConfidenceError):
            ControlEvidence(
                control_id="P07-A",
                outcome=ControlOutcome.PASS,
                confidence_bps=10000,
                evidence_sha256="bad",
            )

    def test_confidence_above_scale_fails_closed(self):
        with self.assertRaises(ProvenanceConfidenceError):
            ProvenanceConfidenceEvaluator(policy()).evaluate(
                (
                    evidence("P07-A", confidence_bps=10001),
                    evidence("P07-B"),
                    evidence("P07-C"),
                    evidence("P07-D"),
                )
            )

    def test_input_order_is_deterministic(self):
        components = full_components(confidence_bps=9200)
        first = ProvenanceConfidenceEvaluator(policy()).evaluate(components)
        second = ProvenanceConfidenceEvaluator(policy()).evaluate(
            tuple(reversed(components))
        )
        self.assertEqual(first.components, second.components)
        self.assertEqual(first.aggregate_confidence_bps, second.aggregate_confidence_bps)
        self.assertEqual(first.evidence_identity, second.evidence_identity)

    def test_feature_quality_adapter_preserves_contract(self):
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(full_components())
        quality = result.to_feature_quality_eligibility()
        self.assertEqual(quality.status, "ELIGIBLE")
        self.assertEqual(quality.quality_policy_version, "p07e-v1")
        self.assertEqual(quality.evidence_sha256, result.evidence_identity)

    def test_unknown_adapter_is_not_promoted_to_eligible(self):
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(full_components()[:-1])
        quality = result.to_feature_quality_eligibility()
        self.assertEqual(quality.status, "UNKNOWN")
        self.assertNotEqual(quality.status, "ELIGIBLE")

    def test_ineligible_adapter_is_not_promoted_to_eligible(self):
        result = ProvenanceConfidenceEvaluator(policy()).evaluate(
            full_components(confidence_bps=8000)
        )
        quality = result.to_feature_quality_eligibility()
        self.assertEqual(quality.status, "INELIGIBLE")
        self.assertNotEqual(quality.status, "ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
