from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.persian_explainability import PersianExplainabilityPolicy, explain_signal_fa
from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.tp_stop_probability import TPStopOutcomeProbability
from packages.signal_intelligence.weighted_fusion import FusionRepresentative, WeightedFusionResult


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/persian-explainability-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = PersianExplainabilityPolicy.from_path(POLICY_PATH)
    fusion = WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state="FUSED",
        signed_score_bps=2500,
        direction=1,
        representatives=(
            FusionRepresentative("1" * 64, "TECH_TREND", "TECHNICAL", 1, 7000),
            FusionRepresentative("2" * 64, "FLOW_DELTA", "ORDER_FLOW_LIQUIDITY", 1, 6000),
            FusionRepresentative("3" * 64, "MACRO_GROWTH", "FUNDAMENTAL_MACRO", -1, -3000),
        ),
        supporting_groups=("TECH_TREND", "FLOW_DELTA"),
        opposing_groups=("MACRO_GROWTH",),
        neutral_groups=(),
        source_families=("TECHNICAL", "ORDER_FLOW_LIQUIDITY", "FUNDAMENTAL_MACRO"),
        excluded_expired_evidence_ids=("e" * 64,),
        excluded_correlated_evidence_ids=("f" * 64,),
        veto_codes=(),
    )
    qualification = ProbabilityUncertaintyQualification(
        prediction_id="b" * 64,
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
        regime_evidence_id="c" * 64,
    )
    outcomes = TPStopOutcomeProbability(
        model_id="d" * 64,
        upstream_qualification_id=qualification.qualification_id,
        as_of_time_ns=3000,
        state="CALIBRATED_TP_STOP",
        tp_first_probability_bps=6000,
        stop_first_probability_bps=3000,
        neither_probability_bps=1000,
        sample_count=50,
        tp_first_count=30,
        stop_first_count=15,
        neither_count=5,
        general_empirical_probability_bps=7000,
        general_overall_uncertainty_bps=900,
        outcome_definition_sha256="e" * 64,
    )
    explanation = explain_signal_fa(policy=policy, fusion=fusion, uncertainty=qualification, outcomes=outcomes)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14F_PERSIAN_EXPLAINABILITY_EVIDENCE",
        "task_id": "FIN-P14-WF-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "explanation_id": explanation.explanation_id,
        "explanation": explanation.payload(),
        "llm_freeform_numeric_authority": False,
        "probability_mutated": False,
        "final_signal_action": None,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P14F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
