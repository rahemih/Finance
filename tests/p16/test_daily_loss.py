from __future__ import annotations

import unittest

from packages.pretrade_firewall.daily_loss import (
    DailyLossCircuitError,
    DailyLossPolicy,
    DailyLossRequest,
    evaluate_daily_loss,
)


POLICY = DailyLossPolicy(
    policy_version="p16f-test-v1",
    max_daily_loss_bps=500,
)


def request(**overrides: object) -> DailyLossRequest:
    values: dict[str, object] = {
        "request_id": "f-1",
        "upstream_health_decision_id": "e-1",
        "upstream_health_status": "PRETRADE_E_ELIGIBLE",
        "trading_day_id": "fixture-day-1",
        "day_start_equity": "10000",
        "current_equity": "9800",
        "prior_circuit_state": "CLEAR",
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return DailyLossRequest(**values)  # type: ignore[arg-type]


class DailyLossCircuitTests(unittest.TestCase):
    def test_loss_below_limit_is_eligible(self) -> None:
        decision = evaluate_daily_loss(policy=POLICY, request=request())
        self.assertEqual(decision.daily_loss_bps, 200)
        self.assertEqual(decision.circuit_state, "CLEAR")
        self.assertEqual(decision.status, "PRETRADE_F_ELIGIBLE")
        self.assertFalse(decision.reset_authority)
        self.assertFalse(decision.position_close_authority)
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_profit_or_flat_yields_zero_loss(self) -> None:
        for equity in ("10000", "11000"):
            with self.subTest(equity=equity):
                decision = evaluate_daily_loss(
                    policy=POLICY,
                    request=request(current_equity=equity),
                )
                self.assertEqual(decision.daily_loss_bps, 0)
                self.assertEqual(decision.status, "PRETRADE_F_ELIGIBLE")

    def test_equal_limit_trips(self) -> None:
        decision = evaluate_daily_loss(
            policy=POLICY,
            request=request(current_equity="9500"),
        )
        self.assertEqual(decision.daily_loss_bps, 500)
        self.assertEqual(decision.circuit_state, "TRIPPED")
        self.assertEqual(decision.status, "VETO")
        self.assertIn("DAILY_LOSS_LIMIT_REACHED", decision.reason_codes)

    def test_above_limit_trips(self) -> None:
        decision = evaluate_daily_loss(
            policy=POLICY,
            request=request(current_equity="9499"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertEqual(decision.circuit_state, "TRIPPED")

    def test_prior_trip_is_latched(self) -> None:
        decision = evaluate_daily_loss(
            policy=POLICY,
            request=request(
                current_equity="11000",
                prior_circuit_state="TRIPPED",
            ),
        )
        self.assertEqual(decision.daily_loss_bps, 0)
        self.assertEqual(decision.circuit_state, "TRIPPED")
        self.assertEqual(decision.status, "VETO")
        self.assertIn("CIRCUIT_ALREADY_TRIPPED", decision.reason_codes)

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_daily_loss(
            policy=POLICY,
            request=request(upstream_health_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_HEALTH_VETO", decision.reason_codes)

    def test_missing_day_id_fails_closed(self) -> None:
        with self.assertRaises(DailyLossCircuitError):
            request(trading_day_id="")

    def test_invalid_equity_fails_closed(self) -> None:
        for field in ("day_start_equity", "current_equity"):
            with self.subTest(field=field):
                with self.assertRaises(DailyLossCircuitError):
                    request(**{field: "0"})

    def test_invalid_circuit_state_fails_closed(self) -> None:
        with self.assertRaises(DailyLossCircuitError):
            request(prior_circuit_state="UNKNOWN")

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_daily_loss(policy=POLICY, request=request())
        right = evaluate_daily_loss(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
