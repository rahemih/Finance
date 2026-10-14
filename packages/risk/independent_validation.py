from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .asset_strategy_limits import AssetStrategyLimitDecision, AssetStrategyLimitRequest
from .counterparty_capital import CounterpartyCapitalDecision, CounterpartyCapitalRequest
from .defensive_modes import DefensiveModeDecision, DefensiveModeRequest
from .drawdown_ruin import DrawdownRuinDecision, DrawdownRuinRequest
from .margin_leverage import MarginLeverageDecision, MarginLeverageRequest
from .policy_hierarchy import RiskBudgetDecision, RiskBudgetRequest
from .portfolio_correlation import PortfolioExposureDecision, PortfolioExposureRequest
from .position_sizing import PositionSizeDecision, PositionSizingRequest


class IndependentRiskValidationError(ValueError):
    """P15-I rejects inconsistent or authority-escalating P15 chains."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RiskValidationChain:
    a_request: RiskBudgetRequest
    a_decision: RiskBudgetDecision
    b_request: PositionSizingRequest
    b_decision: PositionSizeDecision
    c_request: AssetStrategyLimitRequest
    c_decision: AssetStrategyLimitDecision
    d_request: PortfolioExposureRequest
    d_decision: PortfolioExposureDecision
    e_request: MarginLeverageRequest
    e_decision: MarginLeverageDecision
    f_request: DrawdownRuinRequest
    f_decision: DrawdownRuinDecision
    g_request: CounterpartyCapitalRequest
    g_decision: CounterpartyCapitalDecision
    h_request: DefensiveModeRequest
    h_decision: DefensiveModeDecision


@dataclass(frozen=True)
class IndependentRiskValidation:
    validation_id: str
    status: str
    marker: str
    checks: tuple[str, ...]
    final_mode: str
    final_risk_scale_bps: int
    execution_authority: bool = False
    p16_approval_authority: bool = False


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IndependentRiskValidationError(message)


def validate_risk_chain(chain: RiskValidationChain) -> IndependentRiskValidation:
    checks: list[str] = []

    pairs = (
        ("P15-A", chain.a_request.request_id, chain.a_decision.request_id),
        ("P15-B", chain.b_request.request_id, chain.b_decision.request_id),
        ("P15-C", chain.c_request.request_id, chain.c_decision.request_id),
        ("P15-D", chain.d_request.request_id, chain.d_decision.request_id),
        ("P15-E", chain.e_request.request_id, chain.e_decision.request_id),
        ("P15-F", chain.f_request.request_id, chain.f_decision.request_id),
        ("P15-G", chain.g_request.request_id, chain.g_decision.request_id),
        ("P15-H", chain.h_request.request_id, chain.h_decision.request_id),
    )
    for label, request_id, decision_request_id in pairs:
        _require(
            request_id == decision_request_id,
            f"{label} request/decision identity mismatch",
        )
    checks.append("REQUEST_DECISION_IDENTITIES")

    _require(
        chain.b_request.upstream_risk_decision_id == chain.a_decision.decision_id,
        "P15-B upstream decision id mismatch",
    )
    _require(
        chain.b_request.upstream_status == chain.a_decision.status,
        "P15-B upstream status mismatch",
    )
    _require(
        chain.c_request.upstream_size_decision_id == chain.b_decision.decision_id,
        "P15-C upstream decision id mismatch",
    )
    _require(
        chain.c_request.upstream_size_status == chain.b_decision.status,
        "P15-C upstream status mismatch",
    )
    _require(
        chain.d_request.upstream_limit_decision_id == chain.c_decision.decision_id,
        "P15-D upstream decision id mismatch",
    )
    _require(
        chain.d_request.upstream_limit_status == chain.c_decision.status,
        "P15-D upstream status mismatch",
    )
    _require(
        chain.e_request.upstream_portfolio_decision_id == chain.d_decision.decision_id,
        "P15-E upstream decision id mismatch",
    )
    _require(
        chain.e_request.upstream_portfolio_status == chain.d_decision.status,
        "P15-E upstream status mismatch",
    )
    _require(
        chain.f_request.upstream_margin_decision_id == chain.e_decision.decision_id,
        "P15-F upstream decision id mismatch",
    )
    _require(
        chain.f_request.upstream_margin_status == chain.e_decision.status,
        "P15-F upstream status mismatch",
    )
    _require(
        chain.g_request.upstream_drawdown_decision_id == chain.f_decision.decision_id,
        "P15-G upstream decision id mismatch",
    )
    _require(
        chain.g_request.upstream_drawdown_status == chain.f_decision.status,
        "P15-G upstream status mismatch",
    )
    _require(
        chain.h_request.upstream_capital_decision_id == chain.g_decision.decision_id,
        "P15-H capital decision id mismatch",
    )
    _require(
        chain.h_request.upstream_capital_status == chain.g_decision.status,
        "P15-H capital status mismatch",
    )
    _require(
        chain.h_request.upstream_drawdown_status == chain.f_decision.status,
        "P15-H drawdown status mismatch",
    )
    checks.append("UPSTREAM_LINEAGE_AND_STATUS")

    propagation = (
        (chain.a_decision.status == "VETO", chain.b_decision.status == "VETO", "A_TO_B"),
        (chain.b_decision.status == "VETO", chain.c_decision.status == "VETO", "B_TO_C"),
        (chain.c_decision.status == "VETO", chain.d_decision.status == "VETO", "C_TO_D"),
        (chain.d_decision.status == "VETO", chain.e_decision.status == "VETO", "D_TO_E"),
        (chain.e_decision.status == "VETO", chain.f_decision.status == "VETO", "E_TO_F"),
        (chain.f_decision.status == "VETO", chain.g_decision.status == "VETO", "F_TO_G"),
    )
    for upstream_veto, downstream_veto, label in propagation:
        if upstream_veto:
            _require(downstream_veto, f"veto bypass detected: {label}")
    checks.append("NON_BYPASSABLE_VETO_PROPAGATION")

    expected_mode = "NORMAL"
    expected_scale_rule = "NORMAL"
    if (
        chain.h_request.upstream_capital_status == "VETO"
        or chain.h_request.upstream_drawdown_status == "VETO"
        or chain.h_request.data_health == "CRITICAL"
        or chain.h_request.counterparty_health == "CRITICAL"
    ):
        expected_mode = "HALT_NEW_RISK"
        expected_scale_rule = "ZERO"
    elif chain.h_request.upstream_drawdown_status == "DE_RISK_REQUIRED":
        expected_mode = "DEFENSIVE"
        expected_scale_rule = "NON_EXPANSIVE"
    elif (
        chain.h_request.data_health == "DEGRADED"
        or chain.h_request.counterparty_health == "DEGRADED"
    ):
        expected_mode = "REDUCED_RISK"
        expected_scale_rule = "NON_EXPANSIVE"

    _require(chain.h_decision.mode == expected_mode, "P15-H mode is inconsistent")
    if expected_scale_rule == "ZERO":
        _require(chain.h_decision.risk_scale_bps == 0, "HALT_NEW_RISK must scale to zero")
        _require(not chain.h_decision.new_risk_allowed, "HALT_NEW_RISK cannot allow new risk")
    elif expected_scale_rule == "NORMAL":
        _require(chain.h_decision.risk_scale_bps == 10_000, "NORMAL must preserve 10000 bps")
        _require(chain.h_decision.new_risk_allowed, "NORMAL must allow governed new risk")
    else:
        _require(
            0 <= chain.h_decision.risk_scale_bps <= 10_000,
            "defensive scale must remain within governed bps",
        )
        _require(chain.h_decision.new_risk_allowed, "non-halt modes must preserve admission path")
    checks.append("DEFENSIVE_MODE_CONSISTENCY")

    authority_flags = (
        chain.a_decision.position_sizing_authority,
        chain.a_decision.execution_authority,
        chain.b_decision.leverage_authority,
        chain.b_decision.execution_authority,
        chain.c_decision.portfolio_correlation_authority,
        chain.c_decision.leverage_authority,
        chain.c_decision.execution_authority,
        chain.d_decision.leverage_authority,
        chain.d_decision.execution_authority,
        chain.e_decision.execution_authority,
        chain.f_decision.defensive_mode_authority,
        chain.f_decision.execution_authority,
        chain.g_decision.venue_routing_authority,
        chain.g_decision.execution_authority,
        chain.h_decision.position_close_authority,
        chain.h_decision.execution_authority,
    )
    _require(not any(authority_flags), "P15 authority escalation detected")
    checks.append("ZERO_EXECUTION_AND_ROUTING_AUTHORITY")

    decision_ids = (
        chain.a_decision.decision_id,
        chain.b_decision.decision_id,
        chain.c_decision.decision_id,
        chain.d_decision.decision_id,
        chain.e_decision.decision_id,
        chain.f_decision.decision_id,
        chain.g_decision.decision_id,
        chain.h_decision.decision_id,
    )
    _require(len(set(decision_ids)) == len(decision_ids), "duplicate decision identity")
    checks.append("DISTINCT_DECISION_IDENTITIES")

    payload = {
        "marker": "P15_INDEPENDENT_RISK_VALIDATION",
        "status": "PASS",
        "checks": checks,
        "decision_ids": decision_ids,
        "final_mode": chain.h_decision.mode,
        "final_risk_scale_bps": chain.h_decision.risk_scale_bps,
        "execution_authority": False,
        "p16_approval_authority": False,
    }
    return IndependentRiskValidation(
        validation_id=_sha256(payload),
        status="PASS",
        marker="P15_INDEPENDENT_RISK_VALIDATION",
        checks=tuple(checks),
        final_mode=chain.h_decision.mode,
        final_risk_scale_bps=chain.h_decision.risk_scale_bps,
    )
