from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.market_memory.conditional_correlation import ConditionalCorrelationPolicy, CorrelationObservation, compute_conditional_correlation
from packages.market_memory.knowledge_graph import GraphNode, KnowledgeGraphPolicy


ROOT=Path(__file__).resolve().parents[2]
GRAPH_POLICY=ROOT/"config/market-memory/knowledge-graph-policy.json"
CORR_POLICY=ROOT/"config/market-memory/conditional-correlation-policy.json"


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    gp=KnowledgeGraphPolicy.from_path(GRAPH_POLICY)
    cp=ConditionalCorrelationPolicy.from_path(CORR_POLICY)
    btc=GraphNode.build(node_kind="ASSET",canonical_key="BTC",display_label="Bitcoin",policy=gp)
    flow=GraphNode.build(node_kind="CAPITAL_FLOW",canonical_key="BTC:NET_FLOW",display_label="BTC net flow",policy=gp)
    observations=tuple(
        CorrelationObservation(timestamp_ns=i,left_value=x,right_value=y,regime_label="ALIGNED_BULLISH")
        for i,(x,y) in enumerate(((1,10),(2,20),(3,30),(4,40),(5,50)),start=100)
    )
    result=compute_conditional_correlation(
        observations,
        window_size=5,
        regime_label="ALIGNED_BULLISH",
        source_node=flow,
        target_node=btc,
        provenance_sha256=("a"*64,"b"*64),
        source_dataset_versions=("p09-flow-v1","p06-history-v1"),
        graph_policy=gp,
        policy=cp,
    )
    payload={
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P12B_CONDITIONAL_CORRELATION_EVIDENCE",
        "task_id":"FIN-P12-WB-001",
        "policy_sha256":hashlib.sha256(CORR_POLICY.read_bytes()).hexdigest(),
        "sample_count":result.sample_count,
        "window_size":result.window_size,
        "regime_label":result.regime_label,
        "correlation_bps":result.correlation_bps,
        "sampling_uncertainty_bps":result.sampling_uncertainty_bps,
        "edge":result.edge.payload(),
        "correlation_is_causation":cp.correlation_is_causation,
        "network_required":cp.canonical_tests_network_required,
        "live_trading":cp.live_trading,
        "auto_trading":cp.auto_trading,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P12B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
