from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast

from .canonical_position import PositionStateRecord
from .tp_sl import ProtectionPlan


class PartialCloseError(ValueError):
    """P21-C deterministic partial-close invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PartialCloseError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PartialCloseError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise PartialCloseError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class PartialClosePolicy:
    required_position_states: tuple[str, ...]
    reason_codes: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "PartialClosePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PartialCloseError(f"invalid P21-C policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise PartialCloseError("P21-C policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21C_PARTIAL_CLOSE_POLICY",
            "task_id": "FIN-P21-WC-001",
            "mode": "DETERMINISTIC_REFERENCE_PARTIAL_CLOSE_PLAN",
            "quantity_domain": "POSITIVE_FIXED_POINT_INTEGER",
            "strict_partial_only": True,
            "full_close_allowed": False,
            "quantity_source": "CALLER_SUPPLIED_NO_UNIVERSAL_PERCENTAGES",
            "require_current_p21b_protection": True,
            "post_fill_protection_requirement": "P21B_REPLAN_REQUIRED_FOR_NEW_POSITION_RECORD",
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "canonical_position_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise PartialCloseError(f"P21-C policy mismatch: {key}")
        states_value = raw.get("required_position_states")
        reasons_value = raw.get("reason_codes")
        if not isinstance(states_value, list) or not isinstance(reasons_value, list):
            raise PartialCloseError("P21-C policy state/reason taxonomy must be arrays")
        states = tuple(_text(item, field="required_position_states") for item in cast(list[object], states_value))
        reasons = tuple(_text(item, field="reason_codes") for item in cast(list[object], reasons_value))
        if states != ("OPEN", "PARTIALLY_CLOSED"):
            raise PartialCloseError("invalid required_position_states")
        if reasons != ("PARTIAL_PROFIT", "DE_RISK", "HEDGE_REDUCTION", "STAGED_EXIT"):
            raise PartialCloseError("invalid reason_codes")
        return cls(states, reasons, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "required_position_states": list(self.required_position_states),
            "reason_codes": list(self.reason_codes),
            "mode": "DETERMINISTIC_REFERENCE_PARTIAL_CLOSE_PLAN",
            "quantity_source": "CALLER_SUPPLIED_NO_UNIVERSAL_PERCENTAGES",
            "require_current_p21b_protection": True,
            "post_fill_protection_requirement": "P21B_REPLAN_REQUIRED_FOR_NEW_POSITION_RECORD",
            "network_mode": "DISABLED",
            "live_execution_authority": False,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class PartialCloseRequest:
    position_record_id: str
    position_id: str
    close_quantity_scaled: int
    reason_code: str
    exit_decision_id: str
    source_ref: str = "DETERMINISTIC_REFERENCE"

    def validate(self, policy: PartialClosePolicy) -> None:
        _sha256_hex(self.position_record_id, field="position_record_id")
        _text(self.position_id, field="position_id")
        _positive_int(self.close_quantity_scaled, field="close_quantity_scaled")
        if self.reason_code not in policy.reason_codes:
            raise PartialCloseError("unsupported partial-close reason_code")
        _sha256_hex(self.exit_decision_id, field="exit_decision_id")
        _text(self.source_ref, field="source_ref")

    def payload(self) -> dict[str, object]:
        return {
            "position_record_id": self.position_record_id.lower(),
            "position_id": self.position_id,
            "close_quantity_scaled": self.close_quantity_scaled,
            "reason_code": self.reason_code,
            "exit_decision_id": self.exit_decision_id.lower(),
            "source_ref": self.source_ref,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class PartialClosePlan:
    policy_id: str
    request_id: str
    position_record_id: str
    position_id: str
    position_state: str
    side: str
    quantity_scale: int
    price_scale: int
    open_quantity_before_scaled: int
    close_quantity_scaled: int
    remaining_quantity_scaled: int
    reason_code: str
    exit_decision_id: str
    protection_plan_id: str
    post_fill_protection_requirement: str = "P21B_REPLAN_REQUIRED_FOR_NEW_POSITION_RECORD"
    source_mode: str = "REFERENCE_ONLY"
    real_venue_query: bool = False
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    external_order_mutation: bool = False
    automatic_oms_mutation: bool = False
    canonical_position_mutation: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "request_id": self.request_id,
            "position_record_id": self.position_record_id,
            "position_id": self.position_id,
            "position_state": self.position_state,
            "side": self.side,
            "quantity_scale": self.quantity_scale,
            "price_scale": self.price_scale,
            "open_quantity_before_scaled": self.open_quantity_before_scaled,
            "close_quantity_scaled": self.close_quantity_scaled,
            "remaining_quantity_scaled": self.remaining_quantity_scaled,
            "reason_code": self.reason_code,
            "exit_decision_id": self.exit_decision_id,
            "protection_plan_id": self.protection_plan_id,
            "post_fill_protection_requirement": self.post_fill_protection_requirement,
            "source_mode": self.source_mode,
            "real_venue_query": self.real_venue_query,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "external_order_mutation": self.external_order_mutation,
            "automatic_oms_mutation": self.automatic_oms_mutation,
            "canonical_position_mutation": self.canonical_position_mutation,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def plan_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class PartialClosePlanner:
    def __init__(self, policy: PartialClosePolicy) -> None:
        self._policy = policy

    def plan(self, position: PositionStateRecord, protection: ProtectionPlan, request: PartialCloseRequest) -> PartialClosePlan:
        request.validate(self._policy)
        if position.state not in self._policy.required_position_states:
            raise PartialCloseError("partial close requires OPEN or PARTIALLY_CLOSED position")
        if position.open_quantity_scaled <= 0:
            raise PartialCloseError("partial close requires positive open quantity")
        if request.position_id != position.position_id:
            raise PartialCloseError("position_id mismatch")
        if request.position_record_id.lower() != position.record_id:
            raise PartialCloseError("partial-close request is not bound to exact canonical position record")
        if request.close_quantity_scaled >= position.open_quantity_scaled:
            raise PartialCloseError("P21-C requires a strictly partial close with positive remainder")

        if protection.position_record_id != position.record_id:
            raise PartialCloseError("P21-B protection is stale for current canonical position record")
        if protection.position_id != position.position_id:
            raise PartialCloseError("P21-B protection position_id mismatch")
        if protection.position_state != position.state:
            raise PartialCloseError("P21-B protection position state mismatch")
        if protection.side != position.side:
            raise PartialCloseError("P21-B protection side mismatch")
        if protection.open_quantity_scaled != position.open_quantity_scaled:
            raise PartialCloseError("P21-B protection open quantity mismatch")
        if protection.price_scale != position.price_scale:
            raise PartialCloseError("P21-B protection price scale mismatch")
        if (
            protection.source_mode != "REFERENCE_ONLY"
            or protection.real_venue_query
            or protection.network_mode != "DISABLED"
            or protection.external_order_submission
            or protection.external_order_mutation
            or protection.live_execution_authority
        ):
            raise PartialCloseError("P21-B protection authority boundary mismatch")

        remaining = position.open_quantity_scaled - request.close_quantity_scaled
        if remaining <= 0:
            raise PartialCloseError("partial close must preserve positive remainder")

        return PartialClosePlan(
            policy_id=self._policy.policy_id,
            request_id=request.request_id,
            position_record_id=position.record_id,
            position_id=position.position_id,
            position_state=position.state,
            side=position.side,
            quantity_scale=position.quantity_scale,
            price_scale=position.price_scale,
            open_quantity_before_scaled=position.open_quantity_scaled,
            close_quantity_scaled=request.close_quantity_scaled,
            remaining_quantity_scaled=remaining,
            reason_code=request.reason_code,
            exit_decision_id=request.exit_decision_id.lower(),
            protection_plan_id=protection.plan_id,
        )
