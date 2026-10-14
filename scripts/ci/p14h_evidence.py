from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.signal_intelligence.persian_explainability import PersianSignalExplanation
from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.red_team_challenge import RedTeamChallenge
from packages.signal_intelligence.signal_output_contract import CandidatePriceGeometry, SignalOutputPolicy, build_signal_output
from packages.signal_intelligence.tp_stop_probability import BarrierPlanContext, TPStopOutcomeProbability
from packages.signal_intelligence.weighted_fusion import FusionRepresentative, WeightedFusionResult
from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/signal-output-contract-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = SignalOutputPolicy.from_path(POLICY_PATH)
    candidate = OpportunityCandidate(
        candidate_id="candidate-1", window_id="window-1", asset_id="BTC-USD", strategy_id="trend-flow-v1",
        timeframe="1h", regime_label="TRENDING", session_labels=("EUROPE_US_OVERLAP",), sample_count=120,
        adjusted_edge_bps=4200, timing_class="PREFERRED", scanner_state="ELIGIBLE_TIMING_CONTEXT",
        eligible=True, provenance_sha256=("1" * 64,), source_dataset_versions=("dataset-v1",),
    )
    no_trade = NoTradeDecision(candidate_id="candidate-1", decision="TIMING_ELIGIBLE", reason_codes=())
    expiry = ExpiryNoChaseAssessment(
        candidate_id="candidate-1", state="ACTIVE", observed_at_ns=1000, expires_at_ns=5000, as_of_ns=3000,
        age_ns=2000, remaining_ns=2000, price_displacement_bps=20, maximum_chase_bps=50,
        upstream_no_trade_reason_codes=(),
    )
    fusion = WeightedFusionResult(
        subject_id="BTC-USD", as_of_time_ns=3000, state="FUSED", signed_score_bps=4200, direction=1,
        representatives=(
            FusionRepresentative("1" * 64, "TECH_TREND", "TECHNICAL", 1, 7000),
            FusionRepresentative("2" * 64, "FLOW_DELTA", "ORDER_FLOW_LIQUIDITY", 1, 6200),
        ),
        supporting_groups=("FLOW_DELTA", "TECH_TREND"), opposing_groups=(), neutral_groups=(),
        source_families=("ORDER_FLOW_LIQUIDITY", "TECHNICAL"),
        excluded_expired_evidence_ids=("e" * 64,), excluded_correlated_evidence_ids=(), veto_codes=(),
    )
    qualification = ProbabilityUncertaintyQualification(
        prediction_id="b" * 64, empirical_probability_bps=7200, sample_count=120, success_count=86,
        state="QUALIFIED", sample_support="STRONG", confidence_level_bps=9500,
        confidence_interval_lower_bps=6300, confidence_interval_upper_bps=7950, interval_half_width_bps=825,
        regime_similarity_bps=8300, regime_dissimilarity_bps=1700, regime_uncertainty_bps=800,
        overall_uncertainty_bps=800, dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",),
        regime_evidence_id="c" * 64,
    )
    barrier = BarrierPlanContext(
        subject_id="BTC-USD", strategy_id="trend-flow-v1", timeframe="1h", regime_label="TRENDING",
        session_label="EUROPE_US_OVERLAP", direction=1, target_distance_bps=300, stop_distance_bps=150,
        evaluation_horizon_steps=12, outcome_definition_sha256="d" * 64,
    )
    outcomes = TPStopOutcomeProbability(
        model_id="d" * 64, upstream_qualification_id=qualification.qualification_id, as_of_time_ns=3000,
        state="CALIBRATED_TP_STOP", tp_first_probability_bps=6500, stop_first_probability_bps=2500,
        neither_probability_bps=1000, sample_count=60, tp_first_count=39, stop_first_count=15, neither_count=6,
        general_empirical_probability_bps=7200, general_overall_uncertainty_bps=800,
        outcome_definition_sha256="d" * 64,
    )
    explanation = PersianSignalExplanation(
        subject_id="BTC-USD", as_of_time_ns=3000, fusion_id=fusion.fusion_id, fusion_state="FUSED", fusion_direction=1,
        qualification_id=qualification.qualification_id, tp_stop_prediction_id=outcomes.prediction_id,
        summary_fa="ترکیب شواهد مستقل جهت صعودی دارد؛ این توضیح به‌تنهایی دستور معامله نیست.",
        supporting_factors_fa=("عامل تأییدکننده: TECH_TREND",), opposing_factors_fa=(), neutral_factors_fa=(),
        veto_factors_fa=(), probability_fa="72.00٪", uncertainty_fa="8.00٪", tp_stop_fa="TP/Stop",
        evidence_quality_fa="کیفیت شواهد", empirical_probability_bps=7200, overall_uncertainty_bps=800,
        tp_first_probability_bps=6500, stop_first_probability_bps=2500, neither_probability_bps=1000,
    )
    challenge = RedTeamChallenge(
        subject_id="BTC-USD", as_of_time_ns=3000, fusion_id=fusion.fusion_id,
        qualification_id=qualification.qualification_id, tp_stop_prediction_id=outcomes.prediction_id,
        explanation_id=explanation.explanation_id, disposition="CLEAR", findings=(),
        empirical_probability_bps=7200, overall_uncertainty_bps=800,
        tp_first_probability_bps=6500, stop_first_probability_bps=2500,
    )
    geometry = CandidatePriceGeometry(
        price_scale=100, reference_price_scaled=100000, entry_low_scaled=99500, entry_high_scaled=100500,
        entry_anchor_scaled=100000, invalidation_price_scaled=98000, geometry_version_sha256="f" * 64,
    )
    signal = build_signal_output(
        policy=policy, candidate=candidate, no_trade=no_trade, expiry=expiry, fusion=fusion,
        uncertainty=qualification, barrier=barrier, outcomes=outcomes, explanation=explanation,
        challenge=challenge, geometry=geometry,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P14H_SIGNAL_OUTPUT_EVIDENCE",
        "task_id": "FIN-P14-WH-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "signal_id": signal.signal_id,
        "signal": signal.payload(),
        "linear_sync": "BLOCKED_FREE_ISSUE_LIMIT",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P14H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
