from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.system_state import (
    SystemStateError,
    SystemStatePolicy,
    build_health_snapshot,
    decide_system_state,
)


POLICY = Path("config/operations/system-state-policy.json")
CORR = "0123456789abcdef0123456789abcdef"


class SystemStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SystemStatePolicy.from_path(POLICY)

    def snapshot(self, level: str, *reasons: str):
        return build_health_snapshot(
            self.policy,
            health_level=level,  # type: ignore[arg-type]
            observed_at_ns=100,
            correlation_id=CORR,
            reason_codes=tuple(reasons),
        )

    def test_policy_states_are_exact_and_stable(self) -> None:
        self.assertEqual(
            self.policy.states,
            ("NORMAL", "DEGRADED", "SAFE_MODE", "HALTED", "EMERGENCY", "RECOVERY"),
        )
        self.assertEqual(len(self.policy.policy_id), 64)

    def test_normal_health_stays_normal(self) -> None:
        decision = decide_system_state(
            self.policy,
            previous_state="NORMAL",
            snapshot=self.snapshot("HEALTHY"),
        )
        self.assertEqual(decision.next_state, "NORMAL")

    def test_degraded_health_degrades_normal_state(self) -> None:
        decision = decide_system_state(
            self.policy,
            previous_state="NORMAL",
            snapshot=self.snapshot("DEGRADED", "DATA_LATENCY_WARN"),
        )
        self.assertEqual(decision.next_state, "DEGRADED")

    def test_unsafe_health_enters_safe_mode(self) -> None:
        decision = decide_system_state(
            self.policy,
            previous_state="DEGRADED",
            snapshot=self.snapshot("UNSAFE", "RECONCILIATION_MISMATCH"),
        )
        self.assertEqual(decision.next_state, "SAFE_MODE")

    def test_halt_required_enters_halted(self) -> None:
        decision = decide_system_state(
            self.policy,
            previous_state="NORMAL",
            snapshot=self.snapshot("HALT_REQUIRED", "DEPENDENCY_INTEGRITY_FAILURE"),
        )
        self.assertEqual(decision.next_state, "HALTED")

    def test_emergency_health_dominates(self) -> None:
        decision = decide_system_state(
            self.policy,
            previous_state="HALTED",
            snapshot=self.snapshot("EMERGENCY", "CAPITAL_PROTECTION_EMERGENCY"),
        )
        self.assertEqual(decision.next_state, "EMERGENCY")

    def test_restricted_state_does_not_auto_deescalate(self) -> None:
        decision = decide_system_state(
            self.policy,
            previous_state="SAFE_MODE",
            snapshot=self.snapshot("HEALTHY"),
        )
        self.assertEqual(decision.next_state, "SAFE_MODE")
        self.assertTrue(decision.deescalation_blocked)

    def test_recovery_requires_two_healthy_steps(self) -> None:
        healthy = self.snapshot("HEALTHY")
        first = decide_system_state(
            self.policy,
            previous_state="HALTED",
            snapshot=healthy,
            recovery_authorized=True,
        )
        second = decide_system_state(
            self.policy,
            previous_state=first.next_state,
            snapshot=healthy,
        )
        self.assertEqual(first.next_state, "RECOVERY")
        self.assertEqual(second.next_state, "NORMAL")

    def test_recovery_authorization_with_nonhealthy_snapshot_fails_closed(self) -> None:
        with self.assertRaises(SystemStateError):
            decide_system_state(
                self.policy,
                previous_state="SAFE_MODE",
                snapshot=self.snapshot("DEGRADED", "STILL_DEGRADED"),
                recovery_authorized=True,
            )

    def test_reason_codes_are_sorted_deterministically(self) -> None:
        first = build_health_snapshot(
            self.policy,
            health_level="UNSAFE",
            observed_at_ns=10,
            correlation_id=CORR,
            reason_codes=("B_REASON", "A_REASON"),
        )
        second = build_health_snapshot(
            self.policy,
            health_level="UNSAFE",
            observed_at_ns=10,
            correlation_id=CORR,
            reason_codes=("A_REASON", "B_REASON"),
        )
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(first.reason_codes, ("A_REASON", "B_REASON"))

    def test_invalid_snapshot_inputs_fail_closed(self) -> None:
        with self.assertRaises(SystemStateError):
            build_health_snapshot(
                self.policy,
                health_level="UNSAFE",
                observed_at_ns=-1,
                correlation_id=CORR,
                reason_codes=("BAD_TIME",),
            )
        with self.assertRaises(SystemStateError):
            build_health_snapshot(
                self.policy,
                health_level="UNSAFE",
                observed_at_ns=1,
                correlation_id="bad",
                reason_codes=("BAD_CORRELATION",),
            )
        with self.assertRaises(SystemStateError):
            build_health_snapshot(
                self.policy,
                health_level="UNSAFE",
                observed_at_ns=1,
                correlation_id=CORR,
                reason_codes=(),
            )

    def test_decision_is_deterministic(self) -> None:
        snapshot = self.snapshot("UNSAFE", "HEALTH_CONTRACT_FAIL")
        first = decide_system_state(self.policy, previous_state="NORMAL", snapshot=snapshot)
        second = decide_system_state(self.policy, previous_state="NORMAL", snapshot=snapshot)
        self.assertEqual(first.decision_id, second.decision_id)

    def test_policy_preserves_authority_boundary(self) -> None:
        content = POLICY.read_text(encoding="utf-8")
        self.assertIn('"automatic_state_mutation": false', content)
        self.assertIn('"automatic_diagnostics": false', content)
        self.assertIn('"automatic_self_healing": false', content)
        self.assertIn('"automatic_risk_policy_relaxation": false', content)
        self.assertIn('"network_mode": "DISABLED"', content)
        self.assertIn('"credential_mode": "NONE"', content)
        self.assertIn('"live_execution_authority": false', content)
        self.assertIn('"live_trading": "DISABLED"', content)
        self.assertIn('"auto_trading": "DISABLED"', content)


if __name__ == "__main__":
    unittest.main()
