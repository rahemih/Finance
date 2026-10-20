from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from packages.shadow.reproducibility import (
    ReproducibilityCertificate,
    ReproducibilityError,
    ReproducibilityPolicy,
    WorkstreamReproducibilityRecord,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ReproducibilityPolicy.from_path(
    ROOT / "config/shadow/deterministic-reproducibility-policy.json"
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def record(workstream: str) -> WorkstreamReproducibilityRecord:
    kwargs: dict[str, object] = {}
    if workstream == "P19-F":
        kwargs = {
            "claim_scope": "REFERENCE_ONLY",
            "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
            "live_drift_validated": False,
        }
    return WorkstreamReproducibilityRecord(
        workstream=workstream,
        evidence_kind=f"NEXUS_QUANT_{workstream.replace('-', '')}_EVIDENCE",
        evidence_sha256=h(f"evidence-{workstream}"),
        manifest_kind=f"NEXUS_QUANT_{workstream.replace('-', '')}_MANIFEST",
        manifest_sha256=h(f"manifest-{workstream}"),
        package_sha256=h(f"package-{workstream}"),
        policy_sha256=h(f"policy-{workstream}"),
        manifest_state="CANONICAL_COMPLETE",
        lock_state="RELEASED",
        **kwargs,
    )


def records() -> tuple[WorkstreamReproducibilityRecord, ...]:
    return tuple(record(item) for item in POLICY.required_workstreams)


class ReproducibilityTests(unittest.TestCase):
    def test_exact_a_to_f_coverage_builds_deterministic_certificate(self) -> None:
        left = ReproducibilityCertificate.build(records=records(), policy=POLICY)
        right = ReproducibilityCertificate.build(records=records(), policy=POLICY)
        self.assertEqual(left.certificate_id, right.certificate_id)
        self.assertEqual(left.coverage_state, "P19_A_TO_F_COMPLETE")
        self.assertEqual(left.cross_workstream_lineage, "VERIFIED")
        self.assertFalse(left.live_drift_validated)

    def test_missing_workstream_fails_closed(self) -> None:
        with self.assertRaises(ReproducibilityError):
            ReproducibilityCertificate.build(records=records()[:-1], policy=POLICY)

    def test_reordered_workstreams_fail_closed(self) -> None:
        values = list(records())
        values[0], values[1] = values[1], values[0]
        with self.assertRaises(ReproducibilityError):
            ReproducibilityCertificate.build(records=values, policy=POLICY)

    def test_duplicate_workstream_fails_closed(self) -> None:
        values = list(records())
        values[-1] = values[-2]
        with self.assertRaises(ReproducibilityError):
            ReproducibilityCertificate.build(records=values, policy=POLICY)

    def test_noncanonical_manifest_fails_closed(self) -> None:
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-A"), manifest_state="IN_PROGRESS")

    def test_active_lock_fails_closed(self) -> None:
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-B"), lock_state="ACTIVE")

    def test_authority_escalation_fails_closed(self) -> None:
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-C"), execution_authority=True)
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-D"), p20_started=True)

    def test_live_auto_enablement_fails_closed(self) -> None:
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-E"), live_trading="ENABLED")

    def test_p19f_reference_claim_boundary_is_mandatory(self) -> None:
        base = record("P19-F")
        with self.assertRaises(ReproducibilityError):
            replace(base, claim_scope="LIVE_VALIDATED")
        with self.assertRaises(ReproducibilityError):
            replace(base, live_empirical_status="AVAILABLE")
        with self.assertRaises(ReproducibilityError):
            replace(base, live_drift_validated=True)

    def test_non_p19f_record_cannot_carry_live_claim_fields(self) -> None:
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-A"), claim_scope="REFERENCE_ONLY")

    def test_placeholder_hash_is_rejected(self) -> None:
        with self.assertRaises(ReproducibilityError):
            replace(record("P19-A"), evidence_sha256="a" * 64)


if __name__ == "__main__":
    unittest.main()
