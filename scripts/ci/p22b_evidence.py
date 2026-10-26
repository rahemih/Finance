from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.system_state import (
    SystemStatePolicy,
    build_health_snapshot,
    decide_system_state,
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path("config/operations/system-state-policy.json")
    policy = SystemStatePolicy.from_path(policy_path)
    corr = "0123456789abcdef0123456789abcdef"

    degraded = build_health_snapshot(
        policy,
        health_level="DEGRADED",
        observed_at_ns=1_000,
        correlation_id=corr,
        reason_codes=("DATA_LATENCY_WARN",),
    )
    unsafe = build_health_snapshot(
        policy,
        health_level="UNSAFE",
        observed_at_ns=2_000,
        correlation_id=corr,
        reason_codes=("RECONCILIATION_MISMATCH",),
    )
    healthy = build_health_snapshot(
        policy,
        health_level="HEALTHY",
        observed_at_ns=3_000,
        correlation_id=corr,
        reason_codes=(),
    )

    d1 = decide_system_state(policy, previous_state="NORMAL", snapshot=degraded)
    d2 = decide_system_state(policy, previous_state=d1.next_state, snapshot=unsafe)
    d3 = decide_system_state(
        policy,
        previous_state=d2.next_state,
        snapshot=healthy,
        recovery_authorized=True,
    )
    d4 = decide_system_state(policy, previous_state=d3.next_state, snapshot=healthy)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22B_SYSTEM_STATE_EVIDENCE",
        "task_id": "FIN-P22-WB-001",
        "state": "REFERENCE_SYSTEM_STATE_MACHINE_VALIDATED_PASS",
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "sequence": [
            {"snapshot": {"snapshot_id": degraded.snapshot_id, **degraded.payload()}, "decision": {"decision_id": d1.decision_id, **d1.payload()}},
            {"snapshot": {"snapshot_id": unsafe.snapshot_id, **unsafe.payload()}, "decision": {"decision_id": d2.decision_id, **d2.payload()}},
            {"snapshot": {"snapshot_id": healthy.snapshot_id, **healthy.payload()}, "decision": {"decision_id": d3.decision_id, **d3.payload()}},
            {"snapshot": {"snapshot_id": healthy.snapshot_id, **healthy.payload()}, "decision": {"decision_id": d4.decision_id, **d4.payload()}},
        ],
        "expected_states": ["DEGRADED", "SAFE_MODE", "RECOVERY", "NORMAL"],
        "safety": {
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "automatic_state_mutation": False,
            "automatic_diagnostics": False,
            "automatic_self_healing": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-C_NOT_STARTED",
    }
    actual = [item["decision"]["next_state"] for item in payload["sequence"]]
    if actual != payload["expected_states"]:
        raise SystemExit("P22-B evidence sequence mismatch")
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22B_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
