"""P24-C Semi-Auto preparatory S0 controls. unittest discovery is mandatory."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from packages.production.semiauto_s0_preflight import (
    S0Verdict,
    SyntheticApproval,
    SyntheticControls,
    SyntheticIntent,
    evaluate_s0,
)

ROOT = Path(__file__).resolve().parents[2]


class SemiAutoS0PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.intent = SyntheticIntent("S0-001", 1, "DEMO_ONLY", "STRAT_X", "SYNTH_X", "BUY", 1)
        self.controls = SyntheticControls(**{name: True for name in SyntheticControls.__dataclass_fields__})
        self.approval = SyntheticApproval(True, self.intent.digest(), 1, "ACK-S0-001", 120)

    def evaluate(self, *, intent: SyntheticIntent | None = None, approval: SyntheticApproval | None = None,
                 controls: SyntheticControls | None = None, tick: int = 100,
                 consumed: frozenset[str] = frozenset()) -> S0Verdict:
        return evaluate_s0(intent or self.intent, approval or self.approval,
                           controls or self.controls, now_tick=tick, consumed_acknowledgements=consumed)

    def assert_no_authority(self, verdict: S0Verdict) -> None:
        self.assertFalse(verdict.external_order_authority)
        self.assertEqual(verdict.next_action, "NO_ORDER")
        self.assertFalse(verdict.operational_demo_certified)
        self.assertFalse(verdict.p24_c_stage_activated)
        self.assertFalse(verdict.live_trading_enabled)
        self.assertFalse(verdict.auto_trading_enabled)

    def test_default_deny(self) -> None:
        verdict = evaluate_s0(self.intent, SyntheticApproval(), SyntheticControls(), now_tick=100)
        self.assertEqual(verdict.state, "S0_BLOCKED")
        self.assert_no_authority(verdict)

    def test_positive_synthetic_fixture_not_trade_authority(self) -> None:
        verdict = self.evaluate()
        self.assertEqual(verdict.state, "S0_FIXTURE_ELIGIBLE")
        self.assertEqual(verdict.reasons, ())
        self.assert_no_authority(verdict)

    def test_every_missing_control_blocks(self) -> None:
        for name in SyntheticControls.__dataclass_fields__:
            with self.subTest(name=name):
                v = self.evaluate(controls=replace(self.controls, **{name: False}))
                self.assertEqual(v.state, "S0_BLOCKED")
                self.assertIn("MISSING_" + name.upper(), v.reasons)
                self.assert_no_authority(v)

    def test_forged_boolean_control_blocks(self) -> None:
        forged = replace(self.controls, a5_independent_veto_passed=1)  # type: ignore[arg-type]
        v = self.evaluate(controls=forged)
        self.assertIn("INVALID_FLAG_A5_INDEPENDENT_VETO_PASSED", v.reasons)
        self.assert_no_authority(v)

    def test_missing_human_ack(self) -> None:
        v = self.evaluate(approval=replace(self.approval, owner_confirmed=False))
        self.assertIn("OWNER_FIXTURE_ACK_MISSING", v.reasons)
        self.assert_no_authority(v)

    def test_human_ack_int_is_not_boolean(self) -> None:
        v = self.evaluate(approval=replace(self.approval, owner_confirmed=1))  # type: ignore[arg-type]
        self.assertIn("OWNER_FIXTURE_ACK_MISSING", v.reasons)

    def test_intent_change_invalidates_binding(self) -> None:
        for updated in (replace(self.intent, quantity_units=2),
                        replace(self.intent, side="SELL"),
                        replace(self.intent, venue_tag="OTHER"),
                        replace(self.intent, strategy_tag="OTHER"),
                        replace(self.intent, symbol="OTHER"),
                        replace(self.intent, revision=2)):
            with self.subTest(updated=updated):
                v = self.evaluate(intent=updated)
                self.assertEqual(v.state, "S0_BLOCKED")
                self.assert_no_authority(v)

    def test_revision_mismatch(self) -> None:
        self.assertIn("ACK_REVISION_MISMATCH", self.evaluate(approval=replace(self.approval, bound_revision=2)).reasons)

    def test_replay_ack(self) -> None:
        v = self.evaluate(consumed=frozenset(("ACK-S0-001",)))
        self.assertIn("REPLAYED_ACK", v.reasons)
        self.assert_no_authority(v)

    def test_expiration_and_excess_window(self) -> None:
        for expiry in (99, 100, 161, -1, True):
            with self.subTest(expiry=expiry):
                a = replace(self.approval, expires_at_tick=expiry)  # type: ignore[arg-type]
                self.assertIn("ACK_EXPIRED_OR_UNBOUNDED", self.evaluate(approval=a).reasons)

    def test_invalid_current_time(self) -> None:
        for tick in (-1, True):
            with self.subTest(tick=tick):
                v = self.evaluate(tick=tick)
                self.assertIn("INVALID_SYNTHETIC_TIME", v.reasons)

    def test_unknown_ack_or_kill_switch_blocks(self) -> None:
        for name in ("ack_state_known", "reconciliation_complete", "kill_switch_clear"):
            with self.subTest(flag=name):
                self.assertEqual(self.evaluate(controls=replace(self.controls, **{name: False})).state, "S0_BLOCKED")

    def test_broker_attestation_and_data_freshness_missing(self) -> None:
        for name in ("provider_and_data_rights_attested", "time_origin_attested", "quote_freshness_attested"):
            with self.subTest(flag=name):
                self.assertEqual(self.evaluate(controls=replace(self.controls, **{name: False})).state, "S0_BLOCKED")

    def test_invalid_quantity_revision_and_side(self) -> None:
        for intent in (replace(self.intent, quantity_units=0),
                       replace(self.intent, quantity_units=True),  # type: ignore[arg-type]
                       replace(self.intent, revision=0),
                       replace(self.intent, revision=True),  # type: ignore[arg-type]
                       replace(self.intent, side="WAIT")):
            with self.subTest(intent=intent):
                self.assertEqual(self.evaluate(intent=intent).state, "S0_BLOCKED")

    def test_invalid_replay_register(self) -> None:
        v = self.evaluate(consumed=frozenset((3,)))  # type: ignore[arg-type]
        self.assertIn("INVALID_REPLAY_REGISTER", v.reasons)

    def test_digest_deterministic_but_not_human_signature(self) -> None:
        self.assertEqual(self.intent.digest(), self.intent.digest())
        self.assertEqual(len(self.intent.digest()), 64)
        self.assertNotEqual(self.intent.digest(), replace(self.intent, revision=2).digest())

    def test_no_connectivity_or_order_transport_in_module(self) -> None:
        source = (ROOT / "packages/production/semiauto_s0_preflight.py").read_text(encoding="utf-8")
        for forbidden in ("import socket", "import MetaTrader5", "import requests", "order_send(",
                          "order_check(", "WebRequest(", "create_order(", "submit_order("):
            self.assertNotIn(forbidden, source)

    def test_official_p24_still_blocked(self) -> None:
        d = json.loads((ROOT / "config/production/production-readiness-dossier.json").read_text(encoding="utf-8"))
        pre = [x for x in d["production_prerequisites"] if x["stage"] == "PRE_FIRST_LIVE"]
        self.assertEqual(len(pre), 9)
        self.assertTrue(all(x["satisfied"] is False for x in pre))
        self.assertEqual(d["next"]["p24_b"], "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES")
        self.assertEqual(d["phase_authorization"]["first_live_activation"], "NOT_GRANTED")
        self.assertEqual(d["next"]["g13"], "NOT_STARTED")
        self.assertEqual(d["safety"]["live_trading"], "DISABLED")
        self.assertEqual(d["safety"]["auto_trading"], "DISABLED")
        state = (ROOT / "docs/02-current-state/CURRENT-STATE.md").read_text(encoding="utf-8")
        self.assertIn("P24-C..I NOT_STARTED", state)

    def test_bad_intent_id_rejected(self) -> None:
        for bad in ("", "bad user data", "/" * 70):
            with self.subTest(bad=bad):
                v = self.evaluate(intent=replace(self.intent, intent_id=bad))
                self.assertIn("INVALID_INTENT_ID", v.reasons)


if __name__ == "__main__":
    unittest.main()
