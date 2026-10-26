from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.backup import BackupPolicy, build_backup_manifest


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path("config/operations/backup-policy.json")
    policy = BackupPolicy.from_path(policy_path)

    dr0 = build_backup_manifest(
        policy,
        dr_class="DR0",
        source_ref="a" * 64,
        source_content_sha256="b" * 64,
        source_version=7,
        created_at_ns=1_000_000,
        source_size_bytes=8192,
        rights_status="ALLOWED",
        contains_raw_licensed_content=False,
        primary_failure_domain="SITE_A_LOGICAL",
        recovery_failure_domain="SITE_B_LOGICAL",
    )
    rights_blocked = build_backup_manifest(
        policy,
        dr_class="DR2",
        source_ref="c" * 64,
        source_content_sha256="d" * 64,
        source_version=3,
        created_at_ns=2_000_000,
        source_size_bytes=16384,
        rights_status="UNVERIFIED",
        contains_raw_licensed_content=True,
        primary_failure_domain="SITE_A_LOGICAL",
        recovery_failure_domain="SITE_B_LOGICAL",
    )
    dr3 = build_backup_manifest(
        policy,
        dr_class="DR3",
        source_ref="e" * 64,
        source_content_sha256="f" * 64,
        source_version=1,
        created_at_ns=3_000_000,
        source_size_bytes=4096,
        rights_status="DERIVED_ONLY",
        contains_raw_licensed_content=False,
        primary_failure_domain="SITE_A_LOGICAL",
        recovery_failure_domain="SITE_A_LOGICAL",
    )

    if dr0.status != "ELIGIBLE_REFERENCE_BACKUP":
        raise SystemExit("P22-E DR0 reference backup must be eligible")
    if not dr0.reconciliation_after_restore_required:
        raise SystemExit("P22-E DR0 must require post-restore reconciliation")
    if rights_blocked.status != "BLOCKED":
        raise SystemExit("P22-E unverified raw retention must fail closed")
    if dr3.status != "REBUILD_ONLY" or dr3.backup_required:
        raise SystemExit("P22-E DR3 must remain rebuild-only")
    if dr0.measured_rpo_rto_validated:
        raise SystemExit("P22-E must not claim measured RPO/RTO")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22E_BACKUP_EVIDENCE",
        "task_id": "FIN-P22-WE-001",
        "state": "REFERENCE_BACKUP_MANIFEST_VALIDATED_PASS",
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "eligible_dr0": {"manifest_id": dr0.manifest_id, **dr0.payload()},
        "rights_blocked_dr2": {"manifest_id": rights_blocked.manifest_id, **rights_blocked.payload()},
        "rebuild_only_dr3": {"manifest_id": dr3.manifest_id, **dr3.payload()},
        "architecture_targets": {
            "DR0_RPO_SECONDS": 60,
            "DR0_NORMAL_RTO_SECONDS": 3600,
            "DR1_RPO_SECONDS": 900,
            "DR1_RTO_SECONDS": 14400,
            "DR2_RPO_SECONDS": 86400,
            "DR2_RTO_SECONDS": 86400,
            "DR3_RPO_SECONDS": None,
            "DR3_RTO_SECONDS": 172800
        },
        "safety": {
            "real_backup_write": False,
            "measured_rpo_rto_validated": False,
            "production_storage_vendor": "NOT_SELECTED",
            "backup_write_authority": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "production_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        },
        "next": "P22-F_NOT_STARTED"
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22E_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
