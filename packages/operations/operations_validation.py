from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class OperationsValidationError(ValueError):
    """P22-J / G12 deterministic validation invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _as_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise OperationsValidationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _as_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationsValidationError(f"{field} must be non-empty text")
    return value.strip()


def _hex64(value: str, *, field: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise OperationsValidationError(f"{field} must be 64 lowercase hex characters")
    return normalized


@dataclass(frozen=True, slots=True)
class OperationsValidationPolicy:
    required_workstreams: tuple[str, ...]
    required_manifest_state: str
    required_lock_state: str
    required_governance_status: str
    gate_name: str
    gate_claim_scope: str

    @classmethod
    def from_path(cls, path: Path) -> "OperationsValidationPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise OperationsValidationError(f"invalid P22-J policy JSON: {exc}") from exc
        raw = _as_mapping(raw_value, field="policy")
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22J_OPERATIONS_VALIDATION_G12_POLICY",
            "task_id": "FIN-P22-WJ-001",
            "mode": "DETERMINISTIC_REFERENCE_OPERATIONS_VALIDATION",
            "required_workstreams": ["P22-A", "P22-B", "P22-C", "P22-D", "P22-E", "P22-F", "P22-G", "P22-H", "P22-I"],
            "required_manifest_state": "CANONICAL_COMPLETE",
            "required_lock_state": "RELEASED",
            "required_governance_status": "SUCCESS",
            "gate_name": "G12_OPERATIONS_VALIDATED",
            "gate_claim_scope": "REFERENCE_OPERATIONS_VALIDATION",
            "automatic_p23_activation": False,
            "production_readiness": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise OperationsValidationError(f"P22-J policy mismatch: {key}")
        return cls(
            required_workstreams=("P22-A", "P22-B", "P22-C", "P22-D", "P22-E", "P22-F", "P22-G", "P22-H", "P22-I"),
            required_manifest_state="CANONICAL_COMPLETE",
            required_lock_state="RELEASED",
            required_governance_status="SUCCESS",
            gate_name="G12_OPERATIONS_VALIDATED",
            gate_claim_scope="REFERENCE_OPERATIONS_VALIDATION",
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "required_workstreams": self.required_workstreams,
            "required_manifest_state": self.required_manifest_state,
            "required_lock_state": self.required_lock_state,
            "required_governance_status": self.required_governance_status,
            "gate_name": self.gate_name,
            "gate_claim_scope": self.gate_claim_scope,
            "automatic_p23_activation": False,
            "production_readiness": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class OperationsValidationCertificate:
    certificate_id: str
    policy_id: str
    gate_name: str
    result: str
    claim_scope: str
    manifest_sha256: tuple[tuple[str, str], ...]
    automatic_p23_activation: bool
    production_readiness: bool
    network_mode: str
    credential_mode: str
    external_order_authority: bool
    runtime_state_mutation: bool
    live_execution_authority: bool
    live_trading: str
    auto_trading: str

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "gate_name": self.gate_name,
            "result": self.result,
            "claim_scope": self.claim_scope,
            "manifest_sha256": {name: digest for name, digest in self.manifest_sha256},
            "automatic_p23_activation": self.automatic_p23_activation,
            "production_readiness": self.production_readiness,
            "network_mode": self.network_mode,
            "credential_mode": self.credential_mode,
            "external_order_authority": self.external_order_authority,
            "runtime_state_mutation": self.runtime_state_mutation,
            "live_execution_authority": self.live_execution_authority,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }


_FORBIDDEN_TRUE_SAFETY_FIELDS = (
    "vendor_export",
    "automatic_system_state_mutation",
    "automatic_state_mutation",
    "automatic_diagnostics",
    "automatic_self_healing",
    "automatic_risk_policy_relaxation",
    "automatic_remediation",
    "execution_authority",
    "external_side_effects",
    "real_backup_write",
    "backup_write_authority",
    "production_mutation",
    "measured_rpo_rto_validated",
    "production_rpo_rto_certified",
    "real_restore_execution",
    "storage_write_authority",
    "real_failover_execution",
    "dns_mutation",
    "network_mutation",
    "automatic_recovery_authorization",
    "external_order_authority",
    "production_recovery_certified",
    "corrective_action_execution_authority",
    "runtime_state_mutation",
    "automatic_capacity_scaling",
    "automatic_cost_shedding",
    "automatic_safety_workload_throttling",
)


def _validate_safety(workstream: str, safety: Mapping[str, object]) -> None:
    if safety.get("live_execution_authority") is not False:
        raise OperationsValidationError(f"{workstream}: live execution authority drift")
    if safety.get("live_trading") != "DISABLED":
        raise OperationsValidationError(f"{workstream}: live trading must remain disabled")
    if safety.get("auto_trading") != "DISABLED":
        raise OperationsValidationError(f"{workstream}: auto trading must remain disabled")

    if "credential_mode" in safety and safety.get("credential_mode") != "NONE":
        raise OperationsValidationError(f"{workstream}: credential mode drift")
    if "network_mode" in safety and safety.get("network_mode") != "DISABLED":
        raise OperationsValidationError(f"{workstream}: network mode drift")

    for field in _FORBIDDEN_TRUE_SAFETY_FIELDS:
        if field in safety and safety.get(field) is not False:
            raise OperationsValidationError(f"{workstream}: forbidden safety authority enabled: {field}")


def certify_operations_validation(
    policy: OperationsValidationPolicy,
    manifests: Mapping[str, Mapping[str, object]],
    manifest_sha256: Mapping[str, str],
) -> OperationsValidationCertificate:
    actual_workstreams = tuple(manifests.keys())
    if actual_workstreams != policy.required_workstreams:
        raise OperationsValidationError("P22 manifest coverage/order mismatch")
    if tuple(manifest_sha256.keys()) != policy.required_workstreams:
        raise OperationsValidationError("P22 manifest hash coverage/order mismatch")

    normalized_hashes: list[tuple[str, str]] = []
    for workstream in policy.required_workstreams:
        manifest = manifests[workstream]
        if manifest.get("workstream") != workstream:
            raise OperationsValidationError(f"{workstream}: workstream identity mismatch")
        if manifest.get("state") != policy.required_manifest_state:
            raise OperationsValidationError(f"{workstream}: manifest is not CANONICAL_COMPLETE")

        closure = _as_mapping(manifest.get("closure"), field=f"{workstream}.closure")
        if closure.get("lock") != policy.required_lock_state:
            raise OperationsValidationError(f"{workstream}: lock is not RELEASED")

        for key in ("implementation_governance", "post_merge_governance", "post_merge_branch_hygiene"):
            evidence = _as_mapping(closure.get(key), field=f"{workstream}.closure.{key}")
            if evidence.get("status") != policy.required_governance_status:
                raise OperationsValidationError(f"{workstream}: {key} is not SUCCESS")

        safety = _as_mapping(manifest.get("safety"), field=f"{workstream}.safety")
        _validate_safety(workstream, safety)

        digest = _hex64(
            _as_string(manifest_sha256.get(workstream), field=f"{workstream}.sha256"),
            field=f"{workstream}.sha256",
        )
        normalized_hashes.append((workstream, digest))

    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "gate_name": policy.gate_name,
        "result": "PASS",
        "claim_scope": policy.gate_claim_scope,
        "manifest_sha256": {name: digest for name, digest in normalized_hashes},
        "automatic_p23_activation": False,
        "production_readiness": False,
        "network_mode": "DISABLED",
        "credential_mode": "NONE",
        "external_order_authority": False,
        "runtime_state_mutation": False,
        "live_execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    certificate_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return OperationsValidationCertificate(
        certificate_id=certificate_id,
        policy_id=policy.policy_id,
        gate_name=policy.gate_name,
        result="PASS",
        claim_scope=policy.gate_claim_scope,
        manifest_sha256=tuple(normalized_hashes),
        automatic_p23_activation=False,
        production_readiness=False,
        network_mode="DISABLED",
        credential_mode="NONE",
        external_order_authority=False,
        runtime_state_mutation=False,
        live_execution_authority=False,
        live_trading="DISABLED",
        auto_trading="DISABLED",
    )
