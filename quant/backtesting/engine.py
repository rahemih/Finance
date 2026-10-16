from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Protocol, Sequence

from packages.historical_data.replay_snapshot import ReplaySnapshot


class BacktestEngineError(ValueError):
    """P17-A deterministic backtest engine invariant failure."""


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
        raise BacktestEngineError(f"{field} contains unsafe characters")
    return parsed


def _sha256_text(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise BacktestEngineError(f"{field} must be lowercase SHA-256")
    return parsed


def _finite_decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise BacktestEngineError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite():
        raise BacktestEngineError(f"{field} must be finite")
    return parsed


def _positive_decimal(value: str, *, field: str) -> Decimal:
    parsed = _finite_decimal(value, field=field)
    if parsed <= 0:
        raise BacktestEngineError(f"{field} must be positive")
    return parsed


def _non_negative_decimal(value: str, *, field: str) -> Decimal:
    parsed = _finite_decimal(value, field=field)
    if parsed < 0:
        raise BacktestEngineError(f"{field} must be non-negative")
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
class BacktestRunSpec:
    run_id: str
    replay_snapshot_id: str
    strategy_id: str
    strategy_artifact_sha256: str
    execution_simulator_artifact_sha256: str
    initial_cash: str
    base_currency: str

    def __post_init__(self) -> None:
        _safe_id(self.run_id, field="run_id")
        _sha256_text(self.replay_snapshot_id, field="replay_snapshot_id")
        _safe_id(self.strategy_id, field="strategy_id")
        _sha256_text(
            self.strategy_artifact_sha256,
            field="strategy_artifact_sha256",
        )
        _sha256_text(
            self.execution_simulator_artifact_sha256,
            field="execution_simulator_artifact_sha256",
        )
        _positive_decimal(self.initial_cash, field="initial_cash")
        _safe_id(self.base_currency, field="base_currency")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "replay_snapshot_id": self.replay_snapshot_id,
            "strategy_id": self.strategy_id,
            "strategy_artifact_sha256": self.strategy_artifact_sha256,
            "execution_simulator_artifact_sha256": (
                self.execution_simulator_artifact_sha256
            ),
            "initial_cash": _decimal_text(
                _positive_decimal(self.initial_cash, field="initial_cash")
            ),
            "base_currency": self.base_currency,
        }

    @property
    def spec_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class BacktestMarketEvent:
    sequence: int
    event_time_ns: int
    available_at_ns: int
    asset_id: str
    price_scaled: int
    price_scale: int

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise BacktestEngineError("sequence must be non-negative")
        if self.event_time_ns < 0 or self.available_at_ns < 0:
            raise BacktestEngineError("event timestamps must be non-negative")
        if self.available_at_ns > self.event_time_ns:
            raise BacktestEngineError(
                "available_at_ns cannot exceed simulated event_time_ns"
            )
        _safe_id(self.asset_id, field="asset_id")
        if self.price_scaled <= 0 or self.price_scale <= 0:
            raise BacktestEngineError(
                "price_scaled and price_scale must be positive"
            )

    def payload(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_time_ns": self.event_time_ns,
            "available_at_ns": self.available_at_ns,
            "asset_id": self.asset_id,
            "price_scaled": self.price_scaled,
            "price_scale": self.price_scale,
        }


@dataclass(frozen=True, slots=True)
class BacktestDecision:
    decision_id: str
    asset_id: str
    decision_time_ns: int
    quantity_delta: str

    def __post_init__(self) -> None:
        _safe_id(self.decision_id, field="decision_id")
        _safe_id(self.asset_id, field="asset_id")
        if self.decision_time_ns < 0:
            raise BacktestEngineError("decision_time_ns must be non-negative")
        quantity = _finite_decimal(self.quantity_delta, field="quantity_delta")
        if quantity == 0:
            raise BacktestEngineError("quantity_delta must be non-zero")

    def payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "asset_id": self.asset_id,
            "decision_time_ns": self.decision_time_ns,
            "quantity_delta": _decimal_text(
                _finite_decimal(self.quantity_delta, field="quantity_delta")
            ),
        }


@dataclass(frozen=True, slots=True)
class SimulatedFill:
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
            raise BacktestEngineError("fill_time_ns must be non-negative")
        quantity = _finite_decimal(self.quantity_delta, field="quantity_delta")
        if quantity == 0:
            raise BacktestEngineError("fill quantity_delta must be non-zero")
        if self.fill_price_scaled <= 0 or self.price_scale <= 0:
            raise BacktestEngineError(
                "fill_price_scaled and price_scale must be positive"
            )
        _non_negative_decimal(
            self.explicit_cost_cash,
            field="explicit_cost_cash",
        )

    def payload(self) -> dict[str, object]:
        return {
            "fill_id": self.fill_id,
            "decision_id": self.decision_id,
            "asset_id": self.asset_id,
            "fill_time_ns": self.fill_time_ns,
            "quantity_delta": _decimal_text(
                _finite_decimal(self.quantity_delta, field="quantity_delta")
            ),
            "fill_price_scaled": self.fill_price_scaled,
            "price_scale": self.price_scale,
            "explicit_cost_cash": _decimal_text(
                _non_negative_decimal(
                    self.explicit_cost_cash,
                    field="explicit_cost_cash",
                )
            ),
        }


@dataclass(frozen=True, slots=True)
class BacktestPortfolioView:
    cash: str
    equity: str
    positions: tuple[tuple[str, str], ...]
    latest_marks: tuple[tuple[str, int, int], ...]


@dataclass(frozen=True, slots=True)
class EquityPoint:
    sequence: int
    event_time_ns: int
    equity: str

    def payload(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_time_ns": self.event_time_ns,
            "equity": self.equity,
        }


class StrategyEvaluator(Protocol):
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        ...


class ExecutionSimulator(Protocol):
    def on_market_event(
        self,
        event: BacktestMarketEvent,
    ) -> Sequence[SimulatedFill]:
        ...

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> Sequence[SimulatedFill]:
        ...


@dataclass(frozen=True, slots=True)
class BacktestResult:
    result_id: str
    run_id: str
    replay_snapshot_id: str
    status: str
    event_count: int
    decision_ids: tuple[str, ...]
    fill_ids: tuple[str, ...]
    pending_decision_ids: tuple[str, ...]
    initial_cash: str
    ending_cash: str
    ending_equity: str
    pnl_cash: str
    ending_positions: tuple[tuple[str, str], ...]
    equity_curve: tuple[EquityPoint, ...]
    execution_realism_owner: str = "P17-B"
    g9_authority: bool = False
    profitability_claim_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


@dataclass(slots=True)
class _DecisionState:
    asset_id: str
    remaining: Decimal


def _portfolio_view(
    *,
    cash: Decimal,
    positions: dict[str, Decimal],
    marks: dict[str, tuple[int, int]],
) -> BacktestPortfolioView:
    equity = cash
    for asset_id, quantity in positions.items():
        if quantity == 0:
            continue
        mark = marks.get(asset_id)
        if mark is None:
            raise BacktestEngineError(
                f"missing mark for held asset {asset_id}"
            )
        price_scaled, price_scale = mark
        equity += quantity * Decimal(price_scaled) / Decimal(price_scale)
    return BacktestPortfolioView(
        cash=_decimal_text(cash),
        equity=_decimal_text(equity),
        positions=tuple(
            (asset_id, _decimal_text(quantity))
            for asset_id, quantity in sorted(positions.items())
            if quantity != 0
        ),
        latest_marks=tuple(
            (asset_id, value[0], value[1])
            for asset_id, value in sorted(marks.items())
        ),
    )


def run_backtest(
    *,
    spec: BacktestRunSpec,
    snapshot: ReplaySnapshot,
    events: Sequence[BacktestMarketEvent],
    strategy: StrategyEvaluator,
    execution: ExecutionSimulator,
) -> BacktestResult:
    if spec.replay_snapshot_id != snapshot.snapshot_id:
        raise BacktestEngineError(
            "run spec replay_snapshot_id does not match snapshot"
        )

    ordered = tuple(sorted(events, key=lambda item: item.sequence))
    if not ordered:
        raise BacktestEngineError("backtest requires at least one market event")
    sequences = [item.sequence for item in ordered]
    if len(sequences) != len(set(sequences)):
        raise BacktestEngineError("duplicate market event sequence")

    previous_time: int | None = None
    for event in ordered:
        if previous_time is not None and event.event_time_ns < previous_time:
            raise BacktestEngineError(
                "market event time decreases in canonical sequence order"
            )
        snapshot.view_at(event.event_time_ns)
        previous_time = event.event_time_ns

    initial_cash = _positive_decimal(spec.initial_cash, field="initial_cash")
    cash = initial_cash
    positions: dict[str, Decimal] = {}
    marks: dict[str, tuple[int, int]] = {}
    price_scales: dict[str, int] = {}
    decisions: dict[str, _DecisionState] = {}
    decision_ids: list[str] = []
    fill_ids: list[str] = []
    seen_fill_ids: set[str] = set()
    equity_curve: list[EquityPoint] = []

    def apply_fill(fill: SimulatedFill, *, event: BacktestMarketEvent) -> None:
        nonlocal cash
        if fill.fill_id in seen_fill_ids:
            raise BacktestEngineError("duplicate simulated fill ID")
        state = decisions.get(fill.decision_id)
        if state is None:
            raise BacktestEngineError(
                "simulated fill references unknown decision"
            )
        if fill.asset_id != state.asset_id:
            raise BacktestEngineError(
                "simulated fill asset does not match decision asset"
            )
        if fill.fill_time_ns != event.event_time_ns:
            raise BacktestEngineError(
                "simulated fill must be emitted on its fill-time market event"
            )
        expected_scale = price_scales.get(fill.asset_id)
        if expected_scale is None:
            raise BacktestEngineError(
                "simulated fill asset has no known market price scale"
            )
        if fill.price_scale != expected_scale:
            raise BacktestEngineError(
                "simulated fill price scale differs from canonical asset scale"
            )

        quantity = _finite_decimal(
            fill.quantity_delta,
            field="fill.quantity_delta",
        )
        remaining = state.remaining
        if remaining == 0:
            raise BacktestEngineError("simulated fill exceeds completed decision")
        if remaining * quantity <= 0:
            raise BacktestEngineError(
                "simulated fill direction differs from remaining decision"
            )
        if abs(quantity) > abs(remaining):
            raise BacktestEngineError("simulated fill overfills decision")

        cost = _non_negative_decimal(
            fill.explicit_cost_cash,
            field="fill.explicit_cost_cash",
        )
        trade_cash = (
            quantity
            * Decimal(fill.fill_price_scaled)
            / Decimal(fill.price_scale)
        )
        cash -= trade_cash + cost
        positions[fill.asset_id] = (
            positions.get(fill.asset_id, Decimal(0)) + quantity
        )
        state.remaining -= quantity
        seen_fill_ids.add(fill.fill_id)
        fill_ids.append(fill.fill_id)

    for event in ordered:
        existing_scale = price_scales.get(event.asset_id)
        if existing_scale is not None and existing_scale != event.price_scale:
            raise BacktestEngineError(
                "asset price scale changed during backtest"
            )
        price_scales[event.asset_id] = event.price_scale
        marks[event.asset_id] = (event.price_scaled, event.price_scale)

        delayed_fills = tuple(
            sorted(
                execution.on_market_event(event),
                key=lambda item: (item.fill_time_ns, item.fill_id),
            )
        )
        for fill in delayed_fills:
            apply_fill(fill, event=event)

        portfolio = _portfolio_view(
            cash=cash,
            positions=positions,
            marks=marks,
        )
        decision = strategy.on_event(event, portfolio)
        if decision is not None:
            if decision.decision_time_ns != event.event_time_ns:
                raise BacktestEngineError(
                    "strategy decision_time_ns must equal current event_time_ns"
                )
            if decision.decision_id in decisions:
                raise BacktestEngineError("duplicate strategy decision ID")
            if any(
                item.asset_id == decision.asset_id and item.remaining != 0
                for item in decisions.values()
            ):
                raise BacktestEngineError(
                    "new decision overlaps unresolved decision for asset"
                )
            decisions[decision.decision_id] = _DecisionState(
                asset_id=decision.asset_id,
                remaining=_finite_decimal(
                    decision.quantity_delta,
                    field="decision.quantity_delta",
                ),
            )
            decision_ids.append(decision.decision_id)

            immediate_fills = tuple(
                sorted(
                    execution.submit(decision, event),
                    key=lambda item: (item.fill_time_ns, item.fill_id),
                )
            )
            for fill in immediate_fills:
                apply_fill(fill, event=event)

        current = _portfolio_view(
            cash=cash,
            positions=positions,
            marks=marks,
        )
        equity_curve.append(
            EquityPoint(
                sequence=event.sequence,
                event_time_ns=event.event_time_ns,
                equity=current.equity,
            )
        )

    final_view = _portfolio_view(
        cash=cash,
        positions=positions,
        marks=marks,
    )
    ending_equity = _finite_decimal(
        final_view.equity,
        field="ending_equity",
    )
    pending = tuple(
        sorted(
            decision_id
            for decision_id, state in decisions.items()
            if state.remaining != 0
        )
    )
    status = (
        "COMPLETED"
        if not pending
        else "COMPLETED_WITH_UNRESOLVED_DECISIONS"
    )
    body: dict[str, object] = {
        "schema_version": "1.0",
        "spec_id": spec.spec_id,
        "replay_snapshot_id": snapshot.snapshot_id,
        "events": [item.payload() for item in ordered],
        "status": status,
        "decision_ids": decision_ids,
        "fill_ids": fill_ids,
        "pending_decision_ids": list(pending),
        "initial_cash": _decimal_text(initial_cash),
        "ending_cash": final_view.cash,
        "ending_equity": final_view.equity,
        "pnl_cash": _decimal_text(ending_equity - initial_cash),
        "ending_positions": [list(item) for item in final_view.positions],
        "equity_curve": [item.payload() for item in equity_curve],
        "execution_realism_owner": "P17-B",
        "g9_authority": False,
        "profitability_claim_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    result_id = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    return BacktestResult(
        result_id=result_id,
        run_id=spec.run_id,
        replay_snapshot_id=snapshot.snapshot_id,
        status=status,
        event_count=len(ordered),
        decision_ids=tuple(decision_ids),
        fill_ids=tuple(fill_ids),
        pending_decision_ids=pending,
        initial_cash=_decimal_text(initial_cash),
        ending_cash=final_view.cash,
        ending_equity=final_view.equity,
        pnl_cash=_decimal_text(ending_equity - initial_cash),
        ending_positions=final_view.positions,
        equity_curve=tuple(equity_curve),
    )
