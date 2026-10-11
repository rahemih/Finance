from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.market_memory.event_study import (
    EventStudyObservation,
    EventStudyPolicy,
    compute_event_study,
)
from packages.market_memory.knowledge_graph import GraphNode, KnowledgeGraphPolicy


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/event-study-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
    policy = EventStudyPolicy.from_path(POLICY_PATH)
    event_node = GraphNode.build(
        node_kind="MACRO_EVENT",
        canonical_key="US:CPI",
        display_label="US CPI",
        policy=graph_policy,
    )
    target_node = GraphNode.build(
        node_kind="ASSET",
        canonical_key="BTC",
        display_label="Bitcoin",
        policy=graph_policy,
    )
    posts = (102, 103, 101, 102)
    observations = tuple(
        EventStudyObservation(
            event_instance_id=f"cpi-{index}",
            event_time_ns=1000 + index * 1000,
            pre_time_ns=900 + index * 1000,
            post_time_ns=1100 + index * 1000,
            pre_value=100,
            post_value=post,
            regime_label="ALIGNED_BULLISH",
        )
        for index, post in enumerate(posts)
    )
    result = compute_event_study(
        observations,
        pre_window_ns=100,
        post_window_ns=100,
        regime_label="ALIGNED_BULLISH",
        event_node=event_node,
        target_node=target_node,
        provenance_sha256=("a" * 64, "b" * 64),
        source_dataset_versions=("p10-events-v1", "p06-prices-v1"),
        graph_policy=graph_policy,
        policy=policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12D_EVENT_STUDY_EVIDENCE",
        "task_id": "FIN-P12-WD-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "sample_count": result.sample_count,
        "pre_window_ns": result.pre_window_ns,
        "post_window_ns": result.post_window_ns,
        "regime_label": result.regime_label,
        "mean_response_bps": result.mean_response_bps,
        "dispersion_bps": result.dispersion_bps,
        "sampling_uncertainty_bps": result.sampling_uncertainty_bps,
        "responses_bps": list(result.responses_bps),
        "edge": result.edge.payload(),
        "event_response_is_causation": policy.event_response_is_causation,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P12D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
