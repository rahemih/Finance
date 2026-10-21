from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.execution.adapter_contract import (
    AdapterContractPolicy,
    AdapterContractRegistry,
    AdapterDescriptor,
    NormalizedOrderIntent,
)
from packages.execution.crypto_adapter import (
    CryptoAdapterError,
    CryptoExecutionAdapter,
    CryptoExecutionPolicy,
    CryptoSandboxEvent,
    CryptoSymbolRule,
)


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_POLICY = ROOT / "config/execution/adapter-contract-policy.json"
CRYPTO_POLICY = ROOT / "config/execution/crypto-execution-policy.json"


def descriptor(*, cancel_supported: bool = True) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_name="crypto-reference",
        venue_id="crypto-reference-sandbox",
        market="CRYPTO",
        environment="SIMULATED",
        api_version="reference-v1",
        supported_order_types=("MARKET", "LIMIT", "STOP"),
        supported_time_in_force=("GTC", "IOC"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=cancel_supported,
        amend_supported=False,
        reconciliation_supported=True,
    )


def order(*, quantity: int = 100, limit_price: int = 10_000) -> NormalizedOrderIntent:
    return NormalizedOrderIntent(
        intent_id="crypto-intent-001",
        asset_id="BTC-USD",
        market="CRYPTO",
        side="BUY",
        order_type="LIMIT",
        quantity_scaled=quantity,
        quantity_scale=100,
        time_in_force="GTC",
        limit_price_scaled=limit_price,
        price_scale=100,
    )


def symbol_rule() -> CryptoSymbolRule:
    return CryptoSymbolRule(
        asset_id="BTC-USD",
        venue_symbol="BTCUSD",
        quantity_scale=100,
        quantity_step_scaled=10,
        min_quantity_scaled=20,
        price_scale=100,
        price_tick_scaled=5,
    )


class CryptoExecutionAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter_policy = AdapterContractPolicy.from_path(ADAPTER_POLICY)
        self.crypto_policy = CryptoExecutionPolicy.from_path(CRYPTO_POLICY)
        self.descriptor = descriptor()
        registry = AdapterContractRegistry(self.adapter_policy)
        registry.register(self.descriptor)
        self.intent = order()
        self.binding = registry.bind("crypto-reference", self.intent)
        self.adapter = CryptoExecutionAdapter(
            adapter_policy=self.adapter_policy,
            crypto_policy=self.crypto_policy,
            descriptor=self.descriptor,
        )

    def test_policy_is_reference_only_and_zero_authority(self) -> None:
        self.assertEqual(self.crypto_policy.allowed_environments, ("SIMULATED", "SANDBOX"))
        self.assertEqual(self.crypto_policy.live_trading, "DISABLED")
        self.assertEqual(self.crypto_policy.auto_trading, "DISABLED")

    def test_submit_envelope_is_deterministic_and_zero_authority(self) -> None:
        first = self.adapter.build_submit(
            intent=self.intent,
            binding=self.binding,
            symbol_rule=symbol_rule(),
            client_order_id="client-001",
            idempotency_key="idem-001",
        )
        second = self.adapter.build_submit(
            intent=self.intent,
            binding=self.binding,
            symbol_rule=symbol_rule(),
            client_order_id="client-001",
            idempotency_key="idem-001",
        )
        self.assertEqual(first, second)
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(first.network_mode, "DISABLED")
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.live_execution_authority)

    def test_quantity_and_price_filters_fail_closed(self) -> None:
        with self.assertRaises(CryptoAdapterError):
            self.adapter.build_submit(
                intent=order(quantity=25),
                binding=self._binding_for(order(quantity=25)),
                symbol_rule=symbol_rule(),
                client_order_id="client-q",
                idempotency_key="idem-q",
            )
        bad_price = order(limit_price=10_003)
        with self.assertRaises(CryptoAdapterError):
            self.adapter.build_submit(
                intent=bad_price,
                binding=self._binding_for(bad_price),
                symbol_rule=symbol_rule(),
                client_order_id="client-p",
                idempotency_key="idem-p",
            )

    def test_binding_and_asset_lineage_fail_closed(self) -> None:
        with self.assertRaises(CryptoAdapterError):
            self.adapter.build_submit(
                intent=replace(self.intent, asset_id="ETH-USD"),
                binding=self.binding,
                symbol_rule=symbol_rule(),
                client_order_id="client-x",
                idempotency_key="idem-x",
            )
        with self.assertRaises(CryptoAdapterError):
            self.adapter.build_submit(
                intent=replace(self.intent, limit_price_scaled=10_005),
                binding=self.binding,
                symbol_rule=symbol_rule(),
                client_order_id="client-y",
                idempotency_key="idem-y",
            )

    def test_cancel_requires_capability(self) -> None:
        cancel = self.adapter.build_cancel(
            client_order_id="client-001",
            venue_order_id="venue-001",
            symbol_rule=symbol_rule(),
        )
        self.assertEqual(cancel.network_mode, "DISABLED")
        no_cancel = CryptoExecutionAdapter(
            adapter_policy=self.adapter_policy,
            crypto_policy=self.crypto_policy,
            descriptor=descriptor(cancel_supported=False),
        )
        with self.assertRaises(CryptoAdapterError):
            no_cancel.build_cancel(
                client_order_id="client-001",
                venue_order_id="venue-001",
                symbol_rule=symbol_rule(),
            )

    def test_ack_reject_and_cancel_ack_normalize_deterministically(self) -> None:
        submit = self.adapter.build_submit(
            intent=self.intent,
            binding=self.binding,
            symbol_rule=symbol_rule(),
            client_order_id="client-001",
            idempotency_key="idem-001",
        )
        ack = self.adapter.parse_event(
            CryptoSandboxEvent(
                event_type="ACK",
                request_id=submit.request_id,
                client_order_id="client-001",
                venue_order_id="venue-001",
            ),
            expected_request_id=submit.request_id,
            expected_client_order_id="client-001",
        )
        self.assertEqual(ack.disposition, "ACKNOWLEDGED")
        self.assertFalse(ack.oms_state_authority)
        self.assertFalse(ack.retry_authority)
        self.assertFalse(ack.reconciliation_authority)
        reject = self.adapter.parse_event(
            CryptoSandboxEvent(
                event_type="REJECT",
                request_id=submit.request_id,
                client_order_id="client-001",
                reject_code="FILTER_REJECT",
            ),
            expected_request_id=submit.request_id,
            expected_client_order_id="client-001",
        )
        self.assertEqual(reject.disposition, "REJECTED")
        cancel = self.adapter.build_cancel(
            client_order_id="client-001",
            venue_order_id="venue-001",
            symbol_rule=symbol_rule(),
        )
        cancel_ack = self.adapter.parse_event(
            CryptoSandboxEvent(
                event_type="CANCEL_ACK",
                request_id=cancel.request_id,
                client_order_id="client-001",
                venue_order_id="venue-001",
            ),
            expected_request_id=cancel.request_id,
            expected_client_order_id="client-001",
        )
        self.assertEqual(cancel_ack.disposition, "CANCEL_ACKNOWLEDGED")

    def test_event_lineage_mismatch_fails_closed(self) -> None:
        with self.assertRaises(CryptoAdapterError):
            self.adapter.parse_event(
                CryptoSandboxEvent(
                    event_type="ACK",
                    request_id="wrong",
                    client_order_id="client-001",
                    venue_order_id="venue-001",
                ),
                expected_request_id="expected",
                expected_client_order_id="client-001",
            )

    def test_forex_descriptor_is_rejected(self) -> None:
        fx = replace(self.descriptor, market="FOREX")
        with self.assertRaises(CryptoAdapterError):
            CryptoExecutionAdapter(
                adapter_policy=self.adapter_policy,
                crypto_policy=self.crypto_policy,
                descriptor=fx,
            )

    def test_reference_adapter_has_no_network_send_method(self) -> None:
        self.assertFalse(hasattr(self.adapter, "send"))
        self.assertFalse(hasattr(self.adapter, "request"))
        self.assertFalse(hasattr(self.adapter, "connect"))

    def _binding_for(self, intent: NormalizedOrderIntent):
        registry = AdapterContractRegistry(self.adapter_policy)
        registry.register(self.descriptor)
        return registry.bind("crypto-reference", intent)


if __name__ == "__main__":
    unittest.main()
