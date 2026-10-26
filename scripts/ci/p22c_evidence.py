from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.diagnostics import DiagnosticsPolicy, diagnose


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path("config/operations/diagnostics-policy.json")
    policy = DiagnosticsPolicy.from_path(policy_path)
    corr = "0123456789abcdef0123456789abcdef"
    evidence_a = "a" * 64
    evidence_b = "b" * 64

    matched = diagnose(
        policy,
        system_state="SAFE_MODE",
        symptom_codes=("DATA_STALE", "RECONCILIATION_MISMATCH"),
        evidence_refs=(evidence_b, evidence_a),
        observed_at_ns=1_000,
        correlation_id=corr,
    )
    unresolved = diagnose(
        policy,
        system_state="DEGRADED",
        symptom_codes=("UNRECOGNIZED_OPERATIONAL_SYMPTOM",),
        evidence_refs=(evidence_a,),
        observed_at_ns=2_000,
        correlation_id=corr,
    )
    if matched.category != "RECONCILIATION" or matched.severity != "CRITICAL":
        raise SystemExit("P22-C matched diagnostic mismatch")
    if unresolved.status != "UNRESOLVED" or not unresolved.operator_review_required:
        raise SystemExit("P22-C unresolved diagnostic mismatch")
    if matched.remediation_authority or unresolved.remediation_authority:
        raise SystemExit("P22-C remediation authority must remain false")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22C_DIAGNOSTICS_EVIDENCE",
        "task_id": "FIN-P22-WC-001",
        "state": "REFERENCE_AUTO_DIAGNOSTICS_VALIDATED_PASS",
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "matched_report": {"report_id": matched.report_id, **matched.payload()},
        "unresolved_report": {"report_id": unresolved.report_id, **unresolved.payload()},
        "safety": {
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "automatic_remediation": False,
            "automatic_self_healing": False,
            "automatic_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-D_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22C_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
