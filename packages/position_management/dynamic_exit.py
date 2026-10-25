from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast

from .canonical_position import PositionStateRecord
from .tp_sl import ProtectionPlan


class DynamicExitError(ValueError):
    """P21-D deterministic protective-stop ratchet invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DynamicExitError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DynamicExitError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise DynamicExitError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class DynamicExitPolicy:
    required_position_states: tuple[str, ...]
    adjustment_modes: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "DynamicExitPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DynamicExitError(f"invalid P21-D policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise DynamicExitError("P21-D policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21D_DYNAMIC_EXIT_POLICY",
            "task_id": "FIN-P21-WD-001",
            "mode": "DETERMINISTIC_REFERENCE_PROTECTION_RATCHET",
            "price_domain": "POSITIVE_FIXED_POINT_INTEGER",
            "reference_price_source": "CALLER_SUPPLIED_NO_VENUE_QUERY",
            "stop_source": "CALLER_SUPPLIED_NO_UNIVERSAL_TRAIL_DISTANCE",
            "require_current_p21b_protection": True,
            "stop_ratchet": "MONOTONIC_TIGHTEN_ONLY",
            "break_even_rule": "STOP_EQUALS_CANONICAL_ENTRY",
            "reference_boundary": "STOP_STRICTLY_NON_TRIGGERED_SIDE_OF_REFERENCE_AND_REFERENCE_BEFORE_TP",
            "take_profit_change": "P21B_TAKE_PROFIT_PRESERVED",
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
                raise DynamicExitError(f"P21-D policy mismatch: {key}")
        states_value = raw.get("required_position_states")
        modes_value = raw.get("adjustment_modes")
        if not isinstance(states_value, list) or not isinstance(modes_value, list):
            raise DynamicExitError("P21-D policy states/modes must be arrays")
        states = tuple(_text(item, field="required_position_states") for item in cast(list[object], states_value))
        modes = tuple(_text(item, field="adjustment_modes") for item in cast(list[object], modes_value))
        if states != ("OPEN", "PARTIALLY_CLOSED"):
            raise DynamicExitError("invalid required_position_states")
        if modes != ("BREAK_EVEN", "TRAILING", "DYNAMIC_EXIT"):
            raise DynamicExitError("invalid adjustment_modes")
        return cls(states, modes, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "required_position_states": list(self.required_position_states),
            "adjustment_modes": list(self.adjustment_modes),
            "mode": "DETERMINISTIC_REFERENCE_PROTECTION_RATCHET",
            "stop_ratchet": "MONOTONIC_TIGHTEN_ONLY",
            "take_profit_change": "P21B_TAKE_PROFIT_PRESERVED",
            "network_mode": "DISABLED",
            "live_execution_authority": False,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class DynamicExitRequest:
    position_record_id: str
    position_id: str
    mode: str
    reference_price_scaled: int
    requested_stop_price_scaled: int
    exit_decision_id: str
    source_ref: str = "DETERMINISTIC_REFERENCE"

    def validate(self, policy: DynamicExitPolicy) -> None:
        _sha256_hex(self.position_record_id, field="position_record_id")
        _text(self.position_id, field="position_id")
        if self.mode not in policy.adjustment_modes:
            raise DynamicExitError("unsupported dynamic-exit mode")
        _positive_int(self.reference_price_scaled, field="reference_price_scaled")
        _positive_int(self.requested_stop_price_scaled, field="requested_stop_price_scaled")
        _sha256_hex(self.exit_decision_id, field="exit_decision_id")
        _text(self.source_ref, field="source_ref")

    def payload(self) -> dict[str, object]:
        return {
            "position_record_id": self.position_record_id.lower(),
            "position_id": self.position_id,
            "mode": self.mode,
            "reference_price_scaled": self.reference_price_scaled,
            "requested_stop_price_scaled": self.requested_stop_price_scaled,
            "exit_decision_id": self.exit_decision_id.lower(),
            "source_ref": self.source_ref,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DynamicProtectionPlan:
    policy_id: str
    request_id: str
    position_record_id: str
    position_id: str
    position_state: str
    side: str
    mode: str
    open_quantity_scaled: int
    price_scale: int
    entry_price_scaled: int
    reference_price_scaled: int
    take_profit_price_scaled: int
    previous_stop_price_scaled: int
    requested_stop_price_scaled: int
    tightening_distance_scaled: int
    exit_decision_id: str
    parent_protection_plan_id: str
    take_profit_preserved: bool = True
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
            "mode": self.mode,
            "open_quantity_scaled": self.open_quantity_scaled,
            "price_scale": self.price_scale,
            "entry_price_scaled": self.entry_price_scaled,
            "reference_price_scaled": self.reference_price_scaled,
            "take_profit_price_scaled": self.take_profit_price_scaled,
            "previous_stop_price_scaled": self.previous_stop_price_scaled,
            "requested_stop_price_scaled": self.requested_stop_price_scaled,
            "tightening_distance_scaled": self.tightening_distance_scaled,
            "exit_decision_id": self.exit_decision_id,
            "parent_protection_plan_id": self.parent_protection_plan_id,
            "take_profit_preserved": self.take_profit_preserved,
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


class DynamicExitPlanner:
    def __init__(self, policy: DynamicExitPolicy) -> None:
        self._policy = policy

    def plan(
        self,
        position: PositionStateRecord,
        protection: ProtectionPlan,
        request: DynamicExitRequest,
    ) -> DynamicProtectionPlan:
        request.validate(self._policy)
        if position.state not in self._policy.required_position_states:
            raise DynamicExitError("dynamic exit requires OPEN or PARTIALLY_CLOSED position")
        if position.open_quantity_scaled <= 0:
            raise DynamicExitError("dynamic exit requires positive open quantity")
        if request.position_id != position.position_id:
            raise DynamicExitError("position_id mismatch")
        if request.position_record_id.lower() != position.record_id:
            raise DynamicExitError("request is not bound to exact canonical position record")

        if protection.position_record_id != position.record_id:
            raise DynamicExitError("P21-B protection is stale for current canonical position record")
        if protection.position_id != position.position_id:
            raise DynamicExitError("P21-B protection position_id mismatch")
        if protection.position_state != position.state:
            raise DynamicExitError("P21-B protection position state mismatch")
        if protection.side != position.side:
            raise DynamicExitError("P21-B protection side mismatch")
        if protection.open_quantity_scaled != position.open_quantity_scaled:
            raise DynamicExitError("P21-B protection open quantity mismatch")
        if protection.price_scale != position.price_scale:
            raise DynamicExitError("P21-B protection price scale mismatch")
        if protection.entry_price_scaled != position.average_entry_price_scaled_floor:
            raise DynamicExitError("P21-B protection entry does not match canonical position")
        if (
            protection.source_mode != "REFERENCE_ONLY"
            or protection.real_venue_query
            or protection.network_mode != "DISABLED"
            or protection.external_order_submission
            or protection.external_order_mutation
            or protection.live_execution_authority
        ):
            raise DynamicExitError("P21-B protection authority boundary mismatch")

        reference = request.reference_price_scaled
        new_stop = request.requested_stop_price_scaled
        old_stop = protection.stop_loss_price_scaled
        entry = position.average_entry_price_scaled_floor
        target = protection.take_profit_price_scaled

        if position.side == "LONG":
            if new_stop <= old_stop:
                raise DynamicExitError("LONG protective stop must tighten strictly upward")
            if new_stop >= reference:
                raise DynamicExitError("LONG stop must remain strictly below caller reference price")
            if reference >= target:
                raise DynamicExitError("LONG reference price must remain strictly before current TP trigger")
            tightening = new_stop - old_stop
            if request.mode == "BREAK_EVEN":
                if new_stop != entry:
                    raise DynamicExitError("LONG BREAK_EVEN stop must equal canonical entry")
                if reference <= entry:
                    raise DynamicExitError("LONG BREAK_EVEN requires favorable reference price above entry")
        else:
            if new_stop >= old_stop:
                raise DynamicExitError("SHORT protective stop must tighten strictly downward")
            if new_stop <= reference:
                raise DynamicExitError("SHORT stop must remain strictly above caller reference price")
            if reference <= target:
                raise DynamicExitError("SHORT reference price must remain strictly before current TP trigger")
            tightening = old_stop - new_stop
            if request.mode == "BREAK_EVEN":
                if new_stop != entry:
                    raise DynamicExitError("SHORT BREAK_EVEN stop must equal canonical entry")
                if reference >= entry:
                    raise DynamicExitError("SHORT BREAK_EVEN requires favorable reference price below entry")

        return DynamicProtectionPlan(
            policy_id=self._policy.policy_id,
            request_id=request.request_id,
            position_record_id=position.record_id,
            position_id=position.position_id,
            position_state=position.state,
            side=position.side,
            mode=request.mode,
            open_quantity_scaled=position.open_quantity_scaled,
            price_scale=position.price_scale,
            entry_price_scaled=entry,
            reference_price_scaled=reference,
            take_profit_price_scaled=target,
            previous_stop_price_scaled=old_stop,
            requested_stop_price_scaled=new_stop,
            tightening_distance_scaled=tightening,
            exit_decision_id=request.exit_decision_id.lower(),
            parent_protection_plan_id=protection.plan_id,
        )
