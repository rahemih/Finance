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
)


class BreakoutExpansionError(TechnicalFoundationError):
    """P08-F inputs or policy violate governed breakout/expansion invariants."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise BreakoutExpansionError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BreakoutExpansionError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BreakoutExpansionError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BreakoutExpansionError(f"{field} must be a non-negative integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise BreakoutExpansionError(f"{field} must be boolean")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise BreakoutExpansionError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BreakoutExpansionError(
            f"{field} must be decimal-compatible"
        ) from exc
    if not result.is_finite():
        raise BreakoutExpansionError(f"{field} must be finite")
    return result


def _ratio_bps(numerator: Decimal, denominator: Decimal, *, field: str) -> int:
    if denominator == 0:
        raise BreakoutExpansionError(f"{field} denominator cannot be zero")
    raw = (numerator / abs(denominator)) * Decimal(10_000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _average(values: Sequence[Decimal], *, field: str) -> Decimal:
    if not values:
        raise BreakoutExpansionError(f"{field} requires values")
    return (
        sum(values, Decimal("0")) / Decimal(len(values))
    ).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class BreakoutExpansionPolicy:
    independence_group: str
    cross_family_independence_status: str
    channel_lookback_bars: int
    breakout_buffer_bps: int
    min_expansion_ratio_bps: int
    expansion_confirmation_bonus_bps: int
    base_directional_confidence_bps: int
    max_strength_bps: int
    max_confidence_bps: int
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "BreakoutExpansionPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise BreakoutExpansionError("unsupported P08-F policy schema_version")
        if raw.get("family") != "BREAKOUT":
            raise BreakoutExpansionError("P08-F family must be BREAKOUT")
        if raw.get("cross_family_independence_status") != "PROVISIONAL_PENDING_P08_H":
            raise BreakoutExpansionError(
                "cross-family independence must remain pending P08-H"
            )
        if raw.get("score_semantics") != "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY":
            raise BreakoutExpansionError(
                "P08-F scores must not claim trade probability"
            )

        lookback = _positive_int(
            raw.get("channel_lookback_bars"),
            field="channel_lookback_bars",
        )
        if lookback < 2:
            raise BreakoutExpansionError("channel_lookback_bars must be >= 2")

        max_strength = _positive_int(
            raw.get("max_strength_bps"),
            field="max_strength_bps",
        )
        max_confidence = _positive_int(
            raw.get("max_confidence_bps"),
            field="max_confidence_bps",
        )
        if max_strength > 10_000 or max_confidence > 10_000:
            raise BreakoutExpansionError(
                "P08-F score bounds cannot exceed 10000 bps"
            )

        base_confidence = _non_negative_int(
            raw.get("base_directional_confidence_bps"),
            field="base_directional_confidence_bps",
        )
        if base_confidence > max_confidence:
            raise BreakoutExpansionError(
                "base confidence cannot exceed max confidence"
            )

        expansion_ratio = _positive_int(
            raw.get("min_expansion_ratio_bps"),
            field="min_expansion_ratio_bps",
        )
        if expansion_ratio < 10_000:
            raise BreakoutExpansionError(
                "min_expansion_ratio_bps must be >= 10000"
            )

        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise BreakoutExpansionError("P08-F forbids direct trade output")

        return cls(
            independence_group=_text(
                raw.get("independence_group"),
                field="independence_group",
            ),
            cross_family_independence_status=_text(
                raw.get("cross_family_independence_status"),
                field="cross_family_independence_status",
            ),
            channel_lookback_bars=lookback,
            breakout_buffer_bps=_non_negative_int(
                raw.get("breakout_buffer_bps"),
                field="breakout_buffer_bps",
            ),
            min_expansion_ratio_bps=expansion_ratio,
            expansion_confirmation_bonus_bps=_non_negative_int(
                raw.get("expansion_confirmation_bonus_bps"),
                field="expansion_confirmation_bonus_bps",
            ),
            base_directional_confidence_bps=base_confidence,
            max_strength_bps=max_strength,
            max_confidence_bps=max_confidence,
            direct_trade_output_allowed=direct_trade,
        )

    @property
    def required_bars(self) -> int:
        return self.channel_lookback_bars + 1


@dataclass(frozen=True, slots=True)
class BreakoutExpansionEvaluation:
    prior_channel_high_text: str
    prior_channel_low_text: str
    prior_average_range_text: str
    current_range_text: str
    breakout_distance_bps: int
    expansion_ratio_bps: int
    expansion_confirmed: bool
    evidence: TechnicalEvidence
    cross_family_independence_status: str


class BreakoutExpansionModel:
    def __init__(
        self,
        *,
        foundation_policy: TechnicalFoundationPolicy,
        policy: BreakoutExpansionPolicy,
    ) -> None:
        if "BREAKOUT" not in foundation_policy.allowed_families:
            raise BreakoutExpansionError(
                "foundation policy does not allow BREAKOUT family"
            )
        if policy.required_bars > foundation_policy.max_lookback_bars:
            raise BreakoutExpansionError(
                "P08-F required history exceeds foundation lookback bound"
            )
        self._foundation_policy = foundation_policy
        self._policy = policy

    def _window(
        self,
        bars: Sequence[TrustedOHLCVBar],
    ) -> tuple[TrustedOHLCVBar, ...]:
        required = self._policy.required_bars
        if len(bars) < required:
            raise BreakoutExpansionError(
                "insufficient bars for P08-F evaluation"
            )
        window = tuple(bars[-required:])
        first = window[0]
        evaluation_as_of = window[-1].as_of_time_ns
        previous_event = -1
        for bar in window:
            if bar.symbol != first.symbol:
                raise BreakoutExpansionError(
                    "P08-F window must use one symbol"
                )
            if bar.timeframe != first.timeframe:
                raise BreakoutExpansionError(
                    "P08-F window must use one timeframe"
                )
            if bar.source_dataset_version != first.source_dataset_version:
                raise BreakoutExpansionError(
                    "P08-F window must use one dataset version"
                )
            if bar.quality_evidence_sha256 != first.quality_evidence_sha256:
                raise BreakoutExpansionError(
                    "P08-F window must use one quality evidence lineage"
                )
            if bar.event_time_ns <= previous_event:
                raise BreakoutExpansionError(
                    "P08-F event times must be strictly increasing"
                )
            if bar.as_of_time_ns > evaluation_as_of:
                raise BreakoutExpansionError(
                    "P08-F window contains future as-of information"
                )
            previous_event = bar.event_time_ns
        return window

    def definition(self) -> IndicatorDefinition:
        p = self._policy
        return IndicatorDefinition(
            name="breakout.prior-channel-expansion",
            version="1.0.0",
            family="BREAKOUT",
            independence_group=p.independence_group,
            lookback_bars=p.required_bars,
            output_unit="BPS",
            parameters=(
                ("channel_lookback_bars", str(p.channel_lookback_bars)),
                ("breakout_buffer_bps", str(p.breakout_buffer_bps)),
                ("min_expansion_ratio_bps", str(p.min_expansion_ratio_bps)),
            ),
        )

    def evaluate(
        self,
        bars: Sequence[TrustedOHLCVBar],
    ) -> BreakoutExpansionEvaluation:
        p = self._policy
        window = self._window(bars)

        prior = window[:-1]
        current = window[-1]

        prior_highs = tuple(
            _decimal(bar.high_text, field="prior_high")
            for bar in prior
        )
        prior_lows = tuple(
            _decimal(bar.low_text, field="prior_low")
            for bar in prior
        )
        prior_ranges = tuple(
            high - low
            for high, low in zip(prior_highs, prior_lows, strict=True)
        )

        channel_high = max(prior_highs)
        channel_low = min(prior_lows)
        prior_average_range = _average(
            prior_ranges,
            field="prior_average_range",
        )

        current_high = _decimal(current.high_text, field="current_high")
        current_low = _decimal(current.low_text, field="current_low")
        current_close = _decimal(current.close_text, field="current_close")
        current_range = current_high - current_low

        buffer = Decimal(p.breakout_buffer_bps) / Decimal(10_000)
        upper_threshold = channel_high + abs(channel_high) * buffer
        lower_threshold = channel_low - abs(channel_low) * buffer

        direction = 0
        breakout_distance = 0
        if current_close > upper_threshold:
            direction = 1
            breakout_distance = abs(
                _ratio_bps(
                    current_close - channel_high,
                    channel_high,
                    field="up_breakout_distance",
                )
            )
        elif current_close < lower_threshold:
            direction = -1
            breakout_distance = abs(
                _ratio_bps(
                    channel_low - current_close,
                    channel_low,
                    field="down_breakout_distance",
                )
            )

        if prior_average_range == 0:
            if current_range == 0:
                expansion_ratio = 10_000
            else:
                raise BreakoutExpansionError(
                    "nonzero current range cannot use zero prior average range"
                )
        else:
            expansion_ratio = int(
                (
                    current_range
                    / prior_average_range
                    * Decimal(10_000)
                ).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
            )
        expansion_confirmed = (
            expansion_ratio >= p.min_expansion_ratio_bps
        )

        if direction == 0:
            strength = 0
            confidence = 0
        else:
            strength = min(
                p.max_strength_bps,
                self._foundation_policy.max_strength_bps,
                breakout_distance
                + (
                    p.expansion_confirmation_bonus_bps
                    if expansion_confirmed
                    else 0
                ),
            )
            confidence = min(
                p.max_confidence_bps,
                self._foundation_policy.max_confidence_bps,
                p.base_directional_confidence_bps
                + strength // 2,
            )

        evidence = TechnicalEvidence(
            definition_id=self.definition().definition_id,
            family="BREAKOUT",
            independence_group=p.independence_group,
            symbol=current.symbol,
            timeframe=current.timeframe,
            direction=direction,
            strength_bps=strength,
            confidence_bps=confidence,
            event_time_ns=current.event_time_ns,
            as_of_time_ns=current.as_of_time_ns,
            value_text=str(direction * breakout_distance),
            invalidation=(
                "breakout evidence invalidates when the completed close returns inside "
                "the governed prior-only channel/buffer; expansion is correlated context "
                "and does not create a second vote"
            ),
            source_dataset_version=current.source_dataset_version,
            quality_evidence_sha256=current.quality_evidence_sha256,
        )

        return BreakoutExpansionEvaluation(
            prior_channel_high_text=_decimal_text(channel_high),
            prior_channel_low_text=_decimal_text(channel_low),
            prior_average_range_text=_decimal_text(prior_average_range),
            current_range_text=_decimal_text(current_range),
            breakout_distance_bps=breakout_distance,
            expansion_ratio_bps=expansion_ratio,
            expansion_confirmed=expansion_confirmed,
            evidence=evidence,
            cross_family_independence_status=p.cross_family_independence_status,
        )
