from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.execution.oms_lifecycle import (
    OmsLifecycleEngine,
    OmsLifecycleEvent,
    OmsLifecyclePolicy,
    OmsOrderSpec,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/oms-lifecycle-policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _event(order_id: str, sequence: int, event_type: str, *, fill: int = 0) -> OmsLifecycleEvent:
    return OmsLifecycleEvent(
        order_id=order_id,
        sequence=sequence,
        occurred_at_ns=sequence,
        event_type=event_type,
        fill_quantity_scaled=fill,
        source_ref=f"p20d-{order_id}-{sequence}",
    )


def build() -> dict[str, object]:
    policy = OmsLifecyclePolicy.from_path(POLICY)
    engine = OmsLifecycleEngine(policy)

    crypto = OmsOrderSpec(
        order_id="p20d-crypto-001",
        client_order_id="p20d-client-crypto",
        asset_id="BTC-USD",
        market="CRYPTO",
        side="BUY",
        total_quantity_scaled=100,
        quantity_scale=100,
    )
    forex = OmsOrderSpec(
        order_id="p20d-forex-001",
        client_order_id="p20d-client-forex",
        asset_id="EUR-USD",
        market="FOREX",
        side="SELL",
        total_quantity_scaled=100_000,
        quantity_scale=100,
    )
    engine.create_order(crypto, created_at_ns=0)
    engine.create_order(forex, created_at_ns=0)

    engine.apply(_event(crypto.order_id, 1, "SUBMIT"))
    engine.apply(_event(crypto.order_id, 2, "ACK"))
    engine.apply(_event(crypto.order_id, 3, "PARTIAL_FILL", fill=40))
    crypto_final = engine.apply(_event(crypto.order_id, 4, "FILL", fill=60))

    engine.apply(_event(forex.order_id, 1, "SUBMIT"))
    engine.apply(_event(forex.order_id, 2, "ACK"))
    engine.apply(_event(forex.order_id, 3, "CANCEL_REQUEST"))
    forex_final = engine.apply(_event(forex.order_id, 4, "CANCEL_ACK"))

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20D_OMS_LIFECYCLE_EVIDENCE",
        "task_id": "FIN-P20-WD-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "policy_sha256": _sha256(POLICY),
        "policy_id": policy.policy_id,
        "crypto_final_record_id": crypto_final.record_id,
        "crypto_final_state": crypto_final.state,
        "forex_final_record_id": forex_final.record_id,
        "forex_final_state": forex_final.state,
        "snapshot": engine.snapshot(),
        "authority": {
            "idempotency_owner": "P20-E",
            "retry_owner": "P20-F",
            "reconciliation_owner": "P20-G",
            "execution_quality_owner": "P20-H",
            "simulation_gate_owner": "P20-I",
            "position_management_owner": "P21",
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
    print(f"P20D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
