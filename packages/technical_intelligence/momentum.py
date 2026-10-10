from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .foundation import (
    IndicatorDefinition,
    TechnicalEvidence,
    TechnicalFoundationError,
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    rate_of_change_bps,
)


class MomentumFamilyError(TechnicalFoundationError):
    """Momentum-family inputs or policy violate governed P08-C invariants."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MomentumFamilyError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MomentumFamilyError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MomentumFamilyError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MomentumFamilyError(f"{field} must be a non-negative integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise MomentumFamilyError(f"{field} must be boolean")
    return value


@dataclass(frozen=True, slots=True)
class MomentumFamilyPolicy:
    independence_group: str
    short_window: int
    long_window: int
    min_short_roc_bps: int
    min_long_roc_bps: int
    base_directional_confidence_bps: int
    max_strength_bps: int
    max_confidence_bps: int
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "MomentumFamilyPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise MomentumFamilyError("unsupported momentum policy schema_version")
        if raw.get("family") != "MOMENTUM":
            raise MomentumFamilyError("momentum policy family must be MOMENTUM")
        if raw.get("score_semantics") != "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY":
            raise MomentumFamilyError("momentum scores must not claim empirical trade probability")
        short_window = _positive_int(raw.get("short_window"), field="short_window")
        long_window = _positive_int(raw.get("long_window"), field="long_window")
        if short_window >= long_window:
            raise MomentumFamilyError("short_window must be smaller than long_window")
        max_strength = _positive_int(raw.get("max_strength_bps"), field="max_strength_bps")
        max_confidence = _positive_int(raw.get("max_confidence_bps"), field="max_confidence_bps")
        if max_strength > 10_000 or max_confidence > 10_000:
            raise MomentumFamilyError("momentum score bounds cannot exceed 10000 bps")
        base_confidence = _non_negative_int(
            raw.get("base_directional_confidence_bps"),
            field="base_directional_confidence_bps",
        )
        if base_confidence > max_confidence:
            raise MomentumFamilyError("base confidence cannot exceed maximum confidence")
        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise MomentumFamilyError("P08-C forbids direct trade output")
        return cls(
            independence_group=_text(raw.get("independence_group"), field="independence_group"),
            short_window=short_window,
            long_window=long_window,
            min_short_roc_bps=_non_negative_int(
                raw.get("min_short_roc_bps"),
                field="min_short_roc_bps",
            ),
            min_long_roc_bps=_non_negative_int(
                raw.get("min_long_roc_bps"),
                field="min_long_roc_bps",
            ),
            base_directional_confidence_bps=base_confidence,
            max_strength_bps=max_strength,
            max_confidence_bps=max_confidence,
            direct_trade_output_allowed=direct_trade,
        )

    @property
    def required_bars(self) -> int:
        return self.long_window


@dataclass(frozen=True, slots=True)
class MomentumEvaluation:
    short_roc_bps: int
    long_roc_bps: int
    normalized_acceleration_bps: int
    evidence: TechnicalEvidence


class MomentumFamilyModel:
    def __init__(
        self,
        *,
        foundation_policy: TechnicalFoundationPolicy,
        momentum_policy: MomentumFamilyPolicy,
    ) -> None:
        if "MOMENTUM" not in foundation_policy.allowed_families:
            raise MomentumFamilyError("foundation policy does not allow MOMENTUM family")
        if momentum_policy.required_bars > foundation_policy.max_lookback_bars:
            raise MomentumFamilyError("momentum required history exceeds foundation lookback bound")
        self._foundation_policy = foundation_policy
        self._momentum_policy = momentum_policy

    def _window(self, bars: Sequence[TrustedOHLCVBar]) -> tuple[TrustedOHLCVBar, ...]:
        required = self._momentum_policy.required_bars
        if len(bars) < required:
            raise MomentumFamilyError("insufficient bars for momentum-family evaluation")
        window = tuple(bars[-required:])
        first = window[0]
        evaluation_as_of = window[-1].as_of_time_ns
        previous_event = -1
        for bar in window:
            if bar.symbol != first.symbol:
                raise MomentumFamilyError("momentum window must use one symbol")
            if bar.timeframe != first.timeframe:
                raise MomentumFamilyError("momentum window must use one timeframe")
            if bar.source_dataset_version != first.source_dataset_version:
                raise MomentumFamilyError("momentum window must use one dataset version")
            if bar.quality_evidence_sha256 != first.quality_evidence_sha256:
                raise MomentumFamilyError("momentum window must use one quality evidence lineage")
            if bar.event_time_ns <= previous_event:
                raise MomentumFamilyError("momentum event times must be strictly increasing")
            if bar.as_of_time_ns > evaluation_as_of:
                raise MomentumFamilyError("momentum window contains future as-of information")
            previous_event = bar.event_time_ns
        return window

    def definition(self) -> IndicatorDefinition:
        p = self._momentum_policy
        return IndicatorDefinition(
            name="momentum.dual-horizon-roc",
            version="1.0.0",
            family="MOMENTUM",
            independence_group=p.independence_group,
            lookback_bars=p.required_bars,
            output_unit="BPS",
            parameters=(
                ("short_window", str(p.short_window)),
                ("long_window", str(p.long_window)),
                ("min_short_roc_bps", str(p.min_short_roc_bps)),
                ("min_long_roc_bps", str(p.min_long_roc_bps)),
            ),
        )

    def evaluate(self, bars: Sequence[TrustedOHLCVBar]) -> MomentumEvaluation:
        p = self._momentum_policy
        window = self._window(bars)
        short_roc = rate_of_change_bps(
            window[-p.short_window :],
            lookback_bars=p.short_window,
            policy=self._foundation_policy,
        )
        long_roc = rate_of_change_bps(
            window,
            lookback_bars=p.long_window,
            policy=self._foundation_policy,
        )
        short_intervals = p.short_window - 1
        long_intervals = p.long_window - 1
        expected_short_from_long = (long_roc * short_intervals) // long_intervals
        acceleration = short_roc - expected_short_from_long

        bullish = short_roc >= p.min_short_roc_bps and long_roc >= p.min_long_roc_bps
        bearish = short_roc <= -p.min_short_roc_bps and long_roc <= -p.min_long_roc_bps
        direction = 1 if bullish else (-1 if bearish else 0)

        if direction == 0:
            strength = 0
            confidence = 0
        else:
            raw_strength = (abs(short_roc) + abs(long_roc)) // 2
            strength = min(
                p.max_strength_bps,
                self._foundation_policy.max_strength_bps,
                raw_strength,
            )
            acceleration_context = min(abs(acceleration), 1000) // 4
            confidence = min(
                p.max_confidence_bps,
                self._foundation_policy.max_confidence_bps,
                p.base_directional_confidence_bps + strength // 2 + acceleration_context,
            )

        definition = self.definition()
        latest = window[-1]
        evidence = TechnicalEvidence(
            definition_id=definition.definition_id,
            family="MOMENTUM",
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
                "momentum family invalidates when short- and long-horizon return momentum "
                "no longer satisfy the governed directional thresholds"
            ),
            source_dataset_version=latest.source_dataset_version,
            quality_evidence_sha256=latest.quality_evidence_sha256,
        )
        return MomentumEvaluation(
            short_roc_bps=short_roc,
            long_roc_bps=long_roc,
            normalized_acceleration_bps=acceleration,
            evidence=evidence,
        )
