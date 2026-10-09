from __future__ import annotations

import json
from pathlib import Path
import unittest

from packages.data_quality import (
    ControlEvidence,
    ControlOutcome,
    ProvenanceConfidenceEvaluator,
    ProvenanceConfidencePolicy,
    QuarantineRecord,
    QuarantineRecordIntegrityError,
    QuarantineRouter,
    QuarantineRoutingError,
    QuarantineRoutingPolicy,
    RouteDisposition,
)

ROOT = Path(__file__).resolve().parents[2]
ROUTING_POLICY = ROOT / "config/data-quality/quarantine-routing-policy.json"
QUALITY_POLICY = ROOT / "config/data-quality/provenance-confidence-policy.json"


def quality_evaluator() -> ProvenanceConfidenceEvaluator:
    return ProvenanceConfidenceEvaluator(
        ProvenanceConfidencePolicy.from_path(QUALITY_POLICY)
    )


def components(
    *,
    confidence: int = 10000,
    fail_control: str | None = None,
    omit_control: str | None = None,
) -> tuple[ControlEvidence, ...]:
    values: list[ControlEvidence] = []
    for index, control_id in enumerate(("P07-A", "P07-B", "P07-C", "P07-D")):
        if control_id == omit_control:
            continue
        values.append(
            ControlEvidence(
                control_id=control_id,
                outcome=(
                    ControlOutcome.FAIL
                    if control_id == fail_control
                    else ControlOutcome.PASS
                ),
                confidence_bps=confidence,
                evidence_sha256=(hex(index + 10)[2:] * 64)[:64],
            )
        )
    return tuple(values)


def router() -> QuarantineRouter:
    return QuarantineRouter(QuarantineRoutingPolicy.from_path(ROUTING_POLICY))


class RoutingPolicyTests(unittest.TestCase):
    def test_policy_is_offline_non_destructive_and_vendor_neutral(self):
        policy = QuarantineRoutingPolicy.from_path(ROUTING_POLICY)
        self.assertEqual(policy.policy_version, "p07f-v1")
        self.assertEqual(policy.production_quarantine_storage_vendor, "NOT_SELECTED")
        self.assertGreater(policy.max_reason_codes, 0)


class RoutingDecisionTests(unittest.TestCase):
    def test_eligible_without_critical_reason_is_accepted(self):
        quality = quality_evaluator().evaluate(components())
        decision = router().route(subject_id="dataset:clean", quality=quality)
        self.assertEqual(decision.disposition, RouteDisposition.ACCEPTED_DOWNSTREAM)
        self.assertTrue(decision.downstream_allowed)
        self.assertEqual(decision.reason_codes, ())
        self.assertIsNone(decision.quarantine_record)

    def test_ineligible_is_quarantined_and_denied(self):
        quality = quality_evaluator().evaluate(components(confidence=8000))
        decision = router().route(subject_id="dataset:low-confidence", quality=quality)
        self.assertEqual(decision.disposition, RouteDisposition.QUARANTINED)
        self.assertFalse(decision.downstream_allowed)
        self.assertEqual(decision.reason_codes, ("QUALITY_INELIGIBLE",))
        self.assertIsNotNone(decision.quarantine_record)

    def test_unknown_is_blocked_and_denied(self):
        quality = quality_evaluator().evaluate(components(omit_control="P07-D"))
        decision = router().route(subject_id="dataset:unknown", quality=quality)
        self.assertEqual(decision.disposition, RouteDisposition.BLOCKED_UNKNOWN)
        self.assertFalse(decision.downstream_allowed)
        self.assertEqual(decision.reason_codes, ("QUALITY_UNKNOWN",))
        self.assertIsNotNone(decision.quarantine_record)

    def test_explicit_fail_is_quarantined(self):
        quality = quality_evaluator().evaluate(components(fail_control="P07-C"))
        decision = router().route(subject_id="dataset:failed", quality=quality)
        self.assertEqual(decision.disposition, RouteDisposition.QUARANTINED)
        self.assertFalse(decision.downstream_allowed)

    def test_critical_reason_overrides_eligible(self):
        quality = quality_evaluator().evaluate(components())
        decision = router().route(
            subject_id="dataset:critical",
            quality=quality,
            critical_reason_codes=("MANUAL_GOVERNANCE_BLOCK",),
        )
        self.assertEqual(decision.disposition, RouteDisposition.QUARANTINED)
        self.assertFalse(decision.downstream_allowed)
        self.assertEqual(decision.quality_status.value, "ELIGIBLE")
        self.assertEqual(decision.reason_codes, ("MANUAL_GOVERNANCE_BLOCK",))

    def test_nonaccepted_record_preserves_quality_lineage(self):
        quality = quality_evaluator().evaluate(components(confidence=8000))
        decision = router().route(subject_id="dataset:lineage", quality=quality)
        record = decision.quarantine_record
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.quality_status, quality.status)
        self.assertEqual(record.quality_policy_version, quality.policy_version)
        self.assertEqual(record.quality_evidence_sha256, quality.evidence_identity)

    def test_critical_reason_input_order_is_deterministic(self):
        quality = quality_evaluator().evaluate(components())
        first = router().route(
            subject_id="dataset:order",
            quality=quality,
            critical_reason_codes=("SECURITY_BLOCK", "MANUAL_GOVERNANCE_BLOCK"),
        )
        second = router().route(
            subject_id="dataset:order",
            quality=quality,
            critical_reason_codes=("MANUAL_GOVERNANCE_BLOCK", "SECURITY_BLOCK"),
        )
        self.assertEqual(first.reason_codes, second.reason_codes)
        self.assertEqual(first.decision_id, second.decision_id)

    def test_duplicate_reason_codes_fail_closed(self):
        quality = quality_evaluator().evaluate(components())
        with self.assertRaises(QuarantineRoutingError):
            router().route(
                subject_id="dataset:dup",
                quality=quality,
                critical_reason_codes=("SECURITY_BLOCK", "SECURITY_BLOCK"),
            )

    def test_unsafe_reason_code_fails_closed(self):
        quality = quality_evaluator().evaluate(components())
        with self.assertRaises(QuarantineRoutingError):
            router().route(
                subject_id="dataset:unsafe",
                quality=quality,
                critical_reason_codes=("bad reason",),
            )

    def test_reason_count_limit_fails_closed(self):
        policy = QuarantineRoutingPolicy(
            policy_version="test",
            max_reason_codes=1,
            reason_code_pattern=r"^[A-Z][A-Z0-9_]{0,63}$",
            production_quarantine_storage_vendor="NOT_SELECTED",
        )
        quality = quality_evaluator().evaluate(components())
        with self.assertRaises(QuarantineRoutingError):
            QuarantineRouter(policy).route(
                subject_id="dataset:limit",
                quality=quality,
                critical_reason_codes=("ONE", "TWO"),
            )


class QuarantineRecordTests(unittest.TestCase):
    def test_round_trip_preserves_content_identity(self):
        quality = quality_evaluator().evaluate(components(confidence=8000))
        decision = router().route(subject_id="dataset:roundtrip", quality=quality)
        record = decision.quarantine_record
        assert record is not None
        restored = QuarantineRecord.from_bytes(record.to_bytes())
        self.assertEqual(restored, record)
        self.assertEqual(restored.record_id, record.record_id)

    def test_tampered_record_fails_closed(self):
        quality = quality_evaluator().evaluate(components(confidence=8000))
        decision = router().route(subject_id="dataset:tamper", quality=quality)
        record = decision.quarantine_record
        assert record is not None
        payload = json.loads(record.to_bytes().decode("utf-8"))
        payload["reason_codes"] = ["OTHER_REASON"]
        tampered = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with self.assertRaises(QuarantineRecordIntegrityError):
            QuarantineRecord.from_bytes(tampered)

    def test_serialized_unsafe_reason_fails_closed(self):
        quality = quality_evaluator().evaluate(components(confidence=8000))
        decision = router().route(subject_id="dataset:unsafe-serialized", quality=quality)
        record = decision.quarantine_record
        assert record is not None
        payload = json.loads(record.to_bytes().decode("utf-8"))
        payload["reason_codes"] = ["bad reason"]
        # Recompute a bogus declared id to prove semantic validation occurs before trust.
        payload["record_id"] = "0" * 64
        tampered = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with self.assertRaises(QuarantineRoutingError):
            QuarantineRecord.from_bytes(tampered)


if __name__ == "__main__":
    unittest.main()
