from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.opportunity_ranking import (
    OpportunityRankingPolicy,
    rank_opportunities,
)
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/opportunity-ranking-policy.json"


def candidate(
    candidate_id: str,
    asset_id: str,
    timing_class: str,
    adjusted_edge_bps: int,
    sample_count: int,
    *,
    scanner_state: str = "ELIGIBLE_TIMING_CONTEXT",
    eligible: bool = True,
) -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id=candidate_id,
        window_id=f"window-{candidate_id[:8]}",
        asset_id=asset_id,
        strategy_id="trend-v1",
        timeframe="1h",
        regime_label="ALIGNED_BULLISH",
        session_labels=("EUROPE", "US"),
        sample_count=sample_count,
        adjusted_edge_bps=adjusted_edge_bps,
        timing_class=timing_class,
        scanner_state=scanner_state,
        eligible=eligible,
        provenance_sha256=("a" * 64,),
        source_dataset_versions=("p13c-v1",),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = OpportunityRankingPolicy.from_path(POLICY_PATH)
    candidates = (
        candidate("a" * 64, "BTC-USD", "PREFERRED", 150, 60),
        candidate("b" * 64, "ETH-USD", "PREFERRED", 130, 80),
        candidate("c" * 64, "EURUSD", "STANDARD", 300, 100),
        candidate("d" * 64, "GBPUSD", "WEAK", -10, 40, scanner_state="OBSERVE_ONLY", eligible=False),
    )
    result = rank_opportunities(candidates, policy=policy)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13D_OPPORTUNITY_RANKING_EVIDENCE",
        "task_id": "FIN-P13-WD-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "ranked": [
            {
                "rank_position": item.rank_position,
                "candidate_id": item.candidate.candidate_id,
                "asset_id": item.candidate.asset_id,
                "timing_class": item.candidate.timing_class,
                "adjusted_edge_bps": item.candidate.adjusted_edge_bps,
                "sample_count": item.candidate.sample_count,
            }
            for item in result.ranked
        ],
        "excluded_candidate_ids": list(result.excluded_candidate_ids),
        "ranking_is_probability": policy.ranking_is_probability,
        "hard_no_trade_authority": policy.hard_no_trade_authority,
        "signal_expiry_in_scope": policy.signal_expiry_in_scope,
        "signal_probability_in_scope": policy.signal_probability_in_scope,
        "risk_approval_in_scope": policy.risk_approval_in_scope,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
