from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .knowledge_graph import GraphEdge, GraphNode, KnowledgeGraphPolicy


class ConditionalCorrelationError(ValueError):
    """P12-B rolling/conditional correlation invariant failed closed."""


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConditionalCorrelationError(f"{field} must be integer")
    return value


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConditionalCorrelationError(f"{field} must be a non-empty list")
    items = tuple(str(item).strip().upper() for item in cast(list[object], value))
    if any(not item for item in items) or len(set(items)) != len(items):
        raise ConditionalCorrelationError(f"{field} values must be unique non-empty strings")
    return items


@dataclass(frozen=True, slots=True)
class ConditionalCorrelationPolicy:
    minimum_sample_count: int
    allowed_window_sizes: tuple[int, ...]
    correlation_min_bps: int
    correlation_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    edge_kind: str
    attribution_label: str
    evidence_family: str
    correlation_is_causation: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ConditionalCorrelationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise ConditionalCorrelationError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "ROLLING_REGIME_CONDITIONAL_CORRELATION":
            raise ConditionalCorrelationError("unsupported P12-B policy")
        minimum = _integer(raw.get("minimum_sample_count"), field="minimum_sample_count")
        if minimum < 3:
            raise ConditionalCorrelationError("minimum_sample_count must be >= 3")
        windows_value = raw.get("allowed_window_sizes")
        if not isinstance(windows_value, list) or not windows_value:
            raise ConditionalCorrelationError("allowed_window_sizes must be non-empty")
        windows = tuple(sorted({_integer(item, field="allowed_window_size") for item in cast(list[object], windows_value)}))
        if any(item < minimum for item in windows):
            raise ConditionalCorrelationError("window size below minimum_sample_count")
        corr_min = _integer(raw.get("correlation_min_bps"), field="correlation_min_bps")
        corr_max = _integer(raw.get("correlation_max_bps"), field="correlation_max_bps")
        if (corr_min, corr_max) != (-10000, 10000):
            raise ConditionalCorrelationError("correlation must use signed basis points")
        uncertainty_min = _integer(raw.get("uncertainty_min_bps"), field="uncertainty_min_bps")
        uncertainty_max = _integer(raw.get("uncertainty_max_bps"), field="uncertainty_max_bps")
        if (uncertainty_min, uncertainty_max) != (0, 10000):
            raise ConditionalCorrelationError("uncertainty must use unsigned basis points")
        if raw.get("edge_kind") != "OBSERVED_ASSOCIATION" or raw.get("attribution_label") != "UNATTRIBUTED":
            raise ConditionalCorrelationError("P12-B graph edge contract mismatch")
        if raw.get("evidence_family") != "HISTORICAL":
            raise ConditionalCorrelationError("P12-B evidence family must be HISTORICAL")
        if raw.get("correlation_is_causation") is not False:
            raise ConditionalCorrelationError("correlation cannot be treated as causation")
        if raw.get("canonical_tests_network_required") is not False:
            raise ConditionalCorrelationError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise ConditionalCorrelationError("P12-B cannot enable trading")
        return cls(
            minimum_sample_count=minimum,
            allowed_window_sizes=windows,
            correlation_min_bps=corr_min,
            correlation_max_bps=corr_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            edge_kind="OBSERVED_ASSOCIATION",
            attribution_label="UNATTRIBUTED",
            evidence_family="HISTORICAL",
            correlation_is_causation=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class CorrelationObservation:
    timestamp_ns: int
    left_value: int
    right_value: int
    regime_label: str


@dataclass(frozen=True, slots=True)
class ConditionalCorrelationResult:
    sample_count: int
    window_size: int
    regime_label: str
    valid_from_ns: int
    valid_to_ns: int
    correlation_bps: int
    sampling_uncertainty_bps: int
    edge: GraphEdge


def _pearson_bps(observations: Sequence[CorrelationObservation]) -> int:
    n = len(observations)
    sx = sum(item.left_value for item in observations)
    sy = sum(item.right_value for item in observations)
    sxy = sum(item.left_value * item.right_value for item in observations)
    sx2 = sum(item.left_value * item.left_value for item in observations)
    sy2 = sum(item.right_value * item.right_value for item in observations)
    numerator = n * sxy - sx * sy
    left_variance = n * sx2 - sx * sx
    right_variance = n * sy2 - sy * sy
    if left_variance <= 0 or right_variance <= 0:
        raise ConditionalCorrelationError("zero variance correlation is undefined")
    denominator = isqrt(left_variance * right_variance)
    if denominator <= 0:
        raise ConditionalCorrelationError("invalid correlation denominator")
    magnitude = min(10000, (abs(numerator) * 10000) // denominator)
    return -magnitude if numerator < 0 else magnitude


def compute_conditional_correlation(
    observations: Sequence[CorrelationObservation],
    *,
    window_size: int,
    regime_label: str | None,
    source_node: GraphNode,
    target_node: GraphNode,
    provenance_sha256: Sequence[str],
    source_dataset_versions: Sequence[str],
    graph_policy: KnowledgeGraphPolicy,
    policy: ConditionalCorrelationPolicy,
) -> ConditionalCorrelationResult:
    if window_size not in policy.allowed_window_sizes:
        raise ConditionalCorrelationError("window_size is not governed")
    normalized_regime = regime_label.upper() if regime_label is not None else "UNSPECIFIED"
    if normalized_regime not in graph_policy.regime_labels:
        raise ConditionalCorrelationError("unknown regime label")
    ordered = tuple(sorted(observations, key=lambda item: item.timestamp_ns))
    if len({item.timestamp_ns for item in ordered}) != len(ordered):
        raise ConditionalCorrelationError("duplicate observation timestamp")
    if any(item.timestamp_ns < 0 for item in ordered):
        raise ConditionalCorrelationError("timestamp_ns must be non-negative")
    if regime_label is not None:
        ordered = tuple(item for item in ordered if item.regime_label.upper() == normalized_regime)
    selected = ordered[-window_size:]
    if len(selected) < policy.minimum_sample_count:
        raise ConditionalCorrelationError("insufficient qualifying sample count")
    correlation_bps = _pearson_bps(selected)
    sample_count = len(selected)
    uncertainty = min(
        policy.uncertainty_max_bps,
        max(policy.uncertainty_min_bps, 10000 // max(1, isqrt(sample_count))),
    )
    start = selected[0].timestamp_ns
    end = selected[-1].timestamp_ns + 1
    edge = GraphEdge.build(
        edge_kind=policy.edge_kind,
        source_node_id=source_node.node_id,
        target_node_id=target_node.node_id,
        valid_from_ns=start,
        valid_to_ns=end,
        regime_label=normalized_regime,
        sample_count=sample_count,
        strength_bps=correlation_bps,
        uncertainty_bps=uncertainty,
        evidence_families=(policy.evidence_family,),
        provenance_sha256=provenance_sha256,
        source_dataset_versions=source_dataset_versions,
        attribution_label=policy.attribution_label,
        policy=graph_policy,
    )
    return ConditionalCorrelationResult(
        sample_count=sample_count,
        window_size=window_size,
        regime_label=normalized_regime,
        valid_from_ns=start,
        valid_to_ns=end,
        correlation_bps=correlation_bps,
        sampling_uncertainty_bps=uncertainty,
        edge=edge,
    )
