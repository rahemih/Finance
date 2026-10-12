from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.market_memory.historical_analog import (
    HistoricalAnalogPolicy,
    HistoricalFeatureState,
    find_historical_analogs,
)
from packages.market_memory.knowledge_graph import KnowledgeGraphPolicy


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/historical-analog-policy.json"


def state(state_id: str, as_of_ns: int, momentum_delta: int = 0) -> HistoricalFeatureState:
    return HistoricalFeatureState(
        state_id=state_id,
        as_of_ns=as_of_ns,
        regime_label="ALIGNED_BULLISH",
        features=(
            ("TREND", 2000),
            ("MOMENTUM", 1000 + momentum_delta),
            ("VOLATILITY", -500),
            ("LIQUIDITY", 500),
            ("ORDER_FLOW", 1500),
            ("MACRO", -1000),
            ("NEWS", 250),
            ("CAPITAL_FLOW", 1750),
        ),
        provenance_sha256=("a" * 64, "b" * 64),
        source_dataset_versions=("p12-memory-v1", "cira-memory-v1"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
    policy = HistoricalAnalogPolicy.from_path(POLICY_PATH)
    result = find_historical_analogs(
        state("query", 1000),
        (state("far", 100, 3000), state("near", 300), state("mid", 200, 1000)),
        top_k=3,
        graph_policy=graph_policy,
        policy=policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12E_HISTORICAL_ANALOG_EVIDENCE",
        "task_id": "FIN-P12-WE-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "query_state_id": result.query_state_id,
        "query_as_of_ns": result.query_as_of_ns,
        "regime_label": result.regime_label,
        "requested_top_k": result.requested_top_k,
        "matches": [
            {
                "state_id": item.state_id,
                "as_of_ns": item.as_of_ns,
                "shared_features": list(item.shared_features),
                "shared_feature_count": item.shared_feature_count,
                "coverage_bps": item.coverage_bps,
                "mean_distance_bps": item.mean_distance_bps,
                "similarity_bps": item.similarity_bps,
                "uncertainty_bps": item.uncertainty_bps,
                "provenance_sha256": list(item.provenance_sha256),
                "source_dataset_versions": list(item.source_dataset_versions),
            }
            for item in result.matches
        ],
        "future_outcome_consumed": policy.future_outcome_consumed,
        "similarity_is_probability": policy.similarity_is_probability,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P12E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
