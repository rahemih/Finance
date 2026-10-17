#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

STAGES = (
    "OBSERVE_ANALYZE",
    "DEMO_TRADE",
    "OUTCOME",
    "JOURNAL",
    "DATASET",
    "EXPERIMENT",
    "RETRAIN_VALIDATE",
    "CHALLENGER",
    "PROMOTION_GOVERNANCE",
)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def build(*, market: Path, p17_empirical: Path, canonical_lineage: Path) -> dict[str, object]:
    market_data = load(market)
    p17 = load(p17_empirical)
    lineage = load(canonical_lineage)

    if market_data.get("fixture_only") is not False:
        raise RuntimeError("reference runtime requires non-fixture public market data")
    if p17.get("empirical_reference") is not True:
        raise RuntimeError("reference runtime requires empirical P17 evidence")
    if lineage.get("authoritative_path") != "packages.learning.canonical_evidence":
        raise RuntimeError("reference runtime requires authoritative P18 lineage")

    market_sha = file_sha(market)
    p17_sha = file_sha(p17_empirical)
    lineage_sha = file_sha(canonical_lineage)
    inputs = {
        "market_sha256": market_sha,
        "p17_empirical_sha256": p17_sha,
        "canonical_lineage_sha256": lineage_sha,
    }
    source_bundle_sha = digest(inputs)

    material: dict[str, object] = {
        "OBSERVE_ANALYZE": {
            "market_sha256": market_sha,
            "p17_gate_certificate_id": p17["gate_certificate_id"],
            "signal_evidence_id": lineage["signal_evidence_id"],
            "risk_evidence_id": lineage["risk_evidence_id"],
            "firewall_evidence_id": lineage["firewall_evidence_id"],
        },
        "DEMO_TRADE": {
            "strategy_record_id": lineage["strategy_record_id"],
            "model_record_id": lineage["model_record_id"],
            "dataset_id": lineage["dataset_id"],
        },
        "OUTCOME": {
            "empirical_measurements": p17["measurements"],
            "dataset_id": lineage["dataset_id"],
        },
        "JOURNAL": {
            "demo_lineage_id": lineage["demo_lineage_id"],
        },
        "DATASET": {
            "dataset_id": lineage["dataset_id"],
            "retraining_lineage_id": lineage["retraining_lineage_id"],
        },
        "EXPERIMENT": {
            "experiment_id": lineage["experiment_id"],
            "metric_policy_id": lineage["metric_policy_id"],
        },
        "RETRAIN_VALIDATE": {
            "retraining_lineage_id": lineage["retraining_lineage_id"],
            "retraining_budget_id": lineage["retraining_budget_id"],
            "retraining_budget_evidence_id": lineage["retraining_budget_evidence_id"],
        },
        "CHALLENGER": {
            "evaluation_id": lineage["evaluation_id"],
            "metric_policy_id": lineage["metric_policy_id"],
        },
        "PROMOTION_GOVERNANCE": {
            "demo_promotion_decision_id": lineage["demo_promotion_decision_id"],
            "demo_promotion_status": lineage["demo_promotion_status"],
            "live_promotion_status": lineage["live_promotion_status"],
        },
    }

    stage_evidence: dict[str, str] = {}
    prior = source_bundle_sha
    for stage in STAGES:
        payload = {
            "schema_version": "1.0",
            "stage": stage,
            "source_bundle_sha256": source_bundle_sha,
            "prior_stage_evidence_sha256": prior,
            "material": material[stage],
        }
        evidence = digest(payload)
        stage_evidence[stage] = evidence
        prior = evidence

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18_REFERENCE_RUNTIME_STAGE_BUNDLE",
        "task_id": "FIN-P18-WI-001-R01",
        "fixture_only": False,
        "source_bundle_sha256": source_bundle_sha,
        "inputs": inputs,
        "stage_evidence": stage_evidence,
        "stage_count": len(stage_evidence),
        "automatic_live_promotion": False,
        "broker_exchange_routing": False,
        "p19_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--p17-empirical", type=Path, required=True)
    parser.add_argument("--canonical-lineage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(
        market=args.market,
        p17_empirical=args.p17_empirical,
        canonical_lineage=args.canonical_lineage,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P18_REFERENCE_STAGE_BUNDLE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
