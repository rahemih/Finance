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
)


class MultiTimeframeRegimeError(TechnicalFoundationError):
    """P08-G inputs or policy violate governed multi-timeframe/regime invariants."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MultiTimeframeRegimeError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MultiTimeframeRegimeError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MultiTimeframeRegimeError(f"{field} must be a positive integer")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise MultiTimeframeRegimeError(f"{field} must be boolean")
    return value


@dataclass(frozen=True, slots=True)
class MultiTimeframeRegimePolicy:
    independence_group: str
    cross_timeframe_independence_status: str
    cross_family_independence_status: str
    min_timeframes: int
    max_timeframes: int
    same_evaluation_as_of_required: bool
    same_method_definition_required: bool
    same_lineage_required: bool
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "MultiTimeframeRegimePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise MultiTimeframeRegimeError(
                "unsupported P08-G policy schema_version"
            )
        if raw.get("input_family") != "TREND":
            raise MultiTimeframeRegimeError(
                "P08-G input family must be TREND"
            )
        if raw.get("output_family") != "REGIME":
            raise MultiTimeframeRegimeError(
                "P08-G output family must be REGIME"
            )
        if raw.get("cross_timeframe_independence_status") != "RELATED_NOT_INDEPENDENT":
            raise MultiTimeframeRegimeError(
                "timeframe copies must remain related and non-independent"
            )
        if raw.get("cross_family_independence_status") != "PROVISIONAL_PENDING_P08_H":
            raise MultiTimeframeRegimeError(
                "cross-family independence must remain pending P08-H"
            )
        if raw.get("aligned_strength_method") != "AVERAGE":
            raise MultiTimeframeRegimeError(
                "aligned strength method must be AVERAGE"
            )
        if raw.get("aligned_confidence_method") != "MINIMUM":
            raise MultiTimeframeRegimeError(
                "aligned confidence method must be MINIMUM"
            )
        if raw.get("non_aligned_direction_semantics") != "NEUTRAL_ZERO":
            raise MultiTimeframeRegimeError(
                "non-aligned direction must remain neutral zero"
            )
        if raw.get("score_semantics") != "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY":
            raise MultiTimeframeRegimeError(
                "P08-G scores must not claim trade probability"
            )

        minimum = _positive_int(
            raw.get("min_timeframes"),
            field="min_timeframes",
        )
        maximum = _positive_int(
            raw.get("max_timeframes"),
            field="max_timeframes",
        )
        if minimum < 2:
            raise MultiTimeframeRegimeError(
                "min_timeframes must be at least 2"
            )
        if maximum < minimum:
            raise MultiTimeframeRegimeError(
                "max_timeframes cannot be smaller than min_timeframes"
            )

        same_as_of = _boolean(
            raw.get("same_evaluation_as_of_required"),
            field="same_evaluation_as_of_required",
        )
        same_method = _boolean(
            raw.get("same_method_definition_required"),
            field="same_method_definition_required",
        )
        same_lineage = _boolean(
            raw.get("same_lineage_required"),
            field="same_lineage_required",
        )
        if not same_as_of or not same_method or not same_lineage:
            raise MultiTimeframeRegimeError(
                "P08-G baseline requires common as-of, method and lineage"
            )

        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise MultiTimeframeRegimeError(
                "P08-G forbids direct trade output"
            )

        return cls(
            independence_group=_text(
                raw.get("independence_group"),
                field="independence_group",
            ),
            cross_timeframe_independence_status=_text(
                raw.get("cross_timeframe_independence_status"),
                field="cross_timeframe_independence_status",
            ),
            cross_family_independence_status=_text(
                raw.get("cross_family_independence_status"),
                field="cross_family_independence_status",
            ),
            min_timeframes=minimum,
            max_timeframes=maximum,
            same_evaluation_as_of_required=same_as_of,
            same_method_definition_required=same_method,
            same_lineage_required=same_lineage,
            direct_trade_output_allowed=direct_trade,
        )


@dataclass(frozen=True, slots=True)
class MultiTimeframeRegimeEvaluation:
    classification: str
    timeframes: tuple[str, ...]
    evidence: TechnicalEvidence
    cross_timeframe_independence_status: str
    cross_family_independence_status: str


class MultiTimeframeRegimeModel:
    def __init__(
        self,
        *,
        foundation_policy: TechnicalFoundationPolicy,
        policy: MultiTimeframeRegimePolicy,
    ) -> None:
        if "TREND" not in foundation_policy.allowed_families:
            raise MultiTimeframeRegimeError(
                "foundation policy does not allow TREND family"
            )
        if "REGIME" not in foundation_policy.allowed_families:
            raise MultiTimeframeRegimeError(
                "foundation policy does not allow REGIME family"
            )
        self._foundation_policy = foundation_policy
        self._policy = policy

    def definition(self) -> IndicatorDefinition:
        p = self._policy
        return IndicatorDefinition(
            name="regime.multi-timeframe-trend-compatibility",
            version="1.0.0",
            family="REGIME",
            independence_group=p.independence_group,
            lookback_bars=p.min_timeframes,
            output_unit="REGIME_STATE",
            parameters=(
                ("min_timeframes", str(p.min_timeframes)),
                ("max_timeframes", str(p.max_timeframes)),
                (
                    "cross_timeframe_independence",
                    p.cross_timeframe_independence_status,
                ),
                (
                    "cross_family_independence",
                    p.cross_family_independence_status,
                ),
            ),
        )

    def _validated(
        self,
        evidence: Sequence[TechnicalEvidence],
    ) -> tuple[TechnicalEvidence, ...]:
        p = self._policy
        if not p.min_timeframes <= len(evidence) <= p.max_timeframes:
            raise MultiTimeframeRegimeError(
                "timeframe evidence count outside governed bounds"
            )

        ordered = tuple(sorted(evidence, key=lambda item: item.timeframe))
        first = ordered[0]
        seen: set[str] = set()
        for item in ordered:
            if item.family != "TREND":
                raise MultiTimeframeRegimeError(
                    "P08-G accepts TREND evidence only"
                )
            if item.symbol != first.symbol:
                raise MultiTimeframeRegimeError(
                    "P08-G evidence must use one symbol"
                )
            if item.timeframe in seen:
                raise MultiTimeframeRegimeError(
                    "P08-G requires unique timeframes"
                )
            seen.add(item.timeframe)
            if item.as_of_time_ns != first.as_of_time_ns:
                raise MultiTimeframeRegimeError(
                    "P08-G requires one evaluation as-of time"
                )
            if item.definition_id != first.definition_id:
                raise MultiTimeframeRegimeError(
                    "P08-G requires one TREND method definition"
                )
            if item.independence_group != first.independence_group:
                raise MultiTimeframeRegimeError(
                    "P08-G requires one TREND independence group"
                )
            if item.source_dataset_version != first.source_dataset_version:
                raise MultiTimeframeRegimeError(
                    "P08-G requires one source dataset version"
                )
            if item.quality_evidence_sha256 != first.quality_evidence_sha256:
                raise MultiTimeframeRegimeError(
                    "P08-G requires one quality evidence lineage"
                )
        return ordered

    def evaluate(
        self,
        evidence: Sequence[TechnicalEvidence],
    ) -> MultiTimeframeRegimeEvaluation:
        ordered = self._validated(evidence)
        directions = tuple(item.direction for item in ordered)
        direction_set = set(directions)

        if direction_set == {1}:
            classification = "ALIGNED_BULLISH"
            output_direction = 1
        elif direction_set == {-1}:
            classification = "ALIGNED_BEARISH"
            output_direction = -1
        elif direction_set == {0}:
            classification = "NEUTRAL"
            output_direction = 0
        elif 1 in direction_set and -1 in direction_set:
            classification = "CONFLICT"
            output_direction = 0
        else:
            classification = "TRANSITION"
            output_direction = 0

        if output_direction == 0:
            strength = 0
            confidence = 0
        else:
            strength = min(
                self._foundation_policy.max_strength_bps,
                sum(item.strength_bps for item in ordered) // len(ordered),
            )
            confidence = min(
                self._foundation_policy.max_confidence_bps,
                min(item.confidence_bps for item in ordered),
            )

        first = ordered[0]
        event_time = max(item.event_time_ns for item in ordered)
        timeframes = tuple(item.timeframe for item in ordered)
        combined_timeframe = "MULTI:" + ",".join(timeframes)
        regime_evidence = TechnicalEvidence(
            definition_id=self.definition().definition_id,
            family="REGIME",
            independence_group=self._policy.independence_group,
            symbol=first.symbol,
            timeframe=combined_timeframe,
            direction=output_direction,
            strength_bps=strength,
            confidence_bps=confidence,
            event_time_ns=event_time,
            as_of_time_ns=first.as_of_time_ns,
            value_text=str(output_direction),
            invalidation=(
                "regime evidence invalidates when any constituent TREND snapshot changes, "
                "expires, changes method/lineage, or the governed timeframe set changes; "
                "multiple timeframes remain related evidence rather than independent votes"
            ),
            source_dataset_version=first.source_dataset_version,
            quality_evidence_sha256=first.quality_evidence_sha256,
        )

        return MultiTimeframeRegimeEvaluation(
            classification=classification,
            timeframes=timeframes,
            evidence=regime_evidence,
            cross_timeframe_independence_status=(
                self._policy.cross_timeframe_independence_status
            ),
            cross_family_independence_status=(
                self._policy.cross_family_independence_status
            ),
        )
