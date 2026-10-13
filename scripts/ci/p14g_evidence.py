from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.persian_explainability import PersianExplainabilityPolicy, explain_signal_fa
from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.red_team_challenge import RedTeamPolicy, challenge_signal
from packages.signal_intelligence.tp_stop_probability import TPStopOutcomeProbability
from packages.signal_intelligence.weighted_fusion import FusionRepresentative, WeightedFusionResult


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/red-team-challenge-policy.json"
EXPLAIN_POLICY_PATH = ROOT / "config/signal-intelligence/persian-explainability-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    red_policy = RedTeamPolicy.from_path(POLICY_PATH)
    explain_policy = PersianExplainabilityPolicy.from_path(EXPLAIN_POLICY_PATH)

    fusion = WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state="FUSED",
        signed_score_bps=4200,
        direction=1,
        representatives=(
            FusionRepresentative("1" * 64, "TECH_TREND", "TECHNICAL", 1, 7000),
            FusionRepresentative("2" * 64, "FLOW_DELTA", "ORDER_FLOW_LIQUIDITY", 1, 6200),
        ),
        supporting_groups=("FLOW_DELTA", "TECH_TREND"),
        opposing_groups=(),
        neutral_groups=(),
        source_families=("ORDER_FLOW_LIQUIDITY", "TECHNICAL"),
        excluded_expired_evidence_ids=(),
        excluded_correlated_evidence_ids=(),
        veto_codes=(),
    )
    qualification = ProbabilityUncertaintyQualification(
        prediction_id="b" * 64,
        empirical_probability_bps=7200,
        sample_count=120,
        success_count=86,
        state="QUALIFIED",
        sample_support="STRONG",
        confidence_level_bps=9500,
        confidence_interval_lower_bps=6300,
        confidence_interval_upper_bps=7950,
        interval_half_width_bps=825,
        regime_similarity_bps=8300,
        regime_dissimilarity_bps=1700,
        regime_uncertainty_bps=800,
        overall_uncertainty_bps=800,
        dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",),
        regime_evidence_id="c" * 64,
    )
    outcomes = TPStopOutcomeProbability(
        model_id="d" * 64,
        upstream_qualification_id=qualification.qualification_id,
        as_of_time_ns=3000,
        state="CALIBRATED_TP_STOP",
        tp_first_probability_bps=6500,
        stop_first_probability_bps=2500,
        neither_probability_bps=1000,
        sample_count=60,
        tp_first_count=39,
        stop_first_count=15,
        neither_count=6,
        general_empirical_probability_bps=7200,
        general_overall_uncertainty_bps=800,
        outcome_definition_sha256="e" * 64,
    )
    explanation = explain_signal_fa(
        policy=explain_policy,
        fusion=fusion,
        uncertainty=qualification,
        outcomes=outcomes,
    )
    result = challenge_signal(
        policy=red_policy,
        fusion=fusion,
        explanation=explanation,
        uncertainty=qualification,
        outcomes=outcomes,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14G_RED_TEAM_EVIDENCE",
        "task_id": "FIN-P14-WG-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "challenge_id": result.challenge_id,
        "challenge": result.payload(),
        "linear_sync": "BLOCKED_FREE_ISSUE_LIMIT",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P14G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
