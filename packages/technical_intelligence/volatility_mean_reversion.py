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


class VolatilityMeanReversionError(TechnicalFoundationError):
    """P08-E inputs or policy violate governed volatility/mean-reversion invariants."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VolatilityMeanReversionError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VolatilityMeanReversionError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise VolatilityMeanReversionError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VolatilityMeanReversionError(f"{field} must be a non-negative integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise VolatilityMeanReversionError(f"{field} must be boolean")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise VolatilityMeanReversionError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise VolatilityMeanReversionError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise VolatilityMeanReversionError(f"{field} must be finite")
    return result


def _ratio_bps(numerator: Decimal, denominator: Decimal, *, field: str) -> int:
    if denominator == 0:
        raise VolatilityMeanReversionError(f"{field} denominator cannot be zero")
    raw = (numerator / abs(denominator)) * Decimal(10_000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class VolatilityMeanReversionPolicy:
    volatility_independence_group: str
    mean_reversion_independence_group: str
    cross_family_independence_status: str
    short_volatility_window: int
    baseline_volatility_window: int
    mean_window: int
    mean_reversion_threshold_mad_bps: int
    base_volatility_confidence_bps: int
    base_mean_reversion_confidence_bps: int
    max_strength_bps: int
    max_confidence_bps: int
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "VolatilityMeanReversionPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise VolatilityMeanReversionError("unsupported P08-E policy schema_version")
        if raw.get("volatility_family") != "VOLATILITY":
            raise VolatilityMeanReversionError("volatility family must be VOLATILITY")
        if raw.get("mean_reversion_family") != "MEAN_REVERSION":
            raise VolatilityMeanReversionError("mean reversion family must be MEAN_REVERSION")
        if raw.get("cross_family_independence_status") != "PROVISIONAL_PENDING_P08_H":
            raise VolatilityMeanReversionError("cross-family independence must remain pending P08-H")
        if raw.get("volatility_direction_semantics") != "CONTEXT_NEUTRAL_ZERO_ONLY":
            raise VolatilityMeanReversionError("volatility direction must remain context-neutral")
        if raw.get("score_semantics") != "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY":
            raise VolatilityMeanReversionError("P08-E scores must not claim trade probability")

        short = _positive_int(raw.get("short_volatility_window"), field="short_volatility_window")
        baseline = _positive_int(
            raw.get("baseline_volatility_window"),
            field="baseline_volatility_window",
        )
        mean_window = _positive_int(raw.get("mean_window"), field="mean_window")
        if short > baseline:
            raise VolatilityMeanReversionError(
                "short_volatility_window cannot exceed baseline_volatility_window"
            )
        threshold = _positive_int(
            raw.get("mean_reversion_threshold_mad_bps"),
            field="mean_reversion_threshold_mad_bps",
        )
        max_strength = _positive_int(raw.get("max_strength_bps"), field="max_strength_bps")
        max_confidence = _positive_int(raw.get("max_confidence_bps"), field="max_confidence_bps")
        if max_strength > 10_000 or max_confidence > 10_000:
            raise VolatilityMeanReversionError("P08-E score bounds cannot exceed 10000 bps")
        vol_conf = _non_negative_int(
            raw.get("base_volatility_confidence_bps"),
            field="base_volatility_confidence_bps",
        )
        mean_conf = _non_negative_int(
            raw.get("base_mean_reversion_confidence_bps"),
            field="base_mean_reversion_confidence_bps",
        )
        if vol_conf > max_confidence or mean_conf > max_confidence:
            raise VolatilityMeanReversionError("base confidence cannot exceed max confidence")
        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise VolatilityMeanReversionError("P08-E forbids direct trade output")

        return cls(
            volatility_independence_group=_text(
                raw.get("volatility_independence_group"),
                field="volatility_independence_group",
            ),
            mean_reversion_independence_group=_text(
                raw.get("mean_reversion_independence_group"),
                field="mean_reversion_independence_group",
            ),
            cross_family_independence_status=_text(
                raw.get("cross_family_independence_status"),
                field="cross_family_independence_status",
            ),
            short_volatility_window=short,
            baseline_volatility_window=baseline,
            mean_window=mean_window,
            mean_reversion_threshold_mad_bps=threshold,
            base_volatility_confidence_bps=vol_conf,
            base_mean_reversion_confidence_bps=mean_conf,
            max_strength_bps=max_strength,
            max_confidence_bps=max_confidence,
            direct_trade_output_allowed=direct_trade,
        )

    @property
    def required_bars(self) -> int:
        return max(self.baseline_volatility_window, self.mean_window)


@dataclass(frozen=True, slots=True)
class VolatilityMeanReversionEvaluation:
    short_range_bps: int
    baseline_range_bps: int
    volatility_ratio_bps: int
    mean_text: str
    mean_absolute_deviation_text: str
    deviation_mad_bps: int
    volatility_evidence: TechnicalEvidence
    mean_reversion_evidence: TechnicalEvidence
    cross_family_independence_status: str


class VolatilityMeanReversionModel:
    def __init__(
        self,
        *,
        foundation_policy: TechnicalFoundationPolicy,
        policy: VolatilityMeanReversionPolicy,
    ) -> None:
        for family in ("VOLATILITY", "MEAN_REVERSION"):
            if family not in foundation_policy.allowed_families:
                raise VolatilityMeanReversionError(
                    f"foundation policy does not allow {family} family"
                )
        if policy.required_bars > foundation_policy.max_lookback_bars:
            raise VolatilityMeanReversionError(
                "P08-E required history exceeds foundation lookback bound"
            )
        self._foundation_policy = foundation_policy
        self._policy = policy

    def _window(self, bars: Sequence[TrustedOHLCVBar]) -> tuple[TrustedOHLCVBar, ...]:
        required = self._policy.required_bars
        if len(bars) < required:
            raise VolatilityMeanReversionError("insufficient bars for P08-E evaluation")
        window = tuple(bars[-required:])
        first = window[0]
        evaluation_as_of = window[-1].as_of_time_ns
        previous_event = -1
        for bar in window:
            if bar.symbol != first.symbol:
                raise VolatilityMeanReversionError("P08-E window must use one symbol")
            if bar.timeframe != first.timeframe:
                raise VolatilityMeanReversionError("P08-E window must use one timeframe")
            if bar.source_dataset_version != first.source_dataset_version:
                raise VolatilityMeanReversionError("P08-E window must use one dataset version")
            if bar.quality_evidence_sha256 != first.quality_evidence_sha256:
                raise VolatilityMeanReversionError(
                    "P08-E window must use one quality evidence lineage"
                )
            if bar.event_time_ns <= previous_event:
                raise VolatilityMeanReversionError(
                    "P08-E event times must be strictly increasing"
                )
            if bar.as_of_time_ns > evaluation_as_of:
                raise VolatilityMeanReversionError(
                    "P08-E window contains future as-of information"
                )
            previous_event = bar.event_time_ns
        return window

    def volatility_definition(self) -> IndicatorDefinition:
        p = self._policy
        return IndicatorDefinition(
            name="volatility.normalized-range-ratio",
            version="1.0.0",
            family="VOLATILITY",
            independence_group=p.volatility_independence_group,
            lookback_bars=p.baseline_volatility_window,
            output_unit="BPS",
            parameters=(
                ("short_volatility_window", str(p.short_volatility_window)),
                ("baseline_volatility_window", str(p.baseline_volatility_window)),
                ("direction_semantics", "CONTEXT_NEUTRAL_ZERO_ONLY"),
            ),
        )

    def mean_reversion_definition(self) -> IndicatorDefinition:
        p = self._policy
        return IndicatorDefinition(
            name="mean-reversion.mean-absolute-deviation",
            version="1.0.0",
            family="MEAN_REVERSION",
            independence_group=p.mean_reversion_independence_group,
            lookback_bars=p.mean_window,
            output_unit="MAD_BPS",
            parameters=(
                ("mean_window", str(p.mean_window)),
                ("threshold_mad_bps", str(p.mean_reversion_threshold_mad_bps)),
            ),
        )

    def _range_bps(self, bar: TrustedOHLCVBar) -> int:
        high = _decimal(bar.high_text, field="high")
        low = _decimal(bar.low_text, field="low")
        close = _decimal(bar.close_text, field="close")
        if close == 0:
            raise VolatilityMeanReversionError(
                "close cannot be zero for normalized volatility"
            )
        return abs(_ratio_bps(high - low, close, field="normalized_range"))

    def evaluate(self, bars: Sequence[TrustedOHLCVBar]) -> VolatilityMeanReversionEvaluation:
        p = self._policy
        window = self._window(bars)
        baseline_bars = window[-p.baseline_volatility_window:]
        short_bars = window[-p.short_volatility_window:]

        baseline_ranges = tuple(self._range_bps(bar) for bar in baseline_bars)
        short_ranges = tuple(self._range_bps(bar) for bar in short_bars)
        baseline_range = sum(baseline_ranges) // len(baseline_ranges)
        short_range = sum(short_ranges) // len(short_ranges)

        if baseline_range == 0:
            volatility_ratio = 10_000 if short_range == 0 else 20_000
        else:
            volatility_ratio = int(
                (
                    Decimal(short_range)
                    / Decimal(baseline_range)
                    * Decimal(10_000)
                ).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
            )
        volatility_strength = min(
            p.max_strength_bps,
            self._foundation_policy.max_strength_bps,
            abs(volatility_ratio - 10_000),
        )
        volatility_confidence = min(
            p.max_confidence_bps,
            self._foundation_policy.max_confidence_bps,
            p.base_volatility_confidence_bps + volatility_strength // 2,
        )

        mean_bars = window[-p.mean_window:]
        closes = tuple(_decimal(bar.close_text, field="close") for bar in mean_bars)
        mean = sum(closes, Decimal(0)) / Decimal(len(closes))
        mad = sum((abs(value - mean) for value in closes), Decimal(0)) / Decimal(len(closes))
        latest_close = closes[-1]

        deviation_mad_bps = 0
        mean_direction = 0
        mean_strength = 0
        mean_confidence = 0
        if mad != 0:
            deviation_mad_bps = _ratio_bps(
                latest_close - mean,
                mad,
                field="mean_reversion_deviation",
            )
            threshold = p.mean_reversion_threshold_mad_bps
            if deviation_mad_bps >= threshold:
                mean_direction = -1
            elif deviation_mad_bps <= -threshold:
                mean_direction = 1
            if mean_direction != 0:
                mean_strength = min(
                    p.max_strength_bps,
                    self._foundation_policy.max_strength_bps,
                    (abs(deviation_mad_bps) * 5000) // threshold,
                )
                mean_confidence = min(
                    p.max_confidence_bps,
                    self._foundation_policy.max_confidence_bps,
                    p.base_mean_reversion_confidence_bps + mean_strength // 2,
                )

        latest = window[-1]
        volatility_evidence = TechnicalEvidence(
            definition_id=self.volatility_definition().definition_id,
            family="VOLATILITY",
            independence_group=p.volatility_independence_group,
            symbol=latest.symbol,
            timeframe=latest.timeframe,
            direction=0,
            strength_bps=volatility_strength,
            confidence_bps=volatility_confidence,
            event_time_ns=latest.event_time_ns,
            as_of_time_ns=latest.as_of_time_ns,
            value_text=str(short_range),
            invalidation=(
                "volatility context invalidates when the governed short/baseline normalized-range "
                "relationship or trusted input lineage changes"
            ),
            source_dataset_version=latest.source_dataset_version,
            quality_evidence_sha256=latest.quality_evidence_sha256,
        )
        mean_reversion_evidence = TechnicalEvidence(
            definition_id=self.mean_reversion_definition().definition_id,
            family="MEAN_REVERSION",
            independence_group=p.mean_reversion_independence_group,
            symbol=latest.symbol,
            timeframe=latest.timeframe,
            direction=mean_direction,
            strength_bps=mean_strength,
            confidence_bps=mean_confidence,
            event_time_ns=latest.event_time_ns,
            as_of_time_ns=latest.as_of_time_ns,
            value_text=str(deviation_mad_bps),
            invalidation=(
                "mean-reversion evidence invalidates when price deviation from the governed rolling "
                "mean falls back inside the mean-absolute-deviation threshold"
            ),
            source_dataset_version=latest.source_dataset_version,
            quality_evidence_sha256=latest.quality_evidence_sha256,
        )
        return VolatilityMeanReversionEvaluation(
            short_range_bps=short_range,
            baseline_range_bps=baseline_range,
            volatility_ratio_bps=volatility_ratio,
            mean_text=_decimal_text(mean),
            mean_absolute_deviation_text=_decimal_text(mad),
            deviation_mad_bps=deviation_mad_bps,
            volatility_evidence=volatility_evidence,
            mean_reversion_evidence=mean_reversion_evidence,
            cross_family_independence_status=p.cross_family_independence_status,
        )
