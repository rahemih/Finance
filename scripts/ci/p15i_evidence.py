from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.asset_strategy_limits import (
    AssetStrategyLimitPolicy,
    AssetStrategyLimitRequest,
    LimitRule,
    LimitUsage,
)
from packages.risk.counterparty_capital import (
    CapitalSegmentRule,
    CounterpartyCapitalPolicy,
    CounterpartyCapitalRequest,
    CounterpartyRule,
    evaluate_counterparty_capital,
)
from packages.risk.defensive_modes import (
    DefensiveModePolicy,
    DefensiveModeRequest,
    select_defensive_mode,
)
from packages.risk.drawdown_ruin import (
    DrawdownRuinPolicy,
    DrawdownRuinRequest,
    evaluate_drawdown_ruin,
)
from packages.risk.independent_validation import (
    RiskValidationChain,
    validate_risk_chain,
)
from packages.risk.margin_leverage import (
    MarginLeveragePolicy,
    MarginLeverageRequest,
    evaluate_margin_leverage,
)
from packages.risk.policy_hierarchy import (
    RiskBudgetNode,
    RiskBudgetRequest,
    RiskPolicyHierarchy,
)
from packages.risk.portfolio_correlation import (
    PortfolioExposurePolicy,
    PortfolioExposureRequest,
    evaluate_portfolio_exposure,
)
from packages.risk.position_sizing import PositionSizingRequest, size_position


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config/risk/independent-risk-validation.json"


def build_chain(current_equity: str) -> RiskValidationChain:
    hierarchy = RiskPolicyHierarchy.build(
        policy_version="p15i-ci-a-v1",
        effective_from_ns=0,
        nodes=(
            RiskBudgetNode("global", "GLOBAL", "all", None, 10_000),
            RiskBudgetNode("trade", "TRADE", "fixture", "global", 1000),
        ),
    )
    a_request = RiskBudgetRequest("a", "trade", 100, 1000)
    a_decision = hierarchy.evaluate(
        request=a_request,
        utilization_bps={"global": 0, "trade": 0},
    )

    b_request = PositionSizingRequest(
        "b",
        a_decision.decision_id,
        a_decision.status,
        "LONG",
        "10000",
        100,
        "100",
        "99",
        "1",
        "1",
        1000,
    )
    b_decision = size_position(b_request)

    limit_policy = AssetStrategyLimitPolicy.build(
        policy_version="p15i-ci-c-v1",
        rules=(
            LimitRule("ASSET", "BTC", 1000, 5),
            LimitRule("STRATEGY", "trend", 1000, 5),
        ),
    )
    c_request = AssetStrategyLimitRequest(
        "c",
        b_decision.decision_id,
        b_decision.status,
        "BTC",
        "trend",
        100,
        1,
        1000,
    )
    c_decision = limit_policy.evaluate(
        request=c_request,
        usage=(
            LimitUsage("ASSET", "BTC", 0, 0),
            LimitUsage("STRATEGY", "trend", 0, 0),
        ),
    )

    portfolio_policy = PortfolioExposurePolicy(
        "p15i-ci-d-v1",
        10_000,
        10_000,
        800,
        10_000,
    )
    d_request = PortfolioExposureRequest(
        "d",
        c_decision.decision_id,
        c_decision.status,
        "BTC",
        100,
        1000,
    )
    d_decision = evaluate_portfolio_exposure(
        policy=portfolio_policy,
        request=d_request,
        existing=(),
        correlations=(),
    )

    margin_policy = MarginLeveragePolicy("p15i-ci-e-v1", 2000, 5000)
    e_request = MarginLeverageRequest(
        "e",
        d_decision.decision_id,
        d_decision.status,
        "10000",
        "0",
        "0",
        "1000",
        1000,
        1000,
    )
    e_decision = evaluate_margin_leverage(policy=margin_policy, request=e_request)

    drawdown_policy = DrawdownRuinPolicy("p15i-ci-f-v1", 1000, 2000, 50000)
    f_request = DrawdownRuinRequest(
        "f",
        e_decision.decision_id,
        e_decision.status,
        "10000",
        current_equity,
        10000,
        "validated-fixture-model",
        1000,
    )
    f_decision = evaluate_drawdown_ruin(
        policy=drawdown_policy,
        request=f_request,
    )

    capital_policy = CounterpartyCapitalPolicy.build(
        policy_version="p15i-ci-g-v1",
        counterparties=(CounterpartyRule("venue-a", 4000),),
        segments=(CapitalSegmentRule("core", 7000),),
    )
    g_request = CounterpartyCapitalRequest(
        "g",
        f_decision.decision_id,
        f_decision.status,
        "venue-a",
        "core",
        3000,
        1000,
        2000,
        500,
        1000,
    )
    g_decision = evaluate_counterparty_capital(
        policy=capital_policy,
        request=g_request,
    )

    defensive_policy = DefensiveModePolicy("p15i-ci-h-v1", 5000, 2500)
    h_request = DefensiveModeRequest(
        "h",
        g_decision.decision_id,
        g_decision.status,
        f_decision.status,
        "HEALTHY",
        "HEALTHY",
        1000,
    )
    h_decision = select_defensive_mode(
        policy=defensive_policy,
        request=h_request,
    )

    return RiskValidationChain(
        a_request,
        a_decision,
        b_request,
        b_decision,
        c_request,
        c_decision,
        d_request,
        d_decision,
        e_request,
        e_decision,
        f_request,
        f_decision,
        g_request,
        g_decision,
        h_request,
        h_decision,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    normal = validate_risk_chain(build_chain("9500"))
    defensive = validate_risk_chain(build_chain("8500"))
    halted = validate_risk_chain(build_chain("7500"))

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15I_INDEPENDENT_RISK_VALIDATION_EVIDENCE",
        "task_id": "FIN-P15-WI-001",
        "fixture_only": True,
        "contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
        "marker": "P15_INDEPENDENT_RISK_VALIDATION",
        "normal": {
            "validation_id": normal.validation_id,
            "status": normal.status,
            "mode": normal.final_mode,
            "risk_scale_bps": normal.final_risk_scale_bps,
            "checks": list(normal.checks),
        },
        "defensive": {
            "validation_id": defensive.validation_id,
            "status": defensive.status,
            "mode": defensive.final_mode,
            "risk_scale_bps": defensive.final_risk_scale_bps,
        },
        "halted": {
            "validation_id": halted.validation_id,
            "status": halted.status,
            "mode": halted.final_mode,
            "risk_scale_bps": halted.final_risk_scale_bps,
        },
        "execution_authority": False,
        "p16_approval_authority": False,
        "p16_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "P15_INDEPENDENT_RISK_VALIDATION=PASS "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
