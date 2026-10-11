from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.market_memory.knowledge_graph import GraphNode, KnowledgeGraphPolicy
from packages.market_memory.lead_lag import LeadLagObservation, LeadLagPolicy, compute_lead_lag


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/lead-lag-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
    policy = LeadLagPolicy.from_path(POLICY_PATH)
    left = GraphNode.build(
        node_kind="ASSET",
        canonical_key="BTC",
        display_label="Bitcoin",
        policy=graph_policy,
    )
    right = GraphNode.build(
        node_kind="MARKET",
        canonical_key="DXY",
        display_label="US Dollar Index",
        policy=graph_policy,
    )
    values = (3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9)
    right_values = (0,) + values[:-1]
    observations = tuple(
        LeadLagObservation(
            timestamp_ns=index * 100,
            left_value=left_value,
            right_value=right_value,
            regime_label="ALIGNED_BULLISH",
        )
        for index, (left_value, right_value) in enumerate(zip(values, right_values, strict=True))
    )
    result = compute_lead_lag(
        observations,
        sampling_interval_ns=100,
        regime_label="ALIGNED_BULLISH",
        left_node=left,
        right_node=right,
        provenance_sha256=("a" * 64,),
        source_dataset_versions=("history-v1",),
        graph_policy=graph_policy,
        policy=policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12C_LEAD_LAG_EVIDENCE",
        "task_id": "FIN-P12-WC-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "lead_state": result.lead_state,
        "selected_lag_steps": result.selected_lag_steps,
        "selected_lag_ns": result.selected_lag_ns,
        "regime_label": result.regime_label,
        "candidates": [
            {
                "lag_steps": item.lag_steps,
                "lag_ns": item.lag_ns,
                "sample_count": item.sample_count,
                "correlation_bps": item.correlation_bps,
                "sampling_uncertainty_bps": item.sampling_uncertainty_bps,
                "valid_from_ns": item.valid_from_ns,
                "valid_to_ns": item.valid_to_ns,
            }
            for item in result.candidates
        ],
        "edge": None if result.edge is None else result.edge.payload(),
        "temporal_precedence_is_causation": policy.temporal_precedence_is_causation,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P12C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
