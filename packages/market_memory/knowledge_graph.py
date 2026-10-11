from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence, cast


class KnowledgeGraphError(ValueError):
    """P12-A knowledge-graph policy or evidence violates governed invariants."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise KnowledgeGraphError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeGraphError(f"{field} must be non-empty text")
    return value.strip()


def _bool(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise KnowledgeGraphError(f"{field} must be boolean")
    return value


def _int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise KnowledgeGraphError(f"{field} must be an integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    number = _int(value, field=field)
    if number <= 0:
        raise KnowledgeGraphError(f"{field} must be positive")
    return number


def _non_negative_int(value: object, *, field: str) -> int:
    number = _int(value, field=field)
    if number < 0:
        raise KnowledgeGraphError(f"{field} must be non-negative")
    return number


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise KnowledgeGraphError(f"{field} must be a non-empty list")
    items = tuple(_text(item, field=field).upper() for item in cast(list[object], value))
    if len(items) != len(set(items)):
        raise KnowledgeGraphError(f"{field} must contain unique values")
    return items


def _sha256(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise KnowledgeGraphError(f"{field} must be lowercase SHA-256")
    return text


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class KnowledgeGraphPolicy:
    node_kinds: tuple[str, ...]
    edge_kinds: tuple[str, ...]
    regime_labels: tuple[str, ...]
    evidence_families: tuple[str, ...]
    strength_min_bps: int
    strength_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    minimum_sample_count: int
    attribution_labels_allowed: tuple[str, ...]
    causality_claims_allowed: bool
    require_provenance: bool
    require_source_dataset_versions: bool
    self_edges_allowed: bool
    canonical_tests_network_required: bool
    production_graph_vendor: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "KnowledgeGraphPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise KnowledgeGraphError("unsupported knowledge-graph schema_version")
        if raw.get("mode") != "REGIME_AWARE_MARKET_MEMORY_ONTOLOGY":
            raise KnowledgeGraphError("unsupported knowledge-graph mode")

        node_kinds = _string_tuple(raw.get("node_kinds"), field="node_kinds")
        required_nodes = {
            "ASSET",
            "MARKET",
            "MACRO_EVENT",
            "NEWS_EVENT",
            "REGIME",
            "CAPITAL_FLOW",
            "ROTATION_EPISODE",
        }
        if set(node_kinds) != required_nodes:
            raise KnowledgeGraphError("node ontology does not match governed P12-A baseline")

        edge_kinds = _string_tuple(raw.get("edge_kinds"), field="edge_kinds")
        required_edges = {
            "OBSERVED_ASSOCIATION",
            "CONTEXT_LINK",
            "EVENT_CONTEXT",
            "REGIME_CONTEXT",
            "CAPITAL_FLOW_LINK",
            "ROTATION_EPISODE_LINK",
        }
        if set(edge_kinds) != required_edges:
            raise KnowledgeGraphError("edge ontology does not match governed P12-A baseline")

        regime_labels = _string_tuple(raw.get("regime_labels"), field="regime_labels")
        required_regimes = {
            "ALIGNED_BULLISH",
            "ALIGNED_BEARISH",
            "NEUTRAL",
            "CONFLICT",
            "TRANSITION",
            "UNSPECIFIED",
        }
        if set(regime_labels) != required_regimes:
            raise KnowledgeGraphError("regime labels must preserve canonical P08-G states")

        evidence_families = _string_tuple(
            raw.get("evidence_families"),
            field="evidence_families",
        )
        if set(evidence_families) != {
            "TECHNICAL",
            "ORDER_FLOW",
            "FUNDAMENTAL",
            "NEWS",
            "HISTORICAL",
            "COMPOSITE",
        }:
            raise KnowledgeGraphError("unexpected evidence-family ontology")

        strength_min = _int(raw.get("strength_min_bps"), field="strength_min_bps")
        strength_max = _int(raw.get("strength_max_bps"), field="strength_max_bps")
        if strength_min != -10000 or strength_max != 10000:
            raise KnowledgeGraphError("strength must use signed basis-point scale")

        uncertainty_min = _non_negative_int(
            raw.get("uncertainty_min_bps"),
            field="uncertainty_min_bps",
        )
        uncertainty_max = _non_negative_int(
            raw.get("uncertainty_max_bps"),
            field="uncertainty_max_bps",
        )
        if uncertainty_min != 0 or uncertainty_max != 10000:
            raise KnowledgeGraphError("uncertainty must use unsigned basis-point scale")

        attribution = _string_tuple(
            raw.get("attribution_labels_allowed"),
            field="attribution_labels_allowed",
        )
        if attribution != ("UNATTRIBUTED",):
            raise KnowledgeGraphError("P12-A may only emit UNATTRIBUTED relationships")
        causality = _bool(
            raw.get("causality_claims_allowed"),
            field="causality_claims_allowed",
        )
        if causality:
            raise KnowledgeGraphError("P12-A forbids causality claims")

        require_provenance = _bool(
            raw.get("require_provenance"),
            field="require_provenance",
        )
        require_versions = _bool(
            raw.get("require_source_dataset_versions"),
            field="require_source_dataset_versions",
        )
        if not require_provenance or not require_versions:
            raise KnowledgeGraphError("P12-A requires provenance and dataset versions")

        if _bool(raw.get("canonical_tests_network_required"), field="canonical_tests_network_required"):
            raise KnowledgeGraphError("canonical P12-A tests must remain offline")
        if _text(raw.get("production_graph_vendor"), field="production_graph_vendor") != "NOT_SELECTED":
            raise KnowledgeGraphError("P12-A cannot select a production graph vendor")
        if _text(raw.get("live_trading"), field="live_trading") != "DISABLED":
            raise KnowledgeGraphError("P12-A cannot enable live trading")
        if _text(raw.get("auto_trading"), field="auto_trading") != "DISABLED":
            raise KnowledgeGraphError("P12-A cannot enable auto trading")

        return cls(
            node_kinds=node_kinds,
            edge_kinds=edge_kinds,
            regime_labels=regime_labels,
            evidence_families=evidence_families,
            strength_min_bps=strength_min,
            strength_max_bps=strength_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            minimum_sample_count=_positive_int(
                raw.get("minimum_sample_count"),
                field="minimum_sample_count",
            ),
            attribution_labels_allowed=attribution,
            causality_claims_allowed=False,
            require_provenance=True,
            require_source_dataset_versions=True,
            self_edges_allowed=_bool(raw.get("self_edges_allowed"), field="self_edges_allowed"),
            canonical_tests_network_required=False,
            production_graph_vendor="NOT_SELECTED",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    node_kind: str
    canonical_key: str
    display_label: str

    @classmethod
    def build(
        cls,
        *,
        node_kind: str,
        canonical_key: str,
        display_label: str,
        policy: KnowledgeGraphPolicy,
    ) -> "GraphNode":
        kind = _text(node_kind, field="node_kind").upper()
        if kind not in policy.node_kinds:
            raise KnowledgeGraphError("unknown node_kind")
        key = _text(canonical_key, field="canonical_key")
        label = _text(display_label, field="display_label")
        identity = hashlib.sha256(
            _canonical_bytes(
                {
                    "schema_version": "1.0",
                    "node_kind": kind,
                    "canonical_key": key,
                }
            )
        ).hexdigest()
        return cls(
            node_id=identity,
            node_kind=kind,
            canonical_key=key,
            display_label=label,
        )

    def payload(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "node_kind": self.node_kind,
            "canonical_key": self.canonical_key,
            "display_label": self.display_label,
        }


@dataclass(frozen=True, slots=True)
class GraphEdge:
    edge_id: str
    edge_kind: str
    source_node_id: str
    target_node_id: str
    valid_from_ns: int
    valid_to_ns: int
    regime_label: str
    sample_count: int
    strength_bps: int
    uncertainty_bps: int
    evidence_families: tuple[str, ...]
    provenance_sha256: tuple[str, ...]
    source_dataset_versions: tuple[str, ...]
    attribution_label: str

    @classmethod
    def build(
        cls,
        *,
        edge_kind: str,
        source_node_id: str,
        target_node_id: str,
        valid_from_ns: int,
        valid_to_ns: int,
        regime_label: str,
        sample_count: int,
        strength_bps: int,
        uncertainty_bps: int,
        evidence_families: Sequence[str],
        provenance_sha256: Sequence[str],
        source_dataset_versions: Sequence[str],
        attribution_label: str,
        policy: KnowledgeGraphPolicy,
    ) -> "GraphEdge":
        kind = _text(edge_kind, field="edge_kind").upper()
        if kind not in policy.edge_kinds:
            raise KnowledgeGraphError("unknown edge_kind")
        source = _sha256(source_node_id, field="source_node_id")
        target = _sha256(target_node_id, field="target_node_id")
        if source == target and not policy.self_edges_allowed:
            raise KnowledgeGraphError("self edges are forbidden")

        start = _non_negative_int(valid_from_ns, field="valid_from_ns")
        end = _positive_int(valid_to_ns, field="valid_to_ns")
        if end <= start:
            raise KnowledgeGraphError("valid_to_ns must be greater than valid_from_ns")

        regime = _text(regime_label, field="regime_label").upper()
        if regime not in policy.regime_labels:
            raise KnowledgeGraphError("unknown regime_label")

        samples = _positive_int(sample_count, field="sample_count")
        if samples < policy.minimum_sample_count:
            raise KnowledgeGraphError("sample_count below governed minimum")

        strength = _int(strength_bps, field="strength_bps")
        if not policy.strength_min_bps <= strength <= policy.strength_max_bps:
            raise KnowledgeGraphError("strength_bps outside governed bounds")
        uncertainty = _non_negative_int(uncertainty_bps, field="uncertainty_bps")
        if not policy.uncertainty_min_bps <= uncertainty <= policy.uncertainty_max_bps:
            raise KnowledgeGraphError("uncertainty_bps outside governed bounds")

        families = tuple(sorted({_text(value, field="evidence_family").upper() for value in evidence_families}))
        if not families:
            raise KnowledgeGraphError("evidence_families must be non-empty")
        unknown_families = set(families) - set(policy.evidence_families)
        if unknown_families:
            raise KnowledgeGraphError("unknown evidence family")

        provenance = tuple(sorted({_sha256(value, field="provenance_sha256") for value in provenance_sha256}))
        if policy.require_provenance and not provenance:
            raise KnowledgeGraphError("provenance is required")

        versions = tuple(
            sorted({_text(value, field="source_dataset_version") for value in source_dataset_versions})
        )
        if policy.require_source_dataset_versions and not versions:
            raise KnowledgeGraphError("source dataset versions are required")

        attribution = _text(attribution_label, field="attribution_label").upper()
        if attribution not in policy.attribution_labels_allowed:
            raise KnowledgeGraphError("P12-A attribution label is not allowed")

        body: dict[str, object] = {
            "schema_version": "1.0",
            "edge_kind": kind,
            "source_node_id": source,
            "target_node_id": target,
            "valid_from_ns": start,
            "valid_to_ns": end,
            "regime_label": regime,
            "sample_count": samples,
            "strength_bps": strength,
            "uncertainty_bps": uncertainty,
            "evidence_families": list(families),
            "provenance_sha256": list(provenance),
            "source_dataset_versions": list(versions),
            "attribution_label": attribution,
        }
        return cls(
            edge_id=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
            edge_kind=kind,
            source_node_id=source,
            target_node_id=target,
            valid_from_ns=start,
            valid_to_ns=end,
            regime_label=regime,
            sample_count=samples,
            strength_bps=strength,
            uncertainty_bps=uncertainty,
            evidence_families=families,
            provenance_sha256=provenance,
            source_dataset_versions=versions,
            attribution_label=attribution,
        )

    def payload(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "edge_kind": self.edge_kind,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "valid_from_ns": self.valid_from_ns,
            "valid_to_ns": self.valid_to_ns,
            "regime_label": self.regime_label,
            "sample_count": self.sample_count,
            "strength_bps": self.strength_bps,
            "uncertainty_bps": self.uncertainty_bps,
            "evidence_families": list(self.evidence_families),
            "provenance_sha256": list(self.provenance_sha256),
            "source_dataset_versions": list(self.source_dataset_versions),
            "attribution_label": self.attribution_label,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeGraphSnapshot:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    snapshot_id: str

    @classmethod
    def build(
        cls,
        *,
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
        policy: KnowledgeGraphPolicy,
    ) -> "KnowledgeGraphSnapshot":
        ordered_nodes = tuple(sorted(nodes, key=lambda item: item.node_id))
        if not ordered_nodes:
            raise KnowledgeGraphError("knowledge graph requires at least one node")
        node_ids = [node.node_id for node in ordered_nodes]
        if len(node_ids) != len(set(node_ids)):
            raise KnowledgeGraphError("duplicate node_id")
        canonical_pairs = [(node.node_kind, node.canonical_key) for node in ordered_nodes]
        if len(canonical_pairs) != len(set(canonical_pairs)):
            raise KnowledgeGraphError("duplicate canonical node")

        known_nodes = set(node_ids)
        ordered_edges = tuple(sorted(edges, key=lambda item: item.edge_id))
        edge_ids = [edge.edge_id for edge in ordered_edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise KnowledgeGraphError("duplicate edge_id")
        for edge in ordered_edges:
            if edge.edge_kind not in policy.edge_kinds:
                raise KnowledgeGraphError("snapshot contains unknown edge_kind")
            if edge.source_node_id not in known_nodes or edge.target_node_id not in known_nodes:
                raise KnowledgeGraphError("edge references unknown node")
            if edge.attribution_label != "UNATTRIBUTED":
                raise KnowledgeGraphError("P12-A snapshot contains causality attribution")

        payload: dict[str, object] = {
            "schema_version": "1.0",
            "nodes": [node.payload() for node in ordered_nodes],
            "edges": [edge.payload() for edge in ordered_edges],
        }
        return cls(
            nodes=ordered_nodes,
            edges=ordered_edges,
            snapshot_id=hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "snapshot_id": self.snapshot_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [node.payload() for node in self.nodes],
            "edges": [edge.payload() for edge in self.edges],
        }
