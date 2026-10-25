from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    PartialCloseError,
    PartialClosePlanner,
    PartialClosePolicy,
    PartialCloseRequest,
    PositionFillEvent,
    PositionSpec,
    TpSlPlanner,
    TpSlPolicy,
    TpSlRequest,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
TPSL_POLICY = ROOT / "config/position-management/tp-sl-policy.json"
PARTIAL_POLICY = ROOT / "config/position-management/partial-close-policy.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def build_position(position_id: str = "pos-1", side: str = "LONG"):
    policy = CanonicalPositionPolicy.from_path(POSITION_POLICY)
    engine = CanonicalPositionEngine(policy)
    engine.register(PositionSpec(
        position_id=position_id,
        portfolio_id="portfolio",
        strategy_id="strategy",
        asset_id="BTC-USDT" if side == "LONG" else "EUR-USD",
        market="CRYPTO" if side == "LONG" else "FOREX",
        side=side,
        quantity_scale=100_000,
        price_scale=100,
        risk_validation_id=h("risk:" + position_id),
        pretrade_firewall_id=h("fw:" + position_id),
    ))
    engine.apply(PositionFillEvent(
        position_id=position_id,
        sequence=1,
        occurred_at_ns=1,
        event_type="OPEN_FILL",
        quantity_scaled=100_000,
        price_scaled=10_000,
        order_id="order-open-" + position_id,
        client_order_id="client-open-" + position_id,
        oms_record_id=h("oms-open:" + position_id),
        reconciliation_report_id=h("recon-open:" + position_id),
    ))
    return engine


def protection(record):
    planner = TpSlPlanner(TpSlPolicy.from_path(TPSL_POLICY))
    tp, sl = (11_000, 9_000) if record.side == "LONG" else (9_000, 11_000)
    return planner.plan(record, TpSlRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        side=record.side,
        entry_price_scaled=record.average_entry_price_scaled_floor,
        take_profit_price_scaled=tp,
        stop_loss_price_scaled=sl,
        signal_decision_id=h("signal:" + record.position_id),
        risk_validation_id=h("risk-plan:" + record.position_id),
    ))


def request(record, qty: int, reason: str = "PARTIAL_PROFIT") -> PartialCloseRequest:
    return PartialCloseRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        close_quantity_scaled=qty,
        reason_code=reason,
        exit_decision_id=h("exit:" + record.position_id + ":" + str(qty)),
    )


class PartialCloseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PartialClosePolicy.from_path(PARTIAL_POLICY)
        self.planner = PartialClosePlanner(self.policy)

    def test_open_long_partial_close_preserves_positive_remainder(self) -> None:
        engine = build_position()
        record = engine.current("pos-1")
        plan = self.planner.plan(record, protection(record), request(record, 25_000))
        self.assertEqual(plan.open_quantity_before_scaled, 100_000)
        self.assertEqual(plan.close_quantity_scaled, 25_000)
        self.assertEqual(plan.remaining_quantity_scaled, 75_000)
        self.assertEqual(plan.post_fill_protection_requirement, "P21B_REPLAN_REQUIRED_FOR_NEW_POSITION_RECORD")

    def test_short_and_already_partially_closed_position_pass(self) -> None:
        engine = build_position("pos-short", "SHORT")
        engine.apply(PositionFillEvent(
            position_id="pos-short", sequence=2, occurred_at_ns=2, event_type="REDUCE_FILL",
            quantity_scaled=20_000, price_scaled=9_800, order_id="order-reduce",
            client_order_id="client-reduce", oms_record_id=h("oms-reduce"),
            reconciliation_report_id=h("recon-reduce"),
        ))
        record = engine.current("pos-short")
        plan = self.planner.plan(record, protection(record), request(record, 30_000, "DE_RISK"))
        self.assertEqual(record.state, "PARTIALLY_CLOSED")
        self.assertEqual(plan.remaining_quantity_scaled, 50_000)
        self.assertEqual(plan.side, "SHORT")

    def test_zero_full_and_over_close_fail_closed(self) -> None:
        engine = build_position()
        record = engine.current("pos-1")
        current_protection = protection(record)
        for qty in (0, 100_000, 100_001):
            with self.subTest(qty=qty):
                with self.assertRaises(PartialCloseError):
                    self.planner.plan(record, current_protection, request(record, qty))

    def test_stale_position_and_protection_binding_fail_closed(self) -> None:
        engine = build_position()
        old = engine.current("pos-1")
        old_protection = protection(old)
        old_request = request(old, 10_000)
        engine.apply(PositionFillEvent(
            position_id="pos-1", sequence=2, occurred_at_ns=2, event_type="REDUCE_FILL",
            quantity_scaled=5_000, price_scaled=10_100, order_id="order-new",
            client_order_id="client-new", oms_record_id=h("oms-new"),
            reconciliation_report_id=h("recon-new"),
        ))
        current = engine.current("pos-1")
        with self.assertRaises(PartialCloseError):
            self.planner.plan(current, old_protection, old_request)
        with self.assertRaises(PartialCloseError):
            self.planner.plan(current, old_protection, request(current, 10_000))

    def test_mismatched_protection_plan_fails_closed(self) -> None:
        first = build_position("pos-1")
        second = build_position("pos-2")
        record = first.current("pos-1")
        other = second.current("pos-2")
        with self.assertRaises(PartialCloseError):
            self.planner.plan(record, protection(other), request(record, 10_000))

    def test_closed_position_fails_closed(self) -> None:
        engine = build_position()
        open_record = engine.current("pos-1")
        old_protection = protection(open_record)
        engine.apply(PositionFillEvent(
            position_id="pos-1", sequence=2, occurred_at_ns=2, event_type="REDUCE_FILL",
            quantity_scaled=100_000, price_scaled=10_500, order_id="order-close",
            client_order_id="client-close", oms_record_id=h("oms-close"),
            reconciliation_report_id=h("recon-close"),
        ))
        closed = engine.current("pos-1")
        with self.assertRaises(PartialCloseError):
            self.planner.plan(closed, old_protection, request(closed, 1))

    def test_reason_taxonomy_and_determinism(self) -> None:
        engine = build_position()
        record = engine.current("pos-1")
        current_protection = protection(record)
        with self.assertRaises(PartialCloseError):
            self.planner.plan(record, current_protection, request(record, 10_000, "PRICE_MOVED_AGAINST_POSITION"))
        good = request(record, 10_000, "STAGED_EXIT")
        first = self.planner.plan(record, current_protection, good)
        second = self.planner.plan(record, current_protection, good)
        self.assertEqual(first.plan_id, second.plan_id)

    def test_authority_remains_zero(self) -> None:
        engine = build_position()
        record = engine.current("pos-1")
        plan = self.planner.plan(record, protection(record), request(record, 10_000, "HEDGE_REDUCTION"))
        self.assertFalse(plan.real_venue_query)
        self.assertEqual(plan.network_mode, "DISABLED")
        self.assertFalse(plan.external_order_submission)
        self.assertFalse(plan.external_order_mutation)
        self.assertFalse(plan.automatic_oms_mutation)
        self.assertFalse(plan.canonical_position_mutation)
        self.assertFalse(plan.live_execution_authority)


if __name__ == "__main__":
    unittest.main()
