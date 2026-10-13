from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, cast

from .opportunity_scanner import OpportunityCandidate


class NoTradeError(ValueError):
    """P13-E no-trade input or policy violates governed invariants."""


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise NoTradeError(f"{field} must be boolean")
    return value


@dataclass(frozen=True, slots=True)
class NoTradePolicy:
    decisions: tuple[str, ...]
    rankable_scanner_state: str
    hard_veto_reason_codes: tuple[str, ...]
    signal_expiry_computation_in_scope: bool
    signal_probability_in_scope: bool
    portfolio_risk_budget_computation_in_scope: bool
    position_sizing_in_scope: bool
    risk_approval_in_scope: bool
    execution_authority: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "NoTradePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise NoTradeError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_TIMING_NO_TRADE_GUARDIAN":
            raise NoTradeError("unsupported P13-E policy")

        decisions_value = raw.get("decisions")
        if not isinstance(decisions_value, list):
            raise NoTradeError("decisions must be list")
        decisions = tuple(str(item).strip().upper() for item in cast(list[object], decisions_value))
        if decisions != ("TIMING_ELIGIBLE", "NO_TRADE"):
            raise NoTradeError("unexpected no-trade decisions")

        if raw.get("rankable_scanner_state") != "ELIGIBLE_TIMING_CONTEXT":
            raise NoTradeError("unexpected rankable scanner state")

        reasons_value = raw.get("hard_veto_reason_codes")
        if not isinstance(reasons_value, list):
            raise NoTradeError("hard_veto_reason_codes must be list")
        reasons = tuple(str(item).strip().upper() for item in cast(list[object], reasons_value))
        expected = (
            "CANDIDATE_NOT_ELIGIBLE",
            "CONTRADICTORY_EVIDENCE",
            "DEGRADED_DATA",
            "HIGH_EVENT_RISK",
            "POOR_LIQUIDITY",
            "EXCESSIVE_SPREAD",
            "STALE_EVIDENCE",
            "EXTREME_UNCERTAINTY",
        )
        if reasons != expected:
            raise NoTradeError("unexpected hard-veto reason codes")

        boundaries = (
            ("signal_expiry_computation_in_scope", "P13-F"),
            ("signal_probability_in_scope", "P14"),
            ("portfolio_risk_budget_computation_in_scope", "P15"),
            ("position_sizing_in_scope", "P15"),
            ("risk_approval_in_scope", "P15/P16"),
            ("execution_authority", "P20"),
        )
        for key, owner in boundaries:
            if raw.get(key) is not False:
                raise NoTradeError(f"{key} must remain false; owned by {owner}")
        if raw.get("canonical_tests_network_required") is not False:
            raise NoTradeError("canonical P13-E tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise NoTradeError("P13-E cannot enable trading")

        return cls(
            decisions=decisions,
            rankable_scanner_state="ELIGIBLE_TIMING_CONTEXT",
            hard_veto_reason_codes=reasons,
            signal_expiry_computation_in_scope=False,
            signal_probability_in_scope=False,
            portfolio_risk_budget_computation_in_scope=False,
            position_sizing_in_scope=False,
            risk_approval_in_scope=False,
            execution_authority=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class NoTradeContext:
    candidate: OpportunityCandidate
    contradictory_evidence: bool = False
    degraded_data: bool = False
    high_event_risk: bool = False
    poor_liquidity: bool = False
    excessive_spread: bool = False
    stale_evidence: bool = False
    extreme_uncertainty: bool = False


@dataclass(frozen=True, slots=True)
class NoTradeDecision:
    candidate_id: str
    decision: str
    reason_codes: tuple[str, ...]


def evaluate_no_trade(
    context: NoTradeContext,
    *,
    policy: NoTradePolicy,
) -> NoTradeDecision:
    candidate = context.candidate
    is_rankable_state = candidate.scanner_state == policy.rankable_scanner_state
    if candidate.eligible != is_rankable_state:
        raise NoTradeError("candidate eligibility/scanner state mismatch")

    trigger_map = {
        "CONTRADICTORY_EVIDENCE": _boolean(context.contradictory_evidence, field="contradictory_evidence"),
        "DEGRADED_DATA": _boolean(context.degraded_data, field="degraded_data"),
        "HIGH_EVENT_RISK": _boolean(context.high_event_risk, field="high_event_risk"),
        "POOR_LIQUIDITY": _boolean(context.poor_liquidity, field="poor_liquidity"),
        "EXCESSIVE_SPREAD": _boolean(context.excessive_spread, field="excessive_spread"),
        "STALE_EVIDENCE": _boolean(context.stale_evidence, field="stale_evidence"),
        "EXTREME_UNCERTAINTY": _boolean(context.extreme_uncertainty, field="extreme_uncertainty"),
    }
    active: set[str] = set()
    if not candidate.eligible:
        active.add("CANDIDATE_NOT_ELIGIBLE")
    active.update(code for code, enabled in trigger_map.items() if enabled)

    ordered = tuple(code for code in policy.hard_veto_reason_codes if code in active)
    decision = "NO_TRADE" if ordered else "TIMING_ELIGIBLE"
    return NoTradeDecision(
        candidate_id=candidate.candidate_id,
        decision=decision,
        reason_codes=ordered,
    )
