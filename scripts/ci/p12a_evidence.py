from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.market_memory.knowledge_graph import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphPolicy,
    KnowledgeGraphSnapshot,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = KnowledgeGraphPolicy.from_path(POLICY_PATH)
    btc = GraphNode.build(
        node_kind="ASSET",
        canonical_key="BTC",
        display_label="Bitcoin",
        policy=policy,
    )
    dxy = GraphNode.build(
        node_kind="MARKET",
        canonical_key="DXY",
        display_label="US Dollar Index",
        policy=policy,
    )
    flow = GraphNode.build(
        node_kind="CAPITAL_FLOW",
        canonical_key="BTC:INFLOW",
        display_label="BTC observed inflow",
        policy=policy,
    )
    rotation = GraphNode.build(
        node_kind="ROTATION_EPISODE",
        canonical_key="BTC_TO_GOLD:EPISODE_001",
        display_label="BTC to Gold rotation episode",
        policy=policy,
    )

    association = GraphEdge.build(
        edge_kind="OBSERVED_ASSOCIATION",
        source_node_id=btc.node_id,
        target_node_id=dxy.node_id,
        valid_from_ns=1_000,
        valid_to_ns=2_000,
        regime_label="ALIGNED_BULLISH",
        sample_count=64,
        strength_bps=-3100,
        uncertainty_bps=2100,
        evidence_families=("TECHNICAL", "HISTORICAL"),
        provenance_sha256=("a" * 64, "b" * 64),
        source_dataset_versions=("p08-regime-v1", "p06-history-v1"),
        attribution_label="UNATTRIBUTED",
        policy=policy,
    )
    capital_flow = GraphEdge.build(
        edge_kind="CAPITAL_FLOW_LINK",
        source_node_id=flow.node_id,
        target_node_id=btc.node_id,
        valid_from_ns=1_000,
        valid_to_ns=2_000,
        regime_label="ALIGNED_BULLISH",
        sample_count=32,
        strength_bps=4200,
        uncertainty_bps=2400,
        evidence_families=("ORDER_FLOW", "FUNDAMENTAL"),
        provenance_sha256=("c" * 64, "d" * 64),
        source_dataset_versions=("p09-flow-v1", "p10-fundamental-v1"),
        attribution_label="UNATTRIBUTED",
        policy=policy,
    )
    rotation_link = GraphEdge.build(
        edge_kind="ROTATION_EPISODE_LINK",
        source_node_id=rotation.node_id,
        target_node_id=btc.node_id,
        valid_from_ns=1_000,
        valid_to_ns=2_000,
        regime_label="TRANSITION",
        sample_count=12,
        strength_bps=-1800,
        uncertainty_bps=3600,
        evidence_families=("COMPOSITE",),
        provenance_sha256=("e" * 64,),
        source_dataset_versions=("cira-memory-v1",),
        attribution_label="UNATTRIBUTED",
        policy=policy,
    )
    graph = KnowledgeGraphSnapshot.build(
        nodes=(btc, dxy, flow, rotation),
        edges=(association, capital_flow, rotation_link),
        policy=policy,
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12A_KNOWLEDGE_GRAPH_SCHEMA_EVIDENCE",
        "task_id": "FIN-P12-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "snapshot": graph.payload(),
        "capital_flow_node_supported": "CAPITAL_FLOW" in policy.node_kinds,
        "rotation_episode_node_supported": "ROTATION_EPISODE" in policy.node_kinds,
        "causality_claims_allowed": policy.causality_claims_allowed,
        "network_required": policy.canonical_tests_network_required,
        "production_graph_vendor": policy.production_graph_vendor,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P12A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
