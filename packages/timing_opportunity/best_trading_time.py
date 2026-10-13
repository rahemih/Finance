from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class BestTradingTimeError(ValueError):
    """P13-B timing-quality input or policy violates governed invariants."""


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BestTradingTimeError(f"{field} must be integer")
    return value


def _positive_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number <= 0:
        raise BestTradingTimeError(f"{field} must be positive")
    return number


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BestTradingTimeError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class BestTradingTimePolicy:
    minimum_sample_count: int
    edge_min_bps: int
    edge_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    maximum_usable_uncertainty_bps: int
    preferred_min_adjusted_edge_bps: int
    weak_max_adjusted_edge_bps: int
    timing_classes: tuple[str, ...]
    require_open_market_for_usable_window: bool
    best_window_selection_in_scope: bool
    opportunity_ranking_in_scope: bool
    no_trade_authority: bool
    signal_probability_in_scope: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "BestTradingTimePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise BestTradingTimeError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "CONSERVATIVE_HISTORICAL_TIMING_QUALITY":
            raise BestTradingTimeError("unsupported P13-B policy")

        minimum = _positive_integer(raw.get("minimum_sample_count"), field="minimum_sample_count")
        edge_min = _integer(raw.get("edge_min_bps"), field="edge_min_bps")
        edge_max = _integer(raw.get("edge_max_bps"), field="edge_max_bps")
        if (edge_min, edge_max) != (-10000, 10000):
            raise BestTradingTimeError("edge scale must be signed basis points")
        uncertainty_min = _integer(raw.get("uncertainty_min_bps"), field="uncertainty_min_bps")
        uncertainty_max = _integer(raw.get("uncertainty_max_bps"), field="uncertainty_max_bps")
        if (uncertainty_min, uncertainty_max) != (0, 10000):
            raise BestTradingTimeError("uncertainty scale must be unsigned basis points")
        max_usable = _integer(raw.get("maximum_usable_uncertainty_bps"), field="maximum_usable_uncertainty_bps")
        if not uncertainty_min <= max_usable <= uncertainty_max:
            raise BestTradingTimeError("maximum usable uncertainty is invalid")
        preferred = _integer(raw.get("preferred_min_adjusted_edge_bps"), field="preferred_min_adjusted_edge_bps")
        weak = _integer(raw.get("weak_max_adjusted_edge_bps"), field="weak_max_adjusted_edge_bps")
        if weak >= preferred:
            raise BestTradingTimeError("timing thresholds must be ordered")

        classes_value = raw.get("timing_classes")
        if not isinstance(classes_value, list):
            raise BestTradingTimeError("timing_classes must be list")
        classes = tuple(str(item).strip().upper() for item in cast(list[object], classes_value))
        expected = ("PREFERRED", "STANDARD", "WEAK", "INSUFFICIENT_EVIDENCE", "CLOSED_CONTEXT")
        if classes != expected:
            raise BestTradingTimeError("unexpected timing classes")

        if raw.get("require_open_market_for_usable_window") is not True:
            raise BestTradingTimeError("usable timing windows must require open market context")
        if raw.get("best_window_selection_in_scope") is not True:
            raise BestTradingTimeError("P13-B must own best-window selection")
        if raw.get("opportunity_ranking_in_scope") is not False:
            raise BestTradingTimeError("opportunity ranking belongs to P13-D")
        if raw.get("no_trade_authority") is not False:
            raise BestTradingTimeError("hard no-trade authority belongs to P13-E")
        if raw.get("signal_probability_in_scope") is not False:
            raise BestTradingTimeError("signal probability belongs to P14")
        if raw.get("canonical_tests_network_required") is not False:
            raise BestTradingTimeError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise BestTradingTimeError("P13-B cannot enable trading")

        return cls(
            minimum_sample_count=minimum,
            edge_min_bps=edge_min,
            edge_max_bps=edge_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            maximum_usable_uncertainty_bps=max_usable,
            preferred_min_adjusted_edge_bps=preferred,
            weak_max_adjusted_edge_bps=weak,
            timing_classes=classes,
            require_open_market_for_usable_window=True,
            best_window_selection_in_scope=True,
            opportunity_ranking_in_scope=False,
            no_trade_authority=False,
            signal_probability_in_scope=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class TimingWindowEvidence:
    window_id: str
    asset_id: str
    strategy_id: str
    timeframe: str
    regime_label: str
    session_labels: tuple[str, ...]
    sample_count: int
    mean_edge_bps: int
    uncertainty_bps: int
    market_open: bool


@dataclass(frozen=True, slots=True)
class TimingWindowAssessment:
    window_id: str
    asset_id: str
    strategy_id: str
    timeframe: str
    regime_label: str
    session_labels: tuple[str, ...]
    sample_count: int
    mean_edge_bps: int
    uncertainty_bps: int
    adjusted_edge_bps: int
    timing_class: str
    usable: bool


@dataclass(frozen=True, slots=True)
class BestTradingTimeResult:
    selected_window_id: str
    selected: TimingWindowAssessment
    assessments: tuple[TimingWindowAssessment, ...]


def assess_timing_window(
    evidence: TimingWindowEvidence,
    *,
    policy: BestTradingTimePolicy,
) -> TimingWindowAssessment:
    window_id = _text(evidence.window_id, field="window_id")
    asset_id = _text(evidence.asset_id, field="asset_id")
    strategy_id = _text(evidence.strategy_id, field="strategy_id")
    timeframe = _text(evidence.timeframe, field="timeframe")
    regime = _text(evidence.regime_label, field="regime_label").upper()
    sessions = tuple(sorted({_text(item, field="session_label").upper() for item in evidence.session_labels}))
    if not sessions:
        raise BestTradingTimeError("session_labels must be non-empty")
    sample_count = _positive_integer(evidence.sample_count, field="sample_count")
    mean_edge = _integer(evidence.mean_edge_bps, field="mean_edge_bps")
    uncertainty = _integer(evidence.uncertainty_bps, field="uncertainty_bps")
    if not policy.edge_min_bps <= mean_edge <= policy.edge_max_bps:
        raise BestTradingTimeError("mean_edge_bps outside governed bounds")
    if not policy.uncertainty_min_bps <= uncertainty <= policy.uncertainty_max_bps:
        raise BestTradingTimeError("uncertainty_bps outside governed bounds")
    if not isinstance(evidence.market_open, bool):
        raise BestTradingTimeError("market_open must be boolean")

    adjusted = max(policy.edge_min_bps, mean_edge - uncertainty)
    if not evidence.market_open:
        timing_class = "CLOSED_CONTEXT"
        usable = False
    elif sample_count < policy.minimum_sample_count or uncertainty > policy.maximum_usable_uncertainty_bps:
        timing_class = "INSUFFICIENT_EVIDENCE"
        usable = False
    elif adjusted >= policy.preferred_min_adjusted_edge_bps:
        timing_class = "PREFERRED"
        usable = True
    elif adjusted <= policy.weak_max_adjusted_edge_bps:
        timing_class = "WEAK"
        usable = True
    else:
        timing_class = "STANDARD"
        usable = True

    return TimingWindowAssessment(
        window_id=window_id,
        asset_id=asset_id,
        strategy_id=strategy_id,
        timeframe=timeframe,
        regime_label=regime,
        session_labels=sessions,
        sample_count=sample_count,
        mean_edge_bps=mean_edge,
        uncertainty_bps=uncertainty,
        adjusted_edge_bps=adjusted,
        timing_class=timing_class,
        usable=usable,
    )


def select_best_timing_window(
    evidence: Sequence[TimingWindowEvidence],
    *,
    policy: BestTradingTimePolicy,
) -> BestTradingTimeResult:
    if not evidence:
        raise BestTradingTimeError("timing evidence must be non-empty")
    assessments = tuple(assess_timing_window(item, policy=policy) for item in evidence)
    keys = {
        (item.asset_id, item.strategy_id, item.timeframe, item.regime_label)
        for item in assessments
    }
    if len(keys) != 1:
        raise BestTradingTimeError("best-window comparison set must be homogeneous")
    window_ids = [item.window_id for item in assessments]
    if len(window_ids) != len(set(window_ids)):
        raise BestTradingTimeError("duplicate window_id")
    eligible = tuple(item for item in assessments if item.usable)
    if not eligible:
        raise BestTradingTimeError("no usable timing window")
    selected = sorted(
        eligible,
        key=lambda item: (
            -item.adjusted_edge_bps,
            -item.sample_count,
            item.uncertainty_bps,
            item.window_id,
        ),
    )[0]
    return BestTradingTimeResult(
        selected_window_id=selected.window_id,
        selected=selected,
        assessments=tuple(sorted(assessments, key=lambda item: item.window_id)),
    )
