from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .knowledge_graph import GraphEdge, GraphNode, KnowledgeGraphPolicy


class AttributionGuardrailError(ValueError):
    """P12-G attribution evidence violates governed guardrails."""


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AttributionGuardrailError(f"{field} must be integer")
    return value


def _positive_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number <= 0:
        raise AttributionGuardrailError(f"{field} must be positive")
    return number


def _non_negative_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number < 0:
        raise AttributionGuardrailError(f"{field} must be non-negative")
    return number


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AttributionGuardrailError(f"{field} must be non-empty list")
    normalized = tuple(str(item).strip().upper() for item in cast(list[object], value))
    if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
        raise AttributionGuardrailError(f"{field} must contain unique non-empty values")
    return normalized


@dataclass(frozen=True, slots=True)
class AttributionGuardrailPolicy:
    labels: tuple[str, ...]
    primary_independent_evidence_families: tuple[str, ...]
    non_independent_evidence_families: tuple[str, ...]
    driver_source_node_kinds: tuple[str, ...]
    target_node_kinds: tuple[str, ...]
    driver_context_edge_kinds: tuple[str, ...]
    minimum_context_sample_count: int
    maximum_context_uncertainty_bps: int
    minimum_supporting_sample_count: int
    minimum_supporting_independent_families: int
    minimum_supporting_mean_abs_strength_bps: int
    maximum_supporting_uncertainty_bps: int
    minimum_driver_sample_count: int
    minimum_driver_independent_families: int
    minimum_driver_mean_abs_strength_bps: int
    maximum_driver_uncertainty_bps: int
    canonical_edge_attribution_label: str
    temporal_precedence_alone_is_driver: bool
    correlation_alone_is_driver: bool
    likely_driver_is_causal_proof: bool
    narrative_labels_are_probability: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "AttributionGuardrailPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise AttributionGuardrailError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "EVIDENCE_BACKED_NARRATIVE_ATTRIBUTION":
            raise AttributionGuardrailError("unsupported P12-G policy")

        labels = _string_tuple(raw.get("labels"), field="labels")
        if set(labels) != {"LIKELY_DRIVER", "SUPPORTING_FACTOR", "CONTEXT_ONLY", "INSUFFICIENT_EVIDENCE"}:
            raise AttributionGuardrailError("unexpected attribution labels")

        primary = _string_tuple(
            raw.get("primary_independent_evidence_families"),
            field="primary_independent_evidence_families",
        )
        if set(primary) != {"TECHNICAL", "ORDER_FLOW", "FUNDAMENTAL", "NEWS"}:
            raise AttributionGuardrailError("unexpected primary evidence families")
        non_independent = _string_tuple(
            raw.get("non_independent_evidence_families"),
            field="non_independent_evidence_families",
        )
        if set(non_independent) != {"HISTORICAL", "COMPOSITE"}:
            raise AttributionGuardrailError("unexpected non-independent evidence families")

        source_kinds = _string_tuple(raw.get("driver_source_node_kinds"), field="driver_source_node_kinds")
        if set(source_kinds) != {"MACRO_EVENT", "NEWS_EVENT", "CAPITAL_FLOW", "ROTATION_EPISODE"}:
            raise AttributionGuardrailError("unexpected driver source node kinds")
        target_kinds = _string_tuple(raw.get("target_node_kinds"), field="target_node_kinds")
        if set(target_kinds) != {"ASSET", "MARKET"}:
            raise AttributionGuardrailError("unexpected target node kinds")
        driver_edges = _string_tuple(raw.get("driver_context_edge_kinds"), field="driver_context_edge_kinds")
        if set(driver_edges) != {"EVENT_CONTEXT", "CAPITAL_FLOW_LINK", "ROTATION_EPISODE_LINK"}:
            raise AttributionGuardrailError("unexpected driver context edge kinds")

        minimum_context_samples = _positive_integer(
            raw.get("minimum_context_sample_count"),
            field="minimum_context_sample_count",
        )
        maximum_context_uncertainty = _non_negative_integer(
            raw.get("maximum_context_uncertainty_bps"),
            field="maximum_context_uncertainty_bps",
        )
        minimum_supporting_samples = _positive_integer(
            raw.get("minimum_supporting_sample_count"),
            field="minimum_supporting_sample_count",
        )
        minimum_supporting_families = _positive_integer(
            raw.get("minimum_supporting_independent_families"),
            field="minimum_supporting_independent_families",
        )
        minimum_supporting_strength = _non_negative_integer(
            raw.get("minimum_supporting_mean_abs_strength_bps"),
            field="minimum_supporting_mean_abs_strength_bps",
        )
        maximum_supporting_uncertainty = _non_negative_integer(
            raw.get("maximum_supporting_uncertainty_bps"),
            field="maximum_supporting_uncertainty_bps",
        )
        minimum_driver_samples = _positive_integer(
            raw.get("minimum_driver_sample_count"),
            field="minimum_driver_sample_count",
        )
        minimum_driver_families = _positive_integer(
            raw.get("minimum_driver_independent_families"),
            field="minimum_driver_independent_families",
        )
        minimum_driver_strength = _non_negative_integer(
            raw.get("minimum_driver_mean_abs_strength_bps"),
            field="minimum_driver_mean_abs_strength_bps",
        )
        maximum_driver_uncertainty = _non_negative_integer(
            raw.get("maximum_driver_uncertainty_bps"),
            field="maximum_driver_uncertainty_bps",
        )
        for value, field in (
            (maximum_context_uncertainty, "maximum_context_uncertainty_bps"),
            (maximum_supporting_uncertainty, "maximum_supporting_uncertainty_bps"),
            (maximum_driver_uncertainty, "maximum_driver_uncertainty_bps"),
            (minimum_supporting_strength, "minimum_supporting_mean_abs_strength_bps"),
            (minimum_driver_strength, "minimum_driver_mean_abs_strength_bps"),
        ):
            if value > 10000:
                raise AttributionGuardrailError(f"{field} must be <= 10000")
        if not (
            minimum_context_samples <= minimum_supporting_samples <= minimum_driver_samples
            and maximum_driver_uncertainty <= maximum_supporting_uncertainty <= maximum_context_uncertainty
            and minimum_supporting_strength <= minimum_driver_strength
            and minimum_supporting_families <= minimum_driver_families
        ):
            raise AttributionGuardrailError("attribution thresholds are not monotonic")

        if raw.get("canonical_edge_attribution_label") != "UNATTRIBUTED":
            raise AttributionGuardrailError("canonical graph edges must remain UNATTRIBUTED")
        for field in (
            "temporal_precedence_alone_is_driver",
            "correlation_alone_is_driver",
            "likely_driver_is_causal_proof",
            "narrative_labels_are_probability",
            "canonical_tests_network_required",
        ):
            if raw.get(field) is not False:
                raise AttributionGuardrailError(f"{field} must remain false")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise AttributionGuardrailError("P12-G cannot enable trading")

        return cls(
            labels=labels,
            primary_independent_evidence_families=primary,
            non_independent_evidence_families=non_independent,
            driver_source_node_kinds=source_kinds,
            target_node_kinds=target_kinds,
            driver_context_edge_kinds=driver_edges,
            minimum_context_sample_count=minimum_context_samples,
            maximum_context_uncertainty_bps=maximum_context_uncertainty,
            minimum_supporting_sample_count=minimum_supporting_samples,
            minimum_supporting_independent_families=minimum_supporting_families,
            minimum_supporting_mean_abs_strength_bps=minimum_supporting_strength,
            maximum_supporting_uncertainty_bps=maximum_supporting_uncertainty,
            minimum_driver_sample_count=minimum_driver_samples,
            minimum_driver_independent_families=minimum_driver_families,
            minimum_driver_mean_abs_strength_bps=minimum_driver_strength,
            maximum_driver_uncertainty_bps=maximum_driver_uncertainty,
            canonical_edge_attribution_label="UNATTRIBUTED",
            temporal_precedence_alone_is_driver=False,
            correlation_alone_is_driver=False,
            likely_driver_is_causal_proof=False,
            narrative_labels_are_probability=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class AttributionAssessment:
    source_node_id: str
    target_node_id: str
    regime_label: str
    narrative_label: str
    evidence_edge_ids: tuple[str, ...]
    independent_evidence_families: tuple[str, ...]
    independent_evidence_family_count: int
    total_sample_count: int
    mean_abs_strength_bps: int
    maximum_uncertainty_bps: int
    direction_consistent: bool
    driver_context_present: bool
    causal_proof: bool
    probability: bool
    reason_codes: tuple[str, ...]


def assess_attribution(
    *,
    source_node: GraphNode,
    target_node: GraphNode,
    edges: Sequence[GraphEdge],
    graph_policy: KnowledgeGraphPolicy,
    policy: AttributionGuardrailPolicy,
) -> AttributionAssessment:
    if source_node.node_kind not in graph_policy.node_kinds:
        raise AttributionGuardrailError("source node kind is not governed")
    if target_node.node_kind not in policy.target_node_kinds:
        raise AttributionGuardrailError("target node kind is not governed for attribution")

    ordered = tuple(sorted(edges, key=lambda item: item.edge_id))
    edge_ids = tuple(item.edge_id for item in ordered)
    if len(edge_ids) != len(set(edge_ids)):
        raise AttributionGuardrailError("duplicate evidence edge_id")

    regimes = {item.regime_label for item in ordered}
    if len(regimes) > 1:
        raise AttributionGuardrailError("attribution evidence must share one regime")
    regime_label = next(iter(regimes)) if regimes else "UNSPECIFIED"
    if regime_label not in graph_policy.regime_labels:
        raise AttributionGuardrailError("unknown regime label")

    for edge in ordered:
        if edge.source_node_id != source_node.node_id or edge.target_node_id != target_node.node_id:
            raise AttributionGuardrailError("attribution evidence endpoint mismatch")
        if edge.attribution_label != policy.canonical_edge_attribution_label:
            raise AttributionGuardrailError("canonical evidence edge was mutated from UNATTRIBUTED")

    families = tuple(sorted({
        family
        for edge in ordered
        for family in edge.evidence_families
        if family in policy.primary_independent_evidence_families
    }))
    total_samples = sum(item.sample_count for item in ordered)
    mean_abs_strength = (
        sum(abs(item.strength_bps) for item in ordered) // len(ordered)
        if ordered
        else 0
    )
    maximum_uncertainty = max((item.uncertainty_bps for item in ordered), default=10000)
    signs = {
        1 if item.strength_bps > 0 else -1
        for item in ordered
        if item.strength_bps != 0
    }
    direction_consistent = bool(signs) and len(signs) == 1
    driver_context_present = any(
        item.edge_kind in policy.driver_context_edge_kinds for item in ordered
    )
    source_is_driver_kind = source_node.node_kind in policy.driver_source_node_kinds

    reasons: set[str] = set()
    if not ordered:
        reasons.add("NO_EVIDENCE_EDGES")
    if total_samples < policy.minimum_context_sample_count:
        reasons.add("INSUFFICIENT_CONTEXT_SAMPLE")
    if maximum_uncertainty > policy.maximum_context_uncertainty_bps:
        reasons.add("CONTEXT_UNCERTAINTY_TOO_HIGH")

    if (
        not ordered
        or total_samples < policy.minimum_context_sample_count
        or maximum_uncertainty > policy.maximum_context_uncertainty_bps
    ):
        label = "INSUFFICIENT_EVIDENCE"
    else:
        driver_eligible = (
            source_is_driver_kind
            and driver_context_present
            and len(families) >= policy.minimum_driver_independent_families
            and total_samples >= policy.minimum_driver_sample_count
            and mean_abs_strength >= policy.minimum_driver_mean_abs_strength_bps
            and maximum_uncertainty <= policy.maximum_driver_uncertainty_bps
            and direction_consistent
        )
        supporting_eligible = (
            len(families) >= policy.minimum_supporting_independent_families
            and total_samples >= policy.minimum_supporting_sample_count
            and mean_abs_strength >= policy.minimum_supporting_mean_abs_strength_bps
            and maximum_uncertainty <= policy.maximum_supporting_uncertainty_bps
            and direction_consistent
        )
        if driver_eligible:
            label = "LIKELY_DRIVER"
            reasons.add("MULTI_FAMILY_DRIVER_CONTEXT")
        elif supporting_eligible:
            label = "SUPPORTING_FACTOR"
            reasons.add("MULTI_FAMILY_SUPPORT")
        else:
            label = "CONTEXT_ONLY"
            if not source_is_driver_kind:
                reasons.add("SOURCE_KIND_NOT_DRIVER_ELIGIBLE")
            if not driver_context_present:
                reasons.add("NO_DRIVER_CONTEXT_EDGE")
            if len(families) < policy.minimum_supporting_independent_families:
                reasons.add("INSUFFICIENT_INDEPENDENT_FAMILIES")
            if not direction_consistent:
                reasons.add("DIRECTION_CONFLICT_OR_ZERO")
            if mean_abs_strength < policy.minimum_supporting_mean_abs_strength_bps:
                reasons.add("STRENGTH_BELOW_SUPPORTING_THRESHOLD")
            if maximum_uncertainty > policy.maximum_supporting_uncertainty_bps:
                reasons.add("UNCERTAINTY_ABOVE_SUPPORTING_THRESHOLD")

    reasons.add("NARRATIVE_NOT_CAUSAL_PROOF")
    reasons.add("NARRATIVE_NOT_PROBABILITY")
    return AttributionAssessment(
        source_node_id=source_node.node_id,
        target_node_id=target_node.node_id,
        regime_label=regime_label,
        narrative_label=label,
        evidence_edge_ids=edge_ids,
        independent_evidence_families=families,
        independent_evidence_family_count=len(families),
        total_sample_count=total_samples,
        mean_abs_strength_bps=mean_abs_strength,
        maximum_uncertainty_bps=maximum_uncertainty,
        direction_consistent=direction_consistent,
        driver_context_present=driver_context_present,
        causal_proof=False,
        probability=False,
        reason_codes=tuple(sorted(reasons)),
    )
