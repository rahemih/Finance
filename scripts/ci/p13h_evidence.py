from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.best_trading_time import TimingWindowAssessment
from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_ranking import OpportunityRankingResult, RankedOpportunity
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate
from packages.timing_opportunity.scenario_engine import ScenarioFrame, ScenarioSet
from packages.timing_opportunity.session_calendar import SessionContext
from packages.timing_opportunity.validation import (
    TimingRankingValidationBundle,
    TimingRankingValidationPolicy,
    validate_timing_ranking,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/timing-ranking-validation-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = TimingRankingValidationPolicy.from_path(POLICY_PATH)
    candidate = OpportunityCandidate(
        candidate_id="a" * 64,
        window_id="window-validation",
        asset_id="BTC-USD",
        strategy_id="trend-v1",
        timeframe="1h",
        regime_label="ALIGNED_BULLISH",
        session_labels=("EUROPE", "US"),
        sample_count=64,
        adjusted_edge_bps=140,
        timing_class="PREFERRED",
        scanner_state="ELIGIBLE_TIMING_CONTEXT",
        eligible=True,
        provenance_sha256=("b" * 64,),
        source_dataset_versions=("p13h-evidence-v1",),
    )
    session = SessionContext(1, "P13-A-UTC-BASELINE-V1", "CRYPTO_SPOT", 0, 840, True, ("EUROPE", "US"), 2, "OVERLAP")
    timing = TimingWindowAssessment(
        candidate.window_id,
        candidate.asset_id,
        candidate.strategy_id,
        candidate.timeframe,
        candidate.regime_label,
        candidate.session_labels,
        candidate.sample_count,
        170,
        30,
        candidate.adjusted_edge_bps,
        candidate.timing_class,
        True,
    )
    ranking = OpportunityRankingResult((RankedOpportunity(1, candidate),), ())
    no_trade = NoTradeDecision(candidate.candidate_id, "TIMING_ELIGIBLE", ())
    expiry = ExpiryNoChaseAssessment(candidate.candidate_id, "ACTIVE", 100, 300, 200, 100, 100, 10, 20, ())
    scenarios = ScenarioSet(
        candidate.candidate_id,
        "CONDITIONAL_SCENARIOS",
        "ACTIVE",
        (
            ScenarioFrame("1" * 64, candidate.candidate_id, "CONTINUATION", ("A",)),
            ScenarioFrame("2" * 64, candidate.candidate_id, "DETERIORATION", ("B",)),
            ScenarioFrame("3" * 64, candidate.candidate_id, "INVALIDATION", ("C",)),
        ),
        None,
    )
    report = validate_timing_ranking(
        TimingRankingValidationBundle(session, timing, candidate, ranking, no_trade, expiry, scenarios),
        policy=policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13H_TIMING_RANKING_VALIDATION_EVIDENCE",
        "task_id": "FIN-P13-WH-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "validation_state": report.state,
        "candidate_id": report.candidate_id,
        "check_codes": list(report.check_codes),
        "validation_is_probability": policy.validation_is_probability,
        "position_sizing_in_scope": policy.position_sizing_in_scope,
        "risk_approval_in_scope": policy.risk_approval_in_scope,
        "execution_authority": policy.execution_authority,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
