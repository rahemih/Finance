from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.no_trade import (
    NoTradeContext,
    NoTradePolicy,
    evaluate_no_trade,
)
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/no-trade-policy.json"


def candidate(
    candidate_id: str,
    *,
    timing_class: str = "PREFERRED",
    scanner_state: str = "ELIGIBLE_TIMING_CONTEXT",
    eligible: bool = True,
) -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id=candidate_id,
        window_id=f"window-{candidate_id[:6]}",
        asset_id="BTC-USD",
        strategy_id="trend-v1",
        timeframe="1h",
        regime_label="ALIGNED_BULLISH",
        session_labels=("EUROPE", "US"),
        sample_count=80,
        adjusted_edge_bps=150,
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

    policy = NoTradePolicy.from_path(POLICY_PATH)
    contexts = (
        NoTradeContext(candidate("a" * 64)),
        NoTradeContext(candidate("b" * 64), high_event_risk=True),
        NoTradeContext(
            candidate("c" * 64),
            degraded_data=True,
            poor_liquidity=True,
            stale_evidence=True,
        ),
        NoTradeContext(
            candidate(
                "d" * 64,
                timing_class="WEAK",
                scanner_state="OBSERVE_ONLY",
                eligible=False,
            )
        ),
    )
    decisions = tuple(evaluate_no_trade(item, policy=policy) for item in contexts)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13E_NO_TRADE_EVIDENCE",
        "task_id": "FIN-P13-WE-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "decisions": [
            {
                "candidate_id": item.candidate_id,
                "decision": item.decision,
                "reason_codes": list(item.reason_codes),
            }
            for item in decisions
        ],
        "signal_expiry_computation_in_scope": policy.signal_expiry_computation_in_scope,
        "signal_probability_in_scope": policy.signal_probability_in_scope,
        "portfolio_risk_budget_computation_in_scope": policy.portfolio_risk_budget_computation_in_scope,
        "risk_approval_in_scope": policy.risk_approval_in_scope,
        "execution_authority": policy.execution_authority,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
