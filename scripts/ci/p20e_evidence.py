from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.execution.idempotency import (
    IdempotencyLedger,
    IdempotencyPolicy,
    IdempotencyRequest,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/idempotency-policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build() -> dict[str, object]:
    policy = IdempotencyPolicy.from_path(POLICY)
    ledger = IdempotencyLedger(policy)

    submit = IdempotencyRequest(
        market="CRYPTO",
        operation="ORDER_SUBMIT",
        order_id="p20e-order-001",
        client_order_id="p20e-client-001",
        idempotency_key="p20e-submit-001",
        request_fingerprint=_fingerprint("canonical-submit"),
    )
    new_decision = ledger.admit(submit)
    replay_decision = ledger.admit(submit)

    cancel = IdempotencyRequest(
        market="CRYPTO",
        operation="ORDER_CANCEL",
        order_id="p20e-order-001",
        client_order_id="p20e-cancel-client-001",
        idempotency_key="p20e-cancel-001",
        request_fingerprint=_fingerprint("canonical-cancel"),
    )
    cancel_decision = ledger.admit(cancel)

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20E_IDEMPOTENCY_EVIDENCE",
        "task_id": "FIN-P20-WE-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "policy_sha256": _sha256(POLICY),
        "policy_id": policy.policy_id,
        "submit_new_decision_id": new_decision.decision_id,
        "submit_replay_decision_id": replay_decision.decision_id,
        "same_submit_claim": new_decision.claim_id == replay_decision.claim_id,
        "cancel_decision_id": cancel_decision.decision_id,
        "snapshot": ledger.snapshot(),
        "authority": {
            "retry_owner": "P20-F",
            "reconciliation_owner": "P20-G",
            "execution_quality_owner": "P20-H",
            "simulation_gate_owner": "P20-I",
            "position_management_owner": "P21",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
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
    print(f"P20E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
