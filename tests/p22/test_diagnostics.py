from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.diagnostics import DiagnosticsError, DiagnosticsPolicy, diagnose


POLICY = Path("config/operations/diagnostics-policy.json")
CORR = "0123456789abcdef0123456789abcdef"
E1 = "a" * 64
E2 = "b" * 64


class DiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = DiagnosticsPolicy.from_path(POLICY)

    def test_known_rule_is_classified_deterministically(self) -> None:
        report = diagnose(
            self.policy,
            system_state="SAFE_MODE",
            symptom_codes=("RECONCILIATION_MISMATCH",),
            evidence_refs=(E1,),
            observed_at_ns=10,
            correlation_id=CORR,
        )
        self.assertEqual(report.status, "MATCHED_RULE")
        self.assertEqual(report.category, "RECONCILIATION")
        self.assertEqual(report.severity, "CRITICAL")
        self.assertEqual(report.hypothesis_code, "STATE_DIVERGENCE")
        self.assertTrue(report.operator_review_required)
        self.assertFalse(report.remediation_authority)

    def test_highest_severity_rule_wins_deterministically(self) -> None:
        report = diagnose(
            self.policy,
            system_state="NORMAL",
            symptom_codes=("DATA_STALE", "SECURITY_INTEGRITY_ALERT", "DATA_GAP"),
            evidence_refs=(E2, E1),
            observed_at_ns=20,
            correlation_id=CORR,
        )
        self.assertEqual(report.category, "SECURITY")
        self.assertEqual(report.severity, "EMERGENCY")
        self.assertEqual(report.evidence_refs, (E1, E2))

    def test_unknown_symptom_is_unresolved_not_guessed(self) -> None:
        report = diagnose(
            self.policy,
            system_state="NORMAL",
            symptom_codes=("NEW_UNKNOWN_SYMPTOM",),
            evidence_refs=(E1,),
            observed_at_ns=30,
            correlation_id=CORR,
        )
        self.assertEqual(report.status, "UNRESOLVED")
        self.assertEqual(report.category, "UNKNOWN")
        self.assertEqual(report.hypothesis_code, "UNRESOLVED_REQUIRES_OPERATOR_REVIEW")
        self.assertTrue(report.operator_review_required)

    def test_system_state_sets_severity_floor(self) -> None:
        report = diagnose(
            self.policy,
            system_state="EMERGENCY",
            symptom_codes=("DATA_STALE",),
            evidence_refs=(E1,),
            observed_at_ns=40,
            correlation_id=CORR,
        )
        self.assertEqual(report.severity, "EMERGENCY")

    def test_inputs_are_canonical_and_report_id_is_stable(self) -> None:
        kwargs = dict(
            system_state="DEGRADED",
            symptom_codes=("DATA_GAP", "DATA_STALE"),
            evidence_refs=(E2, E1),
            observed_at_ns=50,
            correlation_id=CORR,
        )
        first = diagnose(self.policy, **kwargs)
        second = diagnose(
            self.policy,
            system_state="DEGRADED",
            symptom_codes=("DATA_STALE", "DATA_GAP"),
            evidence_refs=(E1, E2),
            observed_at_ns=50,
            correlation_id=CORR,
        )
        self.assertEqual(first.report_id, second.report_id)
        self.assertEqual(first.symptom_codes, ("DATA_GAP", "DATA_STALE"))

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(DiagnosticsError):
            diagnose(
                self.policy,
                system_state="NORMAL",
                symptom_codes=(),
                evidence_refs=(E1,),
                observed_at_ns=1,
                correlation_id=CORR,
            )
        with self.assertRaises(DiagnosticsError):
            diagnose(
                self.policy,
                system_state="NORMAL",
                symptom_codes=("DATA_STALE",),
                evidence_refs=("bad",),
                observed_at_ns=1,
                correlation_id=CORR,
            )
        with self.assertRaises(DiagnosticsError):
            diagnose(
                self.policy,
                system_state="NORMAL",
                symptom_codes=("DATA_STALE",),
                evidence_refs=(E1,),
                observed_at_ns=-1,
                correlation_id=CORR,
            )

    def test_policy_preserves_no_remediation_boundary(self) -> None:
        content = POLICY.read_text(encoding="utf-8")
        self.assertIn('"automatic_remediation": false', content)
        self.assertIn('"automatic_self_healing": false', content)
        self.assertIn('"automatic_state_mutation": false', content)
        self.assertIn('"automatic_risk_policy_relaxation": false', content)
        self.assertIn('"network_mode": "DISABLED"', content)
        self.assertIn('"credential_mode": "NONE"', content)
        self.assertIn('"live_execution_authority": false', content)
        self.assertIn('"live_trading": "DISABLED"', content)
        self.assertIn('"auto_trading": "DISABLED"', content)


if __name__ == "__main__":
    unittest.main()
