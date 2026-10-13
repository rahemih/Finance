from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.expiry_no_chase import (
    ExpiryNoChaseContext,
    ExpiryNoChasePolicy,
    assess_expiry_no_chase,
)
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/expiry-no-chase-policy.json"


def candidate(candidate_id: str) -> OpportunityCandidate:
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
        timing_class="PREFERRED",
        scanner_state="ELIGIBLE_TIMING_CONTEXT",
        eligible=True,
        provenance_sha256=("b" * 64,),
        source_dataset_versions=("p13c-v1",),
    )


def context(
    candidate_id: str,
    *,
    no_trade: bool = False,
    as_of_ns: int = 1_500,
    displacement_bps: int = 40,
    maximum_chase_bps: int = 50,
) -> ExpiryNoChaseContext:
    item = candidate(candidate_id)
    decision = NoTradeDecision(
        candidate_id=item.candidate_id,
        decision="NO_TRADE" if no_trade else "TIMING_ELIGIBLE",
        reason_codes=("HIGH_EVENT_RISK",) if no_trade else (),
    )
    return ExpiryNoChaseContext(
        candidate=item,
        no_trade_decision=decision,
        observed_at_ns=1_000,
        expires_at_ns=2_000,
        as_of_ns=as_of_ns,
        price_displacement_bps=displacement_bps,
        maximum_chase_bps=maximum_chase_bps,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = ExpiryNoChasePolicy.from_path(POLICY_PATH)
    inputs = (
        context("a" * 64),
        context("b" * 64, as_of_ns=2_000),
        context("c" * 64, displacement_bps=60),
        context("d" * 64, no_trade=True),
    )
    assessments = tuple(assess_expiry_no_chase(item, policy=policy) for item in inputs)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13F_EXPIRY_NO_CHASE_EVIDENCE",
        "task_id": "FIN-P13-WF-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "assessments": [
            {
                "candidate_id": item.candidate_id,
                "state": item.state,
                "observed_at_ns": item.observed_at_ns,
                "expires_at_ns": item.expires_at_ns,
                "as_of_ns": item.as_of_ns,
                "age_ns": item.age_ns,
                "remaining_ns": item.remaining_ns,
                "price_displacement_bps": item.price_displacement_bps,
                "maximum_chase_bps": item.maximum_chase_bps,
                "upstream_no_trade_reason_codes": list(item.upstream_no_trade_reason_codes),
            }
            for item in assessments
        ],
        "universal_expiry_threshold_defined": policy.universal_expiry_threshold_defined,
        "universal_chase_threshold_defined": policy.universal_chase_threshold_defined,
        "upstream_no_trade_bypass_allowed": policy.upstream_no_trade_bypass_allowed,
        "signal_probability_in_scope": policy.signal_probability_in_scope,
        "portfolio_risk_in_scope": policy.portfolio_risk_in_scope,
        "execution_authority": policy.execution_authority,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
