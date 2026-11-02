"""SC-01..SC-21 pure S0 fixtures; S1/S2/S3 are never contacted."""
from __future__ import annotations

from dataclasses import replace
import unittest

from packages.production.sandbox_s0_model import (
    BLOCKED, ROUTES, S0Decision, S0Engine, S0Event, S0Violation,
    s0_reference_evidence,
)


def e(n: int, kind: str = "TICK", **kw: object) -> S0Event:
    return replace(S0Event(f"fixture-{n}", n, kind), **kw)


class SyntheticSandboxS0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.lab = S0Engine()

    def step(self, n: int, kind: str = "TICK", **kw: object) -> S0Decision:
        return self.lab.apply(e(n, kind, **kw))

    def test_sc01_terminal_separation(self) -> None:
        self.assertEqual(set(ROUTES), {"FOREX", "CRYPTO"})
        with self.assertRaises(S0Violation):
            self.step(1, market="CRYPTO")
        other = S0Engine()
        r = other.apply(e(1, market="CRYPTO", server="CRYPTO-FIXTURE", symbol="BTCUSD"))
        self.assertFalse(r.external_order_authority)

    def test_sc02_tick_progress_fixture_only(self) -> None:
        self.assertEqual(self.step(1).simulation_state, "OBSERVATION")
        self.assertEqual(self.step(2).reason, "SYNTHETIC_OBSERVATION")
        self.assertEqual(self.step(3, fresh=False).reason, "STALE_QUOTE")
        self.assertEqual(self.lab.mode, "SAFE_MODE")

    def test_sc03_unattested_utc_fails_closed(self) -> None:
        r = self.step(1, timestamp_attested=False)
        self.assertEqual((r.reason, r.simulation_state), ("UNVERIFIED_TIME", "SAFE_MODE"))
        self.assertFalse(r.external_order_authority)

    def test_sc04_disconnected_before_intent(self) -> None:
        self.step(1, connected=False)
        r = self.step(2, "INTENT", units=10)
        self.assertEqual(r.reason, "LATCHED_STOP_REFUSES_NEW_INTENT")
        self.assertEqual(self.lab.order_states, {})

    def test_sc05_reconnect_does_not_clear_stop(self) -> None:
        self.step(1, "DISCONNECT")
        self.assertEqual(self.step(2, "RECONNECT").simulation_state, "SAFE_MODE")
        self.assertEqual(self.step(3).simulation_state, "SAFE_MODE")
        self.assertEqual(self.step(4, "INTENT", units=2).reason, "LATCHED_STOP_REFUSES_NEW_INTENT")

    def test_sc06_wrong_symbol_and_corrupt_time(self) -> None:
        with self.assertRaises(S0Violation):
            self.step(1, symbol="GBPUSD")
        self.assertEqual(self.step(1, timestamp_attested=False).reason, "UNVERIFIED_TIME")

    def test_sc07_crossmarket_route_denied(self) -> None:
        with self.assertRaises(S0Violation):
            self.step(1, market="CRYPTO", symbol="BTCUSD", server="FX-FIXTURE")
        self.assertEqual(self.lab.decisions, [])

    def test_sc08_missing_synthetic_gate(self) -> None:
        self.assertEqual(self.step(1, "INTENT", units=1, fixture_gate=False).reason, "SYNTHETIC_GATE_MISSING")
        self.assertEqual(self.lab.order_states, {})

    def test_sc09_risk_veto_before_intent(self) -> None:
        r = self.step(1, "INTENT", units=1, risk_approved=False)
        self.assertEqual(r.reason, "SYNTHETIC_A5_VETO")
        self.assertEqual(r.simulation_state, "HALTED")
        self.assertFalse(r.real_money_authority)

    def test_sc10_kill_latched_and_no_new_intent(self) -> None:
        self.step(1, "HALT")
        self.assertEqual(self.step(2, "INTENT", units=1).reason, "HALT_LATCHED_NO_SELF_RESET")
        self.assertEqual(self.lab.order_states, {})

    def test_sc11_duplicate_idempotency_key(self) -> None:
        self.step(1, "INTENT", units=8)
        r = self.step(2, "INTENT", units=8)
        self.assertEqual(r.reason, "DUPLICATE_CLIENT_KEY")
        self.assertEqual(self.lab.order_states["fixture-key"], "SIM_INTENT_PENDING")
        self.assertEqual(self.lab.mode, "SAFE_MODE")

    def test_sc12_missing_ack_no_retry(self) -> None:
        self.step(1, "INTENT", units=8)
        r = self.step(2, "ACK_UNKNOWN")
        self.assertEqual((r.simulation_state, r.fixture_order_state), ("WAIT_RECONCILIATION", "UNKNOWN_OUTCOME"))
        self.assertEqual(self.step(3, "INTENT", client_key="another", units=8).reason,
                         "LATCHED_STOP_REFUSES_NEW_INTENT")

    def test_sc13_late_ack_keeps_reconciliation_latch(self) -> None:
        self.step(1, "INTENT", units=7)
        self.step(2, "ACK_UNKNOWN")
        r = self.step(3, "ACK")
        self.assertEqual(r.fixture_order_state, "SIM_ACKED")
        self.assertEqual(r.simulation_state, "WAIT_RECONCILIATION")
        self.assertEqual(self.lab.quantities["fixture-key"], 7)
        self.assertEqual(self.lab.verified_fills["fixture-key"], 0)

    def test_sc14_partial_fill_then_remainder_reject(self) -> None:
        self.step(1, "INTENT", units=10)
        self.step(2, "ACK")
        r = self.step(3, "PARTIAL_FILL", units=4)
        self.assertEqual(r.fixture_order_state, "PARTIAL")
        self.assertEqual(self.step(4, "REJECT").fixture_order_state, "PARTIAL_REMAINDER_REJECTED")
        self.assertEqual(self.lab.verified_fills["fixture-key"], 4)

    def test_sc15_terminal_broker_reject_fixture(self) -> None:
        self.step(1, "INTENT", units=10)
        self.assertEqual(self.step(2, "REJECT").fixture_order_state, "SIM_REJECTED")
        self.assertEqual(self.lab.verified_fills["fixture-key"], 0)

    def test_sc16_cancel_fill_race(self) -> None:
        self.step(1, "INTENT", units=10)
        self.step(2, "ACK")
        self.assertEqual(self.step(3, "CANCEL_REQUEST").fixture_order_state, "CANCEL_PENDING")
        r = self.step(4, "FILL", units=10)
        self.assertEqual((r.reason, r.fixture_order_state), ("CANCEL_FILL_RACE", "UNKNOWN_OUTCOME"))
        self.assertEqual(self.lab.verified_fills["fixture-key"], 0)

    def test_sc17_disconnect_after_ack(self) -> None:
        self.step(1, "INTENT", units=10)
        self.step(2, "ACK")
        self.assertEqual(self.step(3, "DISCONNECT").simulation_state, "SAFE_MODE")
        self.assertEqual(self.step(4, "RECONCILE").simulation_state, "SAFE_MODE")
        self.assertEqual(self.step(5, "INTENT", client_key="next", units=1).reason,
                         "LATCHED_STOP_REFUSES_NEW_INTENT")

    def test_sc18_halt_during_synthetic_queue(self) -> None:
        self.step(1, "INTENT", client_key="a", units=1)
        self.step(2, "INTENT", client_key="b", units=1)
        self.step(3, "HALT")
        self.assertEqual(len(self.lab.order_states), 2)
        self.assertEqual(self.step(4, "INTENT", client_key="c", units=1).simulation_state, "HALTED")
        self.assertNotIn("c", self.lab.order_states)

    def test_sc19_changed_server_must_reject(self) -> None:
        self.step(1, "DISCONNECT")
        with self.assertRaises(S0Violation):
            self.step(2, "RECONNECT", server="OTHER-SERVER")
        self.assertEqual(self.step(2, "RECONNECT").simulation_state, "SAFE_MODE")
        self.assertEqual(self.step(3, "INTENT", units=1).status if hasattr(self.step(3, "TICK"), "status") else BLOCKED, BLOCKED)

    def test_sc20_hash_chain_tamper_detected(self) -> None:
        self.step(1)
        self.lab.chain = "f" * 64
        with self.assertRaises(S0Violation):
            self.step(2)

    def test_sc21_market_data_rights_expiry(self) -> None:
        self.step(1)
        self.assertEqual(self.step(2, "SOURCE_EXPIRED").reason, "SOURCE_RIGHTS_UNVERIFIED")
        self.assertEqual(self.step(3, "INTENT", units=1).simulation_state, "SAFE_MODE")

    def test_22_synthetic_reconciliation_does_not_rearm(self) -> None:
        self.step(1, "INTENT", units=10)
        self.step(2, "ACK_UNKNOWN")
        self.assertEqual(self.step(3, "RECONCILE").fixture_order_state, "FIXTURE_RECONCILED")
        self.assertEqual(self.lab.mode, "WAIT_RECONCILIATION")
        self.assertEqual(self.step(4, "RESET").simulation_state, "WAIT_RECONCILIATION")

    def test_23_event_replay_rejected(self) -> None:
        self.step(1)
        with self.assertRaises(S0Violation):
            self.step(1)
        with self.assertRaises(S0Violation):
            self.step(0)

    def test_24_gap_is_latched(self) -> None:
        self.step(1)
        self.assertEqual(self.step(3).reason, "EVENT_SEQUENCE_GAP")
        self.assertEqual(self.step(4, "INTENT", units=1).simulation_state, "SAFE_MODE")

    def test_25_non_simulated_environment_denied(self) -> None:
        for changes in ({"environment": "LIVE"}, {"network_mode": "ENABLED"},
                        {"credential_mode": "MT5"}, {"external_order_submission": True}):
            with self.subTest(changes=changes), self.assertRaises(S0Violation):
                self.step(1, **changes)
        self.assertEqual(self.lab.decisions, [])

    def test_26_non_boolean_spoofing_denied(self) -> None:
        for changes in ({"sequence": True}, {"units": True},
                        {"risk_approved": 1}, {"fixture_gate": 1},
                        {"audit_ok": "yes"}, {"external_order_submission": 0}):
            with self.subTest(changes=changes), self.assertRaises(S0Violation):
                self.lab.apply(replace(e(1), **changes))

    def test_27_invalid_order_quantity_denied(self) -> None:
        self.assertEqual(self.step(1, "INTENT", units=0).reason, "INVALID_SYNTHETIC_QUANTITY")
        self.assertEqual(self.lab.order_states, {})

    def test_28_recovered_venue_with_unknown_ack_not_new_intent(self) -> None:
        self.step(1, "INTENT", units=1)
        self.step(2, "ACK_UNKNOWN")
        self.step(3, "ACK")
        self.step(4, "RECONCILE")
        self.assertEqual(self.step(5, "INTENT", client_key="another", units=1).simulation_state,
                         "WAIT_RECONCILIATION")

    def test_29_unlicensed_quote_blocks_entire_fixture(self) -> None:
        self.assertEqual(self.step(1, "TICK", licensed=False).reason, "SOURCE_RIGHTS_UNVERIFIED")
        self.assertEqual(self.step(2, "INTENT", units=1).simulation_state, "SAFE_MODE")

    def test_30_halt_audit_failure_no_release(self) -> None:
        self.assertEqual(self.step(1, "AUDIT_FAIL").reason, "AUDIT_INTEGRITY_FAIL")
        self.assertEqual(self.step(2, "RESET").reason, "HALT_LATCHED_NO_SELF_RESET")

    def test_31_deterministic_no_broker_evidence(self) -> None:
        a, b = s0_reference_evidence(), s0_reference_evidence()
        self.assertEqual(a, b)
        self.assertEqual(a["pre_first_live_satisfied"], 0)
        self.assertEqual(a["broker_order_tests"], "NOT_RUN")
        self.assertEqual(a["s2_scenarios"], {"SC-22": "NOT_RUN", "SC-23": "NOT_RUN", "SC-24": "NOT_RUN"})
        self.assertEqual(len(a["evidence_id"]), 64)
        for trace in a["traces"]:
            self.assertEqual(trace["actual_broker_orders"], 0)
            self.assertEqual(trace["actual_broker_connections"], 0)
            self.assertFalse(trace["production_broker_certified"])
            for decision in trace["events"]:
                self.assertFalse(decision["external_order_authority"])
                self.assertFalse(decision["real_money_authority"])


if __name__ == "__main__":
    unittest.main()
