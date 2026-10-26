from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.diagnostics import DiagnosticsPolicy, diagnose
from packages.operations.self_healing import SelfHealingPolicy, plan_self_healing


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    healing_path = Path("config/operations/constrained-self-healing-policy.json")
    diagnostics_path = Path("config/operations/diagnostics-policy.json")
    healing = SelfHealingPolicy.from_path(healing_path)
    diagnostics = DiagnosticsPolicy.from_path(diagnostics_path)

    correlation = "0123456789abcdef0123456789abcdef"
    evidence = "a" * 64

    warning_report = diagnose(
        diagnostics,
        system_state="DEGRADED",
        symptom_codes=("DATA_STALE",),
        evidence_refs=(evidence,),
        observed_at_ns=1_000,
        correlation_id=correlation,
    )
    eligible = plan_self_healing(
        healing,
        report=warning_report,
        attempt_number=1,
        cooldown_elapsed=True,
    )

    critical_report = diagnose(
        diagnostics,
        system_state="SAFE_MODE",
        symptom_codes=("DATA_GAP",),
        evidence_refs=(evidence,),
        observed_at_ns=2_000,
        correlation_id=correlation,
    )
    blocked = plan_self_healing(
        healing,
        report=critical_report,
        attempt_number=1,
        cooldown_elapsed=True,
    )

    if eligible.status != "ELIGIBLE_REFERENCE_PLAN":
        raise SystemExit("P22-D expected eligible reference plan")
    if eligible.action != "RESTART_STATELESS_OBSERVER":
        raise SystemExit("P22-D unexpected eligible action")
    if eligible.execution_authority or eligible.external_side_effects:
        raise SystemExit("P22-D reference plan unexpectedly gained execution authority")
    if blocked.status != "BLOCKED" or blocked.action is not None:
        raise SystemExit("P22-D critical diagnostic did not fail closed")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22D_CONSTRAINED_SELF_HEALING_EVIDENCE",
        "task_id": "FIN-P22-WD-001",
        "state": "REFERENCE_CONSTRAINED_SELF_HEALING_VALIDATED_PASS",
        "policy_id": healing.policy_id,
        "policy_sha256": hashlib.sha256(healing_path.read_bytes()).hexdigest(),
        "diagnostics_policy_sha256": hashlib.sha256(diagnostics_path.read_bytes()).hexdigest(),
        "eligible_case": {
            "diagnostic_report_id": warning_report.report_id,
            "decision": {"decision_id": eligible.decision_id, **eligible.payload()},
        },
        "blocked_case": {
            "diagnostic_report_id": critical_report.report_id,
            "decision": {"decision_id": blocked.decision_id, **blocked.payload()},
        },
        "safety": {
            "execution_mode": "REFERENCE_PLAN_ONLY",
            "execution_authority": False,
            "external_side_effects": False,
            "automatic_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-E_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22D_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
