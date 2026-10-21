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
from packages.execution.forex_adapter import (
    ForexAdapterError,
    ForexExecutionAdapter,
    ForexExecutionPolicy,
    ForexSandboxEvent,
    ForexSymbolRule,
)


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_POLICY = ROOT / "config/execution/adapter-contract-policy.json"
FOREX_POLICY = ROOT / "config/execution/forex-execution-policy.json"


def descriptor(*, cancel_supported: bool = True) -> AdapterDescriptor:
    return AdapterDescriptor(
        adapter_name="forex-reference",
        venue_id="forex-reference-sandbox",
        market="FOREX",
        environment="SIMULATED",
        api_version="reference-v1",
        supported_order_types=("MARKET", "LIMIT", "STOP"),
        supported_time_in_force=("GTC", "DAY"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=cancel_supported,
        amend_supported=False,
        reconciliation_supported=True,
    )


def order(*, quantity: int = 100_000, limit_price: int = 108_500) -> NormalizedOrderIntent:
    return NormalizedOrderIntent(
        intent_id="forex-intent-001",
        asset_id="EUR-USD",
        market="FOREX",
        side="BUY",
        order_type="LIMIT",
        quantity_scaled=quantity,
        quantity_scale=100,
        time_in_force="GTC",
        limit_price_scaled=limit_price,
        price_scale=100_000,
    )


def symbol_rule() -> ForexSymbolRule:
    return ForexSymbolRule(
        asset_id="EUR-USD",
        broker_symbol="EURUSD",
        quantity_scale=100,
        quantity_step_scaled=10_000,
        min_quantity_scaled=10_000,
        price_scale=100_000,
        price_tick_scaled=1,
        pip_size_scaled=10,
    )


class ForexExecutionAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter_policy = AdapterContractPolicy.from_path(ADAPTER_POLICY)
        self.forex_policy = ForexExecutionPolicy.from_path(FOREX_POLICY)
        self.descriptor = descriptor()
        registry = AdapterContractRegistry(self.adapter_policy)
        registry.register(self.descriptor)
        self.intent = order()
        self.binding = registry.bind("forex-reference", self.intent)
        self.adapter = ForexExecutionAdapter(
            adapter_policy=self.adapter_policy,
            forex_policy=self.forex_policy,
            descriptor=self.descriptor,
        )

    def test_policy_is_reference_only_and_zero_authority(self) -> None:
        self.assertEqual(self.forex_policy.allowed_environments, ("SIMULATED", "SANDBOX"))
        self.assertEqual(self.forex_policy.live_trading, "DISABLED")
        self.assertEqual(self.forex_policy.auto_trading, "DISABLED")

    def test_submit_envelope_is_deterministic_and_zero_authority(self) -> None:
        first = self.adapter.build_submit(
            intent=self.intent,
            binding=self.binding,
            symbol_rule=symbol_rule(),
            client_order_id="fx-client-001",
            idempotency_key="fx-idem-001",
        )
        second = self.adapter.build_submit(
            intent=self.intent,
            binding=self.binding,
            symbol_rule=symbol_rule(),
            client_order_id="fx-client-001",
            idempotency_key="fx-idem-001",
        )
        self.assertEqual(first, second)
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(first.network_mode, "DISABLED")
        self.assertFalse(first.external_order_submission)
        self.assertFalse(first.live_execution_authority)

    def test_quantity_price_and_pip_rules_fail_closed(self) -> None:
        bad_quantity = order(quantity=15_000)
        with self.assertRaises(ForexAdapterError):
            self.adapter.build_submit(
                intent=bad_quantity,
                binding=self._binding_for(bad_quantity),
                symbol_rule=symbol_rule(),
                client_order_id="fx-q",
                idempotency_key="fx-idem-q",
            )
        invalid_rule = replace(symbol_rule(), pip_size_scaled=7)
        with self.assertRaises(ForexAdapterError):
            invalid_rule.validate()
        bad_tick = order(limit_price=108_501)
        rule = replace(symbol_rule(), price_tick_scaled=5, pip_size_scaled=10)
        with self.assertRaises(ForexAdapterError):
            self.adapter.build_submit(
                intent=bad_tick,
                binding=self._binding_for(bad_tick),
                symbol_rule=rule,
                client_order_id="fx-p",
                idempotency_key="fx-idem-p",
            )

    def test_binding_and_asset_lineage_fail_closed(self) -> None:
        with self.assertRaises(ForexAdapterError):
            self.adapter.build_submit(
                intent=replace(self.intent, asset_id="GBP-USD"),
                binding=self.binding,
                symbol_rule=symbol_rule(),
                client_order_id="fx-x",
                idempotency_key="fx-idem-x",
            )
        changed = replace(self.intent, limit_price_scaled=108_510)
        with self.assertRaises(ForexAdapterError):
            self.adapter.build_submit(
                intent=changed,
                binding=self.binding,
                symbol_rule=symbol_rule(),
                client_order_id="fx-y",
                idempotency_key="fx-idem-y",
            )

    def test_cancel_requires_capability(self) -> None:
        cancel = self.adapter.build_cancel(
            client_order_id="fx-client-001",
            broker_order_id="fx-order-001",
            symbol_rule=symbol_rule(),
        )
        self.assertEqual(cancel.network_mode, "DISABLED")
        no_cancel = ForexExecutionAdapter(
            adapter_policy=self.adapter_policy,
            forex_policy=self.forex_policy,
            descriptor=descriptor(cancel_supported=False),
        )
        with self.assertRaises(ForexAdapterError):
            no_cancel.build_cancel(
                client_order_id="fx-client-001",
                broker_order_id="fx-order-001",
                symbol_rule=symbol_rule(),
            )

    def test_ack_reject_and_cancel_ack_normalize_deterministically(self) -> None:
        submit = self.adapter.build_submit(
            intent=self.intent,
            binding=self.binding,
            symbol_rule=symbol_rule(),
            client_order_id="fx-client-001",
            idempotency_key="fx-idem-001",
        )
        ack = self.adapter.parse_event(
            ForexSandboxEvent(
                event_type="ACK",
                request_id=submit.request_id,
                client_order_id="fx-client-001",
                broker_order_id="fx-order-001",
            ),
            expected_request_id=submit.request_id,
            expected_client_order_id="fx-client-001",
        )
        self.assertEqual(ack.disposition, "ACKNOWLEDGED")
        self.assertFalse(ack.oms_state_authority)
        self.assertFalse(ack.retry_authority)
        self.assertFalse(ack.reconciliation_authority)
        reject = self.adapter.parse_event(
            ForexSandboxEvent(
                event_type="REJECT",
                request_id=submit.request_id,
                client_order_id="fx-client-001",
                reject_code="REFERENCE_REJECT",
            ),
            expected_request_id=submit.request_id,
            expected_client_order_id="fx-client-001",
        )
        self.assertEqual(reject.disposition, "REJECTED")
        cancel = self.adapter.build_cancel(
            client_order_id="fx-client-001",
            broker_order_id="fx-order-001",
            symbol_rule=symbol_rule(),
        )
        cancel_ack = self.adapter.parse_event(
            ForexSandboxEvent(
                event_type="CANCEL_ACK",
                request_id=cancel.request_id,
                client_order_id="fx-client-001",
                broker_order_id="fx-order-001",
            ),
            expected_request_id=cancel.request_id,
            expected_client_order_id="fx-client-001",
        )
        self.assertEqual(cancel_ack.disposition, "CANCEL_ACKNOWLEDGED")

    def test_event_lineage_mismatch_fails_closed(self) -> None:
        with self.assertRaises(ForexAdapterError):
            self.adapter.parse_event(
                ForexSandboxEvent(
                    event_type="ACK",
                    request_id="wrong",
                    client_order_id="fx-client-001",
                    broker_order_id="fx-order-001",
                ),
                expected_request_id="expected",
                expected_client_order_id="fx-client-001",
            )

    def test_crypto_descriptor_is_rejected(self) -> None:
        crypto = replace(self.descriptor, market="CRYPTO")
        with self.assertRaises(ForexAdapterError):
            ForexExecutionAdapter(
                adapter_policy=self.adapter_policy,
                forex_policy=self.forex_policy,
                descriptor=crypto,
            )

    def test_reference_adapter_has_no_network_send_method(self) -> None:
        self.assertFalse(hasattr(self.adapter, "send"))
        self.assertFalse(hasattr(self.adapter, "request"))
        self.assertFalse(hasattr(self.adapter, "connect"))

    def _binding_for(self, intent: NormalizedOrderIntent):
        registry = AdapterContractRegistry(self.adapter_policy)
        registry.register(self.descriptor)
        return registry.bind("forex-reference", intent)


if __name__ == "__main__":
    unittest.main()
