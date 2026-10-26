from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import unittest

from packages.operations.incident_postmortem import (
    CorrectiveAction,
    IncidentPostmortemError,
    IncidentPostmortemPolicy,
    IncidentRecord,
    PostmortemRecord,
    build_corrective_action,
    build_incident_event,
    build_incident_record,
    build_postmortem,
)


POLICY = Path("config/operations/incident-postmortem-policy.json")
CORR = "0123456789abcdef0123456789abcdef"
E1 = "a" * 64
E2 = "b" * 64
E3 = "c" * 64


class IncidentPostmortemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = IncidentPostmortemPolicy.from_path(POLICY)

    def event(self, code: str, ts: int, ref: str = E1):
        return build_incident_event(
            self.policy,
            event_code=code,
            occurred_at_ns=ts,
            summary=f"{code} reference event",
            evidence_refs=(ref,),
            correlation_id=CORR,
        )

    def recovered_incident(self) -> IncidentRecord:
        return build_incident_record(
            self.policy,
            severity="SEV2",
            state="RECOVERED",
            opened_at_ns=100,
            contained_at_ns=200,
            recovered_at_ns=300,
            closed_at_ns=None,
            impact_scopes=("OPERATIONS", "DATA"),
            timeline=(
                self.event("DETECTED", 100, E1),
                self.event("CONTAINED", 200, E2),
                self.event("RECOVERED", 300, E3),
            ),
            correlation_id=CORR,
        )

    def action(self) -> CorrectiveAction:
        return build_corrective_action(
            self.policy,
            action_code="ADD_RECOVERY_ASSERTION",
            owner_role="OPERATIONS_OWNER",
            priority="P1",
            verification_required=True,
            evidence_refs=(E2,),
        )

    def test_policy_is_stable_and_advisory_only(self) -> None:
        self.assertEqual(len(self.policy.policy_id), 64)
        content = POLICY.read_text(encoding="utf-8")
        self.assertIn('"corrective_action_execution_authority": false', content)
        self.assertIn('"automatic_remediation": false', content)
        self.assertIn('"network_mode": "DISABLED"', content)
        self.assertIn('"credential_mode": "NONE"', content)
        self.assertIn('"runtime_state_mutation": false', content)

    def test_incident_record_is_deterministic(self) -> None:
        first = self.recovered_incident()
        second = self.recovered_incident()
        self.assertEqual(first.incident_id, second.incident_id)
        self.assertEqual(first.impact_scopes, ("DATA", "OPERATIONS"))

    def test_timeline_must_be_ordered(self) -> None:
        with self.assertRaises(IncidentPostmortemError):
            build_incident_record(
                self.policy,
                severity="SEV2",
                state="RECOVERED",
                opened_at_ns=100,
                contained_at_ns=200,
                recovered_at_ns=300,
                closed_at_ns=None,
                impact_scopes=("OPERATIONS",),
                timeline=(
                    self.event("RECOVERED", 300, E3),
                    self.event("DETECTED", 100, E1),
                ),
                correlation_id=CORR,
            )

    def test_timeline_correlation_mismatch_fails_closed(self) -> None:
        bad = build_incident_event(
            self.policy,
            event_code="DETECTED",
            occurred_at_ns=100,
            summary="bad correlation event",
            evidence_refs=(E1,),
            correlation_id="f" * 32,
        )
        with self.assertRaises(IncidentPostmortemError):
            build_incident_record(
                self.policy,
                severity="SEV2",
                state="OPEN",
                opened_at_ns=100,
                contained_at_ns=None,
                recovered_at_ns=None,
                closed_at_ns=None,
                impact_scopes=("OPERATIONS",),
                timeline=(bad,),
                correlation_id=CORR,
            )

    def test_invalid_lifecycle_timestamps_fail_closed(self) -> None:
        with self.assertRaises(IncidentPostmortemError):
            build_incident_record(
                self.policy,
                severity="SEV1",
                state="CLOSED",
                opened_at_ns=100,
                contained_at_ns=200,
                recovered_at_ns=None,
                closed_at_ns=400,
                impact_scopes=("OPERATIONS",),
                timeline=(self.event("DETECTED", 100),),
                correlation_id=CORR,
            )

    def test_evidence_ref_must_be_sha256(self) -> None:
        with self.assertRaises(IncidentPostmortemError):
            build_incident_event(
                self.policy,
                event_code="DETECTED",
                occurred_at_ns=100,
                summary="bad evidence",
                evidence_refs=("not-a-digest",),
                correlation_id=CORR,
            )

    def test_corrective_action_requires_verification_and_no_execution_authority(self) -> None:
        action = self.action()
        self.assertTrue(action.verification_required)
        self.assertFalse(action.execution_authority)
        self.assertFalse(action.automatic_remediation)
        with self.assertRaises(IncidentPostmortemError):
            build_corrective_action(
                self.policy,
                action_code="NO_VERIFY",
                owner_role="OPERATIONS_OWNER",
                priority="P1",
                verification_required=False,
                evidence_refs=(E1,),
            )

    def test_postmortem_requires_recovered_or_closed_incident(self) -> None:
        open_incident = build_incident_record(
            self.policy,
            severity="SEV3",
            state="OPEN",
            opened_at_ns=100,
            contained_at_ns=None,
            recovered_at_ns=None,
            closed_at_ns=None,
            impact_scopes=("OPERATIONS",),
            timeline=(self.event("DETECTED", 100),),
            correlation_id=CORR,
        )
        with self.assertRaises(IncidentPostmortemError):
            build_postmortem(
                self.policy,
                incident=open_incident,
                root_cause_code="UPSTREAM_TIMEOUT",
                root_cause_summary="Reference root cause",
                contributing_factors=("RETRY_PRESSURE",),
                evidence_refs=(E1,),
                corrective_actions=(self.action(),),
                created_at_ns=400,
            )

    def test_postmortem_cannot_predate_recovery(self) -> None:
        with self.assertRaises(IncidentPostmortemError):
            build_postmortem(
                self.policy,
                incident=self.recovered_incident(),
                root_cause_code="UPSTREAM_TIMEOUT",
                root_cause_summary="Reference root cause",
                contributing_factors=("RETRY_PRESSURE",),
                evidence_refs=(E1, E2),
                corrective_actions=(self.action(),),
                created_at_ns=299,
            )

    def test_postmortem_is_deterministic_and_complete(self) -> None:
        kwargs = dict(
            incident=self.recovered_incident(),
            root_cause_code="UPSTREAM_TIMEOUT",
            root_cause_summary="Reference root cause supported by deterministic evidence.",
            contributing_factors=("RETRY_PRESSURE", "STALE_DEPENDENCY"),
            evidence_refs=(E1, E2, E3),
            corrective_actions=(self.action(),),
            created_at_ns=400,
        )
        first = build_postmortem(self.policy, **kwargs)
        second = build_postmortem(self.policy, **kwargs)
        self.assertEqual(first.postmortem_id, second.postmortem_id)
        self.assertTrue(first.complete)
        self.assertFalse(first.execution_authority)
        self.assertFalse(first.runtime_state_mutation)

    def test_schema_has_no_person_or_pii_fields(self) -> None:
        names = {
            item.name
            for record in (IncidentRecord, CorrectiveAction, PostmortemRecord)
            for item in fields(record)
        }
        forbidden = {"name", "person_name", "email", "phone", "user_id", "employee_id"}
        self.assertTrue(names.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
