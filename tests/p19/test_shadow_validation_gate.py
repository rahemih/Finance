from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from packages.shadow.shadow_validation_gate import (
    ReproducibilityGateSummary,
    ShadowGateWorkstreamRecord,
    ShadowValidationGateError,
    ShadowValidationGatePolicy,
    certify_g10_shadow_validated,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ShadowValidationGatePolicy.from_path(
    ROOT / "config/shadow/shadow-validation-gate-policy.json"
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def record(workstream: str) -> ShadowGateWorkstreamRecord:
    kwargs: dict[str, object] = {}
    if workstream == "P19-F":
        kwargs = {
            "claim_scope": "REFERENCE_ONLY",
            "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
            "live_drift_validated": False,
        }
    elif workstream == "P19-G":
        kwargs = {
            "claim_scope": "REFERENCE_REPRODUCIBILITY_ONLY",
            "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
            "live_drift_validated": False,
        }
    return ShadowGateWorkstreamRecord(
        workstream=workstream,
        evidence_kind=f"KIND_{workstream}",
        evidence_sha256=h(f"evidence-{workstream}"),
        manifest_kind=f"MANIFEST_{workstream}",
        manifest_sha256=h(f"manifest-{workstream}"),
        manifest_state="CANONICAL_COMPLETE",
        lock_state="RELEASED",
        **kwargs,
    )


def summary() -> ReproducibilityGateSummary:
    return ReproducibilityGateSummary(
        reproducibility_certificate_id=h("repro-certificate"),
        coverage_state="P19_A_TO_F_COMPLETE",
        evidence_pair_match="BYTE_IDENTICAL",
        cross_workstream_lineage="VERIFIED",
        claim_scope="REFERENCE_REPRODUCIBILITY_ONLY",
        live_empirical_status="UNAVAILABLE_PRE_P20_H",
        live_drift_validated=False,
    )


class ShadowValidationGateTests(unittest.TestCase):
    def records(self) -> tuple[ShadowGateWorkstreamRecord, ...]:
        return tuple(record(ws) for ws in POLICY.required_workstreams)

    def test_exact_canonical_chain_passes_g10_without_execution_authority(self) -> None:
        gate = certify_g10_shadow_validated(
            policy=POLICY,
            workstream_records=self.records(),
            reproducibility=summary(),
        )
        self.assertEqual(gate.gate_name, "G10_SHADOW_VALIDATED")
        self.assertEqual(gate.state, "PASS")
        self.assertEqual(gate.gate_claim_scope, "SHADOW_REFERENCE_VALIDATION")
        self.assertEqual(
            gate.next_phase_state,
            "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        )
        self.assertFalse(gate.live_execution_validated)
        self.assertFalse(gate.broker_certification_validated)
        self.assertFalse(gate.production_readiness)
        self.assertFalse(gate.automatic_p20_activation)
        self.assertFalse(gate.execution_authority)
        self.assertFalse(gate.order_routing_authority)
        self.assertFalse(gate.p20_started)

    def test_missing_workstream_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            certify_g10_shadow_validated(
                policy=POLICY,
                workstream_records=self.records()[:-1],
                reproducibility=summary(),
            )

    def test_reordered_workstreams_fail_closed(self) -> None:
        values = list(self.records())
        values[0], values[1] = values[1], values[0]
        with self.assertRaises(ShadowValidationGateError):
            certify_g10_shadow_validated(
                policy=POLICY,
                workstream_records=values,
                reproducibility=summary(),
            )

    def test_active_lock_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(record("P19-A"), lock_state="ACTIVE")

    def test_noncanonical_manifest_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(record("P19-B"), manifest_state="IN_PROGRESS")

    def test_live_drift_claim_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(record("P19-F"), live_drift_validated=True)

    def test_wrong_p19g_claim_scope_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(record("P19-G"), claim_scope="LIVE_VALIDATED")

    def test_upstream_g10_authority_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(record("P19-G"), g10_authority=True)

    def test_bad_reproducibility_pair_state_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(summary(), evidence_pair_match="HASH_ONLY")

    def test_live_empirical_status_drift_fails_closed(self) -> None:
        with self.assertRaises(ShadowValidationGateError):
            replace(
                summary(),
                live_empirical_status="LIVE_VALIDATED",
            )

    def test_duplicate_evidence_identity_fails_closed(self) -> None:
        values = list(self.records())
        values[1] = replace(
            values[1],
            evidence_sha256=values[0].evidence_sha256,
        )
        with self.assertRaises(ShadowValidationGateError):
            certify_g10_shadow_validated(
                policy=POLICY,
                workstream_records=values,
                reproducibility=summary(),
            )


if __name__ == "__main__":
    unittest.main()
