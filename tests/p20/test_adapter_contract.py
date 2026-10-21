from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.execution.adapter_contract import (
    AdapterBinding,
    AdapterContractError,
    AdapterContractPolicy,
    AdapterContractRegistry,
    AdapterDescriptor,
    NormalizedOrderIntent,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/adapter-contract-policy.json"


def descriptor(
    *,
    name: str = "crypto-reference",
    venue: str = "venue-a",
    market: str = "CRYPTO",
    environment: str = "SIMULATED",
) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_name=name,
        venue_id=venue,
        market=market,
        environment=environment,
        api_version="v1",
        supported_order_types=("MARKET", "LIMIT", "STOP"),
        supported_time_in_force=("GTC", "IOC"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=True,
        amend_supported=False,
        reconciliation_supported=True,
    )


def intent(
    *,
    market: str = "CRYPTO",
    order_type: str = "LIMIT",
    tif: str = "GTC",
) -> NormalizedOrderIntent:
    asset_id = "BTC-USD" if market == "CRYPTO" else "EUR-USD"
    if order_type == "LIMIT":
        return NormalizedOrderIntent(
            intent_id="intent-001",
            asset_id=asset_id,
            market=market,
            side="BUY",
            order_type="LIMIT",
            quantity_scaled=100,
            quantity_scale=100,
            time_in_force=tif,
            limit_price_scaled=10_000,
            price_scale=100,
        )
    if order_type == "STOP":
        return NormalizedOrderIntent(
            intent_id="intent-001",
            asset_id=asset_id,
            market=market,
            side="BUY",
            order_type="STOP",
            quantity_scaled=100,
            quantity_scale=100,
            time_in_force=tif,
            stop_price_scaled=9_500,
            price_scale=100,
        )
    return NormalizedOrderIntent(
        intent_id="intent-001",
        asset_id=asset_id,
        market=market,
        side="BUY",
        order_type=order_type,
        quantity_scaled=100,
        quantity_scale=100,
        time_in_force=tif,
    )



class AdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = AdapterContractPolicy.from_path(POLICY)

    def test_policy_is_fail_closed_and_live_disabled(self) -> None:
        self.assertEqual(self.policy.environments, ("SIMULATED", "SANDBOX"))
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_contract_identity_is_deterministic(self) -> None:
        first = descriptor()
        second = descriptor()
        first.validate(self.policy)
        second.validate(self.policy)
        self.assertEqual(first.adapter_contract_id, second.adapter_contract_id)

    def test_live_environment_is_rejected(self) -> None:
        with self.assertRaises(AdapterContractError):
            descriptor(environment="LIVE").validate(self.policy)

    def test_mandatory_idempotency_and_reconciliation_cannot_be_disabled(self) -> None:
        with self.assertRaises(AdapterContractError):
            replace(descriptor(), idempotency_key_required=False).validate(self.policy)
        with self.assertRaises(AdapterContractError):
            replace(descriptor(), reconciliation_supported=False).validate(self.policy)

    def test_duplicate_adapter_and_duplicate_venue_binding_fail_closed(self) -> None:
        registry = AdapterContractRegistry(self.policy)
        registry.register(descriptor())
        with self.assertRaises(AdapterContractError):
            registry.register(descriptor())
        with self.assertRaises(AdapterContractError):
            registry.register(descriptor(name="other"))

    def test_market_and_capability_negotiation_fail_closed(self) -> None:
        registry = AdapterContractRegistry(self.policy)
        registry.register(descriptor())
        with self.assertRaises(AdapterContractError):
            registry.bind("crypto-reference", intent(market="FOREX"))
        limited = replace(
            descriptor(name="limited", venue="venue-b"),
            supported_order_types=("MARKET",),
        )
        registry.register(limited)
        with self.assertRaises(AdapterContractError):
            registry.bind("limited", intent(order_type="LIMIT"))

    def test_order_geometry_is_normalized(self) -> None:
        intent(order_type="MARKET").validate(self.policy)
        intent(order_type="LIMIT").validate(self.policy)
        intent(order_type="STOP").validate(self.policy)
        with self.assertRaises(AdapterContractError):
            replace(
                intent(order_type="MARKET"),
                limit_price_scaled=10_000,
                price_scale=100,
            ).validate(self.policy)
        with self.assertRaises(AdapterContractError):
            replace(intent(order_type="LIMIT"), limit_price_scaled=None).validate(
                self.policy
            )

    def test_binding_is_deterministic_and_has_zero_execution_authority(self) -> None:
        registry = AdapterContractRegistry(self.policy)
        registry.register(descriptor())
        first = registry.bind("crypto-reference", intent())
        second = registry.bind("crypto-reference", intent())
        self.assertIsInstance(first, AdapterBinding)
        self.assertEqual(first.binding_id, second.binding_id)
        self.assertEqual(first.routing_mode, "CONTRACT_ONLY")
        self.assertEqual(first.credential_mode, "NONE")
        self.assertEqual(first.network_mode, "DISABLED")
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.live_execution_authority)

    def test_registry_snapshot_is_stable_and_contains_no_authority(self) -> None:
        registry = AdapterContractRegistry(self.policy)
        registry.register(descriptor())
        registry.register(
            descriptor(name="forex-reference", venue="venue-fx", market="FOREX")
        )
        first = registry.snapshot()
        second = registry.snapshot()
        self.assertEqual(first, second)
        authority = first["authority"]
        assert isinstance(authority, dict)
        self.assertEqual(authority["routing_mode"], "CONTRACT_ONLY")
        self.assertEqual(authority["credential_mode"], "NONE")
        self.assertEqual(authority["network_mode"], "DISABLED")
        self.assertFalse(authority["external_order_submission"])
        self.assertFalse(authority["live_execution_authority"])


if __name__ == "__main__":
    unittest.main()
