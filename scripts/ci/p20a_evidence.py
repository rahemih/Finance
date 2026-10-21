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


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/adapter-contract-policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    policy = AdapterContractPolicy.from_path(POLICY)
    registry = AdapterContractRegistry(policy)
    crypto = AdapterDescriptor(
        adapter_name="crypto-reference",
        venue_id="crypto-sim",
        market="CRYPTO",
        environment="SIMULATED",
        api_version="v1",
        supported_order_types=("MARKET", "LIMIT", "STOP"),
        supported_time_in_force=("GTC", "IOC"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=True,
        amend_supported=False,
        reconciliation_supported=True,
    )
    forex = AdapterDescriptor(
        adapter_name="forex-reference",
        venue_id="forex-sim",
        market="FOREX",
        environment="SIMULATED",
        api_version="v1",
        supported_order_types=("MARKET", "LIMIT"),
        supported_time_in_force=("GTC", "DAY"),
        client_order_id_required=True,
        idempotency_key_required=True,
        cancel_supported=True,
        amend_supported=True,
        reconciliation_supported=True,
    )
    crypto_id = registry.register(crypto)
    forex_id = registry.register(forex)

    crypto_binding = registry.bind(
        "crypto-reference",
        NormalizedOrderIntent(
            intent_id="p20a-crypto-001",
            asset_id="BTC-USD",
            market="CRYPTO",
            side="BUY",
            order_type="LIMIT",
            quantity_scaled=100,
            quantity_scale=100,
            time_in_force="GTC",
            limit_price_scaled=10_000,
            price_scale=100,
        ),
    )
    forex_binding = registry.bind(
        "forex-reference",
        NormalizedOrderIntent(
            intent_id="p20a-forex-001",
            asset_id="EUR-USD",
            market="FOREX",
            side="SELL",
            order_type="MARKET",
            quantity_scaled=10_000,
            quantity_scale=100,
            time_in_force="DAY",
        ),
    )
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20A_ADAPTER_CONTRACT_EVIDENCE",
        "task_id": "FIN-P20-WA-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "policy_sha256": _sha256(POLICY),
        "policy_id": policy.policy_id,
        "adapter_contract_ids": {"crypto": crypto_id, "forex": forex_id},
        "binding_ids": {
            "crypto": crypto_binding.binding_id,
            "forex": forex_binding.binding_id,
        },
        "registry": registry.snapshot(),
        "authority": {
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
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
    print(f"P20A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
