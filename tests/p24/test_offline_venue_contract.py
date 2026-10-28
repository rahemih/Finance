from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest

from packages.production.offline_venue_contract import (
    EXPECTED_POLICY,
    OfflineVenueError,
    OfflineVenueReference,
    SyntheticIntent,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/offline-venue-reference-policy.json"


def forex(**changes: object) -> SyntheticIntent:
    base = SyntheticIntent(
        venue_id="FIBO_CTRADER_DEMO_REFERENCE",
        market="FOREX",
        action="SUBMIT_MOCK",
        side="BUY",
        client_order_id="fx-client-1",
        quantity_scaled=100_000,
        quantity_step_scaled=10_000,
        price_scaled=108_500,
        price_tick_scaled=5,
        feed_sequence=42,
    )
    return replace(base, **changes)


def crypto(**changes: object) -> SyntheticIntent:
    base = SyntheticIntent(
        venue_id="TABDEAL_SPOT_MOCK_REFERENCE",
        market="CRYPTO",
        action="SUBMIT_MOCK",
        side="SELL",
        client_order_id="spot-client-1",
        quantity_scaled=100,
        quantity_step_scaled=10,
        price_scaled=50_000,
        price_tick_scaled=5,
        feed_sequence=11,
    )
    return replace(base, **changes)


class OfflineVenueContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = OfflineVenueReference.from_path(POLICY)

    def denied(self, order: SyntheticIntent) -> None:
        with self.assertRaises(OfflineVenueError):
            self.guard.evaluate(order)

    def test_01_policy_exact_and_no_network(self) -> None:
        self.assertEqual(EXPECTED_POLICY["network_mode"], "DISABLED")
        self.assertEqual(EXPECTED_POLICY["credential_mode"], "NONE")
        self.assertFalse(EXPECTED_POLICY["external_order_submission"])
        self.assertEqual(EXPECTED_POLICY["g13"], "NOT_STARTED")

    def test_02_policy_tampering_rejected(self) -> None:
        altered = {**EXPECTED_POLICY, "network_mode": "ENABLED"}
        with tempfile.TemporaryDirectory() as location:
            p = Path(location) / "policy.json"
            p.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaises(OfflineVenueError):
                OfflineVenueReference.from_path(p)

    def test_03_forex_mock_deterministic_no_authority(self) -> None:
        a = self.guard.evaluate(forex())
        b = self.guard.evaluate(forex())
        self.assertEqual(a, b)
        self.assertEqual(a.status, "VALIDATED_OFFLINE_ONLY")
        self.assertFalse(a.external_order_submission)
        self.assertFalse(a.execution_authority)
        self.assertEqual(a.network_mode, "DISABLED")

    def test_04_forex_unknown_venue_or_market(self) -> None:
        self.denied(forex(venue_id="UNAUTHORIZED"))
        self.denied(forex(market="CRYPTO"))

    def test_05_forex_invalid_precision(self) -> None:
        self.denied(forex(quantity_scaled=100_001))
        self.denied(forex(price_scaled=108_501))
        self.denied(forex(quantity_step_scaled=0))

    def test_06_forex_duplicate_identity_fail_closed(self) -> None:
        self.denied(forex(idempotency_seen=True))

    def test_07_forex_reconnect_stale_sequence(self) -> None:
        self.denied(forex(feed_sequence=42, previous_sequence=42))
        self.denied(forex(feed_sequence=41, previous_sequence=42))

    def test_08_forex_partial_fill_requires_reconciliation(self) -> None:
        self.denied(forex(filled_quantity_scaled=20_000))
        result = self.guard.evaluate(
            forex(
                filled_quantity_scaled=20_000,
                native_order_id="synthetic-fx-order",
                known_order=True,
            )
        )
        self.assertEqual(result.status, "VALIDATED_OFFLINE_ONLY")
        self.denied(forex(filled_quantity_scaled=150_000))

    def test_09_forex_cancel_requires_known_native_order(self) -> None:
        self.denied(forex(action="CANCEL_MOCK"))
        result = self.guard.evaluate(
            forex(
                action="CANCEL_MOCK",
                known_order=True,
                native_order_id="synthetic-fx-cancel",
            )
        )
        self.assertFalse(result.execution_authority)

    def test_10_crypto_spot_mock_deterministic(self) -> None:
        self.assertEqual(
            self.guard.evaluate(crypto()).decision_id,
            self.guard.evaluate(crypto()).decision_id,
        )

    def test_11_crypto_invalid_units_and_fills(self) -> None:
        self.denied(crypto(quantity_scaled=101))
        self.denied(crypto(price_scaled=50_001))
        self.denied(crypto(filled_quantity_scaled=-1))
        self.denied(crypto(filled_quantity_scaled=110))

    def test_12_crypto_requires_native_identity_for_fills(self) -> None:
        self.denied(crypto(filled_quantity_scaled=20, known_order=True))
        result = self.guard.evaluate(
            crypto(
                filled_quantity_scaled=20,
                known_order=True,
                native_order_id="synthetic-spot-order",
            )
        )
        self.assertEqual(result.status, "VALIDATED_OFFLINE_ONLY")

    def test_13_crypto_snapshot_stale_or_missing(self) -> None:
        self.denied(crypto(feed_fresh=False))
        self.denied(crypto(feed_sequence=0))
        self.denied(crypto(feed_sequence=5, previous_sequence=9))

    def test_14_crypto_replay_and_unknown_cancel(self) -> None:
        self.denied(crypto(idempotency_seen=True))
        self.denied(crypto(action="CANCEL_MOCK", known_order=False))

    def test_15_leverage_close_without_reduce_only_denied(self) -> None:
        self.denied(crypto(action="CLOSE_LEVERAGE"))
        self.denied(crypto(leveraged=True))
        self.denied(forex(leveraged=True))

    def test_16_risk_veto_global(self) -> None:
        self.denied(forex(risk_veto=True))
        self.denied(crypto(risk_veto=True))

    def test_17_live_network_auth_and_invalid_permission_rejected(self) -> None:
        self.denied(forex(environment="LIVE"))
        self.denied(forex(credential_mode="BROKER_KEY"))
        self.denied(crypto(network_mode="ENABLED"))
        self.denied(crypto(external_order_submission=True))
        self.denied(crypto(live_execution_authority=True))
        self.denied(crypto(permission="TRADE"))

    def test_18_forged_in_memory_policy_identity_rejected(self) -> None:
        forged = OfflineVenueReference(policy_id="unverified-policy")
        with self.assertRaises(OfflineVenueError):
            forged.evaluate(forex())
        with self.assertRaises(OfflineVenueError):
            forged.evaluate(crypto())

    def test_19_policy_boolean_as_integer_is_rejected(self) -> None:
        altered = {**EXPECTED_POLICY, "external_order_submission": 0}
        with tempfile.TemporaryDirectory() as location:
            p = Path(location) / "policy.json"
            p.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaises(OfflineVenueError):
                OfflineVenueReference.from_path(p)


if __name__ == "__main__":
    unittest.main()
