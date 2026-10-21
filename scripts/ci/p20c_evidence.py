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
from packages.execution.forex_adapter import (
    ForexExecutionAdapter,
    ForexExecutionPolicy,
    ForexSandboxEvent,
    ForexSymbolRule,
)


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_POLICY = ROOT / "config/execution/adapter-contract-policy.json"
FOREX_POLICY = ROOT / "config/execution/forex-execution-policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    adapter_policy = AdapterContractPolicy.from_path(ADAPTER_POLICY)
    forex_policy = ForexExecutionPolicy.from_path(FOREX_POLICY)
    descriptor = AdapterDescriptor(
        adapter_name="forex-reference",
        venue_id="forex-reference-sandbox",
        market="FOREX",
        environment="SIMULATED",
        api_version="reference-v1",
        supported_order_types=("MARKET", "LIMIT", "STOP"),
        supported_time_in_force=("GTC", "DAY"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=True,
        amend_supported=False,
        reconciliation_supported=True,
    )
    registry = AdapterContractRegistry(adapter_policy)
    registry.register(descriptor)
    intent = NormalizedOrderIntent(
        intent_id="p20c-forex-001",
        asset_id="EUR-USD",
        market="FOREX",
        side="BUY",
        order_type="LIMIT",
        quantity_scaled=100_000,
        quantity_scale=100,
        time_in_force="GTC",
        limit_price_scaled=108_500,
        price_scale=100_000,
    )
    binding = registry.bind("forex-reference", intent)
    adapter = ForexExecutionAdapter(
        adapter_policy=adapter_policy,
        forex_policy=forex_policy,
        descriptor=descriptor,
    )
    rule = ForexSymbolRule(
        asset_id="EUR-USD",
        broker_symbol="EURUSD",
        quantity_scale=100,
        quantity_step_scaled=10_000,
        min_quantity_scaled=10_000,
        price_scale=100_000,
        price_tick_scaled=1,
        pip_size_scaled=10,
    )
    submit = adapter.build_submit(
        intent=intent,
        binding=binding,
        symbol_rule=rule,
        client_order_id="p20c-client-001",
        idempotency_key="p20c-idem-001",
    )
    ack = adapter.parse_event(
        ForexSandboxEvent(
            event_type="ACK",
            request_id=submit.request_id,
            client_order_id=submit.client_order_id,
            broker_order_id="sandbox-fx-order-001",
        ),
        expected_request_id=submit.request_id,
        expected_client_order_id=submit.client_order_id,
    )
    cancel = adapter.build_cancel(
        client_order_id=submit.client_order_id,
        broker_order_id="sandbox-fx-order-001",
        symbol_rule=rule,
    )
    cancel_ack = adapter.parse_event(
        ForexSandboxEvent(
            event_type="CANCEL_ACK",
            request_id=cancel.request_id,
            client_order_id=submit.client_order_id,
            broker_order_id="sandbox-fx-order-001",
        ),
        expected_request_id=cancel.request_id,
        expected_client_order_id=submit.client_order_id,
    )
    return {
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P20C_FOREX_EXECUTION_EVIDENCE",
        "task_id":"FIN-P20-WC-001",
        "state":"IN_PROGRESS_REFERENCE_VALIDATED",
        "adapter_policy_sha256":_sha256(ADAPTER_POLICY),
        "forex_policy_sha256":_sha256(FOREX_POLICY),
        "forex_policy_id":forex_policy.policy_id,
        "adapter_contract_id":descriptor.adapter_contract_id,
        "binding_id":binding.binding_id,
        "submit_request_id":submit.request_id,
        "ack_result_id":ack.result_id,
        "cancel_request_id":cancel.request_id,
        "cancel_ack_result_id":cancel_ack.result_id,
        "authority":{
            "broker_selection":"NOT_SELECTED",
            "credential_mode":"NONE",
            "network_mode":"DISABLED",
            "external_order_submission":False,
            "oms_state_authority":False,
            "retry_authority":False,
            "reconciliation_authority":False,
            "live_execution_authority":False,
            "live_trading":"DISABLED",
            "auto_trading":"DISABLED",
            "g11_execution_validated":False,
            "p21_started":False,
        },
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    payload=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",
        encoding="utf-8",
    )
    print(f"P20C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
