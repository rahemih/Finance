from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast

from .backup import BackupManifest
from .restore_drill import RestoreDrillResult
from .system_state import SystemState


RecoveryPlanStatus = Literal["REFERENCE_RECOVERY_READY", "AWAITING_OWNER_AUTHORIZATION", "BLOCKED"]
RecoveryMode = Literal["RESTORE", "REBUILD"]


class DisasterRecoveryError(ValueError):
    """P22-G deterministic disaster-recovery invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hex_id(value: str, *, field: str, length: int = 64) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise DisasterRecoveryError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _nonempty(value: str, *, field: str, max_length: int = 128) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise DisasterRecoveryError(f"{field} must be non-empty text of at most {max_length} characters")
    return normalized


def _nonnegative(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise DisasterRecoveryError(f"{field} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class DisasterRecoveryPolicy:
    eligible_system_states: tuple[SystemState, ...]
    supported_dr_classes: tuple[str, ...]
    required_restore_drill_status: str
    separated_classes: tuple[str, ...]
    ordered_reference_steps: tuple[str, ...]

    @classmethod
    def from_path(cls, path: Path) -> "DisasterRecoveryPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DisasterRecoveryError(f"invalid P22-G policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise DisasterRecoveryError("P22-G policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22G_DISASTER_RECOVERY_POLICY",
            "task_id": "FIN-P22-WG-001",
            "mode": "DETERMINISTIC_REFERENCE_DISASTER_RECOVERY_PLAN",
            "eligible_system_states": ["HALTED", "EMERGENCY"],
            "supported_dr_classes": ["DR0", "DR1", "DR2", "DR3"],
            "required_restore_drill_status": "PASS",
            "trusted_restore_drill_required": True,
            "owner_recovery_authorization_required": True,
            "target_failure_domain_separation_required_for": ["DR0", "DR1", "DR2"],
            "dr0_reconciliation_required": True,
            "dr3_rebuild_semantics_required": True,
            "ordered_reference_steps": [
                "DECLARE_DISASTER_REFERENCE",
                "CONTAIN_PRIMARY_REFERENCE",
                "PREPARE_RECOVERY_REFERENCE",
                "VALIDATE_RESTORE_OR_REBUILD_REFERENCE",
                "AWAIT_OWNER_RECOVERY_AUTHORIZATION",
                "REFERENCE_RECOVERY_READY",
            ],
            "execution_mode": "REFERENCE_PLAN_ONLY",
            "real_failover_execution": False,
            "dns_mutation": False,
            "network_mutation": False,
            "storage_mutation": False,
            "automatic_state_mutation": False,
            "automatic_recovery_authorization": False,
            "external_order_authority": False,
            "credential_mode": "NONE",
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise DisasterRecoveryError(f"P22-G policy mismatch: {key}")
        return cls(
            eligible_system_states=("HALTED", "EMERGENCY"),
            supported_dr_classes=("DR0", "DR1", "DR2", "DR3"),
            required_restore_drill_status="PASS",
            separated_classes=("DR0", "DR1", "DR2"),
            ordered_reference_steps=(
                "DECLARE_DISASTER_REFERENCE",
                "CONTAIN_PRIMARY_REFERENCE",
                "PREPARE_RECOVERY_REFERENCE",
                "VALIDATE_RESTORE_OR_REBUILD_REFERENCE",
                "AWAIT_OWNER_RECOVERY_AUTHORIZATION",
                "REFERENCE_RECOVERY_READY",
            ),
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "eligible_system_states": self.eligible_system_states,
            "supported_dr_classes": self.supported_dr_classes,
            "required_restore_drill_status": self.required_restore_drill_status,
            "trusted_restore_drill_required": True,
            "owner_recovery_authorization_required": True,
            "target_failure_domain_separation_required_for": self.separated_classes,
            "dr0_reconciliation_required": True,
            "dr3_rebuild_semantics_required": True,
            "ordered_reference_steps": self.ordered_reference_steps,
            "execution_mode": "REFERENCE_PLAN_ONLY",
            "real_failover_execution": False,
            "dns_mutation": False,
            "network_mutation": False,
            "storage_mutation": False,
            "automatic_state_mutation": False,
            "automatic_recovery_authorization": False,
            "external_order_authority": False,
            "credential_mode": "NONE",
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class DisasterRecoveryPlan:
    plan_id: str
    policy_id: str
    incident_id: str
    system_state: SystemState
    backup_manifest_id: str
    restore_drill_id: str
    dr_class: str
    recovery_mode: RecoveryMode
    status: RecoveryPlanStatus
    reason_code: str
    declared_at_ns: int
    primary_failure_domain: str
    recovery_failure_domain: str
    owner_recovery_authorized: bool
    reference_steps: tuple[str, ...]
    execution_authority: bool
    real_failover_execution: bool
    dns_mutation: bool
    network_mutation: bool
    storage_mutation: bool
    automatic_state_mutation: bool
    external_order_authority: bool
    production_recovery_certified: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "incident_id": self.incident_id,
            "system_state": self.system_state,
            "backup_manifest_id": self.backup_manifest_id,
            "restore_drill_id": self.restore_drill_id,
            "dr_class": self.dr_class,
            "recovery_mode": self.recovery_mode,
            "status": self.status,
            "reason_code": self.reason_code,
            "declared_at_ns": self.declared_at_ns,
            "primary_failure_domain": self.primary_failure_domain,
            "recovery_failure_domain": self.recovery_failure_domain,
            "owner_recovery_authorized": self.owner_recovery_authorized,
            "reference_steps": list(self.reference_steps),
            "execution_authority": self.execution_authority,
            "real_failover_execution": self.real_failover_execution,
            "dns_mutation": self.dns_mutation,
            "network_mutation": self.network_mutation,
            "storage_mutation": self.storage_mutation,
            "automatic_state_mutation": self.automatic_state_mutation,
            "external_order_authority": self.external_order_authority,
            "production_recovery_certified": self.production_recovery_certified,
        }


def _make_plan(
    policy: DisasterRecoveryPolicy,
    *,
    incident_id: str,
    system_state: SystemState,
    manifest: BackupManifest,
    drill: RestoreDrillResult,
    declared_at_ns: int,
    recovery_failure_domain: str,
    owner_recovery_authorized: bool,
    status: RecoveryPlanStatus,
    reason_code: str,
) -> DisasterRecoveryPlan:
    recovery_mode: RecoveryMode = "REBUILD" if manifest.dr_class == "DR3" else "RESTORE"
    steps = list(policy.ordered_reference_steps[:-1])
    if manifest.dr_class == "DR0":
        steps.insert(4, "RECONCILE_EXECUTION_AUTHORITY_REFERENCE")
    if status == "REFERENCE_RECOVERY_READY":
        steps.append("REFERENCE_RECOVERY_READY")
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "incident_id": incident_id,
        "system_state": system_state,
        "backup_manifest_id": manifest.manifest_id,
        "restore_drill_id": drill.drill_id,
        "dr_class": manifest.dr_class,
        "recovery_mode": recovery_mode,
        "status": status,
        "reason_code": reason_code,
        "declared_at_ns": declared_at_ns,
        "primary_failure_domain": manifest.primary_failure_domain,
        "recovery_failure_domain": recovery_failure_domain,
        "owner_recovery_authorized": owner_recovery_authorized,
        "reference_steps": steps,
        "execution_authority": False,
        "real_failover_execution": False,
        "dns_mutation": False,
        "network_mutation": False,
        "storage_mutation": False,
        "automatic_state_mutation": False,
        "external_order_authority": False,
        "production_recovery_certified": False,
    }
    plan_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return DisasterRecoveryPlan(
        plan_id=plan_id,
        policy_id=policy.policy_id,
        incident_id=incident_id,
        system_state=system_state,
        backup_manifest_id=manifest.manifest_id,
        restore_drill_id=drill.drill_id,
        dr_class=manifest.dr_class,
        recovery_mode=recovery_mode,
        status=status,
        reason_code=reason_code,
        declared_at_ns=declared_at_ns,
        primary_failure_domain=manifest.primary_failure_domain,
        recovery_failure_domain=recovery_failure_domain,
        owner_recovery_authorized=owner_recovery_authorized,
        reference_steps=tuple(steps),
        execution_authority=False,
        real_failover_execution=False,
        dns_mutation=False,
        network_mutation=False,
        storage_mutation=False,
        automatic_state_mutation=False,
        external_order_authority=False,
        production_recovery_certified=False,
    )


def build_disaster_recovery_plan(
    policy: DisasterRecoveryPolicy,
    *,
    incident_id: str,
    system_state: SystemState,
    manifest: BackupManifest,
    drill: RestoreDrillResult,
    declared_at_ns: int,
    recovery_failure_domain: str,
    owner_recovery_authorized: bool,
) -> DisasterRecoveryPlan:
    incident = _hex_id(incident_id, field="incident_id")
    declared = _nonnegative(declared_at_ns, field="declared_at_ns")
    recovery_domain = _nonempty(recovery_failure_domain, field="recovery_failure_domain")
    if system_state not in ("NORMAL", "DEGRADED", "SAFE_MODE", "HALTED", "EMERGENCY", "RECOVERY"):
        raise DisasterRecoveryError("unsupported system state")
    if manifest.dr_class not in policy.supported_dr_classes:
        raise DisasterRecoveryError("unsupported DR class")
    if manifest.backup_write_authority or manifest.network_write or manifest.production_mutation:
        raise DisasterRecoveryError("backup manifest unexpectedly carries runtime authority")
    if (
        drill.production_rpo_rto_certified
        or drill.real_restore_execution
        or drill.network_access
        or drill.credential_access
        or drill.production_mutation
    ):
        raise DisasterRecoveryError("restore drill unexpectedly carries runtime authority")

    if system_state not in policy.eligible_system_states:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="SYSTEM_STATE_NOT_DISASTER_ELIGIBLE",
        )
    if drill.backup_manifest_id != manifest.manifest_id:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="BACKUP_DRILL_LINEAGE_MISMATCH",
        )
    if drill.status != policy.required_restore_drill_status or not drill.trusted_after_drill:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="RESTORE_DRILL_NOT_TRUSTED_PASS",
        )
    expected_mode: RecoveryMode = "REBUILD" if manifest.dr_class == "DR3" else "RESTORE"
    if drill.drill_kind != expected_mode:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="RESTORE_DRILL_MODE_MISMATCH",
        )
    if recovery_domain != manifest.recovery_failure_domain:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="RECOVERY_DOMAIN_LINEAGE_MISMATCH",
        )
    if manifest.dr_class in policy.separated_classes and recovery_domain == manifest.primary_failure_domain:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="RECOVERY_FAILURE_DOMAIN_NOT_SEPARATED",
        )
    if manifest.dr_class == "DR0" and not drill.reconciliation_passed:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=owner_recovery_authorized,
            status="BLOCKED",
            reason_code="DR0_RECONCILIATION_NOT_PASSED",
        )
    if not owner_recovery_authorized:
        return _make_plan(
            policy,
            incident_id=incident,
            system_state=system_state,
            manifest=manifest,
            drill=drill,
            declared_at_ns=declared,
            recovery_failure_domain=recovery_domain,
            owner_recovery_authorized=False,
            status="AWAITING_OWNER_AUTHORIZATION",
            reason_code="OWNER_RECOVERY_AUTHORIZATION_REQUIRED",
        )
    return _make_plan(
        policy,
        incident_id=incident,
        system_state=system_state,
        manifest=manifest,
        drill=drill,
        declared_at_ns=declared,
        recovery_failure_domain=recovery_domain,
        owner_recovery_authorized=True,
        status="REFERENCE_RECOVERY_READY",
        reason_code="REFERENCE_DISASTER_RECOVERY_PLAN_VALIDATED",
    )
