from __future__ import annotations

from pathlib import Path
import unittest

from packages.execution.oms_lifecycle import (
    OmsLifecycleEngine,
    OmsLifecycleError,
    OmsLifecycleEvent,
    OmsLifecyclePolicy,
    OmsOrderSpec,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/oms-lifecycle-policy.json"


def spec(order_id: str = "order-001", *, market: str = "CRYPTO") -> OmsOrderSpec:
    return OmsOrderSpec(
        order_id=order_id,
        client_order_id=f"client-{order_id}",
        asset_id="BTC-USD" if market == "CRYPTO" else "EUR-USD",
        market=market,
        side="BUY",
        total_quantity_scaled=100,
        quantity_scale=100,
    )


def event(
    order_id: str,
    sequence: int,
    event_type: str,
    *,
    time_ns: int | None = None,
    fill: int = 0,
) -> OmsLifecycleEvent:
    return OmsLifecycleEvent(
        order_id=order_id,
        sequence=sequence,
        occurred_at_ns=sequence if time_ns is None else time_ns,
        event_type=event_type,
        fill_quantity_scaled=fill,
        source_ref=f"event-{order_id}-{sequence}",
    )


class OmsLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = OmsLifecyclePolicy.from_path(POLICY)
        self.engine = OmsLifecycleEngine(self.policy)
        self.order = spec()
        self.created = self.engine.create_order(self.order, created_at_ns=0)

    def _open(self) -> None:
        self.engine.apply(event(self.order.order_id, 1, "SUBMIT"))
        self.engine.apply(event(self.order.order_id, 2, "ACK"))

    def test_happy_fill_path_is_deterministic(self) -> None:
        self._open()
        partial = self.engine.apply(event(self.order.order_id, 3, "PARTIAL_FILL", fill=40))
        filled = self.engine.apply(event(self.order.order_id, 4, "FILL", fill=60))
        self.assertEqual(partial.state, "PARTIALLY_FILLED")
        self.assertEqual(partial.remaining_quantity_scaled, 60)
        self.assertEqual(filled.state, "FILLED")
        self.assertEqual(filled.cumulative_filled_scaled, 100)
        self.assertEqual(filled.remaining_quantity_scaled, 0)

    def test_reject_path_is_terminal(self) -> None:
        self.engine.apply(event(self.order.order_id, 1, "SUBMIT"))
        rejected = self.engine.apply(event(self.order.order_id, 2, "REJECT"))
        self.assertEqual(rejected.state, "REJECTED")
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 3, "SUBMIT"))

    def test_cancel_path_is_deterministic(self) -> None:
        self._open()
        pending = self.engine.apply(event(self.order.order_id, 3, "CANCEL_REQUEST"))
        canceled = self.engine.apply(event(self.order.order_id, 4, "CANCEL_ACK"))
        self.assertEqual(pending.state, "CANCEL_PENDING")
        self.assertEqual(canceled.state, "CANCELED")
        self.assertEqual(canceled.remaining_quantity_scaled, 100)

    def test_cancel_pending_fill_race_is_deterministic(self) -> None:
        self._open()
        self.engine.apply(event(self.order.order_id, 3, "PARTIAL_FILL", fill=20))
        self.engine.apply(event(self.order.order_id, 4, "CANCEL_REQUEST"))
        race = self.engine.apply(event(self.order.order_id, 5, "PARTIAL_FILL", fill=30))
        canceled = self.engine.apply(event(self.order.order_id, 6, "CANCEL_ACK"))
        self.assertEqual(race.state, "CANCEL_PENDING")
        self.assertEqual(race.cumulative_filled_scaled, 50)
        self.assertEqual(canceled.state, "CANCELED")
        self.assertEqual(canceled.remaining_quantity_scaled, 50)

    def test_cancel_pending_full_fill_wins_race(self) -> None:
        self._open()
        self.engine.apply(event(self.order.order_id, 3, "CANCEL_REQUEST"))
        filled = self.engine.apply(event(self.order.order_id, 4, "FILL", fill=100))
        self.assertEqual(filled.state, "FILLED")
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 5, "CANCEL_ACK"))

    def test_sequence_gap_and_time_regression_fail_closed(self) -> None:
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 2, "SUBMIT"))
        self.engine.apply(event(self.order.order_id, 1, "SUBMIT", time_ns=10))
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 2, "ACK", time_ns=9))

    def test_illegal_transition_fails_closed(self) -> None:
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 1, "ACK"))

    def test_partial_and_final_fill_accounting_fail_closed(self) -> None:
        self._open()
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 3, "PARTIAL_FILL", fill=100))
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 3, "FILL", fill=99))

    def test_expire_path_is_terminal(self) -> None:
        self._open()
        expired = self.engine.apply(event(self.order.order_id, 3, "EXPIRE"))
        self.assertEqual(expired.state, "EXPIRED")
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event(self.order.order_id, 4, "CANCEL_REQUEST"))

    def test_snapshot_is_deterministic_and_zero_authority(self) -> None:
        self._open()
        first = self.engine.snapshot()
        second = self.engine.snapshot()
        self.assertEqual(first, second)
        authority = first["authority"]
        assert isinstance(authority, dict)
        self.assertFalse(authority["idempotency_authority"])
        self.assertFalse(authority["retry_authority"])
        self.assertFalse(authority["reconciliation_authority"])
        self.assertFalse(authority["live_execution_authority"])
        self.assertEqual(authority["network_mode"], "DISABLED")

    def test_unknown_order_and_duplicate_create_fail_closed(self) -> None:
        with self.assertRaises(OmsLifecycleError):
            self.engine.apply(event("unknown", 1, "SUBMIT"))
        with self.assertRaises(OmsLifecycleError):
            self.engine.create_order(self.order, created_at_ns=0)


if __name__ == "__main__":
    unittest.main()
