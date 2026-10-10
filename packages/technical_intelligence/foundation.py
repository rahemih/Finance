from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class TechnicalFoundationError(ValueError):
    """Raised when technical-intelligence foundation invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TechnicalFoundationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TechnicalFoundationError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TechnicalFoundationError(f"{field} must be non-empty text")
    return value.strip()


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise TechnicalFoundationError(f"{field} must be lowercase sha256 hex")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TechnicalFoundationError(f"{field} must be a non-negative integer")
    return value


def _bps(value: object, *, field: str, maximum: int = 10_000) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise TechnicalFoundationError(f"{field} must be integer basis points in [0,{maximum}]")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise TechnicalFoundationError(f"{field} must be boolean")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise TechnicalFoundationError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise TechnicalFoundationError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise TechnicalFoundationError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class TechnicalFoundationPolicy:
    allowed_families: tuple[str, ...]
    max_lookback_bars: int
    max_strength_bps: int
    max_confidence_bps: int
    independent_confirmation_requires_unique_group: bool
    point_in_time_required: bool
    trusted_data_required: bool
    direct_trade_output_allowed: bool
    production_technical_intelligence_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "TechnicalFoundationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise TechnicalFoundationError("unsupported policy schema_version")
        families_value = _object_list(raw.get("allowed_families"), field="allowed_families")
        if not families_value:
            raise TechnicalFoundationError("allowed_families must be a non-empty array")
        families = tuple(_text(item, field="allowed_family") for item in families_value)
        max_lookback = _non_negative_int(raw.get("max_lookback_bars"), field="max_lookback_bars")
        if max_lookback < 2:
            raise TechnicalFoundationError("max_lookback_bars must be >= 2")
        max_strength = _bps(raw.get("max_strength_bps"), field="max_strength_bps")
        max_confidence = _bps(raw.get("max_confidence_bps"), field="max_confidence_bps")
        unique_group = _boolean(
            raw.get("independent_confirmation_requires_unique_group"),
            field="independent_confirmation_requires_unique_group",
        )
        point_in_time = _boolean(raw.get("point_in_time_required"), field="point_in_time_required")
        trusted_data = _boolean(raw.get("trusted_data_required"), field="trusted_data_required")
        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        vendor = _text(
            raw.get("production_technical_intelligence_vendor"),
            field="production_technical_intelligence_vendor",
        )
        if direct_trade:
            raise TechnicalFoundationError("P08-A policy forbids direct trade output")
        return cls(
            allowed_families=families,
            max_lookback_bars=max_lookback,
            max_strength_bps=max_strength,
            max_confidence_bps=max_confidence,
            independent_confirmation_requires_unique_group=unique_group,
            point_in_time_required=point_in_time,
            trusted_data_required=trusted_data,
            direct_trade_output_allowed=direct_trade,
            production_technical_intelligence_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class TrustedOHLCVBar:
    symbol: str
    timeframe: str
    open_text: str
    high_text: str
    low_text: str
    close_text: str
    volume_text: str
    event_time_ns: int
    as_of_time_ns: int
    source_dataset_version: str
    quality_evidence_sha256: str

    def __post_init__(self) -> None:
        symbol = _text(self.symbol, field="symbol")
        timeframe = _text(self.timeframe, field="timeframe")
        open_value = _decimal(self.open_text, field="open")
        high_value = _decimal(self.high_text, field="high")
        low_value = _decimal(self.low_text, field="low")
        close_value = _decimal(self.close_text, field="close")
        volume_value = _decimal(self.volume_text, field="volume")
        event_time = _non_negative_int(self.event_time_ns, field="event_time_ns")
        as_of_time = _non_negative_int(self.as_of_time_ns, field="as_of_time_ns")
        if event_time > as_of_time:
            raise TechnicalFoundationError("event_time_ns cannot exceed as_of_time_ns")
        if volume_value < 0:
            raise TechnicalFoundationError("volume cannot be negative")
        if high_value < max(open_value, close_value, low_value):
            raise TechnicalFoundationError("high must be >= open/close/low")
        if low_value > min(open_value, close_value, high_value):
            raise TechnicalFoundationError("low must be <= open/close/high")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "open_text", _decimal_text(open_value))
        object.__setattr__(self, "high_text", _decimal_text(high_value))
        object.__setattr__(self, "low_text", _decimal_text(low_value))
        object.__setattr__(self, "close_text", _decimal_text(close_value))
        object.__setattr__(self, "volume_text", _decimal_text(volume_value))
        object.__setattr__(
            self,
            "source_dataset_version",
            _sha256_text(self.source_dataset_version, field="source_dataset_version"),
        )
        object.__setattr__(
            self,
            "quality_evidence_sha256",
            _sha256_text(self.quality_evidence_sha256, field="quality_evidence_sha256"),
        )

    @property
    def freshness_ns(self) -> int:
        return self.as_of_time_ns - self.event_time_ns


@dataclass(frozen=True, slots=True)
class IndicatorDefinition:
    name: str
    version: str
    family: str
    independence_group: str
    lookback_bars: int
    output_unit: str
    parameters: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, field="name"))
        object.__setattr__(self, "version", _text(self.version, field="version"))
        object.__setattr__(self, "family", _text(self.family, field="family"))
        object.__setattr__(
            self,
            "independence_group",
            _text(self.independence_group, field="independence_group"),
        )
        lookback = _non_negative_int(self.lookback_bars, field="lookback_bars")
        if lookback < 2:
            raise TechnicalFoundationError("lookback_bars must be >= 2")
        object.__setattr__(self, "lookback_bars", lookback)
        object.__setattr__(self, "output_unit", _text(self.output_unit, field="output_unit"))
        normalized: list[tuple[str, str]] = []
        for key, value in self.parameters:
            normalized.append((_text(key, field="parameter_key"), _text(value, field="parameter_value")))
        object.__setattr__(self, "parameters", tuple(sorted(normalized)))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "name": self.name,
            "version": self.version,
            "family": self.family,
            "independence_group": self.independence_group,
            "lookback_bars": self.lookback_bars,
            "output_unit": self.output_unit,
            "parameters": [{"key": key, "value": value} for key, value in self.parameters],
        }

    @property
    def definition_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class TechnicalEvidence:
    definition_id: str
    family: str
    independence_group: str
    symbol: str
    timeframe: str
    direction: int
    strength_bps: int
    confidence_bps: int
    event_time_ns: int
    as_of_time_ns: int
    value_text: str
    invalidation: str
    source_dataset_version: str
    quality_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _sha256_text(self.definition_id, field="definition_id"))
        object.__setattr__(self, "family", _text(self.family, field="family"))
        object.__setattr__(
            self,
            "independence_group",
            _text(self.independence_group, field="independence_group"),
        )
        object.__setattr__(self, "symbol", _text(self.symbol, field="symbol"))
        object.__setattr__(self, "timeframe", _text(self.timeframe, field="timeframe"))
        if self.direction not in (-1, 0, 1):
            raise TechnicalFoundationError("direction must be -1, 0 or 1")
        object.__setattr__(self, "strength_bps", _bps(self.strength_bps, field="strength_bps"))
        object.__setattr__(
            self,
            "confidence_bps",
            _bps(self.confidence_bps, field="confidence_bps"),
        )
        event_time = _non_negative_int(self.event_time_ns, field="event_time_ns")
        as_of_time = _non_negative_int(self.as_of_time_ns, field="as_of_time_ns")
        if event_time > as_of_time:
            raise TechnicalFoundationError("evidence event_time_ns cannot exceed as_of_time_ns")
        object.__setattr__(self, "value_text", _decimal_text(_decimal(self.value_text, field="value")))
        object.__setattr__(self, "invalidation", _text(self.invalidation, field="invalidation"))
        object.__setattr__(
            self,
            "source_dataset_version",
            _sha256_text(self.source_dataset_version, field="source_dataset_version"),
        )
        object.__setattr__(
            self,
            "quality_evidence_sha256",
            _sha256_text(self.quality_evidence_sha256, field="quality_evidence_sha256"),
        )

    @property
    def freshness_ns(self) -> int:
        return self.as_of_time_ns - self.event_time_ns

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "definition_id": self.definition_id,
            "family": self.family,
            "independence_group": self.independence_group,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "strength_bps": self.strength_bps,
            "confidence_bps": self.confidence_bps,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "freshness_ns": self.freshness_ns,
            "value_text": self.value_text,
            "invalidation": self.invalidation,
            "source_dataset_version": self.source_dataset_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
        }

    @property
    def evidence_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _validated_window(
    bars: Sequence[TrustedOHLCVBar],
    *,
    lookback_bars: int,
    policy: TechnicalFoundationPolicy,
) -> tuple[TrustedOHLCVBar, ...]:
    lookback = _non_negative_int(lookback_bars, field="lookback_bars")
    if lookback < 2 or lookback > policy.max_lookback_bars:
        raise TechnicalFoundationError("lookback_bars outside policy")
    if len(bars) < lookback:
        raise TechnicalFoundationError("insufficient bars for requested lookback")
    window = tuple(bars[-lookback:])
    symbol = window[0].symbol
    timeframe = window[0].timeframe
    previous_time = -1
    for bar in window:
        if bar.symbol != symbol or bar.timeframe != timeframe:
            raise TechnicalFoundationError("indicator window must use one symbol/timeframe")
        if bar.event_time_ns <= previous_time:
            raise TechnicalFoundationError("bar event_time_ns must be strictly increasing")
        previous_time = bar.event_time_ns
    return window


def simple_moving_average(
    bars: Sequence[TrustedOHLCVBar],
    *,
    lookback_bars: int,
    policy: TechnicalFoundationPolicy,
) -> Decimal:
    window = _validated_window(bars, lookback_bars=lookback_bars, policy=policy)
    total = sum((_decimal(bar.close_text, field="close") for bar in window), Decimal("0"))
    return (total / Decimal(len(window))).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)


def rate_of_change_bps(
    bars: Sequence[TrustedOHLCVBar],
    *,
    lookback_bars: int,
    policy: TechnicalFoundationPolicy,
) -> int:
    window = _validated_window(bars, lookback_bars=lookback_bars, policy=policy)
    first = _decimal(window[0].close_text, field="first_close")
    last = _decimal(window[-1].close_text, field="last_close")
    if first == 0:
        raise TechnicalFoundationError("rate of change denominator cannot be zero")
    raw = ((last - first) / abs(first)) * Decimal(10_000)
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def count_independent_confirmations(
    evidence: Sequence[TechnicalEvidence],
    *,
    direction: int,
) -> int:
    if direction not in (-1, 1):
        raise TechnicalFoundationError("confirmation direction must be -1 or 1")
    groups = {item.independence_group for item in evidence if item.direction == direction}
    return len(groups)
