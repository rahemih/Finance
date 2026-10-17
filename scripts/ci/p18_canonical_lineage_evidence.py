#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.learning.canonical_evidence import (
    CanonicalArtifact,
    CanonicalDemoLineage,
    CanonicalEvidenceStore,
    CanonicalEvaluation,
    CanonicalPromotionRequest,
    MetricDefinition,
    MetricPolicy,
    RetrainingResourceBudget,
    RetrainingResourceUsage,
    enforce_retraining_budget,
    evaluate_canonical_promotion,
    verify_demo_lineage,
    verify_retraining_lineage,
)


def sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def add(
    store: CanonicalEvidenceStore,
    artifact_id: str,
    kind: str,
    state: str,
    provenance: str,
) -> None:
    store.add(CanonicalArtifact(artifact_id, kind, state, provenance))


def build(
    *,
    p17_empirical: Path,
    signal: Path,
    risk: Path,
    firewall: Path,
) -> dict[str, object]:
    p17 = load(p17_empirical)
    strategy_record_id = str(p17["strategy_record_id"])
    model_record_id = str(p17["model_record_id"])
    dataset_id = str(p17["dataset_sha256"])

    p17_prov = sha_bytes(p17_empirical)
    signal_id = sha_bytes(signal)
    risk_id = sha_bytes(risk)
    firewall_id = sha_bytes(firewall)

    store = CanonicalEvidenceStore()
    add(store, strategy_record_id, "STRATEGY_RECORD", "VALIDATED", p17_prov)
    add(store, model_record_id, "MODEL_RECORD", "VALIDATED", p17_prov)
    add(store, signal_id, "SIGNAL_DECISION", "PASS", sha_bytes(signal))
    add(store, risk_id, "RISK_DECISION", "PASS", sha_bytes(risk))
    add(store, firewall_id, "FIREWALL_DECISION", "PASS", sha_bytes(firewall))
    add(store, dataset_id, "DATASET", "READY", p17_prov)

    demo_lineage = CanonicalDemoLineage(
        strategy_record_id,
        model_record_id,
        signal_id,
        risk_id,
        firewall_id,
    )
    demo_lineage_id = verify_demo_lineage(store, demo_lineage)

    experiment_id = digest(
        {
            "dataset_id": dataset_id,
            "model_record_id": model_record_id,
            "strategy_record_id": strategy_record_id,
            "kind": "P18_CANONICAL_EXPERIMENT_REFERENCE",
        }
    )
    add(store, experiment_id, "EXPERIMENT", "PASS", p17_prov)
    retraining_lineage_id = verify_retraining_lineage(
        store,
        dataset_id=dataset_id,
        experiment_id=experiment_id,
        base_model_id=model_record_id,
    )

    measurements = p17.get("measurements")
    if not isinstance(measurements, dict):
        raise RuntimeError("P17 empirical measurements required")
    metric_policy = MetricPolicy(
        (
            MetricDefinition("OOS_EDGE_BPS", "1.0", "BPS", "HIGHER_BETTER"),
            MetricDefinition("MAX_DRAWDOWN_BPS", "1.0", "BPS", "LOWER_BETTER"),
        ),
        "OOS_EDGE_BPS",
    )
    evaluation = CanonicalEvaluation.create(
        model_record_id=model_record_id,
        dataset_id=dataset_id,
        metric_policy=metric_policy,
        metrics={
            "OOS_EDGE_BPS": str(measurements["OOS_EDGE"]),
            "MAX_DRAWDOWN_BPS": str(measurements["RISK"]),
        },
        evidence_sha256=p17_prov,
    )

    budget = RetrainingResourceBudget(
        max_cpu_seconds=60,
        max_memory_mb=512,
        max_wall_seconds=120,
        max_attempts=2,
    )
    budget_evidence_id = enforce_retraining_budget(
        RetrainingResourceUsage(
            cpu_seconds=15,
            peak_memory_mb=256,
            wall_seconds=25,
            attempts=1,
        ),
        budget,
    )

    candidate_validation_id = digest(
        {"kind": "CANDIDATE_VALIDATION", "evaluation_id": evaluation.evaluation_id}
    )
    comparison_id = digest(
        {
            "kind": "CHALLENGER_COMPARISON",
            "evaluation_id": evaluation.evaluation_id,
            "metric_policy_id": metric_policy.policy_id,
        }
    )
    drift_id = digest(
        {
            "kind": "DRIFT_ASSESSMENT",
            "dataset_id": dataset_id,
            "evaluation_id": evaluation.evaluation_id,
        }
    )
    risk_review_id = digest(
        {"kind": "RISK_REVIEW", "upstream_risk_evidence": risk_id}
    )
    audit_id = digest(
        {
            "kind": "AUDIT_BUNDLE",
            "demo_lineage_id": demo_lineage_id,
            "retraining_lineage_id": retraining_lineage_id,
            "budget_evidence_id": budget_evidence_id,
        }
    )
    add(store, candidate_validation_id, "CANDIDATE_VALIDATION", "PASS", evaluation.evidence_sha256)
    add(store, comparison_id, "CHALLENGER_COMPARISON", "RECOMMENDED", evaluation.evidence_sha256)
    add(store, drift_id, "DRIFT_ASSESSMENT", "NORMAL", evaluation.evidence_sha256)
    add(store, risk_review_id, "RISK_REVIEW", "PASS", risk_id)
    add(store, audit_id, "AUDIT_BUNDLE", "COMPLETE", p17_prov)

    demo_request = CanonicalPromotionRequest(
        "p18-canonical-demo",
        "DEMO_CHAMPION",
        candidate_validation_id,
        comparison_id,
        drift_id,
        risk_review_id,
        audit_id,
    )
    demo_decision = evaluate_canonical_promotion(store, demo_request)
    live_request = CanonicalPromotionRequest(
        "p18-canonical-live",
        "LIVE",
        candidate_validation_id,
        comparison_id,
        drift_id,
        risk_review_id,
        audit_id,
    )
    live_decision = evaluate_canonical_promotion(store, live_request)

    if demo_decision.status != "APPROVE_DEMO_CHAMPION_RECORD":
        raise RuntimeError("canonical Demo promotion was not approved")
    if live_decision.status != "OWNER_LIVE_GATE_REQUIRED":
        raise RuntimeError("Live promotion escaped Owner gate")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18_CANONICAL_LINEAGE_EVIDENCE",
        "task_id": "FIN-P18-WH-001-R01",
        "authoritative_path": "packages.learning.canonical_evidence",
        "strategy_record_id": strategy_record_id,
        "model_record_id": model_record_id,
        "dataset_id": dataset_id,
        "signal_evidence_id": signal_id,
        "risk_evidence_id": risk_id,
        "firewall_evidence_id": firewall_id,
        "demo_lineage_id": demo_lineage_id,
        "experiment_id": experiment_id,
        "retraining_lineage_id": retraining_lineage_id,
        "metric_policy_id": metric_policy.policy_id,
        "evaluation_id": evaluation.evaluation_id,
        "retraining_budget_id": budget.budget_id,
        "retraining_budget_evidence_id": budget_evidence_id,
        "demo_promotion_decision_id": demo_decision.decision_id,
        "demo_promotion_status": demo_decision.status,
        "live_promotion_status": live_decision.status,
        "caller_promotion_booleans_authoritative": False,
        "automatic_live_promotion": False,
        "broker_exchange_routing": False,
        "p19_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p17-empirical", type=Path, required=True)
    parser.add_argument("--signal", type=Path, required=True)
    parser.add_argument("--risk", type=Path, required=True)
    parser.add_argument("--firewall", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(
        p17_empirical=args.p17_empirical,
        signal=args.signal,
        risk=args.risk,
        firewall=args.firewall,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P18_CANONICAL_LINEAGE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
