from __future__ import annotations

from dataclasses import replace
import unittest

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
    IndependentRiskValidationError,
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


def build_chain(
    *,
    current_equity: str = "9500",
    data_health: str = "HEALTHY",
    counterparty_health: str = "HEALTHY",
) -> RiskValidationChain:
    hierarchy = RiskPolicyHierarchy.build(
        policy_version="p15i-a-v1",
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
        policy_version="p15i-c-v1",
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
        "p15i-d-v1",
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

    margin_policy = MarginLeveragePolicy("p15i-e-v1", 2000, 5000)
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
    e_decision = evaluate_margin_leverage(
        policy=margin_policy,
        request=e_request,
    )

    drawdown_policy = DrawdownRuinPolicy("p15i-f-v1", 1000, 2000, 50000)
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
        policy_version="p15i-g-v1",
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

    defensive_policy = DefensiveModePolicy("p15i-h-v1", 5000, 2500)
    h_request = DefensiveModeRequest(
        "h",
        g_decision.decision_id,
        g_decision.status,
        f_decision.status,
        data_health,
        counterparty_health,
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


class IndependentRiskValidationTests(unittest.TestCase):
    def test_happy_chain_passes(self) -> None:
        result = validate_risk_chain(build_chain())
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.marker, "P15_INDEPENDENT_RISK_VALIDATION")
        self.assertEqual(result.final_mode, "NORMAL")
        self.assertEqual(result.final_risk_scale_bps, 10_000)
        self.assertFalse(result.execution_authority)
        self.assertFalse(result.p16_approval_authority)

    def test_soft_drawdown_maps_to_defensive(self) -> None:
        result = validate_risk_chain(build_chain(current_equity="8500"))
        self.assertEqual(result.final_mode, "DEFENSIVE")
        self.assertEqual(result.final_risk_scale_bps, 2500)

    def test_hard_drawdown_maps_to_halt(self) -> None:
        result = validate_risk_chain(build_chain(current_equity="7500"))
        self.assertEqual(result.final_mode, "HALT_NEW_RISK")
        self.assertEqual(result.final_risk_scale_bps, 0)

    def test_critical_health_maps_to_halt(self) -> None:
        result = validate_risk_chain(
            build_chain(counterparty_health="CRITICAL"),
        )
        self.assertEqual(result.final_mode, "HALT_NEW_RISK")

    def test_tampered_upstream_id_fails_closed(self) -> None:
        chain = build_chain()
        tampered = replace(
            chain,
            b_request=replace(chain.b_request, upstream_risk_decision_id="wrong"),
        )
        with self.assertRaises(IndependentRiskValidationError):
            validate_risk_chain(tampered)

    def test_tampered_upstream_status_fails_closed(self) -> None:
        chain = build_chain()
        tampered = replace(
            chain,
            c_request=replace(chain.c_request, upstream_size_status="VETO"),
        )
        with self.assertRaises(IndependentRiskValidationError):
            validate_risk_chain(tampered)

    def test_veto_bypass_fails_closed(self) -> None:
        chain = build_chain(current_equity="7500")
        tampered = replace(
            chain,
            g_decision=replace(chain.g_decision, status="CAPITAL_SEGMENT_ELIGIBLE"),
        )
        with self.assertRaises(IndependentRiskValidationError):
            validate_risk_chain(tampered)

    def test_authority_escalation_fails_closed(self) -> None:
        chain = build_chain()
        tampered = replace(
            chain,
            h_decision=replace(chain.h_decision, execution_authority=True),
        )
        with self.assertRaises(IndependentRiskValidationError):
            validate_risk_chain(tampered)

    def test_validation_identity_is_deterministic(self) -> None:
        chain = build_chain()
        left = validate_risk_chain(chain)
        right = validate_risk_chain(chain)
        self.assertEqual(left.validation_id, right.validation_id)


if __name__ == "__main__":
    unittest.main()
