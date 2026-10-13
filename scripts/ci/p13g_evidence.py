from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate
from packages.timing_opportunity.scenario_engine import ScenarioEnginePolicy, build_scenarios


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/scenario-engine-policy.json"


def candidate() -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id="a" * 64,
        window_id="window-p13g",
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
        source_dataset_versions=("p13g-evidence-v1",),
    )


def assessment(candidate_id: str, state: str) -> ExpiryNoChaseAssessment:
    return ExpiryNoChaseAssessment(
        candidate_id=candidate_id,
        state=state,
        observed_at_ns=100,
        expires_at_ns=300,
        as_of_ns=200,
        age_ns=100,
        remaining_ns=100,
        price_displacement_bps=10,
        maximum_chase_bps=20,
        upstream_no_trade_reason_codes=(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = ScenarioEnginePolicy.from_path(POLICY_PATH)
    item = candidate()
    eligible = NoTradeDecision(item.candidate_id, "TIMING_ELIGIBLE", ())
    active = build_scenarios(item, eligible, assessment(item.candidate_id, "ACTIVE"), policy=policy)
    expired = build_scenarios(item, eligible, assessment(item.candidate_id, "EXPIRED"), policy=policy)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13G_SCENARIO_ENGINE_EVIDENCE",
        "task_id": "FIN-P13-WG-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "active": {
            "state": active.state,
            "upstream_expiry_state": active.upstream_expiry_state,
            "scenario_kinds": [frame.scenario_kind for frame in active.frames],
            "scenario_ids": [frame.scenario_id for frame in active.frames],
            "condition_codes": [list(frame.condition_codes) for frame in active.frames],
        },
        "expired": {
            "state": expired.state,
            "upstream_expiry_state": expired.upstream_expiry_state,
            "frame_count": len(expired.frames),
            "block_reason": expired.block_reason,
        },
        "scenario_probability_in_scope": policy.scenario_probability_in_scope,
        "confidence_score_in_scope": policy.confidence_score_in_scope,
        "price_target_in_scope": policy.price_target_in_scope,
        "position_sizing_in_scope": policy.position_sizing_in_scope,
        "risk_approval_in_scope": policy.risk_approval_in_scope,
        "execution_authority": policy.execution_authority,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
