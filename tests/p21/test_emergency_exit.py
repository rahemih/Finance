from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    EmergencyExitError,
    EmergencyExitPlanner,
    EmergencyExitPolicy,
    EmergencyExitRequest,
    PositionFillEvent,
    PositionSpec,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
EMERGENCY_POLICY = ROOT / "config/position-management/emergency-exit-policy.json"


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


def request(
    record,
    action: str,
    qty: int,
    trigger: str = "RISK_HALT",
    authority: str = "A5_GOVERNED_REDUCE_ONLY",
    reconciliation: str = "NOT_REQUIRED",
) -> EmergencyExitRequest:
    return EmergencyExitRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        action=action,
        requested_quantity_scaled=qty,
        trigger_code=trigger,
        authority_code=authority,
        reconciliation_status=reconciliation,
        emergency_decision_id=h("emergency:" + record.position_id + ":" + action + ":" + trigger),
        authority_decision_id=h("authority:" + record.position_id + ":" + authority),
    )


class EmergencyExitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = EmergencyExitPlanner(EmergencyExitPolicy.from_path(EMERGENCY_POLICY))

    def test_a5_governed_emergency_reduce_is_strictly_partial(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        plan = self.planner.plan(record, request(record, "EMERGENCY_REDUCE", 30_000))
        self.assertEqual(plan.requested_quantity_scaled, 30_000)
        self.assertEqual(plan.remaining_quantity_scaled, 70_000)
        self.assertTrue(plan.reduce_only)

    def test_owner_explicit_emergency_flatten(self) -> None:
        engine = build_position("pos-short", "SHORT")
        record = engine.current("pos-short")
        plan = self.planner.plan(record, request(
            record,
            "EMERGENCY_FLATTEN",
            100_000,
            trigger="SECURITY_INCIDENT",
            authority="OWNER_EXPLICIT_EMERGENCY_FLATTEN",
        ))
        self.assertEqual(plan.remaining_quantity_scaled, 0)
        self.assertEqual(plan.authority_code, "OWNER_EXPLICIT_EMERGENCY_FLATTEN")

    def test_non_owner_flatten_and_wrong_quantity_fail_closed(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(record, request(record, "EMERGENCY_FLATTEN", 100_000))
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(record, request(
                record,
                "EMERGENCY_FLATTEN",
                99_999,
                authority="OWNER_EXPLICIT_EMERGENCY_FLATTEN",
            ))

    def test_reduce_zero_full_and_over_close_fail_closed(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        for qty in (0, 100_000, 100_001):
            with self.subTest(qty=qty):
                with self.assertRaises(EmergencyExitError):
                    self.planner.plan(record, request(record, "EMERGENCY_REDUCE", qty))

    def test_provider_incident_requires_resolved_reconciliation(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(record, request(
                record,
                "EMERGENCY_REDUCE",
                10_000,
                trigger="PROVIDER_OR_EXECUTION_INCIDENT",
                reconciliation="NOT_REQUIRED",
            ))
        plan = self.planner.plan(record, request(
            record,
            "EMERGENCY_REDUCE",
            10_000,
            trigger="PROVIDER_OR_EXECUTION_INCIDENT",
            reconciliation="RESOLVED_NO_CONFLICT",
        ))
        self.assertEqual(plan.reconciliation_status, "RESOLVED_NO_CONFLICT")

    def test_unknown_reconciliation_state_fails_closed(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(record, request(
                record,
                "EMERGENCY_REDUCE",
                10_000,
                reconciliation="UNKNOWN",
            ))

    def test_p16_trigger_does_not_grant_close_authority(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(record, request(
                record,
                "EMERGENCY_REDUCE",
                10_000,
                trigger="DAILY_LOSS_CIRCUIT_TRIPPED",
                authority="P16_CIRCUIT_TRIGGER_ONLY",
            ))

    def test_stale_and_closed_position_fail_closed(self) -> None:
        engine = build_position()
        old = engine.current("pos-long")
        stale_request = request(old, "EMERGENCY_REDUCE", 10_000)
        engine.apply(PositionFillEvent(
            position_id="pos-long",
            sequence=2,
            occurred_at_ns=2,
            event_type="REDUCE_FILL",
            quantity_scaled=20_000,
            price_scaled=10_200,
            order_id="order-reduce",
            client_order_id="client-reduce",
            oms_record_id=h("oms-reduce"),
            reconciliation_report_id=h("recon-reduce"),
        ))
        current = engine.current("pos-long")
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(current, stale_request)

        engine.apply(PositionFillEvent(
            position_id="pos-long",
            sequence=3,
            occurred_at_ns=3,
            event_type="REDUCE_FILL",
            quantity_scaled=80_000,
            price_scaled=10_300,
            order_id="order-close",
            client_order_id="client-close",
            oms_record_id=h("oms-close"),
            reconciliation_report_id=h("recon-close"),
        ))
        closed = engine.current("pos-long")
        with self.assertRaises(EmergencyExitError):
            self.planner.plan(closed, request(closed, "EMERGENCY_REDUCE", 1))

    def test_determinism_and_authority_boundary(self) -> None:
        engine = build_position()
        record = engine.current("pos-long")
        req = request(
            record,
            "EMERGENCY_REDUCE",
            25_000,
            trigger="SYSTEM_EMERGENCY",
            authority="OWNER_EXPLICIT_EMERGENCY_REDUCE",
        )
        first = self.planner.plan(record, req)
        second = self.planner.plan(record, req)
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertTrue(first.requires_p20_idempotent_execution)
        self.assertTrue(first.requires_reconciliation_before_retry)
        self.assertFalse(first.blind_reroute_allowed)
        self.assertFalse(first.p16_trigger_auto_close_authority)
        self.assertFalse(first.real_venue_query)
        self.assertEqual(first.network_mode, "DISABLED")
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.external_order_mutation)
        self.assertFalse(first.automatic_oms_mutation)
        self.assertFalse(first.canonical_position_mutation)
        self.assertFalse(first.risk_firewall_bypass_authority)
        self.assertFalse(first.live_execution_authority)


if __name__ == "__main__":
    unittest.main()
