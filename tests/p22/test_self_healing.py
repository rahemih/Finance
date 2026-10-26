from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.diagnostics import DiagnosticsPolicy, diagnose
from packages.operations.self_healing import SelfHealingError, SelfHealingPolicy, plan_self_healing
from packages.operations.system_state import SystemState


HEALING_POLICY = Path("config/operations/constrained-self-healing-policy.json")
DIAGNOSTICS_POLICY = Path("config/operations/diagnostics-policy.json")
CORR = "0123456789abcdef0123456789abcdef"
EVIDENCE = "a" * 64


class SelfHealingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SelfHealingPolicy.from_path(HEALING_POLICY)
        self.diagnostics = DiagnosticsPolicy.from_path(DIAGNOSTICS_POLICY)

    def report(self, state: SystemState, symptom: str):
        return diagnose(
            self.diagnostics,
            system_state=state,
            symptom_codes=(symptom,),
            evidence_refs=(EVIDENCE,),
            observed_at_ns=100,
            correlation_id=CORR,
        )

    def test_policy_is_stable_and_reference_only(self) -> None:
        self.assertEqual(len(self.policy.policy_id), 64)
        rule = self.policy.preapproved_actions["DATA_FRESHNESS_DEGRADATION"]
        self.assertEqual(rule.action, "RESTART_STATELESS_OBSERVER")
        self.assertEqual(rule.rollback_action, "STOP_REPLACEMENT_OBSERVER")
        self.assertEqual(rule.max_attempts, 1)

    def test_low_risk_preapproved_diagnostic_is_eligible_reference_plan(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("DEGRADED", "DATA_STALE"),
            attempt_number=1,
            cooldown_elapsed=True,
        )
        self.assertEqual(decision.status, "ELIGIBLE_REFERENCE_PLAN")
        self.assertEqual(decision.action, "RESTART_STATELESS_OBSERVER")
        self.assertEqual(decision.rollback_action, "STOP_REPLACEMENT_OBSERVER")
        self.assertTrue(decision.post_action_validation_required)
        self.assertFalse(decision.execution_authority)
        self.assertFalse(decision.external_side_effects)

    def test_operator_review_diagnostic_is_blocked(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("SAFE_MODE", "DATA_STALE"),
            attempt_number=1,
            cooldown_elapsed=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.reason_code, "OPERATOR_REVIEW_REQUIRED")
        self.assertIsNone(decision.action)

    def test_critical_diagnostic_is_blocked(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("NORMAL", "DATA_GAP"),
            attempt_number=1,
            cooldown_elapsed=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.reason_code, "OPERATOR_REVIEW_REQUIRED")

    def test_security_emergency_is_blocked(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("EMERGENCY", "SECURITY_INTEGRITY_ALERT"),
            attempt_number=1,
            cooldown_elapsed=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertIsNone(decision.action)

    def test_unknown_diagnostic_is_blocked(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("NORMAL", "UNKNOWN_SYMPTOM"),
            attempt_number=1,
            cooldown_elapsed=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.reason_code, "DIAGNOSTIC_STATUS_NOT_ELIGIBLE")

    def test_cooldown_cannot_be_bypassed(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("DEGRADED", "DATA_STALE"),
            attempt_number=1,
            cooldown_elapsed=False,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.reason_code, "COOLDOWN_NOT_ELAPSED")

    def test_attempt_budget_cannot_be_bypassed(self) -> None:
        decision = plan_self_healing(
            self.policy,
            report=self.report("DEGRADED", "DATA_STALE"),
            attempt_number=2,
            cooldown_elapsed=True,
        )
        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.reason_code, "ATTEMPT_BUDGET_EXHAUSTED")

    def test_invalid_attempt_number_fails_closed(self) -> None:
        with self.assertRaises(SelfHealingError):
            plan_self_healing(
                self.policy,
                report=self.report("DEGRADED", "DATA_STALE"),
                attempt_number=0,
                cooldown_elapsed=True,
            )

    def test_decision_is_deterministic(self) -> None:
        report = self.report("DEGRADED", "DATA_STALE")
        first = plan_self_healing(self.policy, report=report, attempt_number=1, cooldown_elapsed=True)
        second = plan_self_healing(self.policy, report=report, attempt_number=1, cooldown_elapsed=True)
        self.assertEqual(first.decision_id, second.decision_id)

    def test_authority_boundary_is_hard_disabled(self) -> None:
        content = HEALING_POLICY.read_text(encoding="utf-8")
        self.assertIn('"execution_mode": "REFERENCE_PLAN_ONLY"', content)
        self.assertIn('"execution_authority": false', content)
        self.assertIn('"external_side_effects": false', content)
        self.assertIn('"automatic_state_mutation": false', content)
        self.assertIn('"automatic_risk_policy_relaxation": false', content)
        self.assertIn('"network_mode": "DISABLED"', content)
        self.assertIn('"credential_mode": "NONE"', content)
        self.assertIn('"live_execution_authority": false', content)
        self.assertIn('"live_trading": "DISABLED"', content)
        self.assertIn('"auto_trading": "DISABLED"', content)


if __name__ == "__main__":
    unittest.main()
