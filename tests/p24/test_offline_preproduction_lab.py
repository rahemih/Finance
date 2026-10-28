from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from packages.production.offline_preproduction_lab import (
    EXPECTED_POLICY,
    OfflineLabError,
    OfflinePreproductionLab,
    SyntheticEvent,
    digest,
    reference_scenarios,
    render_html,
    run_reference_suite,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/p24-offline-lab-policy.json"


def event(**changes: object) -> SyntheticEvent:
    return replace(SyntheticEvent("check", "check-1", 1, "FOREX", "TICK"), **changes)


class OfflinePreproductionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lab = OfflinePreproductionLab.from_path(POLICY)

    def denied(self, bad: SyntheticEvent) -> None:
        with self.assertRaises(OfflineLabError):
            self.lab.accept(bad)
        self.assertEqual(len(self.lab.decisions), 0)

    def test_01_exact_policy_loaded(self) -> None:
        self.assertEqual(self.lab.policy_id, digest(EXPECTED_POLICY))
        self.assertEqual(self.lab.state, "ACTIVE_SIMULATION_ONLY")

    def test_02_policy_network_flip_rejected(self) -> None:
        altered = {**EXPECTED_POLICY, "network_mode": "ENABLED"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            p.write_text(json.dumps(altered))
            with self.assertRaises(OfflineLabError):
                OfflinePreproductionLab.from_path(p)

    def test_03_policy_bool_integer_substitution_rejected(self) -> None:
        altered = {**EXPECTED_POLICY, "external_order_submission": 0}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "policy.json"
            p.write_text(json.dumps(altered))
            with self.assertRaises(OfflineLabError):
                OfflinePreproductionLab.from_path(p)

    def test_04_forged_policy_identity_rejected(self) -> None:
        with self.assertRaises(OfflineLabError):
            OfflinePreproductionLab("arbitrary")

    def test_05_missing_policy_rejected(self) -> None:
        with self.assertRaises(OfflineLabError):
            OfflinePreproductionLab.from_path(Path("/missing-p24wo-policy-for-test.json"))

    def test_06_synthetic_tick_no_order_authority(self) -> None:
        result = self.lab.accept(event())
        self.assertFalse(result.external_order_authority)
        self.assertFalse(result.real_money_authority)
        self.assertEqual(result.state, "ACTIVE_SIMULATION_ONLY")
        self.assertEqual(result.status, "REFERENCE_OBSERVATION_ONLY")

    def test_07_tick_age_at_threshold_allowed(self) -> None:
        self.assertEqual(self.lab.accept(event(age_ms=1500)).state, "ACTIVE_SIMULATION_ONLY")

    def test_08_stale_tick_causes_latched_safe_mode(self) -> None:
        self.assertEqual(self.lab.accept(event(age_ms=1501)).reason, "STALE_MARKET_DATA")
        recovered = self.lab.accept(event(event_id="check-2", sequence=2))
        self.assertEqual(recovered.state, "SAFE_MODE")
        self.assertEqual(recovered.reason, "LATCHED_STOP_REQUIRES_INDEPENDENT_RESET")

    def test_09_disconnection_refused(self) -> None:
        self.assertEqual(self.lab.accept(event(connected=False)).state, "SAFE_MODE")

    def test_10_disconnect_event_refused(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="BROKER_DISCONNECT")).reason, "BROKER_DISCONNECTED")

    def test_11_unknown_ack_must_reconcile(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="ACK_UNKNOWN")).state, "WAIT_RECONCILIATION")

    def test_12_partial_fill_mismatch_must_reconcile(self) -> None:
        self.assertEqual(
            self.lab.accept(event(kind="PARTIAL_FILL_MISMATCH")).state,
            "WAIT_RECONCILIATION",
        )

    def test_13_reconciliation_false_must_reconcile(self) -> None:
        self.assertEqual(self.lab.accept(event(reconciliation_ok=False)).state, "WAIT_RECONCILIATION")

    def test_14_explicit_risk_veto_halts(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="RISK_VETO")).reason, "A5_RISK_VETO")

    def test_15_independent_risk_veto_flag_halts(self) -> None:
        self.assertEqual(self.lab.accept(event(risk_veto=True)).state, "HALTED")

    def test_16_global_kill_halts(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="KILL_SWITCH", kill_scope="GLOBAL")).state, "HALTED")

    def test_17_strategy_kill_halts(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="KILL_SWITCH", kill_scope="STRATEGY")).state, "HALTED")

    def test_18_broker_kill_halts(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="KILL_SWITCH", kill_scope="BROKER")).state, "HALTED")

    def test_19_margin_alarm_halts(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="MARGIN_ALERT")).state, "HALTED")

    def test_20_reset_cannot_undo_halt(self) -> None:
        self.lab.accept(event(kind="KILL_SWITCH", kill_scope="GLOBAL"))
        result = self.lab.accept(event(kind="RESET_REQUEST", event_id="check-2", sequence=2))
        self.assertEqual(result.state, "HALTED")
        self.assertEqual(result.status, "FAIL_CLOSED_NO_ORDER")

    def test_21_reset_is_never_authoritative_even_if_healthy(self) -> None:
        self.assertEqual(self.lab.accept(event(kind="RESET_REQUEST")).reason, "NO_SELF_APPROVAL_OR_RESET_AUTHORITY")

    def test_22_sequence_gap_detected(self) -> None:
        self.lab.accept(event())
        self.assertEqual(
            self.lab.accept(event(event_id="check-3", sequence=3)).reason,
            "SEQUENCE_GAP",
        )

    def test_23_duplicate_event_id_rejected(self) -> None:
        self.lab.accept(event())
        with self.assertRaises(OfflineLabError):
            self.lab.accept(event(sequence=2))

    def test_24_out_of_order_sequence_rejected(self) -> None:
        self.lab.accept(event())
        with self.assertRaises(OfflineLabError):
            self.lab.accept(event(event_id="check-0", sequence=1))

    def test_25_live_environment_rejected(self) -> None:
        self.denied(event(environment="LIVE"))

    def test_26_network_enabled_rejected(self) -> None:
        self.denied(event(network_mode="ENABLED"))

    def test_27_credentials_rejected(self) -> None:
        self.denied(event(credential_mode="BROKER_KEY"))

    def test_28_order_authority_rejected(self) -> None:
        self.denied(event(external_order_submission=True))

    def test_29_live_execution_authority_rejected(self) -> None:
        self.denied(event(live_execution_authority=True))

    def test_30_bool_as_int_rejected(self) -> None:
        self.denied(event(risk_veto=0))
        self.denied(event(connected=1))
        self.denied(event(external_order_submission=0))

    def test_31_sequence_boolean_and_negative_rejected(self) -> None:
        self.denied(event(sequence=True))
        self.denied(event(sequence=-1))
        self.denied(event(age_ms=-1))

    def test_32_unknown_market_or_kind_rejected(self) -> None:
        self.denied(event(market="STOCK"))
        self.denied(event(kind="ORDER_SEND"))

    def test_33_invalid_kill_scope_rejected(self) -> None:
        self.denied(event(kind="KILL_SWITCH", kill_scope="UNLIMITED"))
        self.denied(event(kind="TICK", kill_scope="GLOBAL"))

    def test_34_dynamic_identity_type_rejected(self) -> None:
        self.denied(event(event_id=None))
        self.denied(event(scenario=[]))
        self.denied(event(event_id=" check-1 "))

    def test_35_reference_suite_deterministic(self) -> None:
        self.assertEqual(run_reference_suite(POLICY), run_reference_suite(POLICY))
        result = run_reference_suite(POLICY)
        self.assertEqual(result["scenario_count"], 16)
        self.assertEqual(result["broker_demo_events_observed"], 0)
        self.assertFalse(result["pre_live_kill_switch_certified"])

    def test_36_all_reference_traces_have_no_real_order(self) -> None:
        report = run_reference_suite(POLICY)
        scenarios = report["scenarios"]
        for scenario in scenarios:
            for decision in scenario["snapshot"]["decisions"]:
                self.assertFalse(decision["external_order_authority"])
                self.assertFalse(decision["real_money_authority"])

    def test_37_audit_hash_binds_all_event_fields(self) -> None:
        a = OfflinePreproductionLab.from_path(POLICY)
        b = OfflinePreproductionLab.from_path(POLICY)
        self.assertNotEqual(
            a.accept(event(age_ms=0)).audit_hash,
            b.accept(event(age_ms=1)).audit_hash,
        )

    def test_38_html_dashboard_is_escaped(self) -> None:
        payload = {
            "scenarios": [{"scenario": "<script>alert(1)</script>",
                           "snapshot": {"final_state": "SAFE_MODE", "event_count": 1, "snapshot_id": "abcd"}}],
            "evidence_id": "<onload>",
        }
        html = render_html(payload)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<onload>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("NOT A DEMO-BROKER CERTIFICATION", html)

    def test_39_snapshot_hash_is_chain_bound(self) -> None:
        self.lab.accept(event())
        snapshot = self.lab.snapshot()
        self.assertEqual(len(snapshot["snapshot_id"]), 64)
        self.assertEqual(snapshot["final_chain"], self.lab.decisions[-1].audit_hash)

    def test_40_safety_controls_cannot_be_promoted(self) -> None:
        output = self.lab.snapshot()
        safety = output["safety"]
        self.assertEqual(safety["live_trading"], "DISABLED")
        self.assertFalse(safety["production_pre_live_kill_switch_certified"])
        self.assertEqual(safety["g13"], "NOT_STARTED")


if __name__ == "__main__":
    unittest.main()
