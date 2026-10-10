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


class MarketStructurePriceActionError(TechnicalFoundationError):
    """P08-D inputs or policy violate governed structure/price-action invariants."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MarketStructurePriceActionError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MarketStructurePriceActionError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MarketStructurePriceActionError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MarketStructurePriceActionError(f"{field} must be a non-negative integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise MarketStructurePriceActionError(f"{field} must be boolean")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise MarketStructurePriceActionError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MarketStructurePriceActionError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise MarketStructurePriceActionError(f"{field} must be finite")
    return result


def _ratio_bps(numerator: Decimal, denominator: Decimal, *, field: str) -> int:
    if denominator == 0:
        raise MarketStructurePriceActionError(f"{field} denominator cannot be zero")
    raw = (numerator / abs(denominator)) * Decimal(10_000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class MarketStructurePriceActionPolicy:
    structure_independence_group: str
    price_action_independence_group: str
    cross_family_independence_status: str
    structure_lookback_bars: int
    swing_left_bars: int
    swing_right_bars: int
    min_confirmed_swings_per_side: int
    break_buffer_bps: int
    break_confirmation_bonus_bps: int
    min_body_to_range_bps: int
    min_close_location_bps: int
    base_structure_confidence_bps: int
    base_price_action_confidence_bps: int
    max_strength_bps: int
    max_confidence_bps: int
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "MarketStructurePriceActionPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise MarketStructurePriceActionError("unsupported P08-D policy schema_version")
        if raw.get("structure_family") != "MARKET_STRUCTURE":
            raise MarketStructurePriceActionError("structure family must be MARKET_STRUCTURE")
        if raw.get("price_action_family") != "PRICE_ACTION":
            raise MarketStructurePriceActionError("price action family must be PRICE_ACTION")
        if raw.get("cross_family_independence_status") != "PROVISIONAL_PENDING_P08_H":
            raise MarketStructurePriceActionError("cross-family independence must remain pending P08-H")
        if raw.get("score_semantics") != "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY":
            raise MarketStructurePriceActionError("P08-D scores must not claim trade probability")

        lookback = _positive_int(raw.get("structure_lookback_bars"), field="structure_lookback_bars")
        left = _positive_int(raw.get("swing_left_bars"), field="swing_left_bars")
        right = _positive_int(raw.get("swing_right_bars"), field="swing_right_bars")
        min_swings = _positive_int(
            raw.get("min_confirmed_swings_per_side"),
            field="min_confirmed_swings_per_side",
        )
        if lookback < left + right + 3:
            raise MarketStructurePriceActionError("structure lookback is too small for confirmed swings")
        body = _non_negative_int(raw.get("min_body_to_range_bps"), field="min_body_to_range_bps")
        close_location = _non_negative_int(
            raw.get("min_close_location_bps"),
            field="min_close_location_bps",
        )
        if body > 10_000 or close_location > 10_000:
            raise MarketStructurePriceActionError("price-action thresholds cannot exceed 10000 bps")
        max_strength = _positive_int(raw.get("max_strength_bps"), field="max_strength_bps")
        max_confidence = _positive_int(raw.get("max_confidence_bps"), field="max_confidence_bps")
        if max_strength > 10_000 or max_confidence > 10_000:
            raise MarketStructurePriceActionError("P08-D score bounds cannot exceed 10000 bps")
        structure_conf = _non_negative_int(
            raw.get("base_structure_confidence_bps"),
            field="base_structure_confidence_bps",
        )
        price_conf = _non_negative_int(
            raw.get("base_price_action_confidence_bps"),
            field="base_price_action_confidence_bps",
        )
        if structure_conf > max_confidence or price_conf > max_confidence:
            raise MarketStructurePriceActionError("base confidence cannot exceed max confidence")
        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise MarketStructurePriceActionError("P08-D forbids direct trade output")

        return cls(
            structure_independence_group=_text(
                raw.get("structure_independence_group"),
                field="structure_independence_group",
            ),
            price_action_independence_group=_text(
                raw.get("price_action_independence_group"),
                field="price_action_independence_group",
            ),
            cross_family_independence_status=_text(
                raw.get("cross_family_independence_status"),
                field="cross_family_independence_status",
            ),
            structure_lookback_bars=lookback,
            swing_left_bars=left,
            swing_right_bars=right,
            min_confirmed_swings_per_side=min_swings,
            break_buffer_bps=_non_negative_int(raw.get("break_buffer_bps"), field="break_buffer_bps"),
            break_confirmation_bonus_bps=_non_negative_int(
                raw.get("break_confirmation_bonus_bps"),
                field="break_confirmation_bonus_bps",
            ),
            min_body_to_range_bps=body,
            min_close_location_bps=close_location,
            base_structure_confidence_bps=structure_conf,
            base_price_action_confidence_bps=price_conf,
            max_strength_bps=max_strength,
            max_confidence_bps=max_confidence,
            direct_trade_output_allowed=direct_trade,
        )


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    price_text: str


@dataclass(frozen=True, slots=True)
class MarketStructurePriceActionEvaluation:
    previous_swing_high: SwingPoint | None
    latest_swing_high: SwingPoint | None
    previous_swing_low: SwingPoint | None
    latest_swing_low: SwingPoint | None
    structure_break_direction: int
    body_to_range_bps: int
    bullish_close_location_bps: int
    bearish_close_location_bps: int
    structure_evidence: TechnicalEvidence
    price_action_evidence: TechnicalEvidence
    cross_family_independence_status: str


class MarketStructurePriceActionModel:
    def __init__(
        self,
        *,
        foundation_policy: TechnicalFoundationPolicy,
        policy: MarketStructurePriceActionPolicy,
    ) -> None:
        for family in ("MARKET_STRUCTURE", "PRICE_ACTION"):
            if family not in foundation_policy.allowed_families:
                raise MarketStructurePriceActionError(
                    f"foundation policy does not allow {family} family"
                )
        if policy.structure_lookback_bars > foundation_policy.max_lookback_bars:
            raise MarketStructurePriceActionError(
                "P08-D required history exceeds foundation lookback bound"
            )
        self._foundation_policy = foundation_policy
        self._policy = policy

    def _window(self, bars: Sequence[TrustedOHLCVBar]) -> tuple[TrustedOHLCVBar, ...]:
        p = self._policy
        if len(bars) < p.structure_lookback_bars:
            raise MarketStructurePriceActionError("insufficient bars for P08-D evaluation")
        window = tuple(bars[-p.structure_lookback_bars :])
        first = window[0]
        evaluation_as_of = window[-1].as_of_time_ns
        previous_event = -1
        for bar in window:
            if bar.symbol != first.symbol:
                raise MarketStructurePriceActionError("P08-D window must use one symbol")
            if bar.timeframe != first.timeframe:
                raise MarketStructurePriceActionError("P08-D window must use one timeframe")
            if bar.source_dataset_version != first.source_dataset_version:
                raise MarketStructurePriceActionError("P08-D window must use one dataset version")
            if bar.quality_evidence_sha256 != first.quality_evidence_sha256:
                raise MarketStructurePriceActionError(
                    "P08-D window must use one quality evidence lineage"
                )
            if bar.event_time_ns <= previous_event:
                raise MarketStructurePriceActionError(
                    "P08-D event times must be strictly increasing"
                )
            if bar.as_of_time_ns > evaluation_as_of:
                raise MarketStructurePriceActionError(
                    "P08-D window contains future as-of information"
                )
            previous_event = bar.event_time_ns
        return window

    def _confirmed_swings(
        self,
        window: tuple[TrustedOHLCVBar, ...],
    ) -> tuple[tuple[tuple[int, Decimal], ...], tuple[tuple[int, Decimal], ...]]:
        p = self._policy
        highs: list[tuple[int, Decimal]] = []
        lows: list[tuple[int, Decimal]] = []
        last_candidate = len(window) - p.swing_right_bars
        for index in range(p.swing_left_bars, last_candidate):
            high = _decimal(window[index].high_text, field="high")
            low = _decimal(window[index].low_text, field="low")
            neighbors = tuple(
                j
                for j in range(index - p.swing_left_bars, index + p.swing_right_bars + 1)
                if j != index
            )
            if all(high > _decimal(window[j].high_text, field="neighbor_high") for j in neighbors):
                highs.append((index, high))
            if all(low < _decimal(window[j].low_text, field="neighbor_low") for j in neighbors):
                lows.append((index, low))
        return tuple(highs), tuple(lows)

    def structure_definition(self) -> IndicatorDefinition:
        p = self._policy
        return IndicatorDefinition(
            name="market-structure.confirmed-swings",
            version="1.0.0",
            family="MARKET_STRUCTURE",
            independence_group=p.structure_independence_group,
            lookback_bars=p.structure_lookback_bars,
            output_unit="BPS",
            parameters=(
                ("swing_left_bars", str(p.swing_left_bars)),
                ("swing_right_bars", str(p.swing_right_bars)),
                ("min_confirmed_swings_per_side", str(p.min_confirmed_swings_per_side)),
                ("break_buffer_bps", str(p.break_buffer_bps)),
            ),
        )

    def price_action_definition(self) -> IndicatorDefinition:
        p = self._policy
        return IndicatorDefinition(
            name="price-action.candle-body-close-location",
            version="1.0.0",
            family="PRICE_ACTION",
            independence_group=p.price_action_independence_group,
            lookback_bars=1,
            output_unit="BPS",
            parameters=(
                ("min_body_to_range_bps", str(p.min_body_to_range_bps)),
                ("min_close_location_bps", str(p.min_close_location_bps)),
            ),
        )

    def evaluate(self, bars: Sequence[TrustedOHLCVBar]) -> MarketStructurePriceActionEvaluation:
        p = self._policy
        window = self._window(bars)
        swing_highs, swing_lows = self._confirmed_swings(window)

        previous_high_raw = swing_highs[-2] if len(swing_highs) >= p.min_confirmed_swings_per_side else None
        latest_high_raw = swing_highs[-1] if len(swing_highs) >= p.min_confirmed_swings_per_side else None
        previous_low_raw = swing_lows[-2] if len(swing_lows) >= p.min_confirmed_swings_per_side else None
        latest_low_raw = swing_lows[-1] if len(swing_lows) >= p.min_confirmed_swings_per_side else None

        structure_direction = 0
        structure_strength = 0
        structure_confidence = 0
        structure_break = 0
        latest_close = _decimal(window[-1].close_text, field="latest_close")

        if (
            previous_high_raw is not None
            and latest_high_raw is not None
            and previous_low_raw is not None
            and latest_low_raw is not None
        ):
            previous_high = previous_high_raw[1]
            latest_high = latest_high_raw[1]
            previous_low = previous_low_raw[1]
            latest_low = latest_low_raw[1]
            bullish = latest_high > previous_high and latest_low > previous_low
            bearish = latest_high < previous_high and latest_low < previous_low
            structure_direction = 1 if bullish else (-1 if bearish else 0)

            high_change_bps = abs(
                _ratio_bps(latest_high - previous_high, previous_high, field="swing_high_change")
            )
            low_change_bps = abs(
                _ratio_bps(latest_low - previous_low, previous_low, field="swing_low_change")
            )
            base_strength = (high_change_bps + low_change_bps) // 2

            upper_break_threshold = latest_high * (
                Decimal(1) + Decimal(p.break_buffer_bps) / Decimal(10_000)
            )
            lower_break_threshold = latest_low * (
                Decimal(1) - Decimal(p.break_buffer_bps) / Decimal(10_000)
            )
            if latest_close > upper_break_threshold:
                structure_break = 1
            elif latest_close < lower_break_threshold:
                structure_break = -1

            aligned_break = structure_break == structure_direction and structure_direction != 0
            if structure_direction != 0:
                structure_strength = min(
                    p.max_strength_bps,
                    self._foundation_policy.max_strength_bps,
                    base_strength + (p.break_confirmation_bonus_bps if aligned_break else 0),
                )
                structure_confidence = min(
                    p.max_confidence_bps,
                    self._foundation_policy.max_confidence_bps,
                    p.base_structure_confidence_bps + structure_strength // 2,
                )

        latest = window[-1]
        open_price = _decimal(latest.open_text, field="open")
        high_price = _decimal(latest.high_text, field="high")
        low_price = _decimal(latest.low_text, field="low")
        close_price = _decimal(latest.close_text, field="close")
        candle_range = high_price - low_price

        body_ratio = 0
        bullish_close_location = 0
        bearish_close_location = 0
        price_action_direction = 0
        price_action_strength = 0
        price_action_confidence = 0

        if candle_range > 0:
            body_ratio = abs(_ratio_bps(close_price - open_price, candle_range, field="body_ratio"))
            bullish_close_location = _ratio_bps(
                close_price - low_price,
                candle_range,
                field="bullish_close_location",
            )
            bearish_close_location = _ratio_bps(
                high_price - close_price,
                candle_range,
                field="bearish_close_location",
            )
            bullish_candle = (
                close_price > open_price
                and body_ratio >= p.min_body_to_range_bps
                and bullish_close_location >= p.min_close_location_bps
            )
            bearish_candle = (
                close_price < open_price
                and body_ratio >= p.min_body_to_range_bps
                and bearish_close_location >= p.min_close_location_bps
            )
            price_action_direction = 1 if bullish_candle else (-1 if bearish_candle else 0)
            if price_action_direction != 0:
                price_action_strength = min(
                    p.max_strength_bps,
                    self._foundation_policy.max_strength_bps,
                    (body_ratio + max(bullish_close_location, bearish_close_location)) // 2,
                )
                price_action_confidence = min(
                    p.max_confidence_bps,
                    self._foundation_policy.max_confidence_bps,
                    p.base_price_action_confidence_bps + price_action_strength // 2,
                )

        structure_evidence = TechnicalEvidence(
            definition_id=self.structure_definition().definition_id,
            family="MARKET_STRUCTURE",
            independence_group=p.structure_independence_group,
            symbol=latest.symbol,
            timeframe=latest.timeframe,
            direction=structure_direction,
            strength_bps=structure_strength,
            confidence_bps=structure_confidence,
            event_time_ns=latest.event_time_ns,
            as_of_time_ns=latest.as_of_time_ns,
            value_text=str(structure_direction * structure_strength),
            invalidation=(
                "market-structure evidence invalidates when confirmed swing sequencing no longer "
                "supports the governed higher-high/higher-low or lower-high/lower-low state"
            ),
            source_dataset_version=latest.source_dataset_version,
            quality_evidence_sha256=latest.quality_evidence_sha256,
        )
        price_action_evidence = TechnicalEvidence(
            definition_id=self.price_action_definition().definition_id,
            family="PRICE_ACTION",
            independence_group=p.price_action_independence_group,
            symbol=latest.symbol,
            timeframe=latest.timeframe,
            direction=price_action_direction,
            strength_bps=price_action_strength,
            confidence_bps=price_action_confidence,
            event_time_ns=latest.event_time_ns,
            as_of_time_ns=latest.as_of_time_ns,
            value_text=str(price_action_direction * price_action_strength),
            invalidation=(
                "price-action evidence invalidates when the completed candle no longer satisfies "
                "the governed body-to-range and directional close-location thresholds"
            ),
            source_dataset_version=latest.source_dataset_version,
            quality_evidence_sha256=latest.quality_evidence_sha256,
        )

        def swing(raw: tuple[int, Decimal] | None) -> SwingPoint | None:
            if raw is None:
                return None
            return SwingPoint(index=raw[0], price_text=cast(str, _decimal_text(raw[1])))

        return MarketStructurePriceActionEvaluation(
            previous_swing_high=swing(previous_high_raw),
            latest_swing_high=swing(latest_high_raw),
            previous_swing_low=swing(previous_low_raw),
            latest_swing_low=swing(latest_low_raw),
            structure_break_direction=structure_break,
            body_to_range_bps=body_ratio,
            bullish_close_location_bps=bullish_close_location,
            bearish_close_location_bps=bearish_close_location,
            structure_evidence=structure_evidence,
            price_action_evidence=price_action_evidence,
            cross_family_independence_status=p.cross_family_independence_status,
        )
