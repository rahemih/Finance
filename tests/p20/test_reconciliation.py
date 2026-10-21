from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import unittest

from packages.execution.reconciliation import (
    InternalExecutionView, ReconciliationEngine, ReconciliationError, ReconciliationPolicy, ReferenceVenueObservation,
)

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"config/execution/reconciliation-policy.json"
A="a"*64
B="b"*64
C="c"*64

def internal(*,state:str="OPEN",filled:int=0,safe_hold:bool=False)->InternalExecutionView:
    return InternalExecutionView(
        market="CRYPTO",order_id="order-001",client_order_id="client-001",oms_state=state,
        cumulative_filled_scaled=filled,total_quantity_scaled=100,quantity_scale=100,
        oms_record_id=A,idempotency_claim_id=B,recovery_checkpoint_id=C if safe_hold else None,
        recovery_safe_hold=safe_hold,
    )

def observation(*,status:str="OPEN",filled:int=0)->ReferenceVenueObservation:
    return ReferenceVenueObservation(
        market="CRYPTO",order_id="order-001",client_order_id="client-001",venue_status=status,
        cumulative_filled_scaled=filled,quantity_scale=100,observed_at_ns=100,
        source_ref="REFERENCE_SANDBOX_FIXTURE",venue_order_id="venue-001",
    )

class ReconciliationTests(unittest.TestCase):
    def setUp(self)->None:
        self.policy=ReconciliationPolicy.from_path(POLICY)
        self.engine=ReconciliationEngine(self.policy)

    def test_policy_is_reference_only_and_zero_authority(self)->None:
        self.assertEqual(self.policy.live_trading,"DISABLED")
        self.assertEqual(self.policy.auto_trading,"DISABLED")

    def test_exact_match_is_deterministic(self)->None:
        first=self.engine.reconcile(internal(),observation())
        second=self.engine.reconcile(internal(),observation())
        self.assertEqual(first,second)
        self.assertEqual(first.verdict,"MATCHED")
        self.assertFalse(first.reconciliation_required)
        self.assertFalse(first.automatic_oms_mutation)
        self.assertEqual(first.network_mode,"DISABLED")

    def test_identity_and_scale_mismatch_fail_closed(self)->None:
        with self.assertRaises(ReconciliationError):
            self.engine.reconcile(internal(),replace(observation(),order_id="other"))
        with self.assertRaises(ReconciliationError):
            self.engine.reconcile(internal(),replace(observation(),client_order_id="other"))
        with self.assertRaises(ReconciliationError):
            self.engine.reconcile(internal(),replace(observation(),quantity_scale=10))

    def test_fill_mismatch_is_classified(self)->None:
        report=self.engine.reconcile(internal(state="PARTIALLY_FILLED",filled=20),observation(status="PARTIALLY_FILLED",filled=30))
        self.assertEqual(report.verdict,"FILL_MISMATCH")
        self.assertEqual(report.fill_delta_scaled,10)
        self.assertTrue(report.reconciliation_required)

    def test_venue_ahead_can_suggest_single_unambiguous_event(self)->None:
        ack=self.engine.reconcile(internal(state="SUBMIT_PENDING"),observation(status="OPEN"))
        self.assertEqual(ack.verdict,"VENUE_AHEAD")
        self.assertEqual(ack.suggested_oms_event,"ACK")
        cancel_engine=ReconciliationEngine(self.policy)
        cancel=cancel_engine.reconcile(internal(state="CANCEL_PENDING"),observation(status="CANCELED"))
        self.assertEqual(cancel.suggested_oms_event,"CANCEL_ACK")

    def test_internal_ahead_is_fail_closed(self)->None:
        report=self.engine.reconcile(internal(state="OPEN"),observation(status="NOT_FOUND"))
        self.assertEqual(report.verdict,"INTERNAL_AHEAD")
        self.assertTrue(report.reconciliation_required)

    def test_terminal_conflict_is_fail_closed(self)->None:
        report=self.engine.reconcile(internal(state="FILLED",filled=100),observation(status="CANCELED",filled=100))
        self.assertEqual(report.verdict,"STATE_CONFLICT")
        self.assertTrue(report.reconciliation_required)
        self.assertIsNone(report.suggested_oms_event)

    def test_p20f_safe_hold_can_remain_unresolved(self)->None:
        report=self.engine.reconcile(internal(state="SUBMIT_PENDING",safe_hold=True),observation(status="NOT_FOUND"))
        self.assertEqual(report.verdict,"UNRESOLVED_AMBIGUITY")
        self.assertTrue(report.reconciliation_required)

    def test_venue_overfill_fails_closed(self)->None:
        with self.assertRaises(ReconciliationError):
            self.engine.reconcile(internal(),observation(status="FILLED",filled=101))

    def test_snapshot_is_deterministic_and_has_no_mutation_authority(self)->None:
        self.engine.reconcile(internal(),observation())
        first=self.engine.snapshot(); second=self.engine.snapshot()
        self.assertEqual(first,second)
        authority=first["authority"]; assert isinstance(authority,dict)
        self.assertFalse(authority["real_venue_query"])
        self.assertFalse(authority["automatic_oms_mutation"])
        self.assertFalse(authority["external_order_mutation"])
        self.assertEqual(authority["network_mode"],"DISABLED")
        self.assertFalse(authority["live_execution_authority"])

if __name__=="__main__": unittest.main()
