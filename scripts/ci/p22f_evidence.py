from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.backup import BackupPolicy, build_backup_manifest
from packages.operations.restore_drill import RestoreDrillPolicy, run_restore_drill


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    backup_policy_path = Path("config/operations/backup-policy.json")
    drill_policy_path = Path("config/operations/restore-drill-policy.json")
    backup_policy = BackupPolicy.from_path(backup_policy_path)
    drill_policy = RestoreDrillPolicy.from_path(drill_policy_path)

    dr0 = build_backup_manifest(
        backup_policy,
        dr_class="DR0",
        source_ref="a" * 64,
        source_content_sha256="b" * 64,
        source_version=9,
        created_at_ns=1_000_000_000,
        source_size_bytes=8192,
        rights_status="ALLOWED",
        contains_raw_licensed_content=False,
        primary_failure_domain="SITE_A_LOGICAL",
        recovery_failure_domain="SITE_B_LOGICAL",
    )
    dr0_pass = run_restore_drill(
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
    dr0_blocked_reconciliation = run_restore_drill(
        drill_policy,
        manifest=dr0,
        drill_kind="RESTORE",
        incident_at_ns=31_000_000_000,
        restore_started_at_ns=32_000_000_000,
        validation_completed_at_ns=131_000_000_000,
        restored_content_sha256="b" * 64,
        quarantine_passed=True,
        reconciliation_passed=False,
    )

    dr3 = build_backup_manifest(
        backup_policy,
        dr_class="DR3",
        source_ref="c" * 64,
        source_content_sha256="d" * 64,
        source_version=2,
        created_at_ns=5_000_000_000,
        source_size_bytes=4096,
        rights_status="DERIVED_ONLY",
        contains_raw_licensed_content=False,
        primary_failure_domain="SITE_A_LOGICAL",
        recovery_failure_domain="SITE_A_LOGICAL",
    )
    dr3_rebuild = run_restore_drill(
        drill_policy,
        manifest=dr3,
        drill_kind="REBUILD",
        incident_at_ns=10_000_000_000,
        restore_started_at_ns=11_000_000_000,
        validation_completed_at_ns=20_000_000_000,
        restored_content_sha256="d" * 64,
        quarantine_passed=True,
        reconciliation_passed=True,
    )

    if dr0_pass.status != "PASS":
        raise SystemExit("P22-F DR0 reference restore drill must pass")
    if dr0_pass.measured_rpo_seconds != 30 or dr0_pass.measured_rto_seconds != 100:
        raise SystemExit("P22-F deterministic RPO/RTO measurements changed")
    if dr0_blocked_reconciliation.status != "FAIL":
        raise SystemExit("P22-F DR0 reconciliation requirement did not fail closed")
    if dr3_rebuild.status != "PASS" or dr3_rebuild.drill_kind != "REBUILD":
        raise SystemExit("P22-F DR3 reference rebuild drill must pass")
    if dr0_pass.production_rpo_rto_certified or dr0_pass.real_restore_execution:
        raise SystemExit("P22-F reference drill unexpectedly claimed production authority")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22F_RESTORE_DRILL_EVIDENCE",
        "task_id": "FIN-P22-WF-001",
        "state": "REFERENCE_RESTORE_DRILL_VALIDATED_PASS",
        "backup_policy_sha256": hashlib.sha256(backup_policy_path.read_bytes()).hexdigest(),
        "drill_policy_id": drill_policy.policy_id,
        "drill_policy_sha256": hashlib.sha256(drill_policy_path.read_bytes()).hexdigest(),
        "dr0_pass": {"drill_id": dr0_pass.drill_id, **dr0_pass.payload()},
        "dr0_reconciliation_fail": {
            "drill_id": dr0_blocked_reconciliation.drill_id,
            **dr0_blocked_reconciliation.payload(),
        },
        "dr3_rebuild_pass": {"drill_id": dr3_rebuild.drill_id, **dr3_rebuild.payload()},
        "claim_scope": "DETERMINISTIC_REFERENCE_RESTORE_DRILL",
        "safety": {
            "production_rpo_rto_certified": False,
            "real_restore_execution": False,
            "storage_write_authority": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "production_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
        "next": "P22-G_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22F_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
