from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast

from .backup import BackupManifest


DrillKind = Literal["RESTORE", "REBUILD"]
DrillStatus = Literal["PASS", "FAIL", "BLOCKED"]


class RestoreDrillError(ValueError):
    """P22-F deterministic restore-drill invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hex_id(value: str, *, field: str, length: int = 64) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise RestoreDrillError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _nonnegative(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise RestoreDrillError(f"{field} must be a non-negative integer")
    return value


def _ceil_seconds(delta_ns: int) -> int:
    return (delta_ns + 999_999_999) // 1_000_000_000


@dataclass(frozen=True, slots=True)
class RestoreDrillPolicy:
    drill_kinds: tuple[DrillKind, ...]
    restore_eligible_backup_status: str
    rebuild_eligible_backup_status: str

    @classmethod
    def from_path(cls, path: Path) -> "RestoreDrillPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RestoreDrillError(f"invalid P22-F policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise RestoreDrillError("P22-F policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22F_RESTORE_DRILL_POLICY",
            "task_id": "FIN-P22-WF-001",
            "mode": "DETERMINISTIC_REFERENCE_RESTORE_DRILL",
            "drill_kinds": ["RESTORE", "REBUILD"],
            "restore_eligible_backup_status": "ELIGIBLE_REFERENCE_BACKUP",
            "rebuild_eligible_backup_status": "REBUILD_ONLY",
            "measurement_clock": "CALLER_SUPPLIED_EPOCH_NS",
            "rpo_measurement": "INCIDENT_MINUS_RECOVERY_POINT",
            "rto_measurement": "VALIDATION_COMPLETE_MINUS_INCIDENT",
            "measurement_rounding": "CEILING_SECONDS",
            "integrity_match_required": True,
            "quarantine_requirement_inherited_from_backup_manifest": True,
            "reconciliation_requirement_inherited_from_backup_manifest": True,
            "production_rpo_rto_certification": False,
            "real_restore_execution": False,
            "storage_write_authority": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "production_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise RestoreDrillError(f"P22-F policy mismatch: {key}")
        return cls(
            drill_kinds=("RESTORE", "REBUILD"),
            restore_eligible_backup_status="ELIGIBLE_REFERENCE_BACKUP",
            rebuild_eligible_backup_status="REBUILD_ONLY",
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "drill_kinds": self.drill_kinds,
            "restore_eligible_backup_status": self.restore_eligible_backup_status,
            "rebuild_eligible_backup_status": self.rebuild_eligible_backup_status,
            "measurement_clock": "CALLER_SUPPLIED_EPOCH_NS",
            "rpo_measurement": "INCIDENT_MINUS_RECOVERY_POINT",
            "rto_measurement": "VALIDATION_COMPLETE_MINUS_INCIDENT",
            "measurement_rounding": "CEILING_SECONDS",
            "integrity_match_required": True,
            "production_rpo_rto_certification": False,
            "real_restore_execution": False,
            "storage_write_authority": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "production_mutation": False,
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class RestoreDrillResult:
    drill_id: str
    policy_id: str
    backup_manifest_id: str
    dr_class: str
    drill_kind: DrillKind
    status: DrillStatus
    reason_code: str
    incident_at_ns: int
    restore_started_at_ns: int
    validation_completed_at_ns: int
    measured_rpo_seconds: int
    measured_rto_seconds: int
    rpo_target_seconds: int | None
    rto_target_seconds: int
    rpo_target_met: bool | None
    rto_target_met: bool
    integrity_match: bool
    quarantine_passed: bool
    reconciliation_passed: bool
    trusted_after_drill: bool
    reference_measurement_only: bool
    production_rpo_rto_certified: bool
    real_restore_execution: bool
    network_access: bool
    credential_access: bool
    production_mutation: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "backup_manifest_id": self.backup_manifest_id,
            "dr_class": self.dr_class,
            "drill_kind": self.drill_kind,
            "status": self.status,
            "reason_code": self.reason_code,
            "incident_at_ns": self.incident_at_ns,
            "restore_started_at_ns": self.restore_started_at_ns,
            "validation_completed_at_ns": self.validation_completed_at_ns,
            "measured_rpo_seconds": self.measured_rpo_seconds,
            "measured_rto_seconds": self.measured_rto_seconds,
            "rpo_target_seconds": self.rpo_target_seconds,
            "rto_target_seconds": self.rto_target_seconds,
            "rpo_target_met": self.rpo_target_met,
            "rto_target_met": self.rto_target_met,
            "integrity_match": self.integrity_match,
            "quarantine_passed": self.quarantine_passed,
            "reconciliation_passed": self.reconciliation_passed,
            "trusted_after_drill": self.trusted_after_drill,
            "reference_measurement_only": self.reference_measurement_only,
            "production_rpo_rto_certified": self.production_rpo_rto_certified,
            "real_restore_execution": self.real_restore_execution,
            "network_access": self.network_access,
            "credential_access": self.credential_access,
            "production_mutation": self.production_mutation,
        }


def _blocked_reason(policy: RestoreDrillPolicy, manifest: BackupManifest, drill_kind: DrillKind) -> str | None:
    if manifest.status == "BLOCKED":
        return "BACKUP_MANIFEST_BLOCKED"
    if manifest.status == policy.restore_eligible_backup_status and drill_kind != "RESTORE":
        return "RESTORE_MANIFEST_REQUIRES_RESTORE_DRILL"
    if manifest.status == policy.rebuild_eligible_backup_status and drill_kind != "REBUILD":
        return "REBUILD_ONLY_MANIFEST_REQUIRES_REBUILD_DRILL"
    if manifest.status not in (policy.restore_eligible_backup_status, policy.rebuild_eligible_backup_status):
        return "BACKUP_MANIFEST_STATUS_NOT_ELIGIBLE"
    return None


def run_restore_drill(
    policy: RestoreDrillPolicy,
    *,
    manifest: BackupManifest,
    drill_kind: DrillKind,
    incident_at_ns: int,
    restore_started_at_ns: int,
    validation_completed_at_ns: int,
    restored_content_sha256: str,
    quarantine_passed: bool,
    reconciliation_passed: bool,
) -> RestoreDrillResult:
    if drill_kind not in policy.drill_kinds:
        raise RestoreDrillError("unsupported drill kind")
    incident = _nonnegative(incident_at_ns, field="incident_at_ns")
    started = _nonnegative(restore_started_at_ns, field="restore_started_at_ns")
    completed = _nonnegative(validation_completed_at_ns, field="validation_completed_at_ns")
    restored_hash = _hex_id(restored_content_sha256, field="restored_content_sha256")

    if manifest.backup_write_authority or manifest.network_write or manifest.production_mutation:
        raise RestoreDrillError("P22-E manifest unexpectedly carries runtime authority")
    if incident < manifest.created_at_ns:
        raise RestoreDrillError("incident precedes recovery point")
    if started < incident:
        raise RestoreDrillError("restore start precedes incident")
    if completed < started:
        raise RestoreDrillError("validation completion precedes restore start")

    measured_rpo = _ceil_seconds(incident - manifest.created_at_ns)
    measured_rto = _ceil_seconds(completed - incident)
    rpo_target_met = None if manifest.rpo_target_seconds is None else measured_rpo <= manifest.rpo_target_seconds
    rto_target_met = measured_rto <= manifest.provisional_rto_target_seconds
    integrity_match = restored_hash == manifest.source_content_sha256
    quarantine_met = (not manifest.restore_quarantine_required) or quarantine_passed
    reconciliation_met = (not manifest.reconciliation_after_restore_required) or reconciliation_passed

    blocked_reason = _blocked_reason(policy, manifest, drill_kind)
    if blocked_reason is not None:
        status: DrillStatus = "BLOCKED"
        reason = blocked_reason
    elif not integrity_match:
        status = "FAIL"
        reason = "INTEGRITY_MISMATCH"
    elif not quarantine_met:
        status = "FAIL"
        reason = "RESTORE_QUARANTINE_NOT_PASSED"
    elif not reconciliation_met:
        status = "FAIL"
        reason = "POST_RESTORE_RECONCILIATION_NOT_PASSED"
    elif rpo_target_met is False:
        status = "FAIL"
        reason = "REFERENCE_RPO_TARGET_MISSED"
    elif not rto_target_met:
        status = "FAIL"
        reason = "REFERENCE_RTO_TARGET_MISSED"
    else:
        status = "PASS"
        reason = "REFERENCE_RESTORE_DRILL_VALIDATED"

    trusted = status == "PASS" and integrity_match and quarantine_met and reconciliation_met
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "backup_manifest_id": manifest.manifest_id,
        "dr_class": manifest.dr_class,
        "drill_kind": drill_kind,
        "status": status,
        "reason_code": reason,
        "incident_at_ns": incident,
        "restore_started_at_ns": started,
        "validation_completed_at_ns": completed,
        "measured_rpo_seconds": measured_rpo,
        "measured_rto_seconds": measured_rto,
        "rpo_target_seconds": manifest.rpo_target_seconds,
        "rto_target_seconds": manifest.provisional_rto_target_seconds,
        "rpo_target_met": rpo_target_met,
        "rto_target_met": rto_target_met,
        "integrity_match": integrity_match,
        "quarantine_passed": quarantine_met,
        "reconciliation_passed": reconciliation_met,
        "trusted_after_drill": trusted,
        "reference_measurement_only": True,
        "production_rpo_rto_certified": False,
        "real_restore_execution": False,
        "network_access": False,
        "credential_access": False,
        "production_mutation": False,
    }
    drill_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return RestoreDrillResult(
        drill_id=drill_id,
        policy_id=policy.policy_id,
        backup_manifest_id=manifest.manifest_id,
        dr_class=manifest.dr_class,
        drill_kind=drill_kind,
        status=status,
        reason_code=reason,
        incident_at_ns=incident,
        restore_started_at_ns=started,
        validation_completed_at_ns=completed,
        measured_rpo_seconds=measured_rpo,
        measured_rto_seconds=measured_rto,
        rpo_target_seconds=manifest.rpo_target_seconds,
        rto_target_seconds=manifest.provisional_rto_target_seconds,
        rpo_target_met=rpo_target_met,
        rto_target_met=rto_target_met,
        integrity_match=integrity_match,
        quarantine_passed=quarantine_met,
        reconciliation_passed=reconciliation_met,
        trusted_after_drill=trusted,
        reference_measurement_only=True,
        production_rpo_rto_certified=False,
        real_restore_execution=False,
        network_access=False,
        credential_access=False,
        production_mutation=False,
    )
