from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Protocol, Sequence


class DemoPaperError(ValueError):
    """P18-A deterministic Demo/Paper engine invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _safe_id(value: str, *, field: str) -> str:
    parsed = value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise DemoPaperError(f"{field} contains unsafe characters")
    return parsed


def _sha256_text(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise DemoPaperError(f"{field} must be lowercase SHA-256")
    return parsed


def _finite_decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DemoPaperError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite():
        raise DemoPaperError(f"{field} must be finite")
    return parsed


def _positive_decimal(value: str, *, field: str) -> Decimal:
    parsed = _finite_decimal(value, field=field)
    if parsed <= 0:
        raise DemoPaperError(f"{field} must be positive")
    return parsed


def _non_negative_decimal(value: str, *, field: str) -> Decimal:
    parsed = _finite_decimal(value, field=field)
    if parsed < 0:
        raise DemoPaperError(f"{field} must be non-negative")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@dataclass(frozen=True, slots=True)
class DemoSessionSpec:
    session_id: str
    strategy_id: str
    strategy_version: str
    model_id: str
    model_version: str
    initial_cash: str
    base_currency: str

    def __post_init__(self) -> None:
        _safe_id(self.session_id, field="session_id")
        _safe_id(self.strategy_id, field="strategy_id")
        _safe_id(self.strategy_version, field="strategy_version")
        _safe_id(self.model_id, field="model_id")
        _safe_id(self.model_version, field="model_version")
        _positive_decimal(self.initial_cash, field="initial_cash")
        _safe_id(self.base_currency, field="base_currency")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "session_id": self.session_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "initial_cash": _decimal_text(
                _positive_decimal(self.initial_cash, field="initial_cash")
            ),
            "base_currency": self.base_currency,
        }

    @property
    def spec_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DemoMarketEvent:
    sequence: int
    event_time_ns: int
    available_at_ns: int
    asset_id: str
    price_scaled: int
    price_scale: int
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise DemoPaperError("sequence must be non-negative")
        if self.event_time_ns < 0 or self.available_at_ns < 0:
            raise DemoPaperError("event timestamps must be non-negative")
        if self.available_at_ns > self.event_time_ns:
            raise DemoPaperError(
                "available_at_ns cannot exceed simulated event_time_ns"
            )
        _safe_id(self.asset_id, field="asset_id")
        if self.price_scaled <= 0 or self.price_scale <= 0:
            raise DemoPaperError("price_scaled and price_scale must be positive")
        _sha256_text(self.evidence_sha256, field="evidence_sha256")

    def payload(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_time_ns": self.event_time_ns,
            "available_at_ns": self.available_at_ns,
            "asset_id": self.asset_id,
            "price_scaled": self.price_scaled,
            "price_scale": self.price_scale,
            "evidence_sha256": self.evidence_sha256,
        }

    @property
    def event_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DemoDecision:
    decision_id: str
    asset_id: str
    decision_time_ns: int
    quantity_delta: str
    signal_id: str
    risk_decision_id: str
    firewall_decision_id: str

    def __post_init__(self) -> None:
        _safe_id(self.decision_id, field="decision_id")
        _safe_id(self.asset_id, field="asset_id")
        if self.decision_time_ns < 0:
            raise DemoPaperError("decision_time_ns must be non-negative")
        if _finite_decimal(self.quantity_delta, field="quantity_delta") == 0:
            raise DemoPaperError("quantity_delta must be non-zero")
        _safe_id(self.signal_id, field="signal_id")
        _safe_id(self.risk_decision_id, field="risk_decision_id")
        _safe_id(self.firewall_decision_id, field="firewall_decision_id")

    def payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "asset_id": self.asset_id,
            "decision_time_ns": self.decision_time_ns,
            "quantity_delta": _decimal_text(
                _finite_decimal(self.quantity_delta, field="quantity_delta")
            ),
            "signal_id": self.signal_id,
            "risk_decision_id": self.risk_decision_id,
            "firewall_decision_id": self.firewall_decision_id,
        }


@dataclass(frozen=True, slots=True)
class DemoFill:
    fill_id: str
    decision_id: str
    asset_id: str
    fill_time_ns: int
    quantity_delta: str
    fill_price_scaled: int
    price_scale: int
    explicit_cost_cash: str

    def __post_init__(self) -> None:
        _safe_id(self.fill_id, field="fill_id")
        _safe_id(self.decision_id, field="decision_id")
        _safe_id(self.asset_id, field="asset_id")
        if self.fill_time_ns < 0:
            raise DemoPaperError("fill_time_ns must be non-negative")
        if _finite_decimal(self.quantity_delta, field="quantity_delta") == 0:
            raise DemoPaperError("fill quantity_delta must be non-zero")
        if self.fill_price_scaled <= 0 or self.price_scale <= 0:
            raise DemoPaperError(
                "fill_price_scaled and price_scale must be positive"
            )
        _non_negative_decimal(self.explicit_cost_cash, field="explicit_cost_cash")


@dataclass(frozen=True, slots=True)
class DemoPortfolioView:
    cash: str
    equity: str
    positions: tuple[tuple[str, str], ...]
    latest_marks: tuple[tuple[str, int, int], ...]


class DemoStrategy(Protocol):
    def on_event(
        self,
        event: DemoMarketEvent,
        portfolio: DemoPortfolioView,
    ) -> DemoDecision | None:
        ...

    def checkpoint_sha256(self) -> str:
        ...


class DemoExecutionSimulator(Protocol):
    def on_market_event(self, event: DemoMarketEvent) -> Sequence[DemoFill]:
        ...

    def submit(
        self,
        decision: DemoDecision,
        event: DemoMarketEvent,
    ) -> Sequence[DemoFill]:
        ...

    def checkpoint_sha256(self) -> str:
        ...


@dataclass(frozen=True, slots=True)
class DemoStepRecord:
    event_id: str
    sequence: int
    decision_ids: tuple[str, ...]
    fill_ids: tuple[str, ...]
    state_id: str

    def payload(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "decision_ids": list(self.decision_ids),
            "fill_ids": list(self.fill_ids),
            "state_id": self.state_id,
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DemoPaperState:
    session_spec_id: str
    event_count: int
    last_sequence: int
    last_event_time_ns: int
    cash: str
    equity: str
    positions: tuple[tuple[str, str], ...]
    latest_marks: tuple[tuple[str, int, int], ...]
    pending_decisions: tuple[tuple[str, str, str], ...]
    decision_ids: tuple[str, ...]
    fill_ids: tuple[str, ...]
    step_record_ids: tuple[str, ...]
    strategy_checkpoint_sha256: str
    execution_checkpoint_sha256: str
    mode: str = "DEMO_PAPER_ONLY"
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "session_spec_id": self.session_spec_id,
            "event_count": self.event_count,
            "last_sequence": self.last_sequence,
            "last_event_time_ns": self.last_event_time_ns,
            "cash": self.cash,
            "equity": self.equity,
            "positions": [list(item) for item in self.positions],
            "latest_marks": [list(item) for item in self.latest_marks],
            "pending_decisions": [list(item) for item in self.pending_decisions],
            "decision_ids": list(self.decision_ids),
            "fill_ids": list(self.fill_ids),
            "step_record_ids": list(self.step_record_ids),
            "strategy_checkpoint_sha256": self.strategy_checkpoint_sha256,
            "execution_checkpoint_sha256": self.execution_checkpoint_sha256,
            "mode": self.mode,
            "automatic_live_promotion": self.automatic_live_promotion,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def state_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(slots=True)
class _DecisionState:
    asset_id: str
    remaining: Decimal


class PaperTradingEngine:
    def __init__(
        self,
        *,
        spec: DemoSessionSpec,
        strategy: DemoStrategy,
        execution: DemoExecutionSimulator,
    ) -> None:
        self._spec = spec
        self._strategy = strategy
        self._execution = execution
        self._cash = _positive_decimal(spec.initial_cash, field="initial_cash")
        self._positions: dict[str, Decimal] = {}
        self._marks: dict[str, tuple[int, int]] = {}
        self._price_scales: dict[str, int] = {}
        self._pending: dict[str, _DecisionState] = {}
        self._decision_ids: list[str] = []
        self._seen_decision_ids: set[str] = set()
        self._fill_ids: list[str] = []
        self._seen_fill_ids: set[str] = set()
        self._step_record_ids: list[str] = []
        self._event_count = 0
        self._last_sequence = -1
        self._last_event_time_ns = -1

    @classmethod
    def restore(
        cls,
        *,
        spec: DemoSessionSpec,
        state: DemoPaperState,
        strategy: DemoStrategy,
        execution: DemoExecutionSimulator,
    ) -> PaperTradingEngine:
        if state.session_spec_id != spec.spec_id:
            raise DemoPaperError("state session_spec_id does not match spec")
        if _sha256_text(
            strategy.checkpoint_sha256(), field="strategy_checkpoint_sha256"
        ) != state.strategy_checkpoint_sha256:
            raise DemoPaperError("strategy checkpoint does not match state")
        if _sha256_text(
            execution.checkpoint_sha256(), field="execution_checkpoint_sha256"
        ) != state.execution_checkpoint_sha256:
            raise DemoPaperError("execution checkpoint does not match state")

        engine = cls(spec=spec, strategy=strategy, execution=execution)
        engine._cash = _finite_decimal(state.cash, field="state.cash")
        engine._positions = {
            asset_id: _finite_decimal(quantity, field="state.position")
            for asset_id, quantity in state.positions
        }
        engine._marks = {
            asset_id: (price_scaled, price_scale)
            for asset_id, price_scaled, price_scale in state.latest_marks
        }
        engine._price_scales = {
            asset_id: price_scale
            for asset_id, _, price_scale in state.latest_marks
        }
        engine._pending = {
            decision_id: _DecisionState(
                asset_id=asset_id,
                remaining=_finite_decimal(remaining, field="state.remaining"),
            )
            for decision_id, asset_id, remaining in state.pending_decisions
        }
        engine._decision_ids = list(state.decision_ids)
        engine._seen_decision_ids = set(state.decision_ids)
        engine._fill_ids = list(state.fill_ids)
        engine._seen_fill_ids = set(state.fill_ids)
        engine._step_record_ids = list(state.step_record_ids)
        engine._event_count = state.event_count
        engine._last_sequence = state.last_sequence
        engine._last_event_time_ns = state.last_event_time_ns
        return engine

    def _portfolio_view(self) -> DemoPortfolioView:
        equity = self._cash
        for asset_id, quantity in self._positions.items():
            if quantity == 0:
                continue
            mark = self._marks.get(asset_id)
            if mark is None:
                raise DemoPaperError(f"missing mark for held asset {asset_id}")
            price_scaled, price_scale = mark
            equity += quantity * Decimal(price_scaled) / Decimal(price_scale)
        return DemoPortfolioView(
            cash=_decimal_text(self._cash),
            equity=_decimal_text(equity),
            positions=tuple(
                (asset_id, _decimal_text(quantity))
                for asset_id, quantity in sorted(self._positions.items())
                if quantity != 0
            ),
            latest_marks=tuple(
                (asset_id, mark[0], mark[1])
                for asset_id, mark in sorted(self._marks.items())
            ),
        )

    def _apply_fill(self, fill: DemoFill, *, event: DemoMarketEvent) -> None:
        if fill.fill_id in self._seen_fill_ids:
            raise DemoPaperError("duplicate simulated fill ID")
        decision = self._pending.get(fill.decision_id)
        if decision is None:
            raise DemoPaperError("simulated fill references unknown decision")
        if fill.asset_id != decision.asset_id:
            raise DemoPaperError("simulated fill asset differs from decision asset")
        if fill.fill_time_ns != event.event_time_ns:
            raise DemoPaperError("simulated fill must be emitted at current event time")
        expected_scale = self._price_scales.get(fill.asset_id)
        if expected_scale is None or fill.price_scale != expected_scale:
            raise DemoPaperError("simulated fill price scale mismatch")

        quantity = _finite_decimal(fill.quantity_delta, field="fill.quantity_delta")
        remaining = decision.remaining
        if remaining * quantity <= 0:
            raise DemoPaperError("simulated fill direction differs from decision")
        if abs(quantity) > abs(remaining):
            raise DemoPaperError("simulated fill overfills decision")

        price = Decimal(fill.fill_price_scaled) / Decimal(fill.price_scale)
        cost = _non_negative_decimal(
            fill.explicit_cost_cash, field="fill.explicit_cost_cash"
        )
        self._cash -= quantity * price
        self._cash -= cost
        self._positions[fill.asset_id] = (
            self._positions.get(fill.asset_id, Decimal("0")) + quantity
        )
        decision.remaining -= quantity
        self._seen_fill_ids.add(fill.fill_id)
        self._fill_ids.append(fill.fill_id)
        if decision.remaining == 0:
            del self._pending[fill.decision_id]

    def snapshot(self) -> DemoPaperState:
        portfolio = self._portfolio_view()
        return DemoPaperState(
            session_spec_id=self._spec.spec_id,
            event_count=self._event_count,
            last_sequence=self._last_sequence,
            last_event_time_ns=self._last_event_time_ns,
            cash=portfolio.cash,
            equity=portfolio.equity,
            positions=portfolio.positions,
            latest_marks=portfolio.latest_marks,
            pending_decisions=tuple(
                (
                    decision_id,
                    state.asset_id,
                    _decimal_text(state.remaining),
                )
                for decision_id, state in sorted(self._pending.items())
            ),
            decision_ids=tuple(self._decision_ids),
            fill_ids=tuple(self._fill_ids),
            step_record_ids=tuple(self._step_record_ids),
            strategy_checkpoint_sha256=_sha256_text(
                self._strategy.checkpoint_sha256(),
                field="strategy_checkpoint_sha256",
            ),
            execution_checkpoint_sha256=_sha256_text(
                self._execution.checkpoint_sha256(),
                field="execution_checkpoint_sha256",
            ),
        )

    def ingest(self, event: DemoMarketEvent) -> DemoStepRecord:
        if event.sequence <= self._last_sequence:
            raise DemoPaperError("event sequence must increase strictly")
        if event.event_time_ns < self._last_event_time_ns:
            raise DemoPaperError("event time cannot decrease")

        prior_scale = self._price_scales.get(event.asset_id)
        if prior_scale is not None and prior_scale != event.price_scale:
            raise DemoPaperError("asset price scale cannot drift")

        self._price_scales[event.asset_id] = event.price_scale
        self._marks[event.asset_id] = (event.price_scaled, event.price_scale)

        fill_start = len(self._fill_ids)
        for fill in self._execution.on_market_event(event):
            self._apply_fill(fill, event=event)

        decision = self._strategy.on_event(event, self._portfolio_view())
        step_decisions: list[str] = []
        if decision is not None:
            if decision.decision_id in self._seen_decision_ids:
                raise DemoPaperError("duplicate demo decision ID")
            if decision.decision_time_ns != event.event_time_ns:
                raise DemoPaperError("decision time must equal current event time")
            if decision.asset_id != event.asset_id:
                raise DemoPaperError("decision asset must match current event asset")
            if any(
                state.asset_id == decision.asset_id
                for state in self._pending.values()
            ):
                raise DemoPaperError(
                    "overlapping unresolved demo decision for one asset"
                )
            quantity = _finite_decimal(
                decision.quantity_delta, field="decision.quantity_delta"
            )
            self._pending[decision.decision_id] = _DecisionState(
                asset_id=decision.asset_id,
                remaining=quantity,
            )
            self._seen_decision_ids.add(decision.decision_id)
            self._decision_ids.append(decision.decision_id)
            step_decisions.append(decision.decision_id)
            for fill in self._execution.submit(decision, event):
                self._apply_fill(fill, event=event)

        self._event_count += 1
        self._last_sequence = event.sequence
        self._last_event_time_ns = event.event_time_ns

        state = self.snapshot()
        record = DemoStepRecord(
            event_id=event.event_id,
            sequence=event.sequence,
            decision_ids=tuple(step_decisions),
            fill_ids=tuple(self._fill_ids[fill_start:]),
            state_id=state.state_id,
        )
        self._step_record_ids.append(record.record_id)
        return record
