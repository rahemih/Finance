from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.execution.adapter_contract import (
    AdapterContractPolicy,
    AdapterContractRegistry,
    AdapterDescriptor,
    NormalizedOrderIntent,
)
from packages.execution.crypto_adapter import (
    CryptoExecutionAdapter,
    CryptoExecutionPolicy,
    CryptoSandboxEvent,
    CryptoSymbolRule,
)


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_POLICY = ROOT / "config/execution/adapter-contract-policy.json"
CRYPTO_POLICY = ROOT / "config/execution/crypto-execution-policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    adapter_policy = AdapterContractPolicy.from_path(ADAPTER_POLICY)
    crypto_policy = CryptoExecutionPolicy.from_path(CRYPTO_POLICY)
    descriptor = AdapterDescriptor(
        adapter_name="crypto-reference",
        venue_id="crypto-reference-sandbox",
        market="CRYPTO",
        environment="SIMULATED",
        api_version="reference-v1",
        supported_order_types=("MARKET", "LIMIT", "STOP"),
        supported_time_in_force=("GTC", "IOC"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=True,
        amend_supported=False,
        reconciliation_supported=True,
    )
    registry = AdapterContractRegistry(adapter_policy)
    registry.register(descriptor)
    intent = NormalizedOrderIntent(
        intent_id="p20b-crypto-001",
        asset_id="BTC-USD",
        market="CRYPTO",
        side="BUY",
        order_type="LIMIT",
        quantity_scaled=100,
        quantity_scale=100,
        time_in_force="GTC",
        limit_price_scaled=10_000,
        price_scale=100,
    )
    binding = registry.bind("crypto-reference", intent)
    adapter = CryptoExecutionAdapter(
        adapter_policy=adapter_policy,
        crypto_policy=crypto_policy,
        descriptor=descriptor,
    )
    rule = CryptoSymbolRule(
        asset_id="BTC-USD",
        venue_symbol="BTCUSD",
        quantity_scale=100,
        quantity_step_scaled=10,
        min_quantity_scaled=20,
        price_scale=100,
        price_tick_scaled=5,
    )
    submit = adapter.build_submit(
        intent=intent,
        binding=binding,
        symbol_rule=rule,
        client_order_id="p20b-client-001",
        idempotency_key="p20b-idem-001",
    )
    ack = adapter.parse_event(
        CryptoSandboxEvent(
            event_type="ACK",
            request_id=submit.request_id,
            client_order_id=submit.client_order_id,
            venue_order_id="sandbox-order-001",
        ),
        expected_request_id=submit.request_id,
        expected_client_order_id=submit.client_order_id,
    )
    cancel = adapter.build_cancel(
        client_order_id=submit.client_order_id,
        venue_order_id="sandbox-order-001",
        symbol_rule=rule,
    )
    cancel_ack = adapter.parse_event(
        CryptoSandboxEvent(
            event_type="CANCEL_ACK",
            request_id=cancel.request_id,
            client_order_id=submit.client_order_id,
            venue_order_id="sandbox-order-001",
        ),
        expected_request_id=cancel.request_id,
        expected_client_order_id=submit.client_order_id,
    )
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20B_CRYPTO_EXECUTION_EVIDENCE",
        "task_id": "FIN-P20-WB-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "adapter_policy_sha256": _sha256(ADAPTER_POLICY),
        "crypto_policy_sha256": _sha256(CRYPTO_POLICY),
        "crypto_policy_id": crypto_policy.policy_id,
        "adapter_contract_id": descriptor.adapter_contract_id,
        "binding_id": binding.binding_id,
        "submit_request_id": submit.request_id,
        "ack_result_id": ack.result_id,
        "cancel_request_id": cancel.request_id,
        "cancel_ack_result_id": cancel_ack.result_id,
        "authority": {
            "venue_selection": "NOT_SELECTED",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "oms_state_authority": False,
            "retry_authority": False,
            "reconciliation_authority": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
            "g11_execution_validated": False,
            "p21_started": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P20B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
