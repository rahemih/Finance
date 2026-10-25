from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast

from .canonical_position import PositionStateRecord


class BrokerReconciliationError(ValueError):
    """P21-F deterministic position reconciliation invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrokerReconciliationError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BrokerReconciliationError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise BrokerReconciliationError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class BrokerReconciliationPolicy:
    canonical_position_states: tuple[str, ...]
    observation_statuses: tuple[str, ...]
    verdicts: tuple[str, ...]

    @classmethod
    def from_path(cls, path: Path) -> "BrokerReconciliationPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BrokerReconciliationError(f"invalid P21-F policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise BrokerReconciliationError("P21-F policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21F_BROKER_RECONCILIATION_POLICY",
            "task_id": "FIN-P21-WF-001",
            "mode": "DETERMINISTIC_REFERENCE_POSITION_RECONCILIATION",
            "comparison_mode": "EXACT_FIXED_POINT_NO_HIDDEN_TOLERANCE",
            "observation_source": "CALLER_SUPPLIED_REFERENCE_OR_SANDBOX_ONLY",
            "require_exact_position_record_id": True,
            "require_observation_not_older_than_canonical_record": True,
            "mismatch_disposition": "SAFE_HOLD_NEW_ENTRY_BLOCK",
            "mismatch_action": "MANUAL_GOVERNED_RECONCILIATION_REQUIRED",
            "auto_repair": False,
            "auto_flatten": False,
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
                raise BrokerReconciliationError(f"P21-F policy mismatch: {key}")

        def strings(key: str) -> tuple[str, ...]:
            value = raw.get(key)
            if not isinstance(value, list):
                raise BrokerReconciliationError(f"{key} must be an array")
            return tuple(_text(item, field=key) for item in cast(list[object], value))

        states = strings("canonical_position_states")
        statuses = strings("observation_statuses")
        verdicts = strings("verdicts")
        if states != ("OPEN", "PARTIALLY_CLOSED", "CLOSED"):
            raise BrokerReconciliationError("invalid canonical_position_states")
        if statuses != ("OPEN", "NOT_FOUND"):
            raise BrokerReconciliationError("invalid observation_statuses")
        return cls(states, statuses, verdicts)

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "canonical_position_states": list(self.canonical_position_states),
            "observation_statuses": list(self.observation_statuses),
            "verdicts": list(self.verdicts),
            "comparison_mode": "EXACT_FIXED_POINT_NO_HIDDEN_TOLERANCE",
            "mismatch_disposition": "SAFE_HOLD_NEW_ENTRY_BLOCK",
            "auto_repair": False,
            "auto_flatten": False,
            "live_execution_authority": False,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class ReferenceBrokerPositionObservation:
    position_record_id: str
    position_id: str
    asset_id: str
    market: str
    status: str
    quantity_scale: int
    price_scale: int
    observed_at_ns: int
    source_ref: str
    side: str | None = None
    open_quantity_scaled: int = 0
    average_entry_price_scaled_floor: int | None = None
    external_position_ref: str | None = None

    def validate(self, policy: BrokerReconciliationPolicy) -> None:
        _sha256_hex(self.position_record_id, field="position_record_id")
        _text(self.position_id, field="position_id")
        _text(self.asset_id, field="asset_id")
        _text(self.market, field="market")
        if self.status not in policy.observation_statuses:
            raise BrokerReconciliationError("unsupported observation status")
        _positive_int(self.quantity_scale, field="quantity_scale")
        _positive_int(self.price_scale, field="price_scale")
        _positive_int(self.observed_at_ns, field="observed_at_ns")
        _text(self.source_ref, field="source_ref")
        if self.external_position_ref is not None:
            _text(self.external_position_ref, field="external_position_ref")

        if self.status == "OPEN":
            if self.side not in {"LONG", "SHORT"}:
                raise BrokerReconciliationError("OPEN observation requires LONG or SHORT side")
            _positive_int(self.open_quantity_scaled, field="open_quantity_scaled")
            if self.average_entry_price_scaled_floor is None:
                raise BrokerReconciliationError("OPEN observation requires average entry")
            _positive_int(self.average_entry_price_scaled_floor, field="average_entry_price_scaled_floor")
        else:
            if self.side is not None:
                raise BrokerReconciliationError("NOT_FOUND observation side must be null")
            if self.open_quantity_scaled != 0:
                raise BrokerReconciliationError("NOT_FOUND observation quantity must be zero")
            if self.average_entry_price_scaled_floor is not None:
                raise BrokerReconciliationError("NOT_FOUND observation average entry must be null")

    def payload(self) -> dict[str, object]:
        return {
            "position_record_id": self.position_record_id.lower(),
            "position_id": self.position_id,
            "asset_id": self.asset_id,
            "market": self.market,
            "status": self.status,
            "quantity_scale": self.quantity_scale,
            "price_scale": self.price_scale,
            "observed_at_ns": self.observed_at_ns,
            "source_ref": self.source_ref,
            "side": self.side,
            "open_quantity_scaled": self.open_quantity_scaled,
            "average_entry_price_scaled_floor": self.average_entry_price_scaled_floor,
            "external_position_ref": self.external_position_ref,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionReconciliationReport:
    policy_id: str
    observation_id: str
    position_record_id: str
    position_id: str
    canonical_state: str
    observation_status: str
    verdict: str
    mismatch_fields: tuple[str, ...]
    canonical_source_oms_record_id: str
    canonical_source_reconciliation_report_id: str
    safe_hold_required: bool
    new_entry_block_required: bool
    action: str
    comparison_mode: str = "EXACT_FIXED_POINT_NO_HIDDEN_TOLERANCE"
    source_mode: str = "REFERENCE_OR_SANDBOX_ONLY"
    auto_repair: bool = False
    auto_flatten: bool = False
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
            "observation_id": self.observation_id,
            "position_record_id": self.position_record_id,
            "position_id": self.position_id,
            "canonical_state": self.canonical_state,
            "observation_status": self.observation_status,
            "verdict": self.verdict,
            "mismatch_fields": list(self.mismatch_fields),
            "canonical_source_oms_record_id": self.canonical_source_oms_record_id,
            "canonical_source_reconciliation_report_id": self.canonical_source_reconciliation_report_id,
            "safe_hold_required": self.safe_hold_required,
            "new_entry_block_required": self.new_entry_block_required,
            "action": self.action,
            "comparison_mode": self.comparison_mode,
            "source_mode": self.source_mode,
            "auto_repair": self.auto_repair,
            "auto_flatten": self.auto_flatten,
            "real_venue_query": self.real_venue_query,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "external_order_mutation": self.external_order_mutation,
            "automatic_oms_mutation": self.automatic_oms_mutation,
            "canonical_position_mutation": self.canonical_position_mutation,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def report_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class BrokerPositionReconciler:
    def __init__(self, policy: BrokerReconciliationPolicy) -> None:
        self._policy = policy

    def reconcile(
        self,
        position: PositionStateRecord,
        observation: ReferenceBrokerPositionObservation,
    ) -> PositionReconciliationReport:
        observation.validate(self._policy)
        if position.state not in self._policy.canonical_position_states:
            raise BrokerReconciliationError("unsupported canonical position state")
        if observation.position_record_id.lower() != position.record_id:
            raise BrokerReconciliationError("observation is not bound to exact current canonical position record")
        if observation.observed_at_ns < position.occurred_at_ns:
            raise BrokerReconciliationError("observation predates current canonical position record")

        identity_mismatches: list[str] = []
        if observation.position_id != position.position_id:
            identity_mismatches.append("position_id")
        if observation.asset_id != position.asset_id:
            identity_mismatches.append("asset_id")
        if observation.market != position.market:
            identity_mismatches.append("market")
        if observation.quantity_scale != position.quantity_scale:
            identity_mismatches.append("quantity_scale")
        if observation.price_scale != position.price_scale:
            identity_mismatches.append("price_scale")

        mismatch_fields = list(identity_mismatches)
        verdict = "MATCHED"

        if identity_mismatches:
            verdict = "IDENTITY_MISMATCH"
        elif position.state == "CLOSED":
            if observation.status == "OPEN":
                mismatch_fields.append("external_status")
                verdict = "EXTERNAL_EXPOSURE_CONFLICT"
        elif observation.status == "NOT_FOUND":
            mismatch_fields.append("external_status")
            verdict = "MISSING_EXTERNAL_POSITION"
        else:
            if observation.side != position.side:
                mismatch_fields.append("side")
            if observation.open_quantity_scaled != position.open_quantity_scaled:
                mismatch_fields.append("open_quantity_scaled")
            if observation.average_entry_price_scaled_floor != position.average_entry_price_scaled_floor:
                mismatch_fields.append("average_entry_price_scaled_floor")

            if len(mismatch_fields) > 1:
                verdict = "MULTIPLE_MISMATCH"
            elif mismatch_fields == ["side"]:
                verdict = "SIDE_MISMATCH"
            elif mismatch_fields == ["open_quantity_scaled"]:
                verdict = "QUANTITY_MISMATCH"
            elif mismatch_fields == ["average_entry_price_scaled_floor"]:
                verdict = "ENTRY_PRICE_MISMATCH"

        if verdict not in self._policy.verdicts:
            raise BrokerReconciliationError("computed verdict is outside governed taxonomy")

        mismatch = verdict != "MATCHED"
        return PositionReconciliationReport(
            policy_id=self._policy.policy_id,
            observation_id=observation.observation_id,
            position_record_id=position.record_id,
            position_id=position.position_id,
            canonical_state=position.state,
            observation_status=observation.status,
            verdict=verdict,
            mismatch_fields=tuple(mismatch_fields),
            canonical_source_oms_record_id=position.source_oms_record_id,
            canonical_source_reconciliation_report_id=position.source_reconciliation_report_id,
            safe_hold_required=mismatch,
            new_entry_block_required=mismatch,
            action="MANUAL_GOVERNED_RECONCILIATION_REQUIRED" if mismatch else "NONE",
        )
