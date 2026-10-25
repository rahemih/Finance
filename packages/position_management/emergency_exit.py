from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast

from .canonical_position import PositionStateRecord


class EmergencyExitError(ValueError):
    """P21-E deterministic emergency-exit invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EmergencyExitError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EmergencyExitError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise EmergencyExitError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class EmergencyExitPolicy:
    required_position_states: tuple[str, ...]
    actions: tuple[str, ...]
    trigger_codes: tuple[str, ...]
    reduce_authorities: tuple[str, ...]
    flatten_authority: str
    reconciliation_states: tuple[str, ...]

    @classmethod
    def from_path(cls, path: Path) -> "EmergencyExitPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EmergencyExitError(f"invalid P21-E policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise EmergencyExitError("P21-E policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21E_EMERGENCY_EXIT_POLICY",
            "task_id": "FIN-P21-WE-001",
            "mode": "DETERMINISTIC_REFERENCE_EMERGENCY_EXIT_PLAN",
            "provider_incident_reconciliation": "RESOLVED_NO_CONFLICT_REQUIRED",
            "p16_trigger_auto_close_authority": False,
            "reduce_only": True,
            "blind_reroute_allowed": False,
            "requires_p20_idempotent_execution": True,
            "requires_reconciliation_before_retry": True,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "canonical_position_mutation": False,
            "risk_firewall_bypass_authority": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise EmergencyExitError(f"P21-E policy mismatch: {key}")

        def string_tuple(key: str) -> tuple[str, ...]:
            value = raw.get(key)
            if not isinstance(value, list):
                raise EmergencyExitError(f"{key} must be an array")
            return tuple(_text(item, field=key) for item in cast(list[object], value))

        states = string_tuple("required_position_states")
        actions = string_tuple("actions")
        triggers = string_tuple("trigger_codes")
        reduce_auth = string_tuple("reduce_authorities")
        recon = string_tuple("reconciliation_states")
        flatten = _text(raw.get("flatten_authority"), field="flatten_authority")

        if states != ("OPEN", "PARTIALLY_CLOSED"):
            raise EmergencyExitError("invalid required_position_states")
        if actions != ("EMERGENCY_REDUCE", "EMERGENCY_FLATTEN"):
            raise EmergencyExitError("invalid actions")
        if flatten != "OWNER_EXPLICIT_EMERGENCY_FLATTEN":
            raise EmergencyExitError("invalid flatten authority")
        if recon != ("NOT_REQUIRED", "RESOLVED_NO_CONFLICT"):
            raise EmergencyExitError("invalid reconciliation states")
        return cls(states, actions, triggers, reduce_auth, flatten, recon)

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "required_position_states": list(self.required_position_states),
            "actions": list(self.actions),
            "trigger_codes": list(self.trigger_codes),
            "reduce_authorities": list(self.reduce_authorities),
            "flatten_authority": self.flatten_authority,
            "reconciliation_states": list(self.reconciliation_states),
            "mode": "DETERMINISTIC_REFERENCE_EMERGENCY_EXIT_PLAN",
            "reduce_only": True,
            "blind_reroute_allowed": False,
            "risk_firewall_bypass_authority": False,
            "live_execution_authority": False,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class EmergencyExitRequest:
    position_record_id: str
    position_id: str
    action: str
    requested_quantity_scaled: int
    trigger_code: str
    authority_code: str
    reconciliation_status: str
    emergency_decision_id: str
    authority_decision_id: str
    source_ref: str = "DETERMINISTIC_REFERENCE"

    def validate(self, policy: EmergencyExitPolicy) -> None:
        _sha256_hex(self.position_record_id, field="position_record_id")
        _text(self.position_id, field="position_id")
        if self.action not in policy.actions:
            raise EmergencyExitError("unsupported emergency action")
        _positive_int(self.requested_quantity_scaled, field="requested_quantity_scaled")
        if self.trigger_code not in policy.trigger_codes:
            raise EmergencyExitError("unsupported emergency trigger_code")
        _text(self.authority_code, field="authority_code")
        if self.reconciliation_status not in policy.reconciliation_states:
            raise EmergencyExitError("unresolved or unsupported reconciliation status")
        _sha256_hex(self.emergency_decision_id, field="emergency_decision_id")
        _sha256_hex(self.authority_decision_id, field="authority_decision_id")
        _text(self.source_ref, field="source_ref")

    def payload(self) -> dict[str, object]:
        return {
            "position_record_id": self.position_record_id.lower(),
            "position_id": self.position_id,
            "action": self.action,
            "requested_quantity_scaled": self.requested_quantity_scaled,
            "trigger_code": self.trigger_code,
            "authority_code": self.authority_code,
            "reconciliation_status": self.reconciliation_status,
            "emergency_decision_id": self.emergency_decision_id.lower(),
            "authority_decision_id": self.authority_decision_id.lower(),
            "source_ref": self.source_ref,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class EmergencyExitPlan:
    policy_id: str
    request_id: str
    position_record_id: str
    position_id: str
    position_state: str
    side: str
    action: str
    open_quantity_scaled: int
    requested_quantity_scaled: int
    remaining_quantity_scaled: int
    trigger_code: str
    authority_code: str
    reconciliation_status: str
    emergency_decision_id: str
    authority_decision_id: str
    reduce_only: bool = True
    requires_p20_idempotent_execution: bool = True
    requires_reconciliation_before_retry: bool = True
    blind_reroute_allowed: bool = False
    p16_trigger_auto_close_authority: bool = False
    source_mode: str = "REFERENCE_ONLY"
    real_venue_query: bool = False
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    external_order_mutation: bool = False
    automatic_oms_mutation: bool = False
    canonical_position_mutation: bool = False
    risk_firewall_bypass_authority: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "request_id": self.request_id,
            "position_record_id": self.position_record_id,
            "position_id": self.position_id,
            "position_state": self.position_state,
            "side": self.side,
            "action": self.action,
            "open_quantity_scaled": self.open_quantity_scaled,
            "requested_quantity_scaled": self.requested_quantity_scaled,
            "remaining_quantity_scaled": self.remaining_quantity_scaled,
            "trigger_code": self.trigger_code,
            "authority_code": self.authority_code,
            "reconciliation_status": self.reconciliation_status,
            "emergency_decision_id": self.emergency_decision_id,
            "authority_decision_id": self.authority_decision_id,
            "reduce_only": self.reduce_only,
            "requires_p20_idempotent_execution": self.requires_p20_idempotent_execution,
            "requires_reconciliation_before_retry": self.requires_reconciliation_before_retry,
            "blind_reroute_allowed": self.blind_reroute_allowed,
            "p16_trigger_auto_close_authority": self.p16_trigger_auto_close_authority,
            "source_mode": self.source_mode,
            "real_venue_query": self.real_venue_query,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "external_order_mutation": self.external_order_mutation,
            "automatic_oms_mutation": self.automatic_oms_mutation,
            "canonical_position_mutation": self.canonical_position_mutation,
            "risk_firewall_bypass_authority": self.risk_firewall_bypass_authority,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def plan_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class EmergencyExitPlanner:
    def __init__(self, policy: EmergencyExitPolicy) -> None:
        self._policy = policy

    def plan(self, position: PositionStateRecord, request: EmergencyExitRequest) -> EmergencyExitPlan:
        request.validate(self._policy)
        if position.state not in self._policy.required_position_states:
            raise EmergencyExitError("emergency exit requires OPEN or PARTIALLY_CLOSED position")
        if position.open_quantity_scaled <= 0:
            raise EmergencyExitError("emergency exit requires positive open quantity")
        if request.position_id != position.position_id:
            raise EmergencyExitError("position_id mismatch")
        if request.position_record_id.lower() != position.record_id:
            raise EmergencyExitError("request is not bound to exact canonical position record")

        if request.trigger_code == "PROVIDER_OR_EXECUTION_INCIDENT":
            if request.reconciliation_status != "RESOLVED_NO_CONFLICT":
                raise EmergencyExitError("provider/execution incident requires resolved reconciliation")

        open_quantity = position.open_quantity_scaled
        if request.action == "EMERGENCY_REDUCE":
            if request.authority_code not in self._policy.reduce_authorities:
                raise EmergencyExitError("emergency reduction lacks governed reduce-only authority")
            if request.requested_quantity_scaled >= open_quantity:
                raise EmergencyExitError("EMERGENCY_REDUCE must be strictly partial")
            remaining = open_quantity - request.requested_quantity_scaled
        else:
            if request.authority_code != self._policy.flatten_authority:
                raise EmergencyExitError("EMERGENCY_FLATTEN requires explicit Owner authority")
            if request.requested_quantity_scaled != open_quantity:
                raise EmergencyExitError("EMERGENCY_FLATTEN quantity must equal full current open quantity")
            remaining = 0

        return EmergencyExitPlan(
            policy_id=self._policy.policy_id,
            request_id=request.request_id,
            position_record_id=position.record_id,
            position_id=position.position_id,
            position_state=position.state,
            side=position.side,
            action=request.action,
            open_quantity_scaled=open_quantity,
            requested_quantity_scaled=request.requested_quantity_scaled,
            remaining_quantity_scaled=remaining,
            trigger_code=request.trigger_code,
            authority_code=request.authority_code,
            reconciliation_status=request.reconciliation_status,
            emergency_decision_id=request.emergency_decision_id.lower(),
            authority_decision_id=request.authority_decision_id.lower(),
        )
