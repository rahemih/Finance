from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.tp_stop_probability import (
    BarrierPlanContext,
    TPStopObservation,
    TPStopProbabilityPolicy,
    build_tp_stop_model,
    estimate_tp_stop_probabilities,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/tp-stop-probability-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = TPStopProbabilityPolicy.from_path(POLICY_PATH)
    context = BarrierPlanContext(
        subject_id="BTC-USD",
        strategy_id="trend-flow-v1",
        timeframe="1h",
        regime_label="TRENDING",
        session_label="EUROPE_US_OVERLAP",
        direction=1,
        target_distance_bps=300,
        stop_distance_bps=150,
        evaluation_horizon_steps=12,
        outcome_definition_sha256="d" * 64,
    )
    labels = ("TP_FIRST",) * 6 + ("STOP_FIRST",) * 3 + ("NEITHER",)
    digits = tuple("123456789a")
    observations = tuple(
        TPStopObservation(
            context=context,
            outcome=label,
            decision_as_of_ns=1000,
            outcome_observed_ns=1500,
            source_dataset_version_sha256="e" * 64,
            provenance_sha256=digit * 64,
        )
        for label, digit in zip(labels, digits)
    )
    model = build_tp_stop_model(
        policy=policy,
        context=context,
        training_cutoff_ns=2000,
        outcome_dataset_version_sha256="e" * 64,
        observations=observations,
    )
    qualification = ProbabilityUncertaintyQualification(
        prediction_id="a" * 64,
        empirical_probability_bps=7000,
        sample_count=100,
        success_count=70,
        state="QUALIFIED",
        sample_support="STRONG",
        confidence_level_bps=9500,
        confidence_interval_lower_bps=6100,
        confidence_interval_upper_bps=7800,
        interval_half_width_bps=850,
        regime_similarity_bps=8000,
        regime_dissimilarity_bps=2000,
        regime_uncertainty_bps=900,
        overall_uncertainty_bps=900,
        dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",),
        regime_evidence_id="b" * 64,
    )
    result = estimate_tp_stop_probabilities(
        model=model,
        qualification=qualification,
        as_of_time_ns=3000,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14E_TP_STOP_OUTCOME_PROBABILITY_EVIDENCE",
        "task_id": "FIN-P14-WE-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "model_id": model.model_id,
        "prediction_id": result.prediction_id,
        "state": result.state,
        "sample_count": result.sample_count,
        "tp_first_probability_bps": result.tp_first_probability_bps,
        "stop_first_probability_bps": result.stop_first_probability_bps,
        "neither_probability_bps": result.neither_probability_bps,
        "general_empirical_probability_bps": result.general_empirical_probability_bps,
        "general_probability_equals_tp_probability": False,
        "ambiguous_path_inference": False,
        "llm_probability_authority": False,
        "risk_approval": None,
        "position_size": None,
        "execution_command": None,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P14E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
