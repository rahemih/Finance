from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.shadow.shadow_decisioning import (
    ShadowDecisionError,
    ShadowDecisionInput,
    ShadowDecisionLedger,
    ShadowDecisionPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/shadow/shadow-decisioning-policy.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def directional(
    *,
    observed: int = 10_000,
    action: str = "LONG",
    risk_status: str = "PASS",
    risk_scale: int = 10_000,
    firewall_state: str = "PASS",
) -> ShadowDecisionInput:
    if action == "LONG":
        geometry = dict(
            entry_low_scaled=99_500,
            entry_high_scaled=100_500,
            candidate_stop_scaled=98_500,
            candidate_target_scaled=103_500,
            price_scale=100,
        )
    elif action == "SHORT":
        geometry = dict(
            entry_low_scaled=99_500,
            entry_high_scaled=100_500,
            candidate_stop_scaled=102_000,
            candidate_target_scaled=97_000,
            price_scale=100,
        )
    else:
        geometry = dict(
            entry_low_scaled=None,
            entry_high_scaled=None,
            candidate_stop_scaled=None,
            candidate_target_scaled=None,
            price_scale=None,
        )
    return ShadowDecisionInput(
        asset_id="BTC-USD",
        observed_at_ns=observed,
        market_available_at_ns=observed - 100,
        signal_id=h(f"signal-{observed}-{action}"),
        signal_as_of_ns=observed - 100,
        signal_action=action,
        empirical_probability_bps=7200 if action in {"LONG", "SHORT"} else None,
        overall_uncertainty_bps=800 if action in {"LONG", "SHORT"} else None,
        risk_validation_id=h("risk"),
        risk_status=risk_status,
        risk_scale_bps=risk_scale,
        firewall_gate_id=h("firewall"),
        firewall_state=firewall_state,
        strategy_record_id=h("strategy"),
        model_record_id=h("model"),
        signal_evidence_sha256=h("signal-evidence"),
        risk_evidence_sha256=h("risk-evidence"),
        firewall_evidence_sha256=h("firewall-evidence"),
        quant_evidence_sha256=h("quant-evidence"),
        **geometry,
    )


class ShadowDecisioningTests(unittest.TestCase):
    def policy(self) -> ShadowDecisionPolicy:
        return ShadowDecisionPolicy.from_path(POLICY)

    def test_directional_pass_produces_shadow_would_trade_without_authority(self) -> None:
        record = ShadowDecisionLedger(self.policy()).append(directional())
        self.assertEqual(record.disposition, "SHADOW_WOULD_TRADE")
        self.assertEqual(record.mode, "SHADOW_ONLY")
        self.assertFalse(record.execution_authority)
        self.assertFalse(record.order_routing_authority)
        self.assertFalse(record.broker_exchange_routing)
        self.assertFalse(record.external_order_submission)
        self.assertFalse(record.p20_started)

    def test_same_input_is_deterministic_across_fresh_ledgers(self) -> None:
        value = directional()
        left = ShadowDecisionLedger(self.policy()).append(value)
        right = ShadowDecisionLedger(self.policy()).append(value)
        self.assertEqual(left.record_id, right.record_id)

    def test_duplicate_input_fails_closed(self) -> None:
        ledger = ShadowDecisionLedger(self.policy())
        value = directional()
        ledger.append(value)
        with self.assertRaises(ShadowDecisionError):
            ledger.append(value)

    def test_non_monotonic_event_time_fails_closed(self) -> None:
        ledger = ShadowDecisionLedger(self.policy())
        ledger.append(directional(observed=20_000))
        with self.assertRaises(ShadowDecisionError):
            ledger.append(directional(observed=19_000, action="SHORT"))

    def test_future_information_fails_closed(self) -> None:
        with self.assertRaises(ShadowDecisionError):
            ShadowDecisionInput(
                asset_id="BTC-USD",
                observed_at_ns=10_000,
                market_available_at_ns=10_001,
                signal_id=h("signal"),
                signal_as_of_ns=9_000,
                signal_action="WAIT",
                empirical_probability_bps=None,
                overall_uncertainty_bps=None,
                risk_validation_id=h("risk"),
                risk_status="PASS",
                risk_scale_bps=10_000,
                firewall_gate_id=h("firewall"),
                firewall_state="PASS",
                strategy_record_id=h("strategy"),
                model_record_id=h("model"),
                signal_evidence_sha256=h("se"),
                risk_evidence_sha256=h("re"),
                firewall_evidence_sha256=h("fe"),
                quant_evidence_sha256=h("qe"),
            )

    def test_wait_and_no_trade_are_non_directional(self) -> None:
        ledger = ShadowDecisionLedger(self.policy())
        wait = ledger.append(directional(observed=10_000, action="WAIT"))
        no_trade = ledger.append(directional(observed=20_000, action="NO_TRADE"))
        self.assertEqual(wait.disposition, "SHADOW_WAIT")
        self.assertEqual(no_trade.disposition, "SHADOW_NO_TRADE")

    def test_non_directional_geometry_is_rejected(self) -> None:
        with self.assertRaises(ShadowDecisionError):
            ShadowDecisionInput(
                asset_id="BTC-USD",
                observed_at_ns=10_000,
                market_available_at_ns=9_000,
                signal_id=h("signal"),
                signal_as_of_ns=9_000,
                signal_action="WAIT",
                empirical_probability_bps=None,
                overall_uncertainty_bps=None,
                risk_validation_id=h("risk"),
                risk_status="PASS",
                risk_scale_bps=10_000,
                firewall_gate_id=h("firewall"),
                firewall_state="PASS",
                strategy_record_id=h("strategy"),
                model_record_id=h("model"),
                signal_evidence_sha256=h("se"),
                risk_evidence_sha256=h("re"),
                firewall_evidence_sha256=h("fe"),
                quant_evidence_sha256=h("qe"),
                entry_low_scaled=99_500,
                entry_high_scaled=100_500,
                candidate_stop_scaled=98_500,
                candidate_target_scaled=103_500,
                price_scale=100,
            )

    def test_incoherent_directional_geometry_is_rejected(self) -> None:
        with self.assertRaises(ShadowDecisionError):
            ShadowDecisionInput(
                **{
                    **directional().__dict__,
                    "candidate_stop_scaled": 101_000,
                }
            )

    def test_risk_and_firewall_blocks_cannot_would_trade(self) -> None:
        risk = ShadowDecisionLedger(self.policy()).append(
            directional(risk_status="VETO")
        )
        firewall = ShadowDecisionLedger(self.policy()).append(
            directional(firewall_state="FAIL")
        )
        zero = ShadowDecisionLedger(self.policy()).append(
            directional(risk_scale=0)
        )
        self.assertEqual(risk.disposition, "SHADOW_BLOCKED_RISK")
        self.assertEqual(firewall.disposition, "SHADOW_BLOCKED_FIREWALL")
        self.assertEqual(zero.disposition, "SHADOW_BLOCKED_RISK")

    def test_ledger_chain_and_snapshot_are_deterministic(self) -> None:
        left = ShadowDecisionLedger(self.policy())
        first = left.append(directional(observed=10_000))
        second = left.append(directional(observed=20_000, action="WAIT"))
        self.assertEqual(second.previous_record_id, first.record_id)

        right = ShadowDecisionLedger(self.policy())
        right.append(directional(observed=10_000))
        right.append(directional(observed=20_000, action="WAIT"))
        self.assertEqual(left.snapshot().snapshot_id, right.snapshot().snapshot_id)
        self.assertFalse(left.snapshot().execution_authority)


if __name__ == "__main__":
    unittest.main()
