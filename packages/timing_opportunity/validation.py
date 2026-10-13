from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, cast

from .best_trading_time import TimingWindowAssessment
from .expiry_no_chase import ExpiryNoChaseAssessment
from .no_trade import NoTradeDecision
from .opportunity_ranking import OpportunityRankingResult
from .opportunity_scanner import OpportunityCandidate
from .scenario_engine import ScenarioSet
from .session_calendar import SessionContext


class TimingRankingValidationError(ValueError):
    """P13-H integrated validation failed closed."""


@dataclass(frozen=True, slots=True)
class TimingRankingValidationPolicy:
    required_check_codes: tuple[str, ...]
    validation_is_probability: bool
    position_sizing_in_scope: bool
    risk_approval_in_scope: bool
    execution_authority: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "TimingRankingValidationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise TimingRankingValidationError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_P13_INTEGRATED_VALIDATION":
            raise TimingRankingValidationError("unsupported P13-H policy")
        checks_value = raw.get("required_check_codes")
        if not isinstance(checks_value, list):
            raise TimingRankingValidationError("required_check_codes must be list")
        checks = tuple(str(item).strip().upper() for item in cast(list[object], checks_value))
        expected = (
            "SESSION_TIMING_COHERENCE",
            "TIMING_CANDIDATE_COHERENCE",
            "RANKING_COHERENCE",
            "NO_TRADE_COHERENCE",
            "EXPIRY_COHERENCE",
            "SCENARIO_COHERENCE",
        )
        if checks != expected:
            raise TimingRankingValidationError("unexpected validation check codes")
        for key, owner in (
            ("validation_is_probability", "P14"),
            ("position_sizing_in_scope", "P15"),
            ("risk_approval_in_scope", "P16"),
            ("execution_authority", "P20"),
        ):
            if raw.get(key) is not False:
                raise TimingRankingValidationError(f"{key} must remain false; owned by {owner}")
        if raw.get("canonical_tests_network_required") is not False:
            raise TimingRankingValidationError("canonical P13-H tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise TimingRankingValidationError("P13-H cannot enable trading")
        return cls(
            required_check_codes=checks,
            validation_is_probability=False,
            position_sizing_in_scope=False,
            risk_approval_in_scope=False,
            execution_authority=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class TimingRankingValidationBundle:
    session: SessionContext
    timing: TimingWindowAssessment
    candidate: OpportunityCandidate
    ranking: OpportunityRankingResult
    no_trade: NoTradeDecision
    expiry: ExpiryNoChaseAssessment
    scenarios: ScenarioSet


@dataclass(frozen=True, slots=True)
class TimingRankingValidationReport:
    state: str
    candidate_id: str
    check_codes: tuple[str, ...]


def _validate_session_timing(bundle: TimingRankingValidationBundle) -> None:
    if bundle.timing.usable and not bundle.session.is_market_open:
        raise TimingRankingValidationError("usable timing assessment requires open market context")
    if bundle.timing.usable and bundle.timing.session_labels != bundle.session.active_sessions:
        raise TimingRankingValidationError("timing/session labels mismatch")


def _validate_timing_candidate(bundle: TimingRankingValidationBundle) -> None:
    timing = bundle.timing
    candidate = bundle.candidate
    expected = (
        timing.window_id,
        timing.asset_id,
        timing.strategy_id,
        timing.timeframe,
        timing.regime_label,
        timing.session_labels,
        timing.sample_count,
        timing.adjusted_edge_bps,
        timing.timing_class,
    )
    observed = (
        candidate.window_id,
        candidate.asset_id,
        candidate.strategy_id,
        candidate.timeframe,
        candidate.regime_label,
        candidate.session_labels,
        candidate.sample_count,
        candidate.adjusted_edge_bps,
        candidate.timing_class,
    )
    if expected != observed:
        raise TimingRankingValidationError("timing/candidate identity or metric mismatch")
    if candidate.eligible != (candidate.scanner_state == "ELIGIBLE_TIMING_CONTEXT"):
        raise TimingRankingValidationError("candidate eligibility/scanner state mismatch")


def _validate_ranking(bundle: TimingRankingValidationBundle) -> None:
    ranked = bundle.ranking.ranked
    positions = tuple(item.rank_position for item in ranked)
    if positions != tuple(range(1, len(ranked) + 1)):
        raise TimingRankingValidationError("ranking positions must be contiguous")
    ranked_ids = tuple(item.candidate.candidate_id for item in ranked)
    if len(ranked_ids) != len(set(ranked_ids)):
        raise TimingRankingValidationError("ranking contains duplicate candidate ids")
    for item in ranked:
        if not item.candidate.eligible or item.candidate.scanner_state != "ELIGIBLE_TIMING_CONTEXT":
            raise TimingRankingValidationError("ranking contains non-eligible candidate")
    excluded = bundle.ranking.excluded_candidate_ids
    if len(excluded) != len(set(excluded)):
        raise TimingRankingValidationError("excluded candidate ids contain duplicates")
    if set(ranked_ids) & set(excluded):
        raise TimingRankingValidationError("ranked and excluded candidate ids overlap")
    if bundle.candidate.eligible and bundle.candidate.candidate_id not in ranked_ids:
        raise TimingRankingValidationError("eligible subject candidate missing from ranking")
    if not bundle.candidate.eligible and bundle.candidate.candidate_id not in excluded:
        raise TimingRankingValidationError("non-eligible subject candidate missing from excluded set")


def _validate_no_trade(bundle: TimingRankingValidationBundle) -> None:
    decision = bundle.no_trade
    candidate = bundle.candidate
    if decision.candidate_id != candidate.candidate_id:
        raise TimingRankingValidationError("no-trade candidate identity mismatch")
    if decision.decision == "TIMING_ELIGIBLE":
        if decision.reason_codes or not candidate.eligible:
            raise TimingRankingValidationError("invalid TIMING_ELIGIBLE decision")
    elif decision.decision == "NO_TRADE":
        if not decision.reason_codes:
            raise TimingRankingValidationError("NO_TRADE requires reason codes")
    else:
        raise TimingRankingValidationError("unknown no-trade decision")


def _validate_expiry(bundle: TimingRankingValidationBundle) -> None:
    expiry = bundle.expiry
    decision = bundle.no_trade
    if expiry.candidate_id != bundle.candidate.candidate_id:
        raise TimingRankingValidationError("expiry candidate identity mismatch")
    if decision.decision == "NO_TRADE" and expiry.state != "BLOCKED_BY_NO_TRADE":
        raise TimingRankingValidationError("NO_TRADE must remain blocked downstream")
    if decision.decision == "TIMING_ELIGIBLE" and expiry.state == "BLOCKED_BY_NO_TRADE":
        raise TimingRankingValidationError("TIMING_ELIGIBLE cannot be blocked by no-trade")
    if expiry.state not in {"ACTIVE", "EXPIRED", "NO_CHASE", "BLOCKED_BY_NO_TRADE"}:
        raise TimingRankingValidationError("unknown expiry/no-chase state")


def _validate_scenarios(bundle: TimingRankingValidationBundle) -> None:
    scenarios = bundle.scenarios
    expiry = bundle.expiry
    if scenarios.candidate_id != bundle.candidate.candidate_id:
        raise TimingRankingValidationError("scenario candidate identity mismatch")
    if scenarios.upstream_expiry_state != expiry.state:
        raise TimingRankingValidationError("scenario expiry state mismatch")
    if expiry.state == "ACTIVE":
        if scenarios.state != "CONDITIONAL_SCENARIOS" or len(scenarios.frames) != 3 or scenarios.block_reason is not None:
            raise TimingRankingValidationError("ACTIVE context requires three conditional scenarios")
        kinds = tuple(frame.scenario_kind for frame in scenarios.frames)
        if kinds != ("CONTINUATION", "DETERIORATION", "INVALIDATION"):
            raise TimingRankingValidationError("unexpected scenario ordering")
    else:
        if scenarios.state != "NON_ACTIONABLE" or scenarios.frames or scenarios.block_reason != expiry.state:
            raise TimingRankingValidationError("blocked/expired context must remain non-actionable")


def validate_timing_ranking(
    bundle: TimingRankingValidationBundle,
    *,
    policy: TimingRankingValidationPolicy,
) -> TimingRankingValidationReport:
    _validate_session_timing(bundle)
    _validate_timing_candidate(bundle)
    _validate_ranking(bundle)
    _validate_no_trade(bundle)
    _validate_expiry(bundle)
    _validate_scenarios(bundle)
    return TimingRankingValidationReport(
        state="PASS",
        candidate_id=bundle.candidate.candidate_id,
        check_codes=policy.required_check_codes,
    )
