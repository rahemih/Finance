from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .knowledge_graph import GraphEdge, GraphNode, KnowledgeGraphPolicy


class EventStudyError(ValueError):
    """P12-D event-study policy or evidence violates governed invariants."""


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventStudyError(f"{field} must be integer")
    return value


def _positive_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number <= 0:
        raise EventStudyError(f"{field} must be positive")
    return number


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EventStudyError(f"{field} must be non-empty text")
    return value.strip()


def _trunc_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise EventStudyError("division denominator must be positive")
    if numerator < 0:
        return -((-numerator) // denominator)
    return numerator // denominator


@dataclass(frozen=True, slots=True)
class EventStudyPolicy:
    minimum_event_count: int
    allowed_pre_window_ns: tuple[int, ...]
    allowed_post_window_ns: tuple[int, ...]
    response_min_bps: int
    response_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    event_node_kinds: tuple[str, ...]
    target_node_kinds: tuple[str, ...]
    event_evidence_family: tuple[tuple[str, str], ...]
    edge_kind: str
    attribution_label: str
    event_response_is_causation: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "EventStudyPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise EventStudyError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "REGIME_CONDITIONAL_EVENT_STUDY":
            raise EventStudyError("unsupported P12-D policy")

        minimum = _positive_integer(raw.get("minimum_event_count"), field="minimum_event_count")
        if minimum < 3:
            raise EventStudyError("minimum_event_count must be >= 3")

        def windows(value: object, *, field: str) -> tuple[int, ...]:
            if not isinstance(value, list) or not value:
                raise EventStudyError(f"{field} must be non-empty list")
            normalized = tuple(sorted({_positive_integer(item, field=field) for item in cast(list[object], value)}))
            return normalized

        pre = windows(raw.get("allowed_pre_window_ns"), field="allowed_pre_window_ns")
        post = windows(raw.get("allowed_post_window_ns"), field="allowed_post_window_ns")
        response_min = _integer(raw.get("response_min_bps"), field="response_min_bps")
        response_max = _integer(raw.get("response_max_bps"), field="response_max_bps")
        if (response_min, response_max) != (-10000, 10000):
            raise EventStudyError("event response must use signed basis points")
        uncertainty_min = _integer(raw.get("uncertainty_min_bps"), field="uncertainty_min_bps")
        uncertainty_max = _integer(raw.get("uncertainty_max_bps"), field="uncertainty_max_bps")
        if (uncertainty_min, uncertainty_max) != (0, 10000):
            raise EventStudyError("uncertainty must use unsigned basis points")

        node_value = raw.get("event_node_kinds")
        target_value = raw.get("target_node_kinds")
        if not isinstance(node_value, list) or not isinstance(target_value, list):
            raise EventStudyError("event/target node kinds must be lists")
        event_kinds = tuple(str(item).strip().upper() for item in cast(list[object], node_value))
        target_kinds = tuple(str(item).strip().upper() for item in cast(list[object], target_value))
        if set(event_kinds) != {"MACRO_EVENT", "NEWS_EVENT", "CAPITAL_FLOW", "ROTATION_EPISODE"}:
            raise EventStudyError("unexpected event node kinds")
        if set(target_kinds) != {"ASSET", "MARKET"}:
            raise EventStudyError("unexpected target node kinds")

        family_value = raw.get("event_evidence_family")
        if not isinstance(family_value, Mapping):
            raise EventStudyError("event_evidence_family must be object")
        families = tuple(sorted(
            (str(key).strip().upper(), str(value).strip().upper())
            for key, value in cast(Mapping[object, object], family_value).items()
        ))
        expected_families = {
            ("CAPITAL_FLOW", "ORDER_FLOW"),
            ("MACRO_EVENT", "FUNDAMENTAL"),
            ("NEWS_EVENT", "NEWS"),
            ("ROTATION_EPISODE", "COMPOSITE"),
        }
        if set(families) != expected_families:
            raise EventStudyError("unexpected event evidence-family mapping")

        if raw.get("edge_kind") != "EVENT_CONTEXT" or raw.get("attribution_label") != "UNATTRIBUTED":
            raise EventStudyError("P12-D graph edge contract mismatch")
        if raw.get("event_response_is_causation") is not False:
            raise EventStudyError("event response cannot be treated as causation")
        if raw.get("canonical_tests_network_required") is not False:
            raise EventStudyError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise EventStudyError("P12-D cannot enable trading")

        return cls(
            minimum_event_count=minimum,
            allowed_pre_window_ns=pre,
            allowed_post_window_ns=post,
            response_min_bps=response_min,
            response_max_bps=response_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            event_node_kinds=event_kinds,
            target_node_kinds=target_kinds,
            event_evidence_family=families,
            edge_kind="EVENT_CONTEXT",
            attribution_label="UNATTRIBUTED",
            event_response_is_causation=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    def evidence_family_for(self, event_node_kind: str) -> str:
        try:
            return dict(self.event_evidence_family)[event_node_kind]
        except KeyError as exc:
            raise EventStudyError("event node kind has no evidence family") from exc


@dataclass(frozen=True, slots=True)
class EventStudyObservation:
    event_instance_id: str
    event_time_ns: int
    pre_time_ns: int
    post_time_ns: int
    pre_value: int
    post_value: int
    regime_label: str


@dataclass(frozen=True, slots=True)
class EventStudyResult:
    sample_count: int
    pre_window_ns: int
    post_window_ns: int
    regime_label: str
    mean_response_bps: int
    dispersion_bps: int
    sampling_uncertainty_bps: int
    responses_bps: tuple[int, ...]
    edge: GraphEdge


def compute_event_study(
    observations: Sequence[EventStudyObservation],
    *,
    pre_window_ns: int,
    post_window_ns: int,
    regime_label: str | None,
    event_node: GraphNode,
    target_node: GraphNode,
    provenance_sha256: Sequence[str],
    source_dataset_versions: Sequence[str],
    graph_policy: KnowledgeGraphPolicy,
    policy: EventStudyPolicy,
) -> EventStudyResult:
    if pre_window_ns not in policy.allowed_pre_window_ns:
        raise EventStudyError("pre_window_ns is not governed")
    if post_window_ns not in policy.allowed_post_window_ns:
        raise EventStudyError("post_window_ns is not governed")
    if event_node.node_kind not in policy.event_node_kinds:
        raise EventStudyError("event_node kind is not governed for event studies")
    if target_node.node_kind not in policy.target_node_kinds:
        raise EventStudyError("target_node kind is not governed for event studies")

    normalized_regime = regime_label.upper() if regime_label is not None else "UNSPECIFIED"
    if normalized_regime not in graph_policy.regime_labels:
        raise EventStudyError("unknown regime label")

    ordered = tuple(sorted(observations, key=lambda item: (item.event_time_ns, item.event_instance_id)))
    if not ordered:
        raise EventStudyError("event-study observations must be non-empty")
    ids = [item.event_instance_id for item in ordered]
    if any(not item.strip() for item in ids) or len(ids) != len(set(ids)):
        raise EventStudyError("event_instance_id must be unique non-empty")
    times = [item.event_time_ns for item in ordered]
    if len(times) != len(set(times)):
        raise EventStudyError("event_time_ns must be unique")

    qualifying: list[EventStudyObservation] = []
    for item in ordered:
        if min(item.pre_time_ns, item.event_time_ns, item.post_time_ns) < 0:
            raise EventStudyError("event-study timestamps must be non-negative")
        if item.pre_time_ns != item.event_time_ns - pre_window_ns:
            raise EventStudyError("pre_time_ns does not match governed window")
        if item.post_time_ns != item.event_time_ns + post_window_ns:
            raise EventStudyError("post_time_ns does not match governed window")
        if not item.pre_time_ns < item.event_time_ns < item.post_time_ns:
            raise EventStudyError("event window ordering is invalid")
        if regime_label is not None and item.regime_label.upper() != normalized_regime:
            continue
        if item.pre_value == 0:
            raise EventStudyError("pre_value cannot be zero")
        qualifying.append(item)

    if len(qualifying) < policy.minimum_event_count:
        raise EventStudyError("insufficient qualifying event count")

    responses: list[int] = []
    for item in qualifying:
        numerator = (item.post_value - item.pre_value) * 10000
        response = _trunc_div(numerator, abs(item.pre_value))
        if not policy.response_min_bps <= response <= policy.response_max_bps:
            raise EventStudyError("event response outside governed bounds")
        responses.append(response)

    total = sum(responses)
    mean_response = _trunc_div(total, len(responses))
    dispersion = _trunc_div(sum(abs(value - mean_response) for value in responses), len(responses))
    sampling = 10000 // max(1, isqrt(len(responses)))
    uncertainty = min(
        policy.uncertainty_max_bps,
        max(policy.uncertainty_min_bps, dispersion, sampling),
    )

    edge = GraphEdge.build(
        edge_kind=policy.edge_kind,
        source_node_id=event_node.node_id,
        target_node_id=target_node.node_id,
        valid_from_ns=min(item.pre_time_ns for item in qualifying),
        valid_to_ns=max(item.post_time_ns for item in qualifying) + 1,
        regime_label=normalized_regime,
        sample_count=len(qualifying),
        strength_bps=mean_response,
        uncertainty_bps=uncertainty,
        evidence_families=(policy.evidence_family_for(event_node.node_kind), "HISTORICAL"),
        provenance_sha256=provenance_sha256,
        source_dataset_versions=source_dataset_versions,
        attribution_label=policy.attribution_label,
        policy=graph_policy,
    )
    return EventStudyResult(
        sample_count=len(qualifying),
        pre_window_ns=pre_window_ns,
        post_window_ns=post_window_ns,
        regime_label=normalized_regime,
        mean_response_bps=mean_response,
        dispersion_bps=dispersion,
        sampling_uncertainty_bps=uncertainty,
        responses_bps=tuple(responses),
        edge=edge,
    )
