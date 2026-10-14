from __future__ import annotations

import unittest

from packages.risk.defensive_modes import (
    DefensiveModeError,
    DefensiveModePolicy,
    DefensiveModeRequest,
    select_defensive_mode,
)


POLICY = DefensiveModePolicy(
    policy_version="p15h-test-v1",
    reduced_risk_scale_bps=5000,
    defensive_scale_bps=2500,
)


def request(**overrides: object) -> DefensiveModeRequest:
    values: dict[str, object] = {
        "request_id": "mode-1",
        "upstream_capital_decision_id": "capital-1",
        "upstream_capital_status": "CAPITAL_SEGMENT_ELIGIBLE",
        "upstream_drawdown_status": "WITHIN_LIMITS",
        "data_health": "HEALTHY",
        "counterparty_health": "HEALTHY",
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return DefensiveModeRequest(**values)  # type: ignore[arg-type]


class DefensiveModeTests(unittest.TestCase):
    def test_normal_mode(self) -> None:
        decision = select_defensive_mode(policy=POLICY, request=request())
        self.assertEqual(decision.mode, "NORMAL")
        self.assertEqual(decision.risk_scale_bps, 10000)
        self.assertTrue(decision.new_risk_allowed)
        self.assertFalse(decision.execution_authority)

    def test_degraded_health_reduces_risk(self) -> None:
        decision = select_defensive_mode(
            policy=POLICY,
            request=request(data_health="DEGRADED"),
        )
        self.assertEqual(decision.mode, "REDUCED_RISK")
        self.assertEqual(decision.risk_scale_bps, 5000)

    def test_drawdown_derisk_is_more_restrictive(self) -> None:
        decision = select_defensive_mode(
            policy=POLICY,
            request=request(
                upstream_drawdown_status="DE_RISK_REQUIRED",
                data_health="DEGRADED",
            ),
        )
        self.assertEqual(decision.mode, "DEFENSIVE")
        self.assertEqual(decision.risk_scale_bps, 2500)

    def test_capital_veto_halts_new_risk(self) -> None:
        decision = select_defensive_mode(
            policy=POLICY,
            request=request(upstream_capital_status="VETO"),
        )
        self.assertEqual(decision.mode, "HALT_NEW_RISK")
        self.assertEqual(decision.risk_scale_bps, 0)
        self.assertFalse(decision.new_risk_allowed)

    def test_critical_health_halts_new_risk(self) -> None:
        decision = select_defensive_mode(
            policy=POLICY,
            request=request(counterparty_health="CRITICAL"),
        )
        self.assertEqual(decision.mode, "HALT_NEW_RISK")
        self.assertIn("CRITICAL_COUNTERPARTY_HEALTH", decision.reason_codes)

    def test_invalid_policy_order_fails_closed(self) -> None:
        with self.assertRaises(DefensiveModeError):
            DefensiveModePolicy("x", 2000, 3000)

    def test_unknown_health_fails_closed(self) -> None:
        with self.assertRaises(DefensiveModeError):
            request(data_health="UNKNOWN")

    def test_identity_is_deterministic(self) -> None:
        left = select_defensive_mode(policy=POLICY, request=request())
        right = select_defensive_mode(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
