from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    BrokerPositionReconciler,
    BrokerReconciliationPolicy,
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    PositionFillEvent,
    PositionRecoveryCheckpoint,
    PositionRestartRecovery,
    PositionSpec,
    ReferenceBrokerPositionObservation,
    RestartRecoveryError,
    RestartRecoveryPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
RECON_POLICY = ROOT / "config/position-management/broker-reconciliation-policy.json"
RECOVERY_POLICY = ROOT / "config/position-management/restart-recovery-policy.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def build_position():
    engine = CanonicalPositionEngine(CanonicalPositionPolicy.from_path(POSITION_POLICY))
    engine.register(PositionSpec(
        position_id="pos-recovery",
        portfolio_id="portfolio",
        strategy_id="strategy",
        asset_id="BTC-USDT",
        market="CRYPTO",
        side="LONG",
        quantity_scale=100_000,
        price_scale=100,
        risk_validation_id=h("risk"),
        pretrade_firewall_id=h("fw"),
    ))
    engine.apply(PositionFillEvent(
        position_id="pos-recovery", sequence=1, occurred_at_ns=100,
        event_type="OPEN_FILL", quantity_scaled=100_000, price_scaled=10_000,
        order_id="order-1", client_order_id="client-1",
        oms_record_id=h("oms-1"), reconciliation_report_id=h("recon-1"),
    ))
    return engine


def observation(record, *, quantity=None):
    if quantity is None:
        quantity = record.open_quantity_scaled
    return ReferenceBrokerPositionObservation(
        position_record_id=record.record_id,
        position_id=record.position_id,
        asset_id=record.asset_id,
        market=record.market,
        status="OPEN",
        quantity_scale=record.quantity_scale,
        price_scale=record.price_scale,
        observed_at_ns=record.occurred_at_ns,
        source_ref="reference://p21g",
        side=record.side,
        open_quantity_scaled=quantity,
        average_entry_price_scaled_floor=record.average_entry_price_scaled_floor,
        external_position_ref="sandbox:pos-recovery",
    )


class RestartRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reconciler = BrokerPositionReconciler(BrokerReconciliationPolicy.from_path(RECON_POLICY))
        self.recovery = PositionRestartRecovery(RestartRecoveryPolicy.from_path(RECOVERY_POLICY))

    def test_matched_checkpoint_is_recoverable_without_mutation_authority(self) -> None:
        record = build_position().current("pos-recovery")
        checkpoint = PositionRecoveryCheckpoint.from_record(
            record, persisted_at_ns=200, persistence_ref="checkpoint://p21g/1"
        )
        report = self.reconciler.reconcile(record, observation(record))
        plan = self.recovery.plan(checkpoint, report)
        self.assertEqual(plan.disposition, "RECOVERABLE_MATCHED_CHECKPOINT")
        self.assertEqual(plan.action, "RESTORE_VALIDATED_CANONICAL_STATE")
        self.assertFalse(plan.safe_hold_required)
        self.assertFalse(plan.new_entry_block_required)
        self.assertFalse(plan.automatic_position_mutation)
        self.assertFalse(plan.automatic_oms_mutation)
        self.assertFalse(plan.real_venue_query)
        self.assertEqual(plan.network_mode, "DISABLED")
        self.assertFalse(plan.live_execution_authority)

    def test_reconciliation_mismatch_forces_safe_hold(self) -> None:
        record = build_position().current("pos-recovery")
        checkpoint = PositionRecoveryCheckpoint.from_record(
            record, persisted_at_ns=200, persistence_ref="checkpoint://p21g/2"
        )
        report = self.reconciler.reconcile(
            record, observation(record, quantity=record.open_quantity_scaled - 1)
        )
        plan = self.recovery.plan(checkpoint, report)
        self.assertEqual(plan.disposition, "SAFE_HOLD_MANUAL_RECOVERY_REQUIRED")
        self.assertEqual(plan.action, "MANUAL_GOVERNED_RECOVERY_REQUIRED")
        self.assertTrue(plan.safe_hold_required)
        self.assertTrue(plan.new_entry_block_required)

    def test_corrupted_checkpoint_fails_closed(self) -> None:
        record = build_position().current("pos-recovery")
        checkpoint = PositionRecoveryCheckpoint(
            position_record_id=record.record_id,
            position_payload={**record.payload(), "open_quantity_scaled": record.open_quantity_scaled - 1},
            persisted_at_ns=200,
            persistence_ref="checkpoint://p21g/corrupt",
            content_sha256=hashlib.sha256(b"wrong").hexdigest(),
        )
        report = self.reconciler.reconcile(record, observation(record))
        with self.assertRaises(RestartRecoveryError):
            self.recovery.plan(checkpoint, report)

    def test_report_bound_to_different_record_fails_closed(self) -> None:
        first = build_position()
        record = first.current("pos-recovery")
        checkpoint = PositionRecoveryCheckpoint.from_record(
            record, persisted_at_ns=200, persistence_ref="checkpoint://p21g/stale"
        )
        first.apply(PositionFillEvent(
            position_id="pos-recovery", sequence=2, occurred_at_ns=300,
            event_type="REDUCE_FILL", quantity_scaled=10_000, price_scaled=10_200,
            order_id="order-2", client_order_id="client-2",
            oms_record_id=h("oms-2"), reconciliation_report_id=h("recon-2"),
        ))
        newer = first.current("pos-recovery")
        report = self.reconciler.reconcile(newer, observation(newer))
        with self.assertRaises(RestartRecoveryError):
            self.recovery.plan(checkpoint, report)

    def test_plan_is_deterministic(self) -> None:
        record = build_position().current("pos-recovery")
        checkpoint = PositionRecoveryCheckpoint.from_record(
            record, persisted_at_ns=200, persistence_ref="checkpoint://p21g/deterministic"
        )
        report = self.reconciler.reconcile(record, observation(record))
        first = self.recovery.plan(checkpoint, report)
        second = self.recovery.plan(checkpoint, report)
        self.assertEqual(first.plan_id, second.plan_id)


if __name__ == "__main__":
    unittest.main()
