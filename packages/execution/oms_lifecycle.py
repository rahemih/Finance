from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class OmsLifecycleError(ValueError):
    """P20-D deterministic OMS lifecycle invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OmsLifecycleError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OmsLifecycleError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OmsLifecycleError(f"{field} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class OmsLifecyclePolicy:
    states: tuple[str, ...]
    events: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "OmsLifecyclePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise OmsLifecycleError(f"invalid P20-D policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise OmsLifecycleError("P20-D policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20D_OMS_LIFECYCLE_POLICY",
            "task_id": "FIN-P20-WD-001",
            "mode": "DETERMINISTIC_OMS_LIFECYCLE",
            "idempotency_owner": "P20-E",
            "retry_owner": "P20-F",
            "reconciliation_owner": "P20-G",
            "execution_quality_owner": "P20-H",
            "simulation_gate_owner": "P20-I",
            "position_management_owner": "P21",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise OmsLifecycleError(f"P20-D policy mismatch: {key}")

        states_value = raw.get("states")
        events_value = raw.get("events")
        if not isinstance(states_value, list) or not isinstance(events_value, list):
            raise OmsLifecycleError("P20-D state/event taxonomies must be lists")
        states = tuple(_text(v, field="states") for v in cast(list[object], states_value))
        events = tuple(_text(v, field="events") for v in cast(list[object], events_value))
        if states != (
            "CREATED",
            "SUBMIT_PENDING",
            "OPEN",
            "PARTIALLY_FILLED",
            "CANCEL_PENDING",
            "FILLED",
            "CANCELED",
            "REJECTED",
            "EXPIRED",
        ):
            raise OmsLifecycleError("invalid P20-D state taxonomy")
        if events != (
            "SUBMIT",
            "ACK",
            "REJECT",
            "PARTIAL_FILL",
            "FILL",
            "CANCEL_REQUEST",
            "CANCEL_ACK",
            "EXPIRE",
        ):
            raise OmsLifecycleError("invalid P20-D event taxonomy")
        return cls(states=states, events=events, live_trading="DISABLED", auto_trading="DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "states": list(self.states),
                    "events": list(self.events),
                    "idempotency_owner": "P20-E",
                    "retry_owner": "P20-F",
                    "reconciliation_owner": "P20-G",
                    "execution_quality_owner": "P20-H",
                    "simulation_gate_owner": "P20-I",
                    "position_management_owner": "P21",
                    "credential_mode": "NONE",
                    "network_mode": "DISABLED",
                    "external_order_submission": False,
                    "live_execution_authority": False,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class OmsOrderSpec:
    order_id: str
    client_order_id: str
    asset_id: str
    market: str
    side: str
    total_quantity_scaled: int
    quantity_scale: int

    def validate(self) -> None:
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        _text(self.asset_id, field="asset_id")
        if self.market not in ("CRYPTO", "FOREX"):
            raise OmsLifecycleError("unsupported OMS market")
        if self.side not in ("BUY", "SELL"):
            raise OmsLifecycleError("unsupported OMS side")
        _positive_int(self.total_quantity_scaled, field="total_quantity_scaled")
        _positive_int(self.quantity_scale, field="quantity_scale")

    def payload(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "asset_id": self.asset_id,
            "market": self.market,
            "side": self.side,
            "total_quantity_scaled": self.total_quantity_scaled,
            "quantity_scale": self.quantity_scale,
        }

    @property
    def spec_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class OmsLifecycleEvent:
    order_id: str
    sequence: int
    occurred_at_ns: int
    event_type: str
    fill_quantity_scaled: int = 0
    source_ref: str = "DETERMINISTIC_REFERENCE"

    def validate(self, policy: OmsLifecyclePolicy) -> None:
        _text(self.order_id, field="order_id")
        _positive_int(self.sequence, field="sequence")
        _non_negative_int(self.occurred_at_ns, field="occurred_at_ns")
        if self.event_type not in policy.events:
            raise OmsLifecycleError("unsupported OMS lifecycle event")
        _text(self.source_ref, field="source_ref")
        _non_negative_int(self.fill_quantity_scaled, field="fill_quantity_scaled")
        if self.event_type in ("PARTIAL_FILL", "FILL"):
            _positive_int(self.fill_quantity_scaled, field="fill_quantity_scaled")
        elif self.fill_quantity_scaled != 0:
            raise OmsLifecycleError("non-fill event cannot carry fill quantity")

    def payload(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "sequence": self.sequence,
            "occurred_at_ns": self.occurred_at_ns,
            "event_type": self.event_type,
            "fill_quantity_scaled": self.fill_quantity_scaled,
            "source_ref": self.source_ref,
        }

    @property
    def event_hash(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class OmsStateRecord:
    policy_id: str
    spec_id: str
    order_id: str
    client_order_id: str
    asset_id: str
    market: str
    side: str
    total_quantity_scaled: int
    quantity_scale: int
    state: str
    cumulative_filled_scaled: int
    remaining_quantity_scaled: int
    sequence: int
    occurred_at_ns: int
    event_type: str
    source_event_hash: str
    previous_record_id: str | None
    credential_mode: str = "NONE"
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    idempotency_authority: bool = False
    retry_authority: bool = False
    reconciliation_authority: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "spec_id": self.spec_id,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "asset_id": self.asset_id,
            "market": self.market,
            "side": self.side,
            "total_quantity_scaled": self.total_quantity_scaled,
            "quantity_scale": self.quantity_scale,
            "state": self.state,
            "cumulative_filled_scaled": self.cumulative_filled_scaled,
            "remaining_quantity_scaled": self.remaining_quantity_scaled,
            "sequence": self.sequence,
            "occurred_at_ns": self.occurred_at_ns,
            "event_type": self.event_type,
            "source_event_hash": self.source_event_hash,
            "previous_record_id": self.previous_record_id,
            "credential_mode": self.credential_mode,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "idempotency_authority": self.idempotency_authority,
            "retry_authority": self.retry_authority,
            "reconciliation_authority": self.reconciliation_authority,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class OmsLifecycleEngine:
    _TERMINAL = frozenset({"FILLED", "CANCELED", "REJECTED", "EXPIRED"})

    def __init__(self, policy: OmsLifecyclePolicy) -> None:
        self._policy = policy
        self._specs: dict[str, OmsOrderSpec] = {}
        self._current: dict[str, OmsStateRecord] = {}

    def create_order(self, spec: OmsOrderSpec, *, created_at_ns: int) -> OmsStateRecord:
        spec.validate()
        _non_negative_int(created_at_ns, field="created_at_ns")
        if spec.order_id in self._current:
            raise OmsLifecycleError("order already exists in OMS lifecycle")
        create_hash = hashlib.sha256(
            _canonical_bytes(
                {
                    "kind": "OMS_CREATE",
                    "spec_id": spec.spec_id,
                    "created_at_ns": created_at_ns,
                }
            )
        ).hexdigest()
        record = OmsStateRecord(
            policy_id=self._policy.policy_id,
            spec_id=spec.spec_id,
            order_id=spec.order_id,
            client_order_id=spec.client_order_id,
            asset_id=spec.asset_id,
            market=spec.market,
            side=spec.side,
            total_quantity_scaled=spec.total_quantity_scaled,
            quantity_scale=spec.quantity_scale,
            state="CREATED",
            cumulative_filled_scaled=0,
            remaining_quantity_scaled=spec.total_quantity_scaled,
            sequence=0,
            occurred_at_ns=created_at_ns,
            event_type="CREATE",
            source_event_hash=create_hash,
            previous_record_id=None,
        )
        self._specs[spec.order_id] = spec
        self._current[spec.order_id] = record
        return record

    def apply(self, event: OmsLifecycleEvent) -> OmsStateRecord:
        event.validate(self._policy)
        try:
            current = self._current[event.order_id]
            spec = self._specs[event.order_id]
        except KeyError as exc:
            raise OmsLifecycleError("unknown OMS order") from exc

        if current.state in self._TERMINAL:
            raise OmsLifecycleError("terminal OMS state cannot transition")
        if event.sequence != current.sequence + 1:
            raise OmsLifecycleError("OMS lifecycle sequence must be contiguous")
        if event.occurred_at_ns < current.occurred_at_ns:
            raise OmsLifecycleError("OMS event time cannot regress")

        next_state = self._next_state(current.state, event.event_type)
        cumulative = current.cumulative_filled_scaled
        if event.event_type == "PARTIAL_FILL":
            cumulative += event.fill_quantity_scaled
            if cumulative >= spec.total_quantity_scaled:
                raise OmsLifecycleError("PARTIAL_FILL must leave positive remaining quantity")
        elif event.event_type == "FILL":
            cumulative += event.fill_quantity_scaled
            if cumulative != spec.total_quantity_scaled:
                raise OmsLifecycleError("FILL must exactly consume remaining quantity")
        elif cumulative > spec.total_quantity_scaled:
            raise OmsLifecycleError("OMS cumulative fill cannot exceed order quantity")

        remaining = spec.total_quantity_scaled - cumulative
        if remaining < 0:
            raise OmsLifecycleError("OMS overfill detected")

        record = OmsStateRecord(
            policy_id=self._policy.policy_id,
            spec_id=spec.spec_id,
            order_id=spec.order_id,
            client_order_id=spec.client_order_id,
            asset_id=spec.asset_id,
            market=spec.market,
            side=spec.side,
            total_quantity_scaled=spec.total_quantity_scaled,
            quantity_scale=spec.quantity_scale,
            state=next_state,
            cumulative_filled_scaled=cumulative,
            remaining_quantity_scaled=remaining,
            sequence=event.sequence,
            occurred_at_ns=event.occurred_at_ns,
            event_type=event.event_type,
            source_event_hash=event.event_hash,
            previous_record_id=current.record_id,
        )
        self._current[event.order_id] = record
        return record

    def current(self, order_id: str) -> OmsStateRecord:
        try:
            return self._current[order_id]
        except KeyError as exc:
            raise OmsLifecycleError("unknown OMS order") from exc

    def snapshot(self) -> dict[str, object]:
        orders = [self._current[key].payload() | {"record_id": self._current[key].record_id} for key in sorted(self._current)]
        payload = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20D_OMS_SNAPSHOT",
            "task_id": "FIN-P20-WD-001",
            "policy_id": self._policy.policy_id,
            "orders": orders,
            "authority": {
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "external_order_submission": False,
                "idempotency_authority": False,
                "retry_authority": False,
                "reconciliation_authority": False,
                "live_execution_authority": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        return payload | {"snapshot_id": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}

    @staticmethod
    def _next_state(state: str, event_type: str) -> str:
        transitions: dict[tuple[str, str], str] = {
            ("CREATED", "SUBMIT"): "SUBMIT_PENDING",
            ("SUBMIT_PENDING", "ACK"): "OPEN",
            ("SUBMIT_PENDING", "REJECT"): "REJECTED",
            ("OPEN", "PARTIAL_FILL"): "PARTIALLY_FILLED",
            ("OPEN", "FILL"): "FILLED",
            ("OPEN", "CANCEL_REQUEST"): "CANCEL_PENDING",
            ("OPEN", "EXPIRE"): "EXPIRED",
            ("PARTIALLY_FILLED", "PARTIAL_FILL"): "PARTIALLY_FILLED",
            ("PARTIALLY_FILLED", "FILL"): "FILLED",
            ("PARTIALLY_FILLED", "CANCEL_REQUEST"): "CANCEL_PENDING",
            ("PARTIALLY_FILLED", "EXPIRE"): "EXPIRED",
            ("CANCEL_PENDING", "PARTIAL_FILL"): "CANCEL_PENDING",
            ("CANCEL_PENDING", "FILL"): "FILLED",
            ("CANCEL_PENDING", "CANCEL_ACK"): "CANCELED",
        }
        try:
            return transitions[(state, event_type)]
        except KeyError as exc:
            raise OmsLifecycleError(
                f"illegal OMS transition: {state} + {event_type}"
            ) from exc
