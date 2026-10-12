from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.historical_data.replay_snapshot import ReplayDatasetRef, ReplaySnapshot, ReplaySnapshotPolicy
from packages.market_memory.knowledge_graph import GraphEdge, GraphNode, KnowledgeGraphPolicy, KnowledgeGraphSnapshot
from packages.market_memory.versioning_replay import (
    MarketMemoryReplayPolicy,
    assert_market_memory_replay_equivalent,
    build_market_memory_replay_record,
    build_market_memory_version_bundle,
)


ROOT = Path(__file__).resolve().parents[2]
REPLAY_POLICY_PATH = ROOT / "config/historical-data/replay-snapshot-policy.json"
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/versioning-replay-policy.json"

P12_POLICY_PATHS = {
    "P12_A_KNOWLEDGE_GRAPH": ROOT / "config/market-memory/knowledge-graph-policy.json",
    "P12_B_CONDITIONAL_CORRELATION": ROOT / "config/market-memory/conditional-correlation-policy.json",
    "P12_C_LEAD_LAG": ROOT / "config/market-memory/lead-lag-policy.json",
    "P12_D_EVENT_STUDY": ROOT / "config/market-memory/event-study-policy.json",
    "P12_E_HISTORICAL_ANALOG": ROOT / "config/market-memory/historical-analog-policy.json",
    "P12_F_SEASONALITY": ROOT / "config/market-memory/seasonality-policy.json",
    "P12_G_ATTRIBUTION_GUARDRAIL": ROOT / "config/market-memory/attribution-guardrail-policy.json",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    replay_policy = ReplaySnapshotPolicy.from_path(REPLAY_POLICY_PATH)
    graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
    policy = MarketMemoryReplayPolicy.from_path(POLICY_PATH)
    replay = ReplaySnapshot.build(
        replay_start_ns=0,
        replay_end_ns=1000,
        snapshot_cutoff_ns=900,
        clock_mode="EVENT_TIME",
        scope_ids=("BTC",),
        dataset_refs=(
            ReplayDatasetRef(
                dataset_name="market-memory",
                dataset_version="a" * 64,
                schema_version="1.0",
                window_start_ns=0,
                window_end_ns=1000,
                membership_root_sha256="b" * 64,
                rights_class="INTERNAL",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("p12-quality-v1",),
        config_sha256="c" * 64,
        code_artifact_sha256="d" * 64,
        rights_class="INTERNAL",
        policy=replay_policy,
    )
    source = GraphNode.build(
        node_kind="MARKET",
        canonical_key="DXY",
        display_label="US Dollar Index",
        policy=graph_policy,
    )
    target = GraphNode.build(
        node_kind="ASSET",
        canonical_key="BTC",
        display_label="Bitcoin",
        policy=graph_policy,
    )
    edge = GraphEdge.build(
        edge_kind="OBSERVED_ASSOCIATION",
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        valid_from_ns=100,
        valid_to_ns=401,
        regime_label="ALIGNED_BULLISH",
        sample_count=30,
        strength_bps=-2500,
        uncertainty_bps=2200,
        evidence_families=("HISTORICAL",),
        provenance_sha256=("e" * 64,),
        source_dataset_versions=("memory-v1",),
        attribution_label="UNATTRIBUTED",
        policy=graph_policy,
    )
    graph = KnowledgeGraphSnapshot.build(
        nodes=(target, source),
        edges=(edge,),
        policy=graph_policy,
    )
    policy_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in P12_POLICY_PATHS.items()
    }
    bundle = build_market_memory_version_bundle(
        as_of_ns=500,
        replay_snapshot=replay,
        graph_snapshot=graph,
        component_policy_sha256=policy_hashes,
        policy=policy,
    )
    outputs = {
        "P12_B_CONDITIONAL_CORRELATION": {"correlation_bps": -2500},
        "P12_C_LEAD_LAG": {"lead_state": "LEFT_LEADS_RIGHT"},
        "P12_D_EVENT_STUDY": {"mean_response_bps": 120},
        "P12_E_HISTORICAL_ANALOG": {"similarity_bps": 8500},
        "P12_F_SEASONALITY": {"mean_return_bps": 80},
        "P12_G_ATTRIBUTION_GUARDRAIL": {"narrative_label": "CONTEXT_ONLY"},
    }
    first = build_market_memory_replay_record(
        bundle=bundle,
        component_outputs=outputs,
        policy=policy,
    )
    second = build_market_memory_replay_record(
        bundle=bundle,
        component_outputs=dict(reversed(tuple(outputs.items()))),
        policy=policy,
    )
    assert_market_memory_replay_equivalent(first, second)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12H_VERSIONING_REPLAY_EVIDENCE",
        "task_id": "FIN-P12-WH-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "version_bundle": bundle.payload(),
        "replay_record": first.payload(),
        "deterministic_replay_equivalent": True,
        "anti_lookahead_owner": policy.anti_lookahead_owner,
        "end_to_end_decision_replay_owner": policy.end_to_end_decision_replay_owner,
        "production_memory_version_store_vendor": policy.production_memory_version_store_vendor,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P12H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
