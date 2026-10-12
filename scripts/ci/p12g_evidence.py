from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.market_memory.attribution import AttributionGuardrailPolicy, assess_attribution
from packages.market_memory.knowledge_graph import GraphEdge, GraphNode, KnowledgeGraphPolicy


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/attribution-guardrail-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
    policy = AttributionGuardrailPolicy.from_path(POLICY_PATH)
    event = GraphNode.build(
        node_kind="MACRO_EVENT",
        canonical_key="US:CPI",
        display_label="US CPI",
        policy=graph_policy,
    )
    asset = GraphNode.build(
        node_kind="ASSET",
        canonical_key="BTC",
        display_label="Bitcoin",
        policy=graph_policy,
    )

    def edge(kind: str, family: str, suffix: str) -> GraphEdge:
        return GraphEdge.build(
            edge_kind=kind,
            source_node_id=event.node_id,
            target_node_id=asset.node_id,
            valid_from_ns=100,
            valid_to_ns=200 + len(suffix),
            regime_label="ALIGNED_BULLISH",
            sample_count=3,
            strength_bps=2000,
            uncertainty_bps=2500,
            evidence_families=(family,),
            provenance_sha256=("a" * 64,),
            source_dataset_versions=(f"p12-memory{suffix}",),
            attribution_label="UNATTRIBUTED",
            policy=graph_policy,
        )

    edges = (
        edge("EVENT_CONTEXT", "FUNDAMENTAL", "-fundamental"),
        edge("CONTEXT_LINK", "TECHNICAL", "-technical"),
        edge("OBSERVED_ASSOCIATION", "ORDER_FLOW", "-order-flow"),
    )
    result = assess_attribution(
        source_node=event,
        target_node=asset,
        edges=edges,
        graph_policy=graph_policy,
        policy=policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12G_ATTRIBUTION_GUARDRAIL_EVIDENCE",
        "task_id": "FIN-P12-WG-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "assessment": {
            "source_node_id": result.source_node_id,
            "target_node_id": result.target_node_id,
            "regime_label": result.regime_label,
            "narrative_label": result.narrative_label,
            "evidence_edge_ids": list(result.evidence_edge_ids),
            "independent_evidence_families": list(result.independent_evidence_families),
            "independent_evidence_family_count": result.independent_evidence_family_count,
            "total_sample_count": result.total_sample_count,
            "mean_abs_strength_bps": result.mean_abs_strength_bps,
            "maximum_uncertainty_bps": result.maximum_uncertainty_bps,
            "direction_consistent": result.direction_consistent,
            "driver_context_present": result.driver_context_present,
            "causal_proof": result.causal_proof,
            "probability": result.probability,
            "reason_codes": list(result.reason_codes),
        },
        "canonical_edges_remain_unattributed": all(edge.attribution_label == "UNATTRIBUTED" for edge in edges),
        "temporal_precedence_alone_is_driver": policy.temporal_precedence_alone_is_driver,
        "correlation_alone_is_driver": policy.correlation_alone_is_driver,
        "likely_driver_is_causal_proof": policy.likely_driver_is_causal_proof,
        "narrative_labels_are_probability": policy.narrative_labels_are_probability,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P12G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
