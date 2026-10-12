from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from packages.market_memory.knowledge_graph import KnowledgeGraphPolicy
from packages.market_memory.seasonality import (
    SeasonalityObservation,
    SeasonalityPolicy,
    compute_seasonality,
)


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/seasonality-policy.json"


def ns(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()) * 1_000_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
    policy = SeasonalityPolicy.from_path(POLICY_PATH)
    observations = (
        SeasonalityObservation(ns("2020-01-10T12:00:00"), 100, "ALIGNED_BULLISH"),
        SeasonalityObservation(ns("2021-01-10T12:00:00"), 200, "ALIGNED_BULLISH"),
        SeasonalityObservation(ns("2022-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        SeasonalityObservation(ns("2023-01-10T12:00:00"), 200, "ALIGNED_BULLISH"),
    )
    result = compute_seasonality(
        observations,
        bucket_kind="MONTH_OF_YEAR_UTC",
        bucket_value=1,
        regime_label="ALIGNED_BULLISH",
        provenance_sha256=("a" * 64, "b" * 64),
        source_dataset_versions=("p12-seasonality-v1", "p06-history-v1"),
        graph_policy=graph_policy,
        policy=policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P12F_SEASONALITY_EVIDENCE",
        "task_id": "FIN-P12-WF-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "bucket_kind": result.bucket_kind,
        "bucket_value": result.bucket_value,
        "regime_label": result.regime_label,
        "sample_count": result.sample_count,
        "mean_return_bps": result.mean_return_bps,
        "dispersion_bps": result.dispersion_bps,
        "sampling_uncertainty_bps": result.sampling_uncertainty_bps,
        "valid_from_ns": result.valid_from_ns,
        "valid_to_ns": result.valid_to_ns,
        "provenance_sha256": list(result.provenance_sha256),
        "source_dataset_versions": list(result.source_dataset_versions),
        "session_calendar_in_scope": policy.session_calendar_in_scope,
        "seasonality_is_causation": policy.seasonality_is_causation,
        "seasonality_is_probability": policy.seasonality_is_probability,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P12F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
