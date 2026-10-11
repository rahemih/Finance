from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .knowledge_graph import GraphEdge, GraphNode, KnowledgeGraphPolicy


class LeadLagError(ValueError):
    """P12-C lead/lag policy or evidence violates governed invariants."""


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LeadLagError(f"{field} must be integer")
    return value


@dataclass(frozen=True, slots=True)
class LeadLagPolicy:
    minimum_sample_count: int
    allowed_lag_steps: tuple[int, ...]
    correlation_min_bps: int
    correlation_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    lead_states: tuple[str, ...]
    tie_handling: str
    pairing_semantics: str
    edge_kind: str
    attribution_label: str
    evidence_family: str
    temporal_precedence_is_causation: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "LeadLagPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise LeadLagError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "SYMMETRIC_REGIME_CONDITIONAL_LEAD_LAG":
            raise LeadLagError("unsupported P12-C policy")
        minimum = _integer(raw.get("minimum_sample_count"), field="minimum_sample_count")
        if minimum < 3:
            raise LeadLagError("minimum_sample_count must be >= 3")
        lags_value = raw.get("allowed_lag_steps")
        if not isinstance(lags_value, list) or not lags_value:
            raise LeadLagError("allowed_lag_steps must be non-empty")
        lags = tuple(sorted({_integer(item, field="allowed_lag_step") for item in cast(list[object], lags_value)}))
        if 0 not in lags:
            raise LeadLagError("allowed_lag_steps must include zero")
        if set(lags) != {-item for item in lags}:
            raise LeadLagError("allowed_lag_steps must be symmetric around zero")
        if raw.get("tie_handling") != "AMBIGUOUS_NO_DIRECTIONAL_EDGE":
            raise LeadLagError("P12-C tie handling must fail closed")
        if raw.get("pairing_semantics") != "EXACT_TIMESTAMP_OFFSET":
            raise LeadLagError("P12-C requires exact timestamp-offset pairing")
        states_value = raw.get("lead_states")
        if not isinstance(states_value, list):
            raise LeadLagError("lead_states must be a list")
        states = tuple(str(item).strip().upper() for item in cast(list[object], states_value))
        if set(states) != {"LEFT_LEADS_RIGHT", "RIGHT_LEADS_LEFT", "CONTEMPORANEOUS", "AMBIGUOUS"}:
            raise LeadLagError("unexpected lead states")
        corr_min = _integer(raw.get("correlation_min_bps"), field="correlation_min_bps")
        corr_max = _integer(raw.get("correlation_max_bps"), field="correlation_max_bps")
        if (corr_min, corr_max) != (-10000, 10000):
            raise LeadLagError("correlation must use signed basis points")
        uncertainty_min = _integer(raw.get("uncertainty_min_bps"), field="uncertainty_min_bps")
        uncertainty_max = _integer(raw.get("uncertainty_max_bps"), field="uncertainty_max_bps")
        if (uncertainty_min, uncertainty_max) != (0, 10000):
            raise LeadLagError("uncertainty must use unsigned basis points")
        if raw.get("edge_kind") != "OBSERVED_ASSOCIATION" or raw.get("attribution_label") != "UNATTRIBUTED":
            raise LeadLagError("P12-C graph edge contract mismatch")
        if raw.get("evidence_family") != "HISTORICAL":
            raise LeadLagError("P12-C evidence family must be HISTORICAL")
        if raw.get("temporal_precedence_is_causation") is not False:
            raise LeadLagError("temporal precedence cannot be causation")
        if raw.get("canonical_tests_network_required") is not False:
            raise LeadLagError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise LeadLagError("P12-C cannot enable trading")
        return cls(
            minimum_sample_count=minimum,
            allowed_lag_steps=lags,
            correlation_min_bps=corr_min,
            correlation_max_bps=corr_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            lead_states=states,
            tie_handling="AMBIGUOUS_NO_DIRECTIONAL_EDGE",
            pairing_semantics="EXACT_TIMESTAMP_OFFSET",
            edge_kind="OBSERVED_ASSOCIATION",
            attribution_label="UNATTRIBUTED",
            evidence_family="HISTORICAL",
            temporal_precedence_is_causation=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class LeadLagObservation:
    timestamp_ns: int
    left_value: int
    right_value: int
    regime_label: str


@dataclass(frozen=True, slots=True)
class LeadLagCandidate:
    lag_steps: int
    lag_ns: int
    sample_count: int
    correlation_bps: int
    sampling_uncertainty_bps: int
    valid_from_ns: int
    valid_to_ns: int


@dataclass(frozen=True, slots=True)
class LeadLagResult:
    lead_state: str
    selected_lag_steps: int | None
    selected_lag_ns: int | None
    regime_label: str
    candidates: tuple[LeadLagCandidate, ...]
    edge: GraphEdge | None


def _pearson_bps(pairs: Sequence[tuple[int, int]]) -> int:
    n = len(pairs)
    sx = sum(left for left, _ in pairs)
    sy = sum(right for _, right in pairs)
    sxy = sum(left * right for left, right in pairs)
    sx2 = sum(left * left for left, _ in pairs)
    sy2 = sum(right * right for _, right in pairs)
    numerator = n * sxy - sx * sy
    left_variance = n * sx2 - sx * sx
    right_variance = n * sy2 - sy * sy
    if left_variance <= 0 or right_variance <= 0:
        raise LeadLagError("zero variance lead/lag candidate is undefined")
    denominator = isqrt(left_variance * right_variance)
    if denominator <= 0:
        raise LeadLagError("invalid lead/lag denominator")
    magnitude = min(10000, (abs(numerator) * 10000) // denominator)
    return -magnitude if numerator < 0 else magnitude


def _candidate(
    ordered: tuple[LeadLagObservation, ...],
    *,
    lag_steps: int,
    sampling_interval_ns: int,
    regime_label: str,
    policy: LeadLagPolicy,
) -> LeadLagCandidate | None:
    lag_ns = lag_steps * sampling_interval_ns
    by_time = {item.timestamp_ns: item for item in ordered}
    pairs: list[tuple[int, int]] = []
    times: list[int] = []
    for item in ordered:
        if item.regime_label.upper() != regime_label:
            continue
        target_time = item.timestamp_ns + lag_ns
        target = by_time.get(target_time)
        if target is None or target.regime_label.upper() != regime_label:
            continue
        pairs.append((item.left_value, target.right_value))
        times.extend((item.timestamp_ns, target_time))
    if len(pairs) < policy.minimum_sample_count:
        return None
    correlation = _pearson_bps(pairs)
    uncertainty = min(
        policy.uncertainty_max_bps,
        max(policy.uncertainty_min_bps, 10000 // max(1, isqrt(len(pairs)))),
    )
    return LeadLagCandidate(
        lag_steps=lag_steps,
        lag_ns=lag_ns,
        sample_count=len(pairs),
        correlation_bps=correlation,
        sampling_uncertainty_bps=uncertainty,
        valid_from_ns=min(times),
        valid_to_ns=max(times) + 1,
    )


def compute_lead_lag(
    observations: Sequence[LeadLagObservation],
    *,
    sampling_interval_ns: int,
    regime_label: str | None,
    left_node: GraphNode,
    right_node: GraphNode,
    provenance_sha256: Sequence[str],
    source_dataset_versions: Sequence[str],
    graph_policy: KnowledgeGraphPolicy,
    policy: LeadLagPolicy,
) -> LeadLagResult:
    if isinstance(sampling_interval_ns, bool) or sampling_interval_ns <= 0:
        raise LeadLagError("sampling_interval_ns must be positive integer")
    normalized_regime = regime_label.upper() if regime_label is not None else "UNSPECIFIED"
    if normalized_regime not in graph_policy.regime_labels:
        raise LeadLagError("unknown regime label")
    ordered = tuple(sorted(observations, key=lambda item: item.timestamp_ns))
    if not ordered:
        raise LeadLagError("lead/lag observations must be non-empty")
    if len({item.timestamp_ns for item in ordered}) != len(ordered):
        raise LeadLagError("duplicate observation timestamp")
    if any(item.timestamp_ns < 0 for item in ordered):
        raise LeadLagError("timestamp_ns must be non-negative")

    evaluated: list[LeadLagCandidate] = []
    for lag_steps in policy.allowed_lag_steps:
        try:
            candidate = _candidate(
                ordered,
                lag_steps=lag_steps,
                sampling_interval_ns=sampling_interval_ns,
                regime_label=normalized_regime,
                policy=policy,
            )
        except LeadLagError:
            candidate = None
        if candidate is not None:
            evaluated.append(candidate)
    if not evaluated:
        raise LeadLagError("no valid lead/lag candidate satisfies governed sample and variance rules")

    candidates = tuple(sorted(evaluated, key=lambda item: item.lag_steps))
    best_abs = max(abs(item.correlation_bps) for item in candidates)
    best = tuple(item for item in candidates if abs(item.correlation_bps) == best_abs)
    if len(best) != 1:
        return LeadLagResult(
            lead_state="AMBIGUOUS",
            selected_lag_steps=None,
            selected_lag_ns=None,
            regime_label=normalized_regime,
            candidates=candidates,
            edge=None,
        )

    selected = best[0]
    if selected.lag_steps > 0:
        lead_state = "LEFT_LEADS_RIGHT"
        source_node = left_node
        target_node = right_node
    elif selected.lag_steps < 0:
        lead_state = "RIGHT_LEADS_LEFT"
        source_node = right_node
        target_node = left_node
    else:
        lead_state = "CONTEMPORANEOUS"
        source_node = left_node
        target_node = right_node

    edge = GraphEdge.build(
        edge_kind=policy.edge_kind,
        source_node_id=source_node.node_id,
        target_node_id=target_node.node_id,
        valid_from_ns=selected.valid_from_ns,
        valid_to_ns=selected.valid_to_ns,
        regime_label=normalized_regime,
        sample_count=selected.sample_count,
        strength_bps=selected.correlation_bps,
        uncertainty_bps=selected.sampling_uncertainty_bps,
        evidence_families=(policy.evidence_family,),
        provenance_sha256=provenance_sha256,
        source_dataset_versions=source_dataset_versions,
        attribution_label=policy.attribution_label,
        policy=graph_policy,
    )
    return LeadLagResult(
        lead_state=lead_state,
        selected_lag_steps=selected.lag_steps,
        selected_lag_ns=selected.lag_ns,
        regime_label=normalized_regime,
        candidates=candidates,
        edge=edge,
    )
