from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast


class CanonicalPositionError(ValueError):
    """P21-A deterministic canonical-position invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalPositionError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CanonicalPositionError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CanonicalPositionError(f"{field} must be a non-negative integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise CanonicalPositionError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class CanonicalPositionPolicy:
    markets: tuple[str, ...]
    sides: tuple[str, ...]
    states: tuple[str, ...]
    event_types: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "CanonicalPositionPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CanonicalPositionError(f"invalid P21-A policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise CanonicalPositionError("P21-A policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21A_CANONICAL_POSITION_STATE_POLICY",
            "task_id": "FIN-P21-WA-001",
            "mode": "DETERMINISTIC_EXECUTION_DERIVED_POSITION_STATE",
            "source_mode": "EXPLICIT_EXECUTION_REFERENCE_EVIDENCE_ONLY",
            "required_upstream_gate": "G11_EXECUTION_VALIDATED",
            "required_upstream_gate_scope": "REFERENCE_SIMULATION_EXECUTION_VALIDATION",
            "allow_scale_in_before_reduction": True,
            "allow_scale_in_after_reduction": False,
            "allow_reopen_after_closed": False,
            "require_oms_record_lineage": True,
            "require_reconciliation_lineage": True,
            "duplicate_fill_policy": "FAIL_CLOSED",
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise CanonicalPositionError(f"P21-A policy mismatch: {key}")
        def parse_tuple(key: str) -> tuple[str, ...]:
            value = raw.get(key)
            if not isinstance(value, list) or not value:
                raise CanonicalPositionError(f"{key} must be a non-empty list")
            items = cast(list[object], value)
            parsed = tuple(_text(item, field=key) for item in items)
            if len(set(parsed)) != len(parsed):
                raise CanonicalPositionError(f"{key} cannot contain duplicates")
            return parsed
        markets = parse_tuple("markets")
        sides = parse_tuple("sides")
        states = parse_tuple("states")
        event_types = parse_tuple("event_types")
        if markets != ("CRYPTO", "FOREX"):
            raise CanonicalPositionError("invalid P21-A market taxonomy")
        if sides != ("LONG", "SHORT"):
            raise CanonicalPositionError("invalid P21-A side taxonomy")
        if states != ("OPEN", "PARTIALLY_CLOSED", "CLOSED"):
            raise CanonicalPositionError("invalid P21-A state taxonomy")
        if event_types != ("OPEN_FILL", "ADD_FILL", "REDUCE_FILL"):
            raise CanonicalPositionError("invalid P21-A event taxonomy")
        return cls(markets, sides, states, event_types, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "markets": list(self.markets),
            "sides": list(self.sides),
            "states": list(self.states),
            "event_types": list(self.event_types),
            "source_mode": "EXPLICIT_EXECUTION_REFERENCE_EVIDENCE_ONLY",
            "required_upstream_gate": "G11_EXECUTION_VALIDATED",
            "allow_scale_in_before_reduction": True,
            "allow_scale_in_after_reduction": False,
            "allow_reopen_after_closed": False,
            "duplicate_fill_policy": "FAIL_CLOSED",
            "network_mode": "DISABLED",
            "live_execution_authority": False,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionSpec:
    position_id: str
    portfolio_id: str
    strategy_id: str
    asset_id: str
    market: str
    side: str
    quantity_scale: int
    price_scale: int
    risk_validation_id: str
    pretrade_firewall_id: str

    def validate(self, policy: CanonicalPositionPolicy) -> None:
        _text(self.position_id, field="position_id")
        _text(self.portfolio_id, field="portfolio_id")
        _text(self.strategy_id, field="strategy_id")
        _text(self.asset_id, field="asset_id")
        if self.market not in policy.markets:
            raise CanonicalPositionError("unsupported position market")
        if self.side not in policy.sides:
            raise CanonicalPositionError("unsupported position side")
        _positive_int(self.quantity_scale, field="quantity_scale")
        _positive_int(self.price_scale, field="price_scale")
        _sha256_hex(self.risk_validation_id, field="risk_validation_id")
        _sha256_hex(self.pretrade_firewall_id, field="pretrade_firewall_id")

    def payload(self) -> dict[str, object]:
        return {
            "position_id": self.position_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "asset_id": self.asset_id,
            "market": self.market,
            "side": self.side,
            "quantity_scale": self.quantity_scale,
            "price_scale": self.price_scale,
            "risk_validation_id": self.risk_validation_id.lower(),
            "pretrade_firewall_id": self.pretrade_firewall_id.lower(),
        }

    @property
    def position_spec_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionFillEvent:
    position_id: str
    sequence: int
    occurred_at_ns: int
    event_type: str
    quantity_scaled: int
    price_scaled: int
    order_id: str
    client_order_id: str
    oms_record_id: str
    reconciliation_report_id: str
    source_ref: str = "DETERMINISTIC_REFERENCE"

    def validate(self, policy: CanonicalPositionPolicy) -> None:
        _text(self.position_id, field="position_id")
        _positive_int(self.sequence, field="sequence")
        _non_negative_int(self.occurred_at_ns, field="occurred_at_ns")
        if self.event_type not in policy.event_types:
            raise CanonicalPositionError("unsupported position fill event")
        _positive_int(self.quantity_scaled, field="quantity_scaled")
        _positive_int(self.price_scaled, field="price_scaled")
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        _sha256_hex(self.oms_record_id, field="oms_record_id")
        _sha256_hex(self.reconciliation_report_id, field="reconciliation_report_id")
        _text(self.source_ref, field="source_ref")

    def payload(self) -> dict[str, object]:
        return {
            "position_id": self.position_id,
            "sequence": self.sequence,
            "occurred_at_ns": self.occurred_at_ns,
            "event_type": self.event_type,
            "quantity_scaled": self.quantity_scaled,
            "price_scaled": self.price_scaled,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "oms_record_id": self.oms_record_id.lower(),
            "reconciliation_report_id": self.reconciliation_report_id.lower(),
            "source_ref": self.source_ref,
        }

    @property
    def event_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionStateRecord:
    policy_id: str
    position_spec_id: str
    position_id: str
    portfolio_id: str
    strategy_id: str
    asset_id: str
    market: str
    side: str
    quantity_scale: int
    price_scale: int
    state: str
    total_opened_scaled: int
    total_closed_scaled: int
    open_quantity_scaled: int
    entry_value_product_scaled: int
    average_entry_price_scaled_floor: int
    average_entry_price_remainder: int
    sequence: int
    occurred_at_ns: int
    source_event_id: str
    source_oms_record_id: str
    source_reconciliation_report_id: str
    previous_record_id: str | None
    source_mode: str = "EXPLICIT_EXECUTION_REFERENCE_EVIDENCE_ONLY"
    real_venue_query: bool = False
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    external_order_mutation: bool = False
    automatic_oms_mutation: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "position_spec_id": self.position_spec_id,
            "position_id": self.position_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id": self.strategy_id,
            "asset_id": self.asset_id,
            "market": self.market,
            "side": self.side,
            "quantity_scale": self.quantity_scale,
            "price_scale": self.price_scale,
            "state": self.state,
            "total_opened_scaled": self.total_opened_scaled,
            "total_closed_scaled": self.total_closed_scaled,
            "open_quantity_scaled": self.open_quantity_scaled,
            "entry_value_product_scaled": self.entry_value_product_scaled,
            "average_entry_price_scaled_floor": self.average_entry_price_scaled_floor,
            "average_entry_price_remainder": self.average_entry_price_remainder,
            "sequence": self.sequence,
            "occurred_at_ns": self.occurred_at_ns,
            "source_event_id": self.source_event_id,
            "source_oms_record_id": self.source_oms_record_id,
            "source_reconciliation_report_id": self.source_reconciliation_report_id,
            "previous_record_id": self.previous_record_id,
            "source_mode": self.source_mode,
            "real_venue_query": self.real_venue_query,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "external_order_mutation": self.external_order_mutation,
            "automatic_oms_mutation": self.automatic_oms_mutation,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class CanonicalPositionEngine:
    def __init__(self, policy: CanonicalPositionPolicy) -> None:
        self._policy = policy
        self._specs: dict[str, PositionSpec] = {}
        self._current: dict[str, PositionStateRecord] = {}
        self._seen_oms_records: set[str] = set()

    def register(self, spec: PositionSpec) -> str:
        spec.validate(self._policy)
        if spec.position_id in self._specs:
            existing = self._specs[spec.position_id]
            if existing != spec:
                raise CanonicalPositionError("position_id reused with conflicting specification")
            return existing.position_spec_id
        self._specs[spec.position_id] = spec
        return spec.position_spec_id

    def apply(self, event: PositionFillEvent) -> PositionStateRecord:
        event.validate(self._policy)
        try:
            spec = self._specs[event.position_id]
        except KeyError as exc:
            raise CanonicalPositionError("unknown canonical position") from exc

        oms_id = event.oms_record_id.lower()
        if oms_id in self._seen_oms_records:
            raise CanonicalPositionError("duplicate OMS fill lineage")
        current = self._current.get(event.position_id)

        if current is None:
            if event.sequence != 1 or event.event_type != "OPEN_FILL":
                raise CanonicalPositionError("first position event must be OPEN_FILL with sequence 1")
            opened = event.quantity_scaled
            closed = 0
            entry_value = event.quantity_scaled * event.price_scaled
            state = "OPEN"
            previous_record_id = None
        else:
            if current.state == "CLOSED":
                raise CanonicalPositionError("closed position cannot be reopened")
            if event.sequence != current.sequence + 1:
                raise CanonicalPositionError("position sequence must be contiguous")
            if event.occurred_at_ns < current.occurred_at_ns:
                raise CanonicalPositionError("position event time cannot regress")
            opened = current.total_opened_scaled
            closed = current.total_closed_scaled
            entry_value = current.entry_value_product_scaled
            previous_record_id = current.record_id

            if event.event_type == "OPEN_FILL":
                raise CanonicalPositionError("OPEN_FILL is only valid as first event")
            if event.event_type == "ADD_FILL":
                if closed != 0:
                    raise CanonicalPositionError("scale-in after any reduction is forbidden in P21-A")
                opened += event.quantity_scaled
                entry_value += event.quantity_scaled * event.price_scaled
            elif event.event_type == "REDUCE_FILL":
                if event.quantity_scaled > opened - closed:
                    raise CanonicalPositionError("position reduction exceeds open quantity")
                closed += event.quantity_scaled

            open_quantity = opened - closed
            if open_quantity == 0:
                state = "CLOSED"
            elif closed > 0:
                state = "PARTIALLY_CLOSED"
            else:
                state = "OPEN"

        open_quantity = opened - closed
        average_floor, average_remainder = divmod(entry_value, opened)
        record = PositionStateRecord(
            policy_id=self._policy.policy_id,
            position_spec_id=spec.position_spec_id,
            position_id=spec.position_id,
            portfolio_id=spec.portfolio_id,
            strategy_id=spec.strategy_id,
            asset_id=spec.asset_id,
            market=spec.market,
            side=spec.side,
            quantity_scale=spec.quantity_scale,
            price_scale=spec.price_scale,
            state=state,
            total_opened_scaled=opened,
            total_closed_scaled=closed,
            open_quantity_scaled=open_quantity,
            entry_value_product_scaled=entry_value,
            average_entry_price_scaled_floor=average_floor,
            average_entry_price_remainder=average_remainder,
            sequence=event.sequence,
            occurred_at_ns=event.occurred_at_ns,
            source_event_id=event.event_id,
            source_oms_record_id=oms_id,
            source_reconciliation_report_id=event.reconciliation_report_id.lower(),
            previous_record_id=previous_record_id,
        )
        self._current[event.position_id] = record
        self._seen_oms_records.add(oms_id)
        return record

    def current(self, position_id: str) -> PositionStateRecord:
        try:
            return self._current[position_id]
        except KeyError as exc:
            raise CanonicalPositionError("unknown canonical position state") from exc

    def snapshot(self) -> dict[str, object]:
        positions: list[dict[str, object]] = []
        for position_id in sorted(self._current):
            record = self._current[position_id]
            row: dict[str, object] = dict(record.payload())
            row["record_id"] = record.record_id
            positions.append(row)
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21A_CANONICAL_POSITION_SNAPSHOT",
            "task_id": "FIN-P21-WA-001",
            "policy_id": self._policy.policy_id,
            "positions": positions,
            "authority": {
                "source_mode": "EXPLICIT_EXECUTION_REFERENCE_EVIDENCE_ONLY",
                "real_venue_query": False,
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "external_order_submission": False,
                "external_order_mutation": False,
                "automatic_oms_mutation": False,
                "live_execution_validated": False,
                "live_execution_authority": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        return {**payload, "snapshot_id": hashlib.sha256(_canonical_bytes(payload)).hexdigest()}
