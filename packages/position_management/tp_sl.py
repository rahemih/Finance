from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast

from .canonical_position import PositionStateRecord


class TpSlError(ValueError):
    """P21-B deterministic TP/SL protection-plan invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TpSlError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TpSlError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise TpSlError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class TpSlPolicy:
    required_position_states: tuple[str, ...]
    sides: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "TpSlPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TpSlError(f"invalid P21-B policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise TpSlError("P21-B policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version":"1.0",
            "kind":"NEXUS_QUANT_P21B_TP_SL_POLICY",
            "task_id":"FIN-P21-WB-001",
            "mode":"DETERMINISTIC_REFERENCE_PROTECTION_PLAN",
            "require_take_profit":True,
            "require_stop_loss":True,
            "price_domain":"POSITIVE_FIXED_POINT_INTEGER",
            "long_geometry":"STOP_LT_ENTRY_LT_TARGET",
            "short_geometry":"TARGET_LT_ENTRY_LT_STOP",
            "source_mode":"CALLER_SUPPLIED_LEVELS_VALIDATED_AGAINST_CANONICAL_POSITION",
            "real_venue_query":False,
            "credential_mode":"NONE",
            "network_mode":"DISABLED",
            "external_order_submission":False,
            "external_order_mutation":False,
            "automatic_oms_mutation":False,
            "live_execution_validated":False,
            "live_execution_authority":False,
            "live_trading":"DISABLED",
            "auto_trading":"DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise TpSlError(f"P21-B policy mismatch: {key}")
        states_value=raw.get("required_position_states")
        sides_value=raw.get("sides")
        if not isinstance(states_value,list) or tuple(states_value)!=("OPEN","PARTIALLY_CLOSED"):
            raise TpSlError("invalid required_position_states")
        if not isinstance(sides_value,list) or tuple(sides_value)!=("LONG","SHORT"):
            raise TpSlError("invalid sides")
        return cls(("OPEN","PARTIALLY_CLOSED"),("LONG","SHORT"),"DISABLED","DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "required_position_states":list(self.required_position_states),
            "sides":list(self.sides),
            "mode":"DETERMINISTIC_REFERENCE_PROTECTION_PLAN",
            "source_mode":"CALLER_SUPPLIED_LEVELS_VALIDATED_AGAINST_CANONICAL_POSITION",
            "network_mode":"DISABLED",
            "live_execution_authority":False,
            "live_trading":self.live_trading,
            "auto_trading":self.auto_trading,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class TpSlRequest:
    position_record_id: str
    position_id: str
    side: str
    entry_price_scaled: int
    take_profit_price_scaled: int
    stop_loss_price_scaled: int
    signal_decision_id: str
    risk_validation_id: str
    source_ref: str = "DETERMINISTIC_REFERENCE"

    def validate(self, policy: TpSlPolicy) -> None:
        _sha256_hex(self.position_record_id, field="position_record_id")
        _text(self.position_id, field="position_id")
        if self.side not in policy.sides:
            raise TpSlError("unsupported side")
        _positive_int(self.entry_price_scaled, field="entry_price_scaled")
        _positive_int(self.take_profit_price_scaled, field="take_profit_price_scaled")
        _positive_int(self.stop_loss_price_scaled, field="stop_loss_price_scaled")
        _sha256_hex(self.signal_decision_id, field="signal_decision_id")
        _sha256_hex(self.risk_validation_id, field="risk_validation_id")
        _text(self.source_ref, field="source_ref")
        if self.side == "LONG":
            if not self.stop_loss_price_scaled < self.entry_price_scaled < self.take_profit_price_scaled:
                raise TpSlError("LONG TP/SL geometry must be stop < entry < target")
        else:
            if not self.take_profit_price_scaled < self.entry_price_scaled < self.stop_loss_price_scaled:
                raise TpSlError("SHORT TP/SL geometry must be target < entry < stop")

    def payload(self) -> dict[str, object]:
        return {
            "position_record_id":self.position_record_id.lower(),
            "position_id":self.position_id,
            "side":self.side,
            "entry_price_scaled":self.entry_price_scaled,
            "take_profit_price_scaled":self.take_profit_price_scaled,
            "stop_loss_price_scaled":self.stop_loss_price_scaled,
            "signal_decision_id":self.signal_decision_id.lower(),
            "risk_validation_id":self.risk_validation_id.lower(),
            "source_ref":self.source_ref,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ProtectionPlan:
    policy_id: str
    request_id: str
    position_record_id: str
    position_id: str
    position_state: str
    side: str
    open_quantity_scaled: int
    price_scale: int
    entry_price_scaled: int
    take_profit_price_scaled: int
    stop_loss_price_scaled: int
    target_distance_scaled: int
    stop_distance_scaled: int
    signal_decision_id: str
    risk_validation_id: str
    source_mode: str = "REFERENCE_ONLY"
    real_venue_query: bool = False
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    external_order_mutation: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id":self.policy_id,
            "request_id":self.request_id,
            "position_record_id":self.position_record_id,
            "position_id":self.position_id,
            "position_state":self.position_state,
            "side":self.side,
            "open_quantity_scaled":self.open_quantity_scaled,
            "price_scale":self.price_scale,
            "entry_price_scaled":self.entry_price_scaled,
            "take_profit_price_scaled":self.take_profit_price_scaled,
            "stop_loss_price_scaled":self.stop_loss_price_scaled,
            "target_distance_scaled":self.target_distance_scaled,
            "stop_distance_scaled":self.stop_distance_scaled,
            "signal_decision_id":self.signal_decision_id,
            "risk_validation_id":self.risk_validation_id,
            "source_mode":self.source_mode,
            "real_venue_query":self.real_venue_query,
            "network_mode":self.network_mode,
            "external_order_submission":self.external_order_submission,
            "external_order_mutation":self.external_order_mutation,
            "live_execution_authority":self.live_execution_authority,
        }

    @property
    def plan_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class TpSlPlanner:
    def __init__(self, policy: TpSlPolicy) -> None:
        self._policy=policy

    def plan(self, position: PositionStateRecord, request: TpSlRequest) -> ProtectionPlan:
        request.validate(self._policy)
        if position.state not in self._policy.required_position_states:
            raise TpSlError("TP/SL requires OPEN or PARTIALLY_CLOSED position")
        if position.open_quantity_scaled <= 0:
            raise TpSlError("TP/SL requires positive open quantity")
        if request.position_id != position.position_id:
            raise TpSlError("position_id mismatch")
        if request.position_record_id.lower() != position.record_id:
            raise TpSlError("TP/SL request is not bound to exact canonical position record")
        if request.side != position.side:
            raise TpSlError("position side mismatch")
        if request.entry_price_scaled != position.average_entry_price_scaled_floor:
            raise TpSlError("entry price must match canonical average-entry floor")

        if request.side == "LONG":
            target_distance=request.take_profit_price_scaled-request.entry_price_scaled
            stop_distance=request.entry_price_scaled-request.stop_loss_price_scaled
        else:
            target_distance=request.entry_price_scaled-request.take_profit_price_scaled
            stop_distance=request.stop_loss_price_scaled-request.entry_price_scaled

        return ProtectionPlan(
            policy_id=self._policy.policy_id,
            request_id=request.request_id,
            position_record_id=position.record_id,
            position_id=position.position_id,
            position_state=position.state,
            side=position.side,
            open_quantity_scaled=position.open_quantity_scaled,
            price_scale=position.price_scale,
            entry_price_scaled=request.entry_price_scaled,
            take_profit_price_scaled=request.take_profit_price_scaled,
            stop_loss_price_scaled=request.stop_loss_price_scaled,
            target_distance_scaled=target_distance,
            stop_distance_scaled=stop_distance,
            signal_decision_id=request.signal_decision_id.lower(),
            risk_validation_id=request.risk_validation_id.lower(),
        )
