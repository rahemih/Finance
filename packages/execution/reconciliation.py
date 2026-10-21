from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast


class ReconciliationError(ValueError):
    """P20-G deterministic execution reconciliation invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReconciliationError(f"{field} must be non-empty text")
    return value.strip()


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise ReconciliationError(f"{field} must be a sha256 hex digest")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReconciliationError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    value = _non_negative_int(value, field=field)
    if value == 0:
        raise ReconciliationError(f"{field} must be positive")
    return value


def _tuple_text(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ReconciliationError(f"{field} must be a non-empty list")
    parsed = tuple(_text(v, field=field) for v in cast(list[object], value))
    if len(set(parsed)) != len(parsed):
        raise ReconciliationError(f"{field} cannot contain duplicates")
    return parsed


@dataclass(frozen=True, slots=True)
class ReconciliationPolicy:
    markets: tuple[str, ...]
    internal_states: tuple[str, ...]
    venue_statuses: tuple[str, ...]
    verdicts: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ReconciliationPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReconciliationError(f"invalid P20-G policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise ReconciliationError("P20-G policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20G_RECONCILIATION_POLICY",
            "task_id": "FIN-P20-WG-001",
            "mode": "DETERMINISTIC_REFERENCE_RECONCILIATION",
            "source_mode": "EXPLICIT_REFERENCE_SANDBOX_OBSERVATION_ONLY",
            "real_venue_query": False,
            "automatic_oms_mutation": False,
            "external_order_mutation": False,
            "execution_quality_owner": "P20-H",
            "simulation_gate_owner": "P20-I",
            "position_management_owner": "P21",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise ReconciliationError(f"P20-G policy mismatch: {key}")
        markets = _tuple_text(raw.get("markets"), field="markets")
        internal_states = _tuple_text(raw.get("internal_states"), field="internal_states")
        venue_statuses = _tuple_text(raw.get("venue_statuses"), field="venue_statuses")
        verdicts = _tuple_text(raw.get("verdicts"), field="verdicts")
        if markets != ("CRYPTO", "FOREX"):
            raise ReconciliationError("invalid P20-G market taxonomy")
        if internal_states != ("CREATED","SUBMIT_PENDING","OPEN","PARTIALLY_FILLED","CANCEL_PENDING","FILLED","CANCELED","REJECTED","EXPIRED"):
            raise ReconciliationError("invalid P20-G internal state taxonomy")
        if venue_statuses != ("NOT_FOUND","OPEN","PARTIALLY_FILLED","FILLED","CANCELED","REJECTED","EXPIRED"):
            raise ReconciliationError("invalid P20-G venue status taxonomy")
        if verdicts != ("MATCHED","VENUE_AHEAD","INTERNAL_AHEAD","FILL_MISMATCH","STATE_CONFLICT","UNRESOLVED_AMBIGUITY"):
            raise ReconciliationError("invalid P20-G verdict taxonomy")
        return cls(markets, internal_states, venue_statuses, verdicts, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        payload: dict[str, object] = {
            "markets": list(self.markets), "internal_states": list(self.internal_states),
            "venue_statuses": list(self.venue_statuses), "verdicts": list(self.verdicts),
            "source_mode": "EXPLICIT_REFERENCE_SANDBOX_OBSERVATION_ONLY",
            "real_venue_query": False, "automatic_oms_mutation": False, "external_order_mutation": False,
            "network_mode": "DISABLED", "live_execution_authority": False,
            "live_trading": self.live_trading, "auto_trading": self.auto_trading,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class InternalExecutionView:
    market: str
    order_id: str
    client_order_id: str
    oms_state: str
    cumulative_filled_scaled: int
    total_quantity_scaled: int
    quantity_scale: int
    oms_record_id: str
    idempotency_claim_id: str
    recovery_checkpoint_id: str | None = None
    recovery_safe_hold: bool = False

    def validate(self, policy: ReconciliationPolicy) -> None:
        if self.market not in policy.markets:
            raise ReconciliationError("internal market outside P20-G policy")
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        if self.oms_state not in policy.internal_states:
            raise ReconciliationError("unsupported internal OMS state")
        _non_negative_int(self.cumulative_filled_scaled, field="cumulative_filled_scaled")
        _positive_int(self.total_quantity_scaled, field="total_quantity_scaled")
        _positive_int(self.quantity_scale, field="quantity_scale")
        if self.cumulative_filled_scaled > self.total_quantity_scaled:
            raise ReconciliationError("internal cumulative fill exceeds total quantity")
        _sha256_hex(self.oms_record_id, field="oms_record_id")
        _sha256_hex(self.idempotency_claim_id, field="idempotency_claim_id")
        if self.recovery_checkpoint_id is not None:
            _sha256_hex(self.recovery_checkpoint_id, field="recovery_checkpoint_id")
        if self.recovery_safe_hold and self.recovery_checkpoint_id is None:
            raise ReconciliationError("recovery safe hold requires checkpoint lineage")

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market, "order_id": self.order_id, "client_order_id": self.client_order_id,
            "oms_state": self.oms_state, "cumulative_filled_scaled": self.cumulative_filled_scaled,
            "total_quantity_scaled": self.total_quantity_scaled, "quantity_scale": self.quantity_scale,
            "oms_record_id": self.oms_record_id, "idempotency_claim_id": self.idempotency_claim_id,
            "recovery_checkpoint_id": self.recovery_checkpoint_id, "recovery_safe_hold": self.recovery_safe_hold,
        }


@dataclass(frozen=True, slots=True)
class ReferenceVenueObservation:
    market: str
    order_id: str
    client_order_id: str
    venue_status: str
    cumulative_filled_scaled: int
    quantity_scale: int
    observed_at_ns: int
    source_ref: str
    venue_order_id: str | None = None

    def validate(self, policy: ReconciliationPolicy) -> None:
        if self.market not in policy.markets:
            raise ReconciliationError("observation market outside P20-G policy")
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        if self.venue_status not in policy.venue_statuses:
            raise ReconciliationError("unsupported reference venue status")
        _non_negative_int(self.cumulative_filled_scaled, field="cumulative_filled_scaled")
        _positive_int(self.quantity_scale, field="quantity_scale")
        _non_negative_int(self.observed_at_ns, field="observed_at_ns")
        _text(self.source_ref, field="source_ref")
        if self.venue_order_id is not None:
            _text(self.venue_order_id, field="venue_order_id")

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market, "order_id": self.order_id, "client_order_id": self.client_order_id,
            "venue_status": self.venue_status, "cumulative_filled_scaled": self.cumulative_filled_scaled,
            "quantity_scale": self.quantity_scale, "observed_at_ns": self.observed_at_ns,
            "source_ref": self.source_ref, "venue_order_id": self.venue_order_id,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    policy_id: str
    observation_id: str
    order_id: str
    client_order_id: str
    market: str
    internal_state: str
    venue_status: str
    internal_filled_scaled: int
    venue_filled_scaled: int
    fill_delta_scaled: int
    verdict: str
    suggested_oms_event: str | None
    reconciliation_required: bool
    automatic_oms_mutation: bool = False
    real_venue_query: bool = False
    external_order_mutation: bool = False
    network_mode: str = "DISABLED"
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id, "observation_id": self.observation_id,
            "order_id": self.order_id, "client_order_id": self.client_order_id, "market": self.market,
            "internal_state": self.internal_state, "venue_status": self.venue_status,
            "internal_filled_scaled": self.internal_filled_scaled, "venue_filled_scaled": self.venue_filled_scaled,
            "fill_delta_scaled": self.fill_delta_scaled, "verdict": self.verdict,
            "suggested_oms_event": self.suggested_oms_event, "reconciliation_required": self.reconciliation_required,
            "automatic_oms_mutation": self.automatic_oms_mutation, "real_venue_query": self.real_venue_query,
            "external_order_mutation": self.external_order_mutation, "network_mode": self.network_mode,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def report_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class ReconciliationEngine:
    _EXPECTED: dict[str, str] = {
        "CREATED":"NOT_FOUND","SUBMIT_PENDING":"NOT_FOUND","OPEN":"OPEN",
        "PARTIALLY_FILLED":"PARTIALLY_FILLED","CANCEL_PENDING":"OPEN",
        "FILLED":"FILLED","CANCELED":"CANCELED","REJECTED":"REJECTED","EXPIRED":"EXPIRED",
    }

    def __init__(self, policy: ReconciliationPolicy) -> None:
        self._policy = policy
        self._reports: dict[str, ReconciliationReport] = {}

    def reconcile(self, internal: InternalExecutionView, observation: ReferenceVenueObservation) -> ReconciliationReport:
        internal.validate(self._policy)
        observation.validate(self._policy)
        if internal.market != observation.market:
            raise ReconciliationError("market identity mismatch")
        if internal.order_id != observation.order_id:
            raise ReconciliationError("order identity mismatch")
        if internal.client_order_id != observation.client_order_id:
            raise ReconciliationError("client-order identity mismatch")
        if internal.quantity_scale != observation.quantity_scale:
            raise ReconciliationError("quantity scale mismatch")
        if observation.cumulative_filled_scaled > internal.total_quantity_scaled:
            raise ReconciliationError("venue cumulative fill exceeds internal total quantity")

        fill_delta = observation.cumulative_filled_scaled - internal.cumulative_filled_scaled
        expected = self._EXPECTED[internal.oms_state]
        suggested: str | None = None
        required = False

        if fill_delta != 0:
            verdict = "FILL_MISMATCH"
            required = True
        elif internal.recovery_safe_hold and internal.oms_state == "SUBMIT_PENDING" and observation.venue_status == "NOT_FOUND":
            verdict = "UNRESOLVED_AMBIGUITY"
            required = True
        elif observation.venue_status == expected:
            verdict = "MATCHED"
        elif internal.oms_state == "SUBMIT_PENDING" and observation.venue_status in ("OPEN","REJECTED"):
            verdict = "VENUE_AHEAD"
            suggested = "ACK" if observation.venue_status == "OPEN" else "REJECT"
            required = True
        elif internal.oms_state == "CANCEL_PENDING" and observation.venue_status == "CANCELED":
            verdict = "VENUE_AHEAD"
            suggested = "CANCEL_ACK"
            required = True
        elif internal.oms_state in ("CREATED","OPEN","PARTIALLY_FILLED","CANCEL_PENDING") and observation.venue_status == "NOT_FOUND":
            verdict = "INTERNAL_AHEAD"
            required = True
        else:
            verdict = "STATE_CONFLICT"
            required = True

        report = ReconciliationReport(
            policy_id=self._policy.policy_id, observation_id=observation.observation_id,
            order_id=internal.order_id, client_order_id=internal.client_order_id, market=internal.market,
            internal_state=internal.oms_state, venue_status=observation.venue_status,
            internal_filled_scaled=internal.cumulative_filled_scaled,
            venue_filled_scaled=observation.cumulative_filled_scaled, fill_delta_scaled=fill_delta,
            verdict=verdict, suggested_oms_event=suggested, reconciliation_required=required,
        )
        existing = self._reports.get(observation.observation_id)
        if existing is not None and existing != report:
            raise ReconciliationError("observation identity produced conflicting reconciliation report")
        self._reports[observation.observation_id] = report
        return report

    def snapshot(self) -> dict[str, object]:
        reports: list[dict[str, object]] = []
        for observation_id in sorted(self._reports):
            report = self._reports[observation_id]
            item = dict(report.payload())
            item["report_id"] = report.report_id
            reports.append(item)
        payload: dict[str, object] = {
            "schema_version":"1.0","kind":"NEXUS_QUANT_P20G_RECONCILIATION_SNAPSHOT",
            "task_id":"FIN-P20-WG-001","policy_id":self._policy.policy_id,"reports":reports,
            "authority":{
                "source_mode":"EXPLICIT_REFERENCE_SANDBOX_OBSERVATION_ONLY","real_venue_query":False,
                "automatic_oms_mutation":False,"external_order_mutation":False,"credential_mode":"NONE",
                "network_mode":"DISABLED","execution_quality_owner":"P20-H","simulation_gate_owner":"P20-I",
                "position_management_owner":"P21","live_execution_authority":False,
                "live_trading":self._policy.live_trading,"auto_trading":self._policy.auto_trading,
            },
        }
        result = dict(payload)
        result["snapshot_id"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        return result
