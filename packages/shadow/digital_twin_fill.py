from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from quant.backtesting.engine import BacktestDecision, BacktestMarketEvent, SimulatedFill
from quant.backtesting.execution_realism import (
    ExecutionRealismDiagnostic,
    ExecutionRealismError,
    ExecutionRealismPolicy,
    HistoricalExecutionContext,
    HistoricalExecutionSimulator,
)


class DigitalTwinFillError(ValueError):
    """P19-E deterministic Digital Twin fill/slippage invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DigitalTwinFillError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DigitalTwinFillError(f"{field} must be non-empty text")
    return value.strip()


def _sha(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise DigitalTwinFillError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise DigitalTwinFillError(f"{field} cannot be degenerate placeholder identity")
    return parsed


def _decimal(value: object, *, field: str) -> Decimal:
    if not isinstance(value, str):
        raise DigitalTwinFillError(f"{field} must be decimal text")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DigitalTwinFillError(f"{field} must be decimal text") from exc
    if not parsed.is_finite():
        raise DigitalTwinFillError(f"{field} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DigitalTwinFillError(f"{field} must be positive integer")
    return value


@dataclass(frozen=True, slots=True)
class DigitalTwinFillPolicy:
    accepted_context_quality: tuple[str, ...]
    execution_policy: ExecutionRealismPolicy
    reference_half_spread_bps: int = 5
    reference_level_spacing_bps: int = 5
    reference_levels_per_side: int = 2
    reference_displayed_quantity: str = "1"
    reference_quantity: str = "0.01"
    reference_direction_source: str = "P19_A_SIGNAL_ACTION"
    reference_price_source: str = "LATEST_P19_B_VISIBLE_CLOSE"
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @classmethod
    def from_path(cls, path: Path) -> "DigitalTwinFillPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DigitalTwinFillError(f"invalid P19-E policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19E_DIGITAL_TWIN_FILL_POLICY",
            "task_id": "FIN-P19-WE-001",
            "mode": "P17B_EXECUTION_REALISM_DIGITAL_TWIN",
            "execution_realism_owner": "P17-B",
            "incident_replay_owner": "P19-D",
            "reference_context_quality": "DERIVED_REFERENCE_DEPTH",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise DigitalTwinFillError(f"P19-E policy mismatch: {key}")
        quality_raw = raw.get("accepted_context_quality")
        if not isinstance(quality_raw, list):
            raise DigitalTwinFillError("accepted_context_quality must be a list")
        qualities = tuple(
            _text(item, field="accepted_context_quality")
            for item in cast(list[object], quality_raw)
        )
        if qualities != ("EXPLICIT_HISTORICAL_DEPTH", "DERIVED_REFERENCE_DEPTH"):
            raise DigitalTwinFillError("P19-E context-quality taxonomy drift")
        reference_raw = _mapping(
            raw.get("reference_execution_policy"),
            field="reference_execution_policy",
        )
        version = _text(reference_raw.get("policy_version"), field="policy_version")
        fee = reference_raw.get("taker_fee_bps")
        latency = reference_raw.get("decision_latency_ns")
        participation = reference_raw.get("max_displayed_depth_participation_bps")
        if (
            isinstance(fee, bool)
            or not isinstance(fee, int)
            or isinstance(latency, bool)
            or not isinstance(latency, int)
            or isinstance(participation, bool)
            or not isinstance(participation, int)
        ):
            raise DigitalTwinFillError("reference execution policy values must be integers")
        derivation = _mapping(
            raw.get("reference_depth_derivation"),
            field="reference_depth_derivation",
        )
        if derivation.get("method") != "CLOSE_CENTERED_SYNTHETIC_BOOK_V1":
            raise DigitalTwinFillError("unsupported reference depth derivation")
        half_spread = derivation.get("half_spread_bps")
        level_spacing = derivation.get("level_spacing_bps")
        levels_per_side = derivation.get("levels_per_side")
        displayed_quantity = derivation.get("displayed_quantity_btc")
        if (
            isinstance(half_spread, bool)
            or not isinstance(half_spread, int)
            or not 1 <= half_spread <= 10_000
            or isinstance(level_spacing, bool)
            or not isinstance(level_spacing, int)
            or not 1 <= level_spacing <= 10_000
            or isinstance(levels_per_side, bool)
            or not isinstance(levels_per_side, int)
            or not 1 <= levels_per_side <= 16
        ):
            raise DigitalTwinFillError("invalid reference depth derivation integers")
        displayed = _decimal(displayed_quantity, field="displayed_quantity_btc")
        if displayed <= 0:
            raise DigitalTwinFillError("displayed_quantity_btc must be positive")
        request_raw = _mapping(
            raw.get("reference_simulation_request"),
            field="reference_simulation_request",
        )
        reference_quantity = _decimal(
            request_raw.get("quantity_btc"),
            field="reference_simulation_request.quantity_btc",
        )
        if reference_quantity <= 0:
            raise DigitalTwinFillError("reference simulation quantity must be positive")
        direction_source = _text(
            request_raw.get("direction_source"),
            field="reference_simulation_request.direction_source",
        )
        price_source = _text(
            request_raw.get("reference_price_source"),
            field="reference_simulation_request.reference_price_source",
        )
        if direction_source != "P19_A_SIGNAL_ACTION":
            raise DigitalTwinFillError("unsupported reference direction source")
        if price_source != "LATEST_P19_B_VISIBLE_CLOSE":
            raise DigitalTwinFillError("unsupported reference price source")
        required_true = (
            "production_quality_context_required_for_production_claim",
            "reference_only_context_cannot_claim_production_fill_accuracy",
        )
        if any(raw.get(field) is not True for field in required_true):
            raise DigitalTwinFillError("P19-E production-claim guard disabled")
        required_false = (
            "production_fill_accuracy_claim",
            "broker_truth",
            "network_required",
            "credentials_required",
            "decision_authority",
            "fill_authority",
            "execution_authority",
            "order_routing_authority",
            "broker_exchange_routing",
            "p20_started",
        )
        if any(raw.get(field) is not False for field in required_false):
            raise DigitalTwinFillError("P19-E authority/claim policy drift")
        return cls(
            accepted_context_quality=qualities,
            execution_policy=ExecutionRealismPolicy(
                policy_version=version,
                taker_fee_bps=fee,
                decision_latency_ns=latency,
                max_displayed_depth_participation_bps=participation,
            ),
            reference_half_spread_bps=half_spread,
            reference_level_spacing_bps=level_spacing,
            reference_levels_per_side=levels_per_side,
            reference_displayed_quantity=_decimal_text(displayed),
            reference_quantity=_decimal_text(reference_quantity),
            reference_direction_source=direction_source,
            reference_price_source=price_source,
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "accepted_context_quality": list(self.accepted_context_quality),
                    "execution_policy_id": self.execution_policy.policy_id,
                    "execution_realism_owner": "P17-B",
                    "reference_depth_derivation": {
                        "method": "CLOSE_CENTERED_SYNTHETIC_BOOK_V1",
                        "half_spread_bps": self.reference_half_spread_bps,
                        "level_spacing_bps": self.reference_level_spacing_bps,
                        "levels_per_side": self.reference_levels_per_side,
                        "displayed_quantity_btc": self.reference_displayed_quantity,
                    },
                    "reference_simulation_request": {
                        "quantity_btc": self.reference_quantity,
                        "direction_source": self.reference_direction_source,
                        "reference_price_source": self.reference_price_source,
                    },
                    "production_fill_accuracy_claim": False,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class DigitalTwinFillRequest:
    twin_name: str
    incident_replay_root_id: str
    decision_replay_session_id: str
    shadow_record_id: str
    asset_id: str
    decision_time_ns: int
    quantity_delta: str
    reference_price_scaled: int
    price_scale: int
    context_quality: str
    source_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "twin_name", _text(self.twin_name, field="twin_name"))
        for field in (
            "incident_replay_root_id",
            "decision_replay_session_id",
            "shadow_record_id",
            "source_evidence_sha256",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))
        object.__setattr__(self, "asset_id", _text(self.asset_id, field="asset_id"))
        object.__setattr__(
            self,
            "decision_time_ns",
            _positive_int(self.decision_time_ns, field="decision_time_ns"),
        )
        quantity = _decimal(self.quantity_delta, field="quantity_delta")
        if quantity == 0:
            raise DigitalTwinFillError("quantity_delta must be non-zero")
        object.__setattr__(self, "quantity_delta", _decimal_text(quantity))
        object.__setattr__(
            self,
            "reference_price_scaled",
            _positive_int(self.reference_price_scaled, field="reference_price_scaled"),
        )
        object.__setattr__(
            self,
            "price_scale",
            _positive_int(self.price_scale, field="price_scale"),
        )
        object.__setattr__(
            self,
            "context_quality",
            _text(self.context_quality, field="context_quality"),
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "twin_name": self.twin_name,
            "incident_replay_root_id": self.incident_replay_root_id,
            "decision_replay_session_id": self.decision_replay_session_id,
            "shadow_record_id": self.shadow_record_id,
            "asset_id": self.asset_id,
            "decision_time_ns": self.decision_time_ns,
            "quantity_delta": self.quantity_delta,
            "reference_price_scaled": self.reference_price_scaled,
            "price_scale": self.price_scale,
            "context_quality": self.context_quality,
            "source_evidence_sha256": self.source_evidence_sha256,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DigitalTwinMarketSlice:
    event: BacktestMarketEvent
    context: HistoricalExecutionContext

    def __post_init__(self) -> None:
        if self.context.sequence != self.event.sequence:
            raise DigitalTwinFillError("execution context sequence mismatch")
        if self.context.event_time_ns != self.event.event_time_ns:
            raise DigitalTwinFillError("execution context event time mismatch")
        if self.context.asset_id != self.event.asset_id:
            raise DigitalTwinFillError("execution context asset mismatch")
        if self.context.price_scale != self.event.price_scale:
            raise DigitalTwinFillError("execution context price scale mismatch")

    @property
    def slice_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "event": self.event.payload(),
                    "context_id": self.context.context_id,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class DigitalTwinFillResult:
    request_id: str
    policy_id: str
    execution_policy_id: str
    execution_realism_owner: str
    context_quality: str
    production_quality_context: bool
    production_fill_accuracy_claim: bool
    broker_truth: bool
    status: str
    side: str
    requested_quantity: str
    filled_quantity: str
    remaining_quantity: str
    vwap_price_scaled: str | None
    reference_price_scaled: int
    adverse_slippage_bps: str | None
    total_fee_cash: str
    fill_ids: tuple[str, ...]
    context_ids: tuple[str, ...]
    diagnostic_ids: tuple[str, ...]
    diagnostics: tuple[ExecutionRealismDiagnostic, ...]
    decision_authority: bool = False
    fill_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "request_id": self.request_id,
            "policy_id": self.policy_id,
            "execution_policy_id": self.execution_policy_id,
            "execution_realism_owner": self.execution_realism_owner,
            "context_quality": self.context_quality,
            "production_quality_context": self.production_quality_context,
            "production_fill_accuracy_claim": self.production_fill_accuracy_claim,
            "broker_truth": self.broker_truth,
            "status": self.status,
            "side": self.side,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "vwap_price_scaled": self.vwap_price_scaled,
            "reference_price_scaled": self.reference_price_scaled,
            "adverse_slippage_bps": self.adverse_slippage_bps,
            "total_fee_cash": self.total_fee_cash,
            "fill_ids": list(self.fill_ids),
            "context_ids": list(self.context_ids),
            "diagnostic_ids": list(self.diagnostic_ids),
            "diagnostics": [item.payload() for item in self.diagnostics],
            "decision_authority": self.decision_authority,
            "fill_authority": self.fill_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def result_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class DigitalTwinFillEngine:
    def __init__(self, policy: DigitalTwinFillPolicy) -> None:
        self._policy = policy

    def simulate(
        self,
        *,
        request: DigitalTwinFillRequest,
        timeline: Sequence[DigitalTwinMarketSlice],
    ) -> DigitalTwinFillResult:
        if request.context_quality not in self._policy.accepted_context_quality:
            raise DigitalTwinFillError("unsupported Digital Twin context quality")
        if not timeline:
            raise DigitalTwinFillError("Digital Twin timeline cannot be empty")
        if timeline[0].event.event_time_ns != request.decision_time_ns:
            raise DigitalTwinFillError("first market slice must equal decision time")

        previous_sequence: int | None = None
        previous_time: int | None = None
        for item in timeline:
            event = item.event
            if event.asset_id != request.asset_id:
                raise DigitalTwinFillError("Digital Twin event asset mismatch")
            if event.price_scale != request.price_scale:
                raise DigitalTwinFillError("Digital Twin event price scale mismatch")
            if previous_sequence is not None and event.sequence <= previous_sequence:
                raise DigitalTwinFillError("Digital Twin sequence must increase strictly")
            if previous_time is not None and event.event_time_ns <= previous_time:
                raise DigitalTwinFillError("Digital Twin event time must increase strictly")
            previous_sequence = event.sequence
            previous_time = event.event_time_ns

        simulator = HistoricalExecutionSimulator(
            policy=self._policy.execution_policy,
            contexts=tuple(item.context for item in timeline),
        )
        decision = BacktestDecision(
            decision_id=request.request_id,
            asset_id=request.asset_id,
            decision_time_ns=request.decision_time_ns,
            quantity_delta=request.quantity_delta,
        )
        fills: list[SimulatedFill] = []
        try:
            fills.extend(simulator.submit(decision, timeline[0].event))
            for item in timeline[1:]:
                fills.extend(simulator.on_market_event(item.event))
        except ExecutionRealismError as exc:
            raise DigitalTwinFillError(f"P17-B Digital Twin simulation failed: {exc}") from exc

        requested = abs(_decimal(request.quantity_delta, field="quantity_delta"))
        filled = sum(
            (abs(_decimal(fill.quantity_delta, field="fill.quantity_delta")) for fill in fills),
            Decimal(0),
        )
        if filled > requested:
            raise DigitalTwinFillError("P17-B simulation overfilled Digital Twin request")
        remaining = requested - filled
        status = "FULL_FILL" if remaining == 0 else ("PARTIAL_FILL" if filled > 0 else "NO_FILL")
        side = "BUY" if _decimal(request.quantity_delta, field="quantity_delta") > 0 else "SELL"

        vwap: Decimal | None = None
        slippage: Decimal | None = None
        total_fee = sum(
            (_decimal(fill.explicit_cost_cash, field="fill.explicit_cost_cash") for fill in fills),
            Decimal(0),
        )
        if fills:
            weighted = sum(
                (
                    abs(_decimal(fill.quantity_delta, field="fill.quantity_delta"))
                    * Decimal(fill.fill_price_scaled)
                    for fill in fills
                ),
                Decimal(0),
            )
            vwap = weighted / filled
            reference = Decimal(request.reference_price_scaled)
            if side == "BUY":
                slippage = (vwap / reference - Decimal(1)) * Decimal(10_000)
            else:
                slippage = (Decimal(1) - vwap / reference) * Decimal(10_000)

        diagnostics = simulator.diagnostics
        diagnostic_ids = tuple(
            hashlib.sha256(_canonical_bytes(item.payload())).hexdigest()
            for item in diagnostics
        )
        production_quality = request.context_quality == "EXPLICIT_HISTORICAL_DEPTH"
        return DigitalTwinFillResult(
            request_id=request.request_id,
            policy_id=self._policy.policy_id,
            execution_policy_id=self._policy.execution_policy.policy_id,
            execution_realism_owner="P17-B",
            context_quality=request.context_quality,
            production_quality_context=production_quality,
            production_fill_accuracy_claim=False,
            broker_truth=False,
            status=status,
            side=side,
            requested_quantity=_decimal_text(requested),
            filled_quantity=_decimal_text(filled),
            remaining_quantity=_decimal_text(remaining),
            vwap_price_scaled=None if vwap is None else _decimal_text(vwap),
            reference_price_scaled=request.reference_price_scaled,
            adverse_slippage_bps=None if slippage is None else _decimal_text(slippage),
            total_fee_cash=_decimal_text(total_fee),
            fill_ids=tuple(fill.fill_id for fill in fills),
            context_ids=tuple(item.context.context_id for item in timeline),
            diagnostic_ids=diagnostic_ids,
            diagnostics=diagnostics,
            live_trading=self._policy.live_trading,
            auto_trading=self._policy.auto_trading,
        )
