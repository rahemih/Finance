from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
import re
from typing import Sequence

from .engine import (
    BacktestDecision,
    BacktestEngineError,
    BacktestMarketEvent,
    BacktestPortfolioView,
    SimulatedCashAdjustment,
    SimulatedFill,
)


class ExecutionRealismError(BacktestEngineError):
    """P17-B historical execution-realism input or state is invalid."""


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
        raise ExecutionRealismError(f"{field} contains unsafe characters")
    return parsed


def _sha256_text(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise ExecutionRealismError(f"{field} must be lowercase SHA-256")
    return parsed


def _decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ExecutionRealismError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite():
        raise ExecutionRealismError(f"{field} must be finite")
    return parsed


def _positive_decimal(value: str, *, field: str) -> Decimal:
    parsed = _decimal(value, field=field)
    if parsed <= 0:
        raise ExecutionRealismError(f"{field} must be positive")
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
class ExecutionRealismPolicy:
    policy_version: str
    taker_fee_bps: int
    decision_latency_ns: int
    max_displayed_depth_participation_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ExecutionRealismError("policy_version must be non-empty")
        if not 0 <= self.taker_fee_bps <= 10_000:
            raise ExecutionRealismError("taker_fee_bps must be within [0,10000]")
        if self.decision_latency_ns < 0:
            raise ExecutionRealismError("decision_latency_ns must be non-negative")
        if not 1 <= self.max_displayed_depth_participation_bps <= 10_000:
            raise ExecutionRealismError(
                "max_displayed_depth_participation_bps must be within [1,10000]"
            )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "policy_version": self.policy_version,
                    "taker_fee_bps": self.taker_fee_bps,
                    "decision_latency_ns": self.decision_latency_ns,
                    "max_displayed_depth_participation_bps": (
                        self.max_displayed_depth_participation_bps
                    ),
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class HistoricalDepthLevel:
    price_scaled: int
    quantity_text: str

    def __post_init__(self) -> None:
        if self.price_scaled <= 0:
            raise ExecutionRealismError("depth price_scaled must be positive")
        _positive_decimal(self.quantity_text, field="depth quantity_text")

    @property
    def quantity(self) -> Decimal:
        return _positive_decimal(self.quantity_text, field="depth quantity_text")

    def payload(self) -> dict[str, object]:
        return {
            "price_scaled": self.price_scaled,
            "quantity_text": _decimal_text(self.quantity),
        }


@dataclass(frozen=True, slots=True)
class HistoricalExecutionContext:
    sequence: int
    event_time_ns: int
    available_at_ns: int
    asset_id: str
    price_scale: int
    bids: tuple[HistoricalDepthLevel, ...]
    asks: tuple[HistoricalDepthLevel, ...]
    source_evidence_sha256: str
    funding_due: bool = False
    funding_rate_text: str | None = None
    funding_mark_price_scaled: int | None = None
    funding_evidence_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ExecutionRealismError("sequence must be non-negative")
        if self.event_time_ns < 0 or self.available_at_ns < 0:
            raise ExecutionRealismError("context timestamps must be non-negative")
        if self.available_at_ns > self.event_time_ns:
            raise ExecutionRealismError(
                "execution context cannot be available after simulated event"
            )
        _safe_id(self.asset_id, field="asset_id")
        if self.price_scale <= 0:
            raise ExecutionRealismError("price_scale must be positive")
        _sha256_text(self.source_evidence_sha256, field="source_evidence_sha256")
        if not self.bids or not self.asks:
            raise ExecutionRealismError("historical context requires bids and asks")

        bid_prices = [item.price_scaled for item in self.bids]
        ask_prices = [item.price_scaled for item in self.asks]
        if any(bid_prices[i] <= bid_prices[i + 1] for i in range(len(bid_prices) - 1)):
            raise ExecutionRealismError("bids must be strictly descending")
        if any(ask_prices[i] >= ask_prices[i + 1] for i in range(len(ask_prices) - 1)):
            raise ExecutionRealismError("asks must be strictly ascending")
        if bid_prices[0] >= ask_prices[0]:
            raise ExecutionRealismError("historical book cannot be locked/crossed")

        funding_fields = (
            self.funding_rate_text,
            self.funding_mark_price_scaled,
            self.funding_evidence_sha256,
        )
        if self.funding_due:
            if any(value is None for value in funding_fields):
                raise ExecutionRealismError(
                    "funding_due requires rate, mark price and evidence"
                )
            rate = self.funding_rate_text
            mark = self.funding_mark_price_scaled
            evidence = self.funding_evidence_sha256
            assert rate is not None and mark is not None and evidence is not None
            _decimal(rate, field="funding_rate_text")
            if mark <= 0:
                raise ExecutionRealismError(
                    "funding_mark_price_scaled must be positive"
                )
            _sha256_text(evidence, field="funding_evidence_sha256")
        elif any(value is not None for value in funding_fields):
            raise ExecutionRealismError(
                "funding fields are forbidden when funding_due is false"
            )

    def payload(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_time_ns": self.event_time_ns,
            "available_at_ns": self.available_at_ns,
            "asset_id": self.asset_id,
            "price_scale": self.price_scale,
            "bids": [item.payload() for item in self.bids],
            "asks": [item.payload() for item in self.asks],
            "source_evidence_sha256": self.source_evidence_sha256,
            "funding_due": self.funding_due,
            "funding_rate_text": self.funding_rate_text,
            "funding_mark_price_scaled": self.funding_mark_price_scaled,
            "funding_evidence_sha256": self.funding_evidence_sha256,
        }

    @property
    def context_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionRealismDiagnostic:
    decision_id: str
    context_id: str
    side: str
    requested_quantity: str
    filled_quantity: str
    fill_price_scaled: int | None
    visible_best_price_scaled: int
    fee_cash: str
    depth_levels_consumed: int

    def payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "context_id": self.context_id,
            "side": self.side,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "fill_price_scaled": self.fill_price_scaled,
            "visible_best_price_scaled": self.visible_best_price_scaled,
            "fee_cash": self.fee_cash,
            "depth_levels_consumed": self.depth_levels_consumed,
        }


@dataclass(slots=True)
class _PendingDecision:
    decision: BacktestDecision
    remaining: Decimal
    eligible_at_ns: int


class HistoricalExecutionSimulator:
    def __init__(
        self,
        *,
        policy: ExecutionRealismPolicy,
        contexts: Sequence[HistoricalExecutionContext],
    ) -> None:
        self._policy = policy
        by_sequence: dict[int, HistoricalExecutionContext] = {}
        for context in contexts:
            if context.sequence in by_sequence:
                raise ExecutionRealismError("duplicate execution context sequence")
            by_sequence[context.sequence] = context
        if not by_sequence:
            raise ExecutionRealismError("at least one execution context is required")
        self._contexts = by_sequence
        self._pending: dict[str, _PendingDecision] = {}
        self._funding_applied: set[str] = set()
        self._diagnostics: list[ExecutionRealismDiagnostic] = []

    @property
    def policy(self) -> ExecutionRealismPolicy:
        return self._policy

    @property
    def diagnostics(self) -> tuple[ExecutionRealismDiagnostic, ...]:
        return tuple(self._diagnostics)

    def _context(self, event: BacktestMarketEvent) -> HistoricalExecutionContext:
        context = self._contexts.get(event.sequence)
        if context is None:
            raise ExecutionRealismError(
                "missing historical execution context for market event"
            )
        if (
            context.event_time_ns != event.event_time_ns
            or context.asset_id != event.asset_id
            or context.price_scale != event.price_scale
        ):
            raise ExecutionRealismError(
                "historical execution context does not match market event"
            )
        if context.available_at_ns > event.event_time_ns:
            raise ExecutionRealismError(
                "historical execution context violates point-in-time safety"
            )
        return context

    def _attempt_fill(
        self,
        pending: _PendingDecision,
        *,
        context: HistoricalExecutionContext,
    ) -> SimulatedFill | None:
        if context.event_time_ns < pending.eligible_at_ns:
            return None
        remaining = pending.remaining
        if remaining == 0:
            return None

        side = "BUY" if remaining > 0 else "SELL"
        levels = context.asks if side == "BUY" else context.bids
        target = abs(remaining)
        filled = Decimal(0)
        notional_scaled = Decimal(0)
        consumed = 0
        for level in levels:
            allowed = (
                level.quantity
                * Decimal(self._policy.max_displayed_depth_participation_bps)
                / Decimal(10_000)
            )
            if allowed <= 0:
                continue
            take = min(target - filled, allowed)
            if take <= 0:
                break
            filled += take
            notional_scaled += take * Decimal(level.price_scaled)
            consumed += 1
            if filled >= target:
                break

        best_price = levels[0].price_scaled
        if filled <= 0:
            self._diagnostics.append(
                ExecutionRealismDiagnostic(
                    pending.decision.decision_id,
                    context.context_id,
                    side,
                    _decimal_text(target),
                    "0",
                    None,
                    best_price,
                    "0",
                    0,
                )
            )
            return None

        raw_scaled = notional_scaled / filled
        rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
        fill_price_scaled = int(raw_scaled.to_integral_value(rounding=rounding))
        signed_quantity = filled if side == "BUY" else -filled
        fill_notional = (
            filled
            * Decimal(fill_price_scaled)
            / Decimal(context.price_scale)
        )
        fee = (
            fill_notional
            * Decimal(self._policy.taker_fee_bps)
            / Decimal(10_000)
        )
        pending.remaining -= signed_quantity

        diagnostic = ExecutionRealismDiagnostic(
            decision_id=pending.decision.decision_id,
            context_id=context.context_id,
            side=side,
            requested_quantity=_decimal_text(target),
            filled_quantity=_decimal_text(filled),
            fill_price_scaled=fill_price_scaled,
            visible_best_price_scaled=best_price,
            fee_cash=_decimal_text(fee),
            depth_levels_consumed=consumed,
        )
        self._diagnostics.append(diagnostic)

        fill_body = {
            "decision_id": pending.decision.decision_id,
            "context_id": context.context_id,
            "fill_time_ns": context.event_time_ns,
            "quantity_delta": _decimal_text(signed_quantity),
            "fill_price_scaled": fill_price_scaled,
            "fee_cash": _decimal_text(fee),
        }
        fill_id = hashlib.sha256(_canonical_bytes(fill_body)).hexdigest()
        return SimulatedFill(
            fill_id=fill_id,
            decision_id=pending.decision.decision_id,
            asset_id=pending.decision.asset_id,
            fill_time_ns=context.event_time_ns,
            quantity_delta=_decimal_text(signed_quantity),
            fill_price_scaled=fill_price_scaled,
            price_scale=context.price_scale,
            explicit_cost_cash=_decimal_text(fee),
        )

    def on_market_event(
        self,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        context = self._context(event)
        fills: list[SimulatedFill] = []
        for decision_id in sorted(self._pending):
            pending = self._pending[decision_id]
            if pending.decision.asset_id != event.asset_id:
                continue
            fill = self._attempt_fill(pending, context=context)
            if fill is not None:
                fills.append(fill)
        return tuple(fills)

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        context = self._context(event)
        if decision.decision_id in self._pending:
            raise ExecutionRealismError("duplicate submitted decision")
        pending = _PendingDecision(
            decision=decision,
            remaining=_decimal(
                decision.quantity_delta,
                field="decision.quantity_delta",
            ),
            eligible_at_ns=(
                decision.decision_time_ns + self._policy.decision_latency_ns
            ),
        )
        self._pending[decision.decision_id] = pending
        if pending.eligible_at_ns > event.event_time_ns:
            return ()
        fill = self._attempt_fill(pending, context=context)
        return () if fill is None else (fill,)

    def cash_adjustments_on_market_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> tuple[SimulatedCashAdjustment, ...]:
        context = self._context(event)
        if not context.funding_due:
            return ()

        funding_key = context.context_id
        if funding_key in self._funding_applied:
            raise ExecutionRealismError("funding context applied more than once")
        self._funding_applied.add(funding_key)

        position_map = {
            asset_id: _decimal(quantity, field="portfolio position")
            for asset_id, quantity in portfolio.positions
        }
        position = position_map.get(context.asset_id, Decimal(0))
        if position == 0:
            return ()

        rate_text = context.funding_rate_text
        mark_scaled = context.funding_mark_price_scaled
        evidence = context.funding_evidence_sha256
        assert rate_text is not None and mark_scaled is not None and evidence is not None
        rate = _decimal(rate_text, field="funding_rate_text")
        mark = Decimal(mark_scaled) / Decimal(context.price_scale)
        amount = -(position * mark * rate)
        if amount == 0:
            return ()

        body = {
            "context_id": context.context_id,
            "asset_id": context.asset_id,
            "event_time_ns": context.event_time_ns,
            "position": _decimal_text(position),
            "funding_mark": _decimal_text(mark),
            "funding_rate": _decimal_text(rate),
            "amount_cash": _decimal_text(amount),
            "funding_evidence_sha256": evidence,
        }
        adjustment_id = hashlib.sha256(_canonical_bytes(body)).hexdigest()
        return (
            SimulatedCashAdjustment(
                adjustment_id=adjustment_id,
                asset_id=context.asset_id,
                event_time_ns=context.event_time_ns,
                amount_cash=_decimal_text(amount),
                kind="FUNDING",
                evidence_sha256=evidence,
            ),
        )
