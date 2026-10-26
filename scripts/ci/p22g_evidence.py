from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.backup import BackupPolicy, build_backup_manifest
from packages.operations.disaster_recovery import DisasterRecoveryPolicy, build_disaster_recovery_plan
from packages.operations.restore_drill import RestoreDrillPolicy, run_restore_drill


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    backup_path = Path("config/operations/backup-policy.json")
    drill_path = Path("config/operations/restore-drill-policy.json")
    dr_path = Path("config/operations/disaster-recovery-policy.json")
    backup_policy = BackupPolicy.from_path(backup_path)
    drill_policy = RestoreDrillPolicy.from_path(drill_path)
    dr_policy = DisasterRecoveryPolicy.from_path(dr_path)

    dr0 = build_backup_manifest(
        backup_policy,
        dr_class="DR0",
        source_ref="a" * 64,
        source_content_sha256="b" * 64,
        source_version=11,
        created_at_ns=1_000_000_000,
        source_size_bytes=8192,
        rights_status="ALLOWED",
        contains_raw_licensed_content=False,
        primary_failure_domain="SITE_A_LOGICAL",
        recovery_failure_domain="SITE_B_LOGICAL",
    )
    drill = run_restore_drill(
        drill_policy,
        manifest=dr0,
        drill_kind="RESTORE",
        incident_at_ns=31_000_000_000,
        restore_started_at_ns=32_000_000_000,
        validation_completed_at_ns=131_000_000_000,
        restored_content_sha256="b" * 64,
        quarantine_passed=True,
        reconciliation_passed=True,
    )
    waiting = build_disaster_recovery_plan(
        dr_policy,
        incident_id="c" * 64,
        system_state="EMERGENCY",
        manifest=dr0,
        drill=drill,
        declared_at_ns=200_000_000_000,
        recovery_failure_domain="SITE_B_LOGICAL",
        owner_recovery_authorized=False,
    )
    ready = build_disaster_recovery_plan(
        dr_policy,
        incident_id="c" * 64,
        system_state="EMERGENCY",
        manifest=dr0,
        drill=drill,
        declared_at_ns=200_000_000_000,
        recovery_failure_domain="SITE_B_LOGICAL",
        owner_recovery_authorized=True,
    )
    blocked = build_disaster_recovery_plan(
        dr_policy,
        incident_id="d" * 64,
        system_state="SAFE_MODE",
        manifest=dr0,
        drill=drill,
        declared_at_ns=210_000_000_000,
        recovery_failure_domain="SITE_B_LOGICAL",
        owner_recovery_authorized=True,
    )

    if waiting.status != "AWAITING_OWNER_AUTHORIZATION":
        raise SystemExit("P22-G must require owner recovery authorization")
    if ready.status != "REFERENCE_RECOVERY_READY":
        raise SystemExit("P22-G authorized reference plan must be recovery-ready")
    if blocked.status != "BLOCKED":
        raise SystemExit("P22-G non-disaster state must fail closed")
    if ready.execution_authority or ready.real_failover_execution or ready.production_recovery_certified:
        raise SystemExit("P22-G reference plan unexpectedly gained runtime authority")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22G_DISASTER_RECOVERY_EVIDENCE",
        "task_id": "FIN-P22-WG-001",
        "state": "REFERENCE_DISASTER_RECOVERY_VALIDATED_PASS",
        "backup_policy_sha256": hashlib.sha256(backup_path.read_bytes()).hexdigest(),
        "restore_drill_policy_sha256": hashlib.sha256(drill_path.read_bytes()).hexdigest(),
        "disaster_recovery_policy_id": dr_policy.policy_id,
        "disaster_recovery_policy_sha256": hashlib.sha256(dr_path.read_bytes()).hexdigest(),
        "waiting_owner_authorization": {"plan_id": waiting.plan_id, **waiting.payload()},
        "reference_recovery_ready": {"plan_id": ready.plan_id, **ready.payload()},
        "blocked_non_disaster_state": {"plan_id": blocked.plan_id, **blocked.payload()},
        "claim_scope": "DETERMINISTIC_REFERENCE_DISASTER_RECOVERY",
        "safety": {
            "execution_mode": "REFERENCE_PLAN_ONLY",
            "real_failover_execution": False,
            "dns_mutation": False,
            "network_mutation": False,
            "storage_mutation": False,
            "automatic_state_mutation": False,
            "automatic_recovery_authorization": False,
            "external_order_authority": False,
            "credential_mode": "NONE",
            "production_recovery_certified": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-H_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22G_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
