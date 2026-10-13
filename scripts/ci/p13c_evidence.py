from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.best_trading_time import (
    BestTradingTimePolicy,
    TimingWindowEvidence,
    assess_timing_window,
)
from packages.timing_opportunity.opportunity_scanner import (
    OpportunityScanInput,
    OpportunityScannerPolicy,
    scan_opportunities,
)


ROOT = Path(__file__).resolve().parents[2]
BEST_POLICY_PATH = ROOT / "config/timing-opportunity/best-trading-time-policy.json"
SCANNER_POLICY_PATH = ROOT / "config/timing-opportunity/opportunity-scanner-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    best_policy = BestTradingTimePolicy.from_path(BEST_POLICY_PATH)
    scanner_policy = OpportunityScannerPolicy.from_path(SCANNER_POLICY_PATH)

    raw = (
        TimingWindowEvidence("btc-preferred", "BTC-USD", "trend-v1", "1h", "ALIGNED_BULLISH", ("EUROPE", "US"), 60, 180, 20, True),
        TimingWindowEvidence("eth-standard", "ETH-USD", "trend-v1", "1h", "ALIGNED_BULLISH", ("US",), 45, 80, 20, True),
        TimingWindowEvidence("eur-weak", "EURUSD", "trend-v1", "1h", "CONFLICT", ("EUROPE",), 50, 10, 20, True),
        TimingWindowEvidence("closed", "GBPUSD", "trend-v1", "1h", "ALIGNED_BULLISH", ("US",), 50, 180, 20, False),
    )
    assessments = tuple(assess_timing_window(item, policy=best_policy) for item in raw)
    result = scan_opportunities(
        tuple(
            OpportunityScanInput(
                assessment=item,
                provenance_sha256=("a" * 64,),
                source_dataset_versions=("p13b-v1", "p06-history-v1"),
            )
            for item in assessments
        ),
        policy=scanner_policy,
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13C_OPPORTUNITY_SCANNER_EVIDENCE",
        "task_id": "FIN-P13-WC-001",
        "best_policy_sha256": hashlib.sha256(BEST_POLICY_PATH.read_bytes()).hexdigest(),
        "scanner_policy_sha256": hashlib.sha256(SCANNER_POLICY_PATH.read_bytes()).hexdigest(),
        "candidates": [
            {
                "candidate_id": item.candidate_id,
                "window_id": item.window_id,
                "asset_id": item.asset_id,
                "strategy_id": item.strategy_id,
                "timeframe": item.timeframe,
                "regime_label": item.regime_label,
                "session_labels": list(item.session_labels),
                "sample_count": item.sample_count,
                "adjusted_edge_bps": item.adjusted_edge_bps,
                "timing_class": item.timing_class,
                "scanner_state": item.scanner_state,
                "eligible": item.eligible,
                "provenance_sha256": list(item.provenance_sha256),
                "source_dataset_versions": list(item.source_dataset_versions),
            }
            for item in result.candidates
        ],
        "eligible_candidate_ids": list(result.eligible_candidate_ids),
        "observe_only_candidate_ids": list(result.observe_only_candidate_ids),
        "ineligible_candidate_ids": list(result.ineligible_candidate_ids),
        "opportunity_ranking_in_scope": scanner_policy.opportunity_ranking_in_scope,
        "hard_no_trade_authority": scanner_policy.hard_no_trade_authority,
        "signal_expiry_in_scope": scanner_policy.signal_expiry_in_scope,
        "signal_probability_in_scope": scanner_policy.signal_probability_in_scope,
        "network_required": scanner_policy.canonical_tests_network_required,
        "live_trading": scanner_policy.live_trading,
        "auto_trading": scanner_policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
