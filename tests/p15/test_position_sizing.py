from __future__ import annotations

import unittest

from packages.risk.position_sizing import (
    PositionSizingError,
    PositionSizingRequest,
    size_position,
)


def request(**overrides: object) -> PositionSizingRequest:
    values: dict[str, object] = {
        "request_id": "size-1",
        "upstream_risk_decision_id": "risk-decision-1",
        "upstream_status": "POLICY_CAPACITY_ELIGIBLE",
        "side": "LONG",
        "account_equity": "10000",
        "risk_budget_bps": 100,
        "entry_price": "100",
        "stop_price": "95",
        "contract_multiplier": "1",
        "quantity_step": "0.1",
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return PositionSizingRequest(**values)  # type: ignore[arg-type]


class PositionSizingTests(unittest.TestCase):
    def test_long_candidate_is_deterministic_and_bounded(self) -> None:
        decision = size_position(request())
        self.assertEqual(decision.status, "SIZE_CANDIDATE")
        self.assertEqual(decision.risk_amount, "100")
        self.assertEqual(decision.per_unit_stop_loss, "5")
        self.assertEqual(decision.candidate_quantity, "20")
        self.assertEqual(decision.planned_stop_loss, "100")
        self.assertFalse(decision.leverage_authority)
        self.assertFalse(decision.execution_authority)

    def test_short_geometry_supported(self) -> None:
        decision = size_position(
            request(side="SHORT", entry_price="100", stop_price="105")
        )
        self.assertEqual(decision.status, "SIZE_CANDIDATE")
        self.assertEqual(decision.candidate_quantity, "20")

    def test_upstream_veto_fails_closed(self) -> None:
        decision = size_position(request(upstream_status="VETO"))
        self.assertEqual(decision.status, "VETO")
        self.assertEqual(decision.reason_codes, ("UPSTREAM_RISK_VETO",))
        self.assertEqual(decision.candidate_quantity, "0")

    def test_invalid_long_stop_geometry_vetoes(self) -> None:
        decision = size_position(request(stop_price="101"))
        self.assertEqual(decision.status, "VETO")
        self.assertIn("INVALID_LONG_STOP_GEOMETRY", decision.reason_codes)

    def test_invalid_short_stop_geometry_vetoes(self) -> None:
        decision = size_position(
            request(side="SHORT", entry_price="100", stop_price="99")
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("INVALID_SHORT_STOP_GEOMETRY", decision.reason_codes)

    def test_invalid_positive_inputs_fail_closed(self) -> None:
        for field in (
            "account_equity",
            "entry_price",
            "stop_price",
            "contract_multiplier",
            "quantity_step",
        ):
            with self.subTest(field=field), self.assertRaises(PositionSizingError):
                request(**{field: "0"})

    def test_risk_budget_bounds_fail_closed(self) -> None:
        with self.assertRaises(PositionSizingError):
            request(risk_budget_bps=0)
        with self.assertRaises(PositionSizingError):
            request(risk_budget_bps=10001)

    def test_quantity_is_floored_to_explicit_step(self) -> None:
        decision = size_position(request(quantity_step="3"))
        self.assertEqual(decision.raw_quantity, "20")
        self.assertEqual(decision.candidate_quantity, "18")
        self.assertEqual(decision.planned_stop_loss, "90")

    def test_zero_quantity_after_floor_is_vetoed(self) -> None:
        decision = size_position(request(quantity_step="25"))
        self.assertEqual(decision.status, "VETO")
        self.assertIn("SIZE_BELOW_MIN_STEP", decision.reason_codes)

    def test_planned_loss_never_exceeds_budget(self) -> None:
        decision = size_position(
            request(
                account_equity="12345.67",
                risk_budget_bps=37,
                entry_price="63123.45",
                stop_price="62789.12",
                contract_multiplier="0.01",
                quantity_step="0.001",
            )
        )
        self.assertLessEqual(
            float(decision.planned_stop_loss),
            float(decision.risk_amount),
        )

    def test_identity_is_repeatable(self) -> None:
        left = size_position(request())
        right = size_position(request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
