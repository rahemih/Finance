from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.probability_calibration import CalibratedProbability
from packages.signal_intelligence.probability_uncertainty import (
    ProbabilityUncertaintyPolicy,
    RegimeSimilarityEvidence,
    qualify_probability_uncertainty,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/probability-uncertainty-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = ProbabilityUncertaintyPolicy.from_path(POLICY_PATH)
    calibrated = CalibratedProbability(
        model_id="a" * 64,
        fusion_id="b" * 64,
        as_of_time_ns=3000,
        state="CALIBRATED",
        probability_bps=6200,
        sample_count=100,
        success_count=62,
        lower_abs_score_bps=2500,
        upper_abs_score_exclusive_bps=5000,
        outcome_definition_sha256="c" * 64,
    )
    regime = RegimeSimilarityEvidence(
        prediction_id=calibrated.prediction_id,
        source_kind="P12_HISTORICAL_ANALOG",
        as_of_time_ns=3000,
        similarity_bps=8800,
        uncertainty_bps=900,
        source_record_id="p12e-analog-001",
        provenance_sha256="d" * 64,
    )
    result = qualify_probability_uncertainty(
        policy=policy,
        calibrated=calibrated,
        regime=regime,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14D_PROBABILITY_UNCERTAINTY_EVIDENCE",
        "task_id": "FIN-P14-WD-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "qualification_id": result.qualification_id,
        "qualification": result.payload(),
        "empirical_probability_immutable": result.empirical_probability_bps == calibrated.probability_bps,
        "regime_similarity_is_probability": False,
        "llm_probability_authority": False,
        "llm_uncertainty_authority": False,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P14D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
