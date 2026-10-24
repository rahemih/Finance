from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    PositionFillEvent,
    PositionSpec,
    TpSlError,
    TpSlPlanner,
    TpSlPolicy,
    TpSlRequest,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
TPSL_POLICY = ROOT / "config/position-management/tp-sl-policy.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def position(side: str = "LONG", position_id: str = "pos-1"):
    p_policy = CanonicalPositionPolicy.from_path(POSITION_POLICY)
    engine = CanonicalPositionEngine(p_policy)
    engine.register(PositionSpec(
        position_id=position_id,
        portfolio_id="portfolio",
        strategy_id="strategy",
        asset_id="BTC-USDT" if side == "LONG" else "EUR-USD",
        market="CRYPTO" if side == "LONG" else "FOREX",
        side=side,
        quantity_scale=100_000,
        price_scale=100,
        risk_validation_id=h("risk:"+position_id),
        pretrade_firewall_id=h("fw:"+position_id),
    ))
    engine.apply(PositionFillEvent(
        position_id=position_id,
        sequence=1,
        occurred_at_ns=1,
        event_type="OPEN_FILL",
        quantity_scaled=100_000,
        price_scaled=10_000,
        order_id="order-"+position_id,
        client_order_id="client-"+position_id,
        oms_record_id=h("oms:"+position_id),
        reconciliation_report_id=h("recon:"+position_id),
    ))
    return engine


def request(record, *, tp: int, sl: int, entry: int | None = None) -> TpSlRequest:
    return TpSlRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        side=record.side,
        entry_price_scaled=record.average_entry_price_scaled_floor if entry is None else entry,
        take_profit_price_scaled=tp,
        stop_loss_price_scaled=sl,
        signal_decision_id=h("signal:"+record.position_id),
        risk_validation_id=h("risk-plan:"+record.position_id),
    )


class TpSlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = TpSlPolicy.from_path(TPSL_POLICY)
        self.planner = TpSlPlanner(self.policy)

    def test_long_geometry_passes(self) -> None:
        engine = position("LONG")
        record = engine.current("pos-1")
        plan = self.planner.plan(record, request(record, tp=11_000, sl=9_000))
        self.assertEqual(plan.side, "LONG")
        self.assertEqual(plan.target_distance_scaled, 1_000)
        self.assertEqual(plan.stop_distance_scaled, 1_000)

    def test_short_geometry_passes(self) -> None:
        engine = position("SHORT", "pos-short")
        record = engine.current("pos-short")
        plan = self.planner.plan(record, request(record, tp=9_000, sl=11_000))
        self.assertEqual(plan.side, "SHORT")
        self.assertEqual(plan.target_distance_scaled, 1_000)
        self.assertEqual(plan.stop_distance_scaled, 1_000)

    def test_inverted_or_equal_geometry_fails_closed(self) -> None:
        long_engine = position("LONG")
        long_record = long_engine.current("pos-1")
        with self.assertRaises(TpSlError):
            self.planner.plan(long_record, request(long_record, tp=9_000, sl=11_000))
        with self.assertRaises(TpSlError):
            self.planner.plan(long_record, request(long_record, tp=10_000, sl=9_000))

    def test_stale_position_record_binding_fails_closed(self) -> None:
        engine = position("LONG")
        first = engine.current("pos-1")
        engine.apply(PositionFillEvent(
            position_id="pos-1",
            sequence=2,
            occurred_at_ns=2,
            event_type="ADD_FILL",
            quantity_scaled=50_000,
            price_scaled=11_000,
            order_id="order-add",
            client_order_id="client-add",
            oms_record_id=h("oms-add"),
            reconciliation_report_id=h("recon-add"),
        ))
        current = engine.current("pos-1")
        stale = request(first, tp=11_000, sl=9_000)
        with self.assertRaises(TpSlError):
            self.planner.plan(current, stale)

    def test_closed_position_fails_closed(self) -> None:
        engine = position("LONG")
        engine.apply(PositionFillEvent(
            position_id="pos-1",
            sequence=2,
            occurred_at_ns=2,
            event_type="REDUCE_FILL",
            quantity_scaled=100_000,
            price_scaled=11_000,
            order_id="order-close",
            client_order_id="client-close",
            oms_record_id=h("oms-close"),
            reconciliation_report_id=h("recon-close"),
        ))
        record = engine.current("pos-1")
        with self.assertRaises(TpSlError):
            self.planner.plan(record, request(record, tp=11_000, sl=9_000))

    def test_entry_binding_and_plan_identity_are_deterministic(self) -> None:
        engine = position("LONG")
        record = engine.current("pos-1")
        with self.assertRaises(TpSlError):
            self.planner.plan(record, request(record, tp=11_000, sl=9_000, entry=10_001))
        first = self.planner.plan(record, request(record, tp=11_000, sl=9_000))
        second = self.planner.plan(record, request(record, tp=11_000, sl=9_000))
        self.assertEqual(first, second)
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertFalse(first.real_venue_query)
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.external_order_mutation)
        self.assertFalse(first.live_execution_authority)


if __name__ == "__main__":
    unittest.main()
