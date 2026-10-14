from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.policy_hierarchy import (
    RiskBudgetNode,
    RiskBudgetRequest,
    RiskPolicyHierarchy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/risk-policy-hierarchy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    nodes = (
        RiskBudgetNode("global", "GLOBAL", "GLOBAL", None, 10_000),
        RiskBudgetNode("portfolio-main", "PORTFOLIO", "MAIN", "global", 8_000),
        RiskBudgetNode("market-crypto", "MARKET", "CRYPTO", "portfolio-main", 6_000),
        RiskBudgetNode("asset-btc", "ASSET", "BTC", "market-crypto", 4_000),
        RiskBudgetNode("strategy-trend", "STRATEGY", "TREND", "asset-btc", 2_500),
        RiskBudgetNode("trade-fixture", "TRADE", "CI_FIXTURE_ONLY", "strategy-trend", 1_000),
    )
    policy = RiskPolicyHierarchy.build(
        policy_version="p15a-ci-fixture-v1",
        effective_from_ns=1_000,
        nodes=nodes,
    )
    eligible = policy.evaluate(
        request=RiskBudgetRequest(
            request_id="ci-eligible",
            leaf_node_id="trade-fixture",
            requested_budget_bps=100,
            as_of_ns=1_100,
        ),
        utilization_bps={"trade-fixture": 100},
    )
    veto = policy.evaluate(
        request=RiskBudgetRequest(
            request_id="ci-veto",
            leaf_node_id="trade-fixture",
            requested_budget_bps=400,
            as_of_ns=1_100,
        ),
        utilization_bps={"trade-fixture": 700},
    )

    config = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15A_RISK_POLICY_HIERARCHY_EVIDENCE",
        "task_id": "FIN-P15-WA-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "hierarchy_policy_id": policy.policy_id,
        "root_budget_bps": policy.by_id["global"].budget_bps,
        "production_monetary_risk_ceiling": config["production_monetary_risk_ceiling"],
        "production_numeric_defaults": config["production_numeric_defaults"],
        "eligible_decision_id": eligible.decision_id,
        "eligible_status": eligible.status,
        "veto_decision_id": veto.decision_id,
        "veto_status": veto.status,
        "veto_reason_codes": list(veto.reason_codes),
        "risk_veto_non_bypassable": config["risk_veto_non_bypassable"],
        "risk_agent_can_modify_ceilings": config["risk_agent_can_modify_ceilings"],
        "position_sizing_authority": eligible.position_sizing_authority,
        "execution_authority": eligible.execution_authority,
        "live_trading": config["live_trading"],
        "auto_trading": config["auto_trading"],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P15A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
