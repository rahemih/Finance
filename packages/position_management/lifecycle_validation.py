from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class PositionLifecycleValidationError(ValueError):
    """P21-H deterministic lifecycle-validation invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PositionLifecycleValidationError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PositionLifecycleValidationPolicy:
    required_workstreams: tuple[str, ...]
    required_manifest_state: str
    required_lock_state: str
    claim_scope: str

    @classmethod
    def from_path(cls, path: Path) -> "PositionLifecycleValidationPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PositionLifecycleValidationError(f"invalid P21-H policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise PositionLifecycleValidationError("P21-H policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21H_POSITION_LIFECYCLE_VALIDATION_POLICY",
            "task_id": "FIN-P21-WH-001",
            "mode": "DETERMINISTIC_REFERENCE_POSITION_LIFECYCLE_VALIDATION",
            "required_manifest_state": "CANONICAL_COMPLETE",
            "required_lock_state": "RELEASED",
            "claim_scope": "REFERENCE_POSITION_LIFECYCLE_VALIDATION",
            "require_all_p21_contract_tests": True,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "automatic_position_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "production_readiness": False,
            "automatic_p22_activation": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise PositionLifecycleValidationError(f"P21-H policy mismatch: {key}")
        ws_raw = raw.get("required_workstreams")
        if not isinstance(ws_raw, list):
            raise PositionLifecycleValidationError("required_workstreams must be an array")
        workstreams = tuple(_text(item, field="required_workstreams") for item in cast(list[object], ws_raw))
        if workstreams != ("P21-A", "P21-B", "P21-C", "P21-D", "P21-E", "P21-F", "P21-G"):
            raise PositionLifecycleValidationError("invalid P21-H workstream coverage")
        return cls(workstreams, "CANONICAL_COMPLETE", "RELEASED", "REFERENCE_POSITION_LIFECYCLE_VALIDATION")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "required_workstreams": list(self.required_workstreams),
            "required_manifest_state": self.required_manifest_state,
            "required_lock_state": self.required_lock_state,
            "claim_scope": self.claim_scope,
            "automatic_p22_activation": False,
            "live_execution_authority": False,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionLifecycleValidationCertificate:
    policy_id: str
    state: str
    claim_scope: str
    workstream_coverage: tuple[str, ...]
    manifest_sha256: tuple[tuple[str, str], ...]
    p22_state: str = "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED"
    automatic_p22_activation: bool = False
    live_execution_validated: bool = False
    live_execution_authority: bool = False
    production_readiness: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "state": self.state,
            "claim_scope": self.claim_scope,
            "workstream_coverage": list(self.workstream_coverage),
            "manifest_sha256": {key: value for key, value in self.manifest_sha256},
            "p22_state": self.p22_state,
            "automatic_p22_activation": self.automatic_p22_activation,
            "live_execution_validated": self.live_execution_validated,
            "live_execution_authority": self.live_execution_authority,
            "production_readiness": self.production_readiness,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def certificate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def certify_position_lifecycle(
    policy: PositionLifecycleValidationPolicy,
    manifests: Mapping[str, Mapping[str, object]],
    manifest_sha256: Mapping[str, str],
) -> PositionLifecycleValidationCertificate:
    if tuple(manifests.keys()) != policy.required_workstreams:
        raise PositionLifecycleValidationError("P21-H manifest coverage/order mismatch")
    if tuple(manifest_sha256.keys()) != policy.required_workstreams:
        raise PositionLifecycleValidationError("P21-H manifest hash coverage/order mismatch")

    hashes: list[tuple[str, str]] = []
    for workstream in policy.required_workstreams:
        manifest = manifests[workstream]
        if manifest.get("state") != policy.required_manifest_state:
            raise PositionLifecycleValidationError(f"{workstream} is not CANONICAL_COMPLETE")
        closure = manifest.get("closure")
        if not isinstance(closure, Mapping) or closure.get("lock") != policy.required_lock_state:
            raise PositionLifecycleValidationError(f"{workstream} lock is not RELEASED")
        safety = manifest.get("safety")
        if not isinstance(safety, Mapping):
            raise PositionLifecycleValidationError(f"{workstream} safety block missing")
        forbidden_false = (
            "real_venue_query",
            "external_order_submission",
            "external_order_mutation",
            "automatic_oms_mutation",
            "live_execution_validated",
            "live_execution_authority",
        )
        for field in forbidden_false:
            if safety.get(field) is not False:
                raise PositionLifecycleValidationError(f"{workstream}.{field} must be false")
        if safety.get("credential_mode") != "NONE":
            raise PositionLifecycleValidationError(f"{workstream}.credential_mode must be NONE")
        if safety.get("network_mode") != "DISABLED":
            raise PositionLifecycleValidationError(f"{workstream}.network_mode must be DISABLED")
        if safety.get("live_trading") != "DISABLED" or safety.get("auto_trading") != "DISABLED":
            raise PositionLifecycleValidationError(f"{workstream} trading authority drift")
        digest = _text(manifest_sha256[workstream], field=f"{workstream}.manifest_sha256").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise PositionLifecycleValidationError(f"{workstream} manifest SHA256 invalid")
        hashes.append((workstream, digest))

    return PositionLifecycleValidationCertificate(
        policy_id=policy.policy_id,
        state="P21_POSITION_LIFECYCLE_VALIDATED_PASS",
        claim_scope=policy.claim_scope,
        workstream_coverage=policy.required_workstreams,
        manifest_sha256=tuple(hashes),
    )
