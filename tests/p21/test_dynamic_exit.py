from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    DynamicExitError,
    DynamicExitPlanner,
    DynamicExitPolicy,
    DynamicExitRequest,
    PositionFillEvent,
    PositionSpec,
    TpSlPlanner,
    TpSlPolicy,
    TpSlRequest,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
TPSL_POLICY = ROOT / "config/position-management/tp-sl-policy.json"
DYNAMIC_POLICY = ROOT / "config/position-management/dynamic-exit-policy.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def build_position(position_id: str = "pos-long", side: str = "LONG"):
    engine = CanonicalPositionEngine(CanonicalPositionPolicy.from_path(POSITION_POLICY))
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
    if record.side == "LONG":
        tp, sl = 12_000, 9_000
    else:
        tp, sl = 8_000, 11_000
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


def request(record, mode: str, reference: int, stop: int) -> DynamicExitRequest:
    return DynamicExitRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        mode=mode,
        reference_price_scaled=reference,
        requested_stop_price_scaled=stop,
        exit_decision_id=h("exit:" + record.position_id + ":" + mode + ":" + str(reference) + ":" + str(stop)),
    )


class DynamicExitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = DynamicExitPlanner(DynamicExitPolicy.from_path(DYNAMIC_POLICY))

    def test_long_break_even_exact_entry(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        current = protection(record)
        plan = self.planner.plan(record, current, request(record, "BREAK_EVEN", 10_500, 10_000))
        self.assertEqual(plan.requested_stop_price_scaled, 10_000)
        self.assertEqual(plan.tightening_distance_scaled, 1_000)
        self.assertEqual(plan.take_profit_price_scaled, current.take_profit_price_scaled)

    def test_short_break_even_exact_entry(self) -> None:
        engine = build_position("pos-short", "SHORT")
        record = engine.current("pos-short")
        current = protection(record)
        plan = self.planner.plan(record, current, request(record, "BREAK_EVEN", 9_500, 10_000))
        self.assertEqual(plan.requested_stop_price_scaled, 10_000)
        self.assertEqual(plan.tightening_distance_scaled, 1_000)

    def test_trailing_and_dynamic_exit_can_lock_profit(self) -> None:
        long_engine = build_position()
        long_record = long_engine.current("pos-long")
        long_plan = self.planner.plan(
            long_record,
            protection(long_record),
            request(long_record, "TRAILING", 11_500, 10_800),
        )
        self.assertGreater(long_plan.requested_stop_price_scaled, long_plan.entry_price_scaled)

        short_engine = build_position("pos-short", "SHORT")
        short_record = short_engine.current("pos-short")
        short_plan = self.planner.plan(
            short_record,
            protection(short_record),
            request(short_record, "DYNAMIC_EXIT", 8_800, 9_300),
        )
        self.assertLess(short_plan.requested_stop_price_scaled, short_plan.entry_price_scaled)

    def test_stop_can_never_loosen_or_noop(self) -> None:
        long_engine = build_position()
        long_record = long_engine.current("pos-long")
        long_protection = protection(long_record)
        for stop in (8_900, 9_000):
            with self.subTest(side="LONG", stop=stop):
                with self.assertRaises(DynamicExitError):
                    self.planner.plan(long_record, long_protection, request(long_record, "TRAILING", 10_500, stop))

        short_engine = build_position("pos-short", "SHORT")
        short_record = short_engine.current("pos-short")
        short_protection = protection(short_record)
        for stop in (11_000, 11_100):
            with self.subTest(side="SHORT", stop=stop):
                with self.assertRaises(DynamicExitError):
                    self.planner.plan(short_record, short_protection, request(short_record, "TRAILING", 9_500, stop))

    def test_triggered_geometry_fails_closed(self) -> None:
        long_engine = build_position()
        long_record = long_engine.current("pos-long")
        long_protection = protection(long_record)
        with self.assertRaises(DynamicExitError):
            self.planner.plan(long_record, long_protection, request(long_record, "TRAILING", 10_500, 10_500))
        with self.assertRaises(DynamicExitError):
            self.planner.plan(long_record, long_protection, request(long_record, "TRAILING", 12_000, 11_000))

        short_engine = build_position("pos-short", "SHORT")
        short_record = short_engine.current("pos-short")
        short_protection = protection(short_record)
        with self.assertRaises(DynamicExitError):
            self.planner.plan(short_record, short_protection, request(short_record, "TRAILING", 9_500, 9_500))
        with self.assertRaises(DynamicExitError):
            self.planner.plan(short_record, short_protection, request(short_record, "TRAILING", 8_000, 9_000))

    def test_break_even_requires_exact_entry_and_favorable_reference(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        current = protection(record)
        with self.assertRaises(DynamicExitError):
            self.planner.plan(record, current, request(record, "BREAK_EVEN", 10_500, 10_100))
        with self.assertRaises(DynamicExitError):
            self.planner.plan(record, current, request(record, "BREAK_EVEN", 10_000, 10_000))

    def test_stale_position_and_protection_binding_fail_closed(self) -> None:
        engine = build_position()
        old = engine.current("pos-long")
        old_protection = protection(old)
        old_request = request(old, "TRAILING", 10_500, 9_500)
        engine.apply(PositionFillEvent(
            position_id="pos-long",
            sequence=2,
            occurred_at_ns=2,
            event_type="REDUCE_FILL",
            quantity_scaled=10_000,
            price_scaled=10_300,
            order_id="order-reduce",
            client_order_id="client-reduce",
            oms_record_id=h("oms-reduce"),
            reconciliation_report_id=h("recon-reduce"),
        ))
        current = engine.current("pos-long")
        with self.assertRaises(DynamicExitError):
            self.planner.plan(current, old_protection, old_request)
        with self.assertRaises(DynamicExitError):
            self.planner.plan(current, old_protection, request(current, "TRAILING", 10_500, 9_500))

    def test_closed_position_fails_closed(self) -> None:
        engine = build_position()
        open_record = engine.current("pos-long")
        old_protection = protection(open_record)
        engine.apply(PositionFillEvent(
            position_id="pos-long",
            sequence=2,
            occurred_at_ns=2,
            event_type="REDUCE_FILL",
            quantity_scaled=100_000,
            price_scaled=10_500,
            order_id="order-close",
            client_order_id="client-close",
            oms_record_id=h("oms-close"),
            reconciliation_report_id=h("recon-close"),
        ))
        closed = engine.current("pos-long")
        with self.assertRaises(DynamicExitError):
            self.planner.plan(closed, old_protection, request(closed, "TRAILING", 10_600, 9_500))

    def test_determinism_and_authority_boundary(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        current = protection(record)
        req = request(record, "DYNAMIC_EXIT", 11_000, 10_400)
        first = self.planner.plan(record, current, req)
        second = self.planner.plan(record, current, req)
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertTrue(first.take_profit_preserved)
        self.assertFalse(first.real_venue_query)
        self.assertEqual(first.network_mode, "DISABLED")
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.external_order_mutation)
        self.assertFalse(first.automatic_oms_mutation)
        self.assertFalse(first.canonical_position_mutation)
        self.assertFalse(first.live_execution_authority)


if __name__ == "__main__":
    unittest.main()
