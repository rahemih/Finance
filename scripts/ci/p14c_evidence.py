from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.evidence_contract import EvidenceBundle, EvidenceContractPolicy, SignalEvidence
from packages.signal_intelligence.probability_calibration import (
    CalibrationContext,
    CalibrationObservation,
    ProbabilityCalibrationPolicy,
    build_calibration_model,
    calibrate_probability,
)
from packages.signal_intelligence.weighted_fusion import WeightedFusionPolicy, fuse_evidence


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_POLICY_PATH = ROOT / "config/signal-intelligence/evidence-contract-policy.json"
FUSION_POLICY_PATH = ROOT / "config/signal-intelligence/weighted-evidence-fusion-policy.json"
CALIBRATION_POLICY_PATH = ROOT / "config/signal-intelligence/probability-calibration-policy.json"
OUTCOME_DEF = "d" * 64
DATASET = "e" * 64


def signal(phase: str, family: str, evidence_family: str, group: str, direction: int, strength: int, quality: int, index: int) -> SignalEvidence:
    return SignalEvidence(
        source_phase=phase,
        source_family=family,
        evidence_family=evidence_family,
        independence_group=group,
        subject_id="BTC-USD",
        timeframe="1h",
        regime_label="TRENDING",
        direction=direction,
        strength_bps=strength,
        quality_bps=quality,
        sample_count=120,
        event_time_ns=900,
        as_of_time_ns=1000,
        valid_until_ns=1200,
        source_record_id=f"p14c-source-{index}",
        provenance_sha256=f"{index + 1:x}" * 64,
        invalidation="source invalidated",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence_policy = EvidenceContractPolicy.from_path(EVIDENCE_POLICY_PATH)
    fusion_policy = WeightedFusionPolicy.from_path(FUSION_POLICY_PATH)
    calibration_policy = ProbabilityCalibrationPolicy.from_path(CALIBRATION_POLICY_PATH)

    bundle = EvidenceBundle.build(
        policy=evidence_policy,
        subject_id="BTC-USD",
        as_of_time_ns=1000,
        evidence=(
            signal("P08", "TECHNICAL", "TREND", "TECH_TREND", 1, 8000, 9000, 0),
            signal("P09", "ORDER_FLOW_LIQUIDITY", "CVD", "FLOW_DELTA", 1, 7000, 8000, 1),
            signal("P10", "FUNDAMENTAL_MACRO", "MACRO", "MACRO_GROWTH", -1, 5000, 8000, 2),
        ),
    )
    fused = fuse_evidence(bundle=bundle, policy=fusion_policy)

    ctx = CalibrationContext(
        subject_id="BTC-USD",
        strategy_id="trend-flow-v1",
        timeframe="1h",
        regime_label="TRENDING",
        session_label="EUROPE_US_OVERLAP",
        outcome_definition_sha256=OUTCOME_DEF,
    )
    observations = tuple(
        CalibrationObservation(
            context=ctx,
            signed_score_bps=3000 + index * 10,
            direction=1,
            success=index < 4,
            decision_as_of_ns=100 + index * 100,
            outcome_observed_ns=700 + index * 100,
            source_dataset_version_sha256=DATASET,
            provenance_sha256=f"{index + 4:x}" * 64,
        )
        for index in range(5)
    )
    model = build_calibration_model(
        policy=calibration_policy,
        context=ctx,
        training_cutoff_ns=1500,
        calibration_dataset_version_sha256=DATASET,
        observations=observations,
    )
    calibrated = calibrate_probability(model=model, fusion=fused, as_of_time_ns=2000)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14C_PROBABILITY_CALIBRATION",
        "task_id": "FIN-P14-WC-001",
        "calibration_policy_sha256": hashlib.sha256(CALIBRATION_POLICY_PATH.read_bytes()).hexdigest(),
        "fusion_id": fused.fusion_id,
        "fusion_signed_score_bps": fused.signed_score_bps,
        "model_id": model.model_id,
        "prediction": calibrated.payload() | {"prediction_id": calibrated.prediction_id},
        "probability_estimator": "RAW_EMPIRICAL_FREQUENCY",
        "synthetic_prior": None,
        "confidence_interval": None,
        "tp_probability": None,
        "stop_probability": None,
        "llm_probability_authority": False,
        "live_trading": calibration_policy.live_trading,
        "auto_trading": calibration_policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P14C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
