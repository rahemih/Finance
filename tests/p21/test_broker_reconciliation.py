from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    BrokerPositionReconciler,
    BrokerReconciliationError,
    BrokerReconciliationPolicy,
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    PositionFillEvent,
    PositionSpec,
    ReferenceBrokerPositionObservation,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
RECON_POLICY = ROOT / "config/position-management/broker-reconciliation-policy.json"


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
        occurred_at_ns=100,
        event_type="OPEN_FILL",
        quantity_scaled=100_000,
        price_scaled=10_000,
        order_id="order-open-" + position_id,
        client_order_id="client-open-" + position_id,
        oms_record_id=h("oms-open:" + position_id),
        reconciliation_report_id=h("recon-open:" + position_id),
    ))
    return engine


def observation(record, *, status: str = "OPEN", observed_at_ns: int = 100, **changes):
    values = {
        "position_record_id": record.record_id,
        "position_id": record.position_id,
        "asset_id": record.asset_id,
        "market": record.market,
        "status": status,
        "quantity_scale": record.quantity_scale,
        "price_scale": record.price_scale,
        "observed_at_ns": observed_at_ns,
        "source_ref": "reference://p21f/" + record.position_id,
        "side": record.side if status == "OPEN" else None,
        "open_quantity_scaled": record.open_quantity_scaled if status == "OPEN" else 0,
        "average_entry_price_scaled_floor": record.average_entry_price_scaled_floor if status == "OPEN" else None,
        "external_position_ref": "external:" + record.position_id if status == "OPEN" else None,
    }
    values.update(changes)
    return ReferenceBrokerPositionObservation(**values)


class BrokerReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reconciler = BrokerPositionReconciler(BrokerReconciliationPolicy.from_path(RECON_POLICY))

    def test_matching_open_position(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        report = self.reconciler.reconcile(record, observation(record))
        self.assertEqual(report.verdict, "MATCHED")
        self.assertFalse(report.safe_hold_required)
        self.assertFalse(report.new_entry_block_required)
        self.assertEqual(report.action, "NONE")

    def test_closed_plus_not_found_is_matched(self) -> None:
        engine = build_position()
        engine.apply(PositionFillEvent(
            position_id="pos-long", sequence=2, occurred_at_ns=200, event_type="REDUCE_FILL",
            quantity_scaled=100_000, price_scaled=10_500, order_id="order-close",
            client_order_id="client-close", oms_record_id=h("oms-close"),
            reconciliation_report_id=h("recon-close"),
        ))
        record = engine.current("pos-long")
        report = self.reconciler.reconcile(record, observation(record, status="NOT_FOUND", observed_at_ns=200))
        self.assertEqual(record.state, "CLOSED")
        self.assertEqual(report.verdict, "MATCHED")

    def test_open_missing_external_position_fails_safe(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        report = self.reconciler.reconcile(record, observation(record, status="NOT_FOUND"))
        self.assertEqual(report.verdict, "MISSING_EXTERNAL_POSITION")
        self.assertTrue(report.safe_hold_required)
        self.assertTrue(report.new_entry_block_required)
        self.assertEqual(report.action, "MANUAL_GOVERNED_RECONCILIATION_REQUIRED")

    def test_closed_with_external_exposure_conflict(self) -> None:
        engine = build_position()
        engine.apply(PositionFillEvent(
            position_id="pos-long", sequence=2, occurred_at_ns=200, event_type="REDUCE_FILL",
            quantity_scaled=100_000, price_scaled=10_500, order_id="order-close",
            client_order_id="client-close", oms_record_id=h("oms-close"),
            reconciliation_report_id=h("recon-close"),
        ))
        record = engine.current("pos-long")
        report = self.reconciler.reconcile(
            record,
            observation(
                record,
                status="OPEN",
                observed_at_ns=200,
                side="LONG",
                open_quantity_scaled=1,
                average_entry_price_scaled_floor=10_000,
            ),
        )
        self.assertEqual(report.verdict, "EXTERNAL_EXPOSURE_CONFLICT")
        self.assertTrue(report.safe_hold_required)

    def test_exact_side_quantity_entry_and_identity_mismatches(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")

        side = self.reconciler.reconcile(record, observation(record, side="SHORT"))
        self.assertEqual(side.verdict, "SIDE_MISMATCH")

        quantity = self.reconciler.reconcile(
            record,
            observation(record, open_quantity_scaled=record.open_quantity_scaled + 1),
        )
        self.assertEqual(quantity.verdict, "QUANTITY_MISMATCH")

        entry = self.reconciler.reconcile(
            record,
            observation(record, average_entry_price_scaled_floor=record.average_entry_price_scaled_floor + 1),
        )
        self.assertEqual(entry.verdict, "ENTRY_PRICE_MISMATCH")

        identity = self.reconciler.reconcile(record, observation(record, market="WRONG"))
        self.assertEqual(identity.verdict, "IDENTITY_MISMATCH")

        multiple = self.reconciler.reconcile(
            record,
            observation(
                record,
                side="SHORT",
                open_quantity_scaled=record.open_quantity_scaled - 1,
                average_entry_price_scaled_floor=record.average_entry_price_scaled_floor + 1,
            ),
        )
        self.assertEqual(multiple.verdict, "MULTIPLE_MISMATCH")
        self.assertEqual(
            multiple.mismatch_fields,
            ("side", "open_quantity_scaled", "average_entry_price_scaled_floor"),
        )

    def test_stale_record_and_old_observation_fail_closed(self) -> None:
        engine = build_position()
        old = engine.current("pos-long")
        old_observation = observation(old)
        engine.apply(PositionFillEvent(
            position_id="pos-long", sequence=2, occurred_at_ns=200, event_type="REDUCE_FILL",
            quantity_scaled=10_000, price_scaled=10_200, order_id="order-reduce",
            client_order_id="client-reduce", oms_record_id=h("oms-reduce"),
            reconciliation_report_id=h("recon-reduce"),
        ))
        current = engine.current("pos-long")
        with self.assertRaises(BrokerReconciliationError):
            self.reconciler.reconcile(current, old_observation)

        with self.assertRaises(BrokerReconciliationError):
            self.reconciler.reconcile(current, observation(current, observed_at_ns=199))

    def test_malformed_not_found_observation_fails_closed(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        with self.assertRaises(BrokerReconciliationError):
            self.reconciler.reconcile(
                record,
                observation(record, status="NOT_FOUND", side="LONG"),
            )

    def test_determinism_lineage_and_no_mutation_authority(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        obs = observation(record, open_quantity_scaled=99_999)
        first = self.reconciler.reconcile(record, obs)
        second = self.reconciler.reconcile(record, obs)
        self.assertEqual(first.report_id, second.report_id)
        self.assertEqual(first.canonical_source_oms_record_id, record.source_oms_record_id)
        self.assertEqual(
            first.canonical_source_reconciliation_report_id,
            record.source_reconciliation_report_id,
        )
        self.assertFalse(first.auto_repair)
        self.assertFalse(first.auto_flatten)
        self.assertFalse(first.real_venue_query)
        self.assertEqual(first.network_mode, "DISABLED")
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.external_order_mutation)
        self.assertFalse(first.automatic_oms_mutation)
        self.assertFalse(first.canonical_position_mutation)
        self.assertFalse(first.live_execution_authority)


if __name__ == "__main__":
    unittest.main()
