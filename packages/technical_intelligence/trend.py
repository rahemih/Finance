from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .foundation import (
    IndicatorDefinition,
    TechnicalEvidence,
    TechnicalFoundationError,
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    simple_moving_average,
)


class TrendFamilyError(TechnicalFoundationError):
    """Trend-family inputs or policy violate governed P08-B invariants."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TrendFamilyError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrendFamilyError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TrendFamilyError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TrendFamilyError(f"{field} must be a non-negative integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise TrendFamilyError(f"{field} must be boolean")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise TrendFamilyError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise TrendFamilyError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise TrendFamilyError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _ratio_bps(numerator: Decimal, denominator: Decimal, *, field: str) -> int:
    if denominator == 0:
        raise TrendFamilyError(f"{field} denominator cannot be zero")
    raw = (numerator / abs(denominator)) * Decimal(10_000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


@dataclass(frozen=True, slots=True)
class TrendFamilyPolicy:
    independence_group: str
    fast_window: int
    slow_window: int
    slope_offset_bars: int
    min_alignment_bps: int
    min_slope_bps: int
    min_price_distance_bps: int
    base_directional_confidence_bps: int
    max_strength_bps: int
    max_confidence_bps: int
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "TrendFamilyPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise TrendFamilyError("unsupported trend policy schema_version")
        if raw.get("family") != "TREND":
            raise TrendFamilyError("trend policy family must be TREND")
        if raw.get("score_semantics") != "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY":
            raise TrendFamilyError("trend score semantics must not claim empirical trade probability")
        fast = _positive_int(raw.get("fast_window"), field="fast_window")
        slow = _positive_int(raw.get("slow_window"), field="slow_window")
        slope = _positive_int(raw.get("slope_offset_bars"), field="slope_offset_bars")
        if fast >= slow:
            raise TrendFamilyError("fast_window must be smaller than slow_window")
        max_strength = _positive_int(raw.get("max_strength_bps"), field="max_strength_bps")
        max_confidence = _positive_int(raw.get("max_confidence_bps"), field="max_confidence_bps")
        if max_strength > 10_000 or max_confidence > 10_000:
            raise TrendFamilyError("trend score bounds cannot exceed 10000 bps")
        base_confidence = _non_negative_int(
            raw.get("base_directional_confidence_bps"),
            field="base_directional_confidence_bps",
        )
        if base_confidence > max_confidence:
            raise TrendFamilyError("base confidence cannot exceed maximum confidence")
        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise TrendFamilyError("P08-B forbids direct trade output")
        return cls(
            independence_group=_text(raw.get("independence_group"), field="independence_group"),
            fast_window=fast,
            slow_window=slow,
            slope_offset_bars=slope,
            min_alignment_bps=_non_negative_int(raw.get("min_alignment_bps"), field="min_alignment_bps"),
            min_slope_bps=_non_negative_int(raw.get("min_slope_bps"), field="min_slope_bps"),
            min_price_distance_bps=_non_negative_int(
                raw.get("min_price_distance_bps"),
                field="min_price_distance_bps",
            ),
            base_directional_confidence_bps=base_confidence,
            max_strength_bps=max_strength,
            max_confidence_bps=max_confidence,
            direct_trade_output_allowed=direct_trade,
        )

    @property
    def required_bars(self) -> int:
        return self.slow_window + self.slope_offset_bars


@dataclass(frozen=True, slots=True)
class TrendEvaluation:
    fast_sma_text: str
    slow_sma_text: str
    previous_slow_sma_text: str
    alignment_bps: int
    slope_bps: int
    price_distance_bps: int
    evidence: TechnicalEvidence


class TrendFamilyModel:
    def __init__(
        self,
        *,
        foundation_policy: TechnicalFoundationPolicy,
        trend_policy: TrendFamilyPolicy,
    ) -> None:
        if "TREND" not in foundation_policy.allowed_families:
            raise TrendFamilyError("foundation policy does not allow TREND family")
        if trend_policy.required_bars > foundation_policy.max_lookback_bars:
            raise TrendFamilyError("trend required history exceeds foundation lookback bound")
        self._foundation_policy = foundation_policy
        self._trend_policy = trend_policy

    def _window(self, bars: Sequence[TrustedOHLCVBar]) -> tuple[TrustedOHLCVBar, ...]:
        required = self._trend_policy.required_bars
        if len(bars) < required:
            raise TrendFamilyError("insufficient bars for trend-family evaluation")
        window = tuple(bars[-required:])
        first = window[0]
        evaluation_as_of = window[-1].as_of_time_ns
        previous_event = -1
        for bar in window:
            if bar.symbol != first.symbol:
                raise TrendFamilyError("trend window must use one symbol")
            if bar.timeframe != first.timeframe:
                raise TrendFamilyError("trend window must use one timeframe")
            if bar.source_dataset_version != first.source_dataset_version:
                raise TrendFamilyError("trend window must use one dataset version")
            if bar.quality_evidence_sha256 != first.quality_evidence_sha256:
                raise TrendFamilyError("trend window must use one quality evidence lineage")
            if bar.event_time_ns <= previous_event:
                raise TrendFamilyError("trend event times must be strictly increasing")
            if bar.as_of_time_ns > evaluation_as_of:
                raise TrendFamilyError("trend window contains future as-of information")
            previous_event = bar.event_time_ns
        return window

    def definition(self) -> IndicatorDefinition:
        p = self._trend_policy
        return IndicatorDefinition(
            name="trend.dual-sma-slope",
            version="1.0.0",
            family="TREND",
            independence_group=p.independence_group,
            lookback_bars=p.required_bars,
            output_unit="BPS",
            parameters=(
                ("fast_window", str(p.fast_window)),
                ("slow_window", str(p.slow_window)),
                ("slope_offset_bars", str(p.slope_offset_bars)),
                ("min_alignment_bps", str(p.min_alignment_bps)),
                ("min_slope_bps", str(p.min_slope_bps)),
                ("min_price_distance_bps", str(p.min_price_distance_bps)),
            ),
        )

    def evaluate(self, bars: Sequence[TrustedOHLCVBar]) -> TrendEvaluation:
        p = self._trend_policy
        window = self._window(bars)
        current_slow_window = window[-p.slow_window :]
        previous_slow_window = window[-(p.slow_window + p.slope_offset_bars) : -p.slope_offset_bars]
        current_fast_window = window[-p.fast_window :]

        fast_sma = simple_moving_average(
            current_fast_window,
            lookback_bars=p.fast_window,
            policy=self._foundation_policy,
        )
        slow_sma = simple_moving_average(
            current_slow_window,
            lookback_bars=p.slow_window,
            policy=self._foundation_policy,
        )
        previous_slow_sma = simple_moving_average(
            previous_slow_window,
            lookback_bars=p.slow_window,
            policy=self._foundation_policy,
        )
        latest_close = _decimal(window[-1].close_text, field="latest_close")

        alignment_bps = _ratio_bps(fast_sma - slow_sma, slow_sma, field="alignment")
        slope_bps = _ratio_bps(slow_sma - previous_slow_sma, previous_slow_sma, field="slope")
        price_distance_bps = _ratio_bps(
            latest_close - slow_sma,
            slow_sma,
            field="price_distance",
        )

        bullish = (
            alignment_bps >= p.min_alignment_bps
            and slope_bps >= p.min_slope_bps
            and price_distance_bps >= p.min_price_distance_bps
        )
        bearish = (
            alignment_bps <= -p.min_alignment_bps
            and slope_bps <= -p.min_slope_bps
            and price_distance_bps <= -p.min_price_distance_bps
        )
        direction = 1 if bullish else (-1 if bearish else 0)

        if direction == 0:
            strength = 0
            confidence = 0
        else:
            raw_strength = (
                abs(alignment_bps) + abs(slope_bps) + abs(price_distance_bps)
            ) // 3
            strength = min(
                p.max_strength_bps,
                self._foundation_policy.max_strength_bps,
                raw_strength,
            )
            confidence = min(
                p.max_confidence_bps,
                self._foundation_policy.max_confidence_bps,
                p.base_directional_confidence_bps + strength // 2,
            )

        definition = self.definition()
        latest = window[-1]
        evidence = TechnicalEvidence(
            definition_id=definition.definition_id,
            family="TREND",
            independence_group=p.independence_group,
            symbol=latest.symbol,
            timeframe=latest.timeframe,
            direction=direction,
            strength_bps=strength,
            confidence_bps=confidence,
            event_time_ns=latest.event_time_ns,
            as_of_time_ns=latest.as_of_time_ns,
            value_text=str(direction * strength),
            invalidation=(
                "trend family invalidates when fast/slow alignment, slow-baseline slope, "
                "and price distance no longer satisfy the governed directional thresholds"
            ),
            source_dataset_version=latest.source_dataset_version,
            quality_evidence_sha256=latest.quality_evidence_sha256,
        )
        return TrendEvaluation(
            fast_sma_text=_decimal_text(fast_sma),
            slow_sma_text=_decimal_text(slow_sma),
            previous_slow_sma_text=_decimal_text(previous_slow_sma),
            alignment_bps=alignment_bps,
            slope_bps=slope_bps,
            price_distance_bps=price_distance_bps,
            evidence=evidence,
        )
