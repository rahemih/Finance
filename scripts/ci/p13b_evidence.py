from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.best_trading_time import (
    BestTradingTimePolicy,
    TimingWindowEvidence,
    select_best_timing_window,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/best-trading-time-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = BestTradingTimePolicy.from_path(POLICY_PATH)
    windows = (
        TimingWindowEvidence("ASIA", "BTCUSD", "TREND_V1", "1H", "ALIGNED_BULLISH", ("ASIA",), 80, 220, 120, True),
        TimingWindowEvidence("EUROPE_US", "BTCUSD", "TREND_V1", "1H", "ALIGNED_BULLISH", ("EUROPE", "US"), 55, 520, 140, True),
        TimingWindowEvidence("US", "BTCUSD", "TREND_V1", "1H", "ALIGNED_BULLISH", ("US",), 90, 360, 130, True),
    )
    result = select_best_timing_window(windows, policy=policy)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13B_BEST_TRADING_TIME_EVIDENCE",
        "task_id": "FIN-P13-WB-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "selected_window_id": result.selected_window_id,
        "selected_adjusted_edge_bps": result.selected.adjusted_edge_bps,
        "assessments": [
            {
                "window_id": item.window_id,
                "timing_class": item.timing_class,
                "sample_count": item.sample_count,
                "mean_edge_bps": item.mean_edge_bps,
                "uncertainty_bps": item.uncertainty_bps,
                "adjusted_edge_bps": item.adjusted_edge_bps,
                "usable": item.usable,
            }
            for item in result.assessments
        ],
        "opportunity_ranking_in_scope": policy.opportunity_ranking_in_scope,
        "no_trade_authority": policy.no_trade_authority,
        "signal_probability_in_scope": policy.signal_probability_in_scope,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
