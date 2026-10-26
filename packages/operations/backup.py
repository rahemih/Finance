from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast


DRClass = Literal["DR0", "DR1", "DR2", "DR3"]
RightsStatus = Literal["ALLOWED", "DERIVED_ONLY", "FORBIDDEN", "UNVERIFIED"]
BackupPlanStatus = Literal["ELIGIBLE_REFERENCE_BACKUP", "REBUILD_ONLY", "BLOCKED"]


class BackupError(ValueError):
    """P22-E deterministic backup-contract invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hex_id(value: str, *, field: str, length: int = 64) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise BackupError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _nonempty(value: str, *, field: str, max_length: int = 128) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise BackupError(f"{field} must be non-empty text of at most {max_length} characters")
    return normalized


def _nonnegative(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise BackupError(f"{field} must be a non-negative integer")
    return value


def _positive(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 1:
        raise BackupError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class DRClassRule:
    description: str
    backup_required: bool
    rpo_target_seconds: int | None
    provisional_rto_target_seconds: int
    off_primary_required: bool
    restore_quarantine_required: bool
    reconciliation_after_restore_required: bool


@dataclass(frozen=True, slots=True)
class BackupPolicy:
    dr_classes: Mapping[DRClass, DRClassRule]
    rights_statuses: tuple[RightsStatus, ...]

    @classmethod
    def from_path(cls, path: Path) -> "BackupPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BackupError(f"invalid P22-E policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise BackupError("P22-E policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22E_BACKUP_POLICY",
            "task_id": "FIN-P22-WE-001",
            "mode": "DETERMINISTIC_REFERENCE_BACKUP_MANIFEST",
            "dr_classes": {
                "DR0": {
                    "description": "EXECUTION_AUTHORITY_STATE",
                    "backup_required": True,
                    "rpo_target_seconds": 60,
                    "provisional_rto_target_seconds": 3600,
                    "off_primary_required": True,
                    "restore_quarantine_required": True,
                    "reconciliation_after_restore_required": True,
                },
                "DR1": {
                    "description": "CONTROL_SECURITY_STATE",
                    "backup_required": True,
                    "rpo_target_seconds": 900,
                    "provisional_rto_target_seconds": 14400,
                    "off_primary_required": True,
                    "restore_quarantine_required": True,
                    "reconciliation_after_restore_required": False,
                },
                "DR2": {
                    "description": "MARKET_HISTORICAL_RESEARCH_DATA",
                    "backup_required": True,
                    "rpo_target_seconds": 86400,
                    "provisional_rto_target_seconds": 86400,
                    "off_primary_required": True,
                    "restore_quarantine_required": True,
                    "reconciliation_after_restore_required": False,
                },
                "DR3": {
                    "description": "REBUILDABLE_DERIVED_STATE",
                    "backup_required": False,
                    "rpo_target_seconds": None,
                    "provisional_rto_target_seconds": 172800,
                    "off_primary_required": False,
                    "restore_quarantine_required": True,
                    "reconciliation_after_restore_required": False,
                },
            },
            "rights_statuses": ["ALLOWED", "DERIVED_ONLY", "FORBIDDEN", "UNVERIFIED"],
            "same_failure_domain_counts_as_dr": False,
            "versioned_backup_required": True,
            "content_addressed_integrity_required": True,
            "restored_data_trusted_before_validation": False,
            "raw_retention_fail_closed_when_forbidden_or_unverified": True,
            "rpo_rto_claim_mode": "PROVISIONAL_TARGETS_ONLY_P22F_VALIDATES",
            "production_storage_vendor": "NOT_SELECTED",
            "cloud_region_country": "UNSET",
            "backup_write_authority": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "production_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise BackupError(f"P22-E policy mismatch: {key}")

        rules: dict[DRClass, DRClassRule] = {
            "DR0": DRClassRule("EXECUTION_AUTHORITY_STATE", True, 60, 3600, True, True, True),
            "DR1": DRClassRule("CONTROL_SECURITY_STATE", True, 900, 14400, True, True, False),
            "DR2": DRClassRule("MARKET_HISTORICAL_RESEARCH_DATA", True, 86400, 86400, True, True, False),
            "DR3": DRClassRule("REBUILDABLE_DERIVED_STATE", False, None, 172800, False, True, False),
        }
        return cls(rules, ("ALLOWED", "DERIVED_ONLY", "FORBIDDEN", "UNVERIFIED"))

    @property
    def policy_id(self) -> str:
        payload = {
            "dr_classes": {
                key: {
                    "description": rule.description,
                    "backup_required": rule.backup_required,
                    "rpo_target_seconds": rule.rpo_target_seconds,
                    "provisional_rto_target_seconds": rule.provisional_rto_target_seconds,
                    "off_primary_required": rule.off_primary_required,
                    "restore_quarantine_required": rule.restore_quarantine_required,
                    "reconciliation_after_restore_required": rule.reconciliation_after_restore_required,
                }
                for key, rule in sorted(self.dr_classes.items())
            },
            "rights_statuses": self.rights_statuses,
            "same_failure_domain_counts_as_dr": False,
            "versioned_backup_required": True,
            "content_addressed_integrity_required": True,
            "restored_data_trusted_before_validation": False,
            "raw_retention_fail_closed_when_forbidden_or_unverified": True,
            "rpo_rto_claim_mode": "PROVISIONAL_TARGETS_ONLY_P22F_VALIDATES",
            "production_storage_vendor": "NOT_SELECTED",
            "backup_write_authority": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "production_mutation": False,
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class BackupManifest:
    manifest_id: str
    policy_id: str
    dr_class: DRClass
    status: BackupPlanStatus
    reason_code: str
    source_ref: str
    source_content_sha256: str
    source_version: int
    created_at_ns: int
    source_size_bytes: int
    rights_status: RightsStatus
    contains_raw_licensed_content: bool
    primary_failure_domain: str
    recovery_failure_domain: str
    backup_required: bool
    rpo_target_seconds: int | None
    provisional_rto_target_seconds: int
    off_primary_required: bool
    restore_quarantine_required: bool
    reconciliation_after_restore_required: bool
    integrity_validation_required: bool
    measured_rpo_rto_validated: bool
    backup_write_authority: bool
    network_write: bool
    production_mutation: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "dr_class": self.dr_class,
            "status": self.status,
            "reason_code": self.reason_code,
            "source_ref": self.source_ref,
            "source_content_sha256": self.source_content_sha256,
            "source_version": self.source_version,
            "created_at_ns": self.created_at_ns,
            "source_size_bytes": self.source_size_bytes,
            "rights_status": self.rights_status,
            "contains_raw_licensed_content": self.contains_raw_licensed_content,
            "primary_failure_domain": self.primary_failure_domain,
            "recovery_failure_domain": self.recovery_failure_domain,
            "backup_required": self.backup_required,
            "rpo_target_seconds": self.rpo_target_seconds,
            "provisional_rto_target_seconds": self.provisional_rto_target_seconds,
            "off_primary_required": self.off_primary_required,
            "restore_quarantine_required": self.restore_quarantine_required,
            "reconciliation_after_restore_required": self.reconciliation_after_restore_required,
            "integrity_validation_required": self.integrity_validation_required,
            "measured_rpo_rto_validated": self.measured_rpo_rto_validated,
            "backup_write_authority": self.backup_write_authority,
            "network_write": self.network_write,
            "production_mutation": self.production_mutation,
        }


def build_backup_manifest(
    policy: BackupPolicy,
    *,
    dr_class: DRClass,
    source_ref: str,
    source_content_sha256: str,
    source_version: int,
    created_at_ns: int,
    source_size_bytes: int,
    rights_status: RightsStatus,
    contains_raw_licensed_content: bool,
    primary_failure_domain: str,
    recovery_failure_domain: str,
) -> BackupManifest:
    if dr_class not in policy.dr_classes:
        raise BackupError("unsupported DR class")
    if rights_status not in policy.rights_statuses:
        raise BackupError("unsupported rights status")
    source = _hex_id(source_ref, field="source_ref")
    content_hash = _hex_id(source_content_sha256, field="source_content_sha256")
    version = _positive(source_version, field="source_version")
    created = _nonnegative(created_at_ns, field="created_at_ns")
    size = _nonnegative(source_size_bytes, field="source_size_bytes")
    primary_domain = _nonempty(primary_failure_domain, field="primary_failure_domain")
    recovery_domain = _nonempty(recovery_failure_domain, field="recovery_failure_domain")
    rule = policy.dr_classes[dr_class]

    status: BackupPlanStatus
    reason: str

    if rights_status in ("FORBIDDEN", "UNVERIFIED"):
        status = "BLOCKED"
        reason = "RETENTION_RIGHTS_NOT_PERMITTED"
    elif contains_raw_licensed_content and rights_status != "ALLOWED":
        status = "BLOCKED"
        reason = "RAW_LICENSED_CONTENT_NOT_PERMITTED"
    elif dr_class == "DR3":
        status = "REBUILD_ONLY"
        reason = "REBUILDABLE_DERIVED_STATE"
    elif rule.off_primary_required and primary_domain == recovery_domain:
        status = "BLOCKED"
        reason = "SAME_FAILURE_DOMAIN_NOT_DR"
    else:
        status = "ELIGIBLE_REFERENCE_BACKUP"
        reason = "BACKUP_MANIFEST_ELIGIBLE"

    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "dr_class": dr_class,
        "status": status,
        "reason_code": reason,
        "source_ref": source,
        "source_content_sha256": content_hash,
        "source_version": version,
        "created_at_ns": created,
        "source_size_bytes": size,
        "rights_status": rights_status,
        "contains_raw_licensed_content": contains_raw_licensed_content,
        "primary_failure_domain": primary_domain,
        "recovery_failure_domain": recovery_domain,
        "backup_required": rule.backup_required,
        "rpo_target_seconds": rule.rpo_target_seconds,
        "provisional_rto_target_seconds": rule.provisional_rto_target_seconds,
        "off_primary_required": rule.off_primary_required,
        "restore_quarantine_required": rule.restore_quarantine_required,
        "reconciliation_after_restore_required": rule.reconciliation_after_restore_required,
        "integrity_validation_required": True,
        "measured_rpo_rto_validated": False,
        "backup_write_authority": False,
        "network_write": False,
        "production_mutation": False,
    }
    manifest_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return BackupManifest(
        manifest_id=manifest_id,
        policy_id=policy.policy_id,
        dr_class=dr_class,
        status=status,
        reason_code=reason,
        source_ref=source,
        source_content_sha256=content_hash,
        source_version=version,
        created_at_ns=created,
        source_size_bytes=size,
        rights_status=rights_status,
        contains_raw_licensed_content=contains_raw_licensed_content,
        primary_failure_domain=primary_domain,
        recovery_failure_domain=recovery_domain,
        backup_required=rule.backup_required,
        rpo_target_seconds=rule.rpo_target_seconds,
        provisional_rto_target_seconds=rule.provisional_rto_target_seconds,
        off_primary_required=rule.off_primary_required,
        restore_quarantine_required=rule.restore_quarantine_required,
        reconciliation_after_restore_required=rule.reconciliation_after_restore_required,
        integrity_validation_required=True,
        measured_rpo_rto_validated=False,
        backup_write_authority=False,
        network_write=False,
        production_mutation=False,
    )
