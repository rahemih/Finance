from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, cast

from .no_trade import NoTradeDecision
from .opportunity_scanner import OpportunityCandidate


class ExpiryNoChaseError(ValueError):
    """P13-F expiry/no-chase input or policy violates governed invariants."""


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExpiryNoChaseError(f"{field} must be integer")
    return value


@dataclass(frozen=True, slots=True)
class ExpiryNoChasePolicy:
    states: tuple[str, ...]
    displacement_min_bps: int
    displacement_max_bps: int
    universal_expiry_threshold_defined: bool
    universal_chase_threshold_defined: bool
    upstream_no_trade_bypass_allowed: bool
    signal_probability_in_scope: bool
    portfolio_risk_in_scope: bool
    position_sizing_in_scope: bool
    risk_approval_in_scope: bool
    execution_authority: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ExpiryNoChasePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise ExpiryNoChaseError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "EXPLICIT_DEADLINE_CANDIDATE_SPECIFIC_NO_CHASE":
            raise ExpiryNoChaseError("unsupported P13-F policy")
        states_value = raw.get("states")
        if not isinstance(states_value, list):
            raise ExpiryNoChaseError("states must be list")
        states = tuple(str(item).strip().upper() for item in cast(list[object], states_value))
        if states != ("ACTIVE", "EXPIRED", "NO_CHASE", "BLOCKED_BY_NO_TRADE"):
            raise ExpiryNoChaseError("unexpected expiry/no-chase states")
        minimum = _integer(raw.get("displacement_min_bps"), field="displacement_min_bps")
        maximum = _integer(raw.get("displacement_max_bps"), field="displacement_max_bps")
        if (minimum, maximum) != (0, 10000):
            raise ExpiryNoChaseError("displacement scale must be unsigned basis points")
        if raw.get("universal_expiry_threshold_defined") is not False:
            raise ExpiryNoChaseError("P13-F cannot invent a universal expiry threshold")
        if raw.get("universal_chase_threshold_defined") is not False:
            raise ExpiryNoChaseError("P13-F cannot invent a universal chase threshold")
        if raw.get("upstream_no_trade_bypass_allowed") is not False:
            raise ExpiryNoChaseError("P13-E NO_TRADE cannot be bypassed")
        for key, owner in (
            ("signal_probability_in_scope", "P14"),
            ("portfolio_risk_in_scope", "P15"),
            ("position_sizing_in_scope", "P15"),
            ("risk_approval_in_scope", "P15/P16"),
            ("execution_authority", "P20"),
        ):
            if raw.get(key) is not False:
                raise ExpiryNoChaseError(f"{key} must remain false; owned by {owner}")
        if raw.get("canonical_tests_network_required") is not False:
            raise ExpiryNoChaseError("canonical P13-F tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise ExpiryNoChaseError("P13-F cannot enable trading")
        return cls(
            states=states,
            displacement_min_bps=minimum,
            displacement_max_bps=maximum,
            universal_expiry_threshold_defined=False,
            universal_chase_threshold_defined=False,
            upstream_no_trade_bypass_allowed=False,
            signal_probability_in_scope=False,
            portfolio_risk_in_scope=False,
            position_sizing_in_scope=False,
            risk_approval_in_scope=False,
            execution_authority=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class ExpiryNoChaseContext:
    candidate: OpportunityCandidate
    no_trade_decision: NoTradeDecision
    observed_at_ns: int
    expires_at_ns: int
    as_of_ns: int
    price_displacement_bps: int
    maximum_chase_bps: int


@dataclass(frozen=True, slots=True)
class ExpiryNoChaseAssessment:
    candidate_id: str
    state: str
    observed_at_ns: int
    expires_at_ns: int
    as_of_ns: int
    age_ns: int
    remaining_ns: int
    price_displacement_bps: int
    maximum_chase_bps: int
    upstream_no_trade_reason_codes: tuple[str, ...]


def assess_expiry_no_chase(
    context: ExpiryNoChaseContext,
    *,
    policy: ExpiryNoChasePolicy,
) -> ExpiryNoChaseAssessment:
    candidate = context.candidate
    upstream = context.no_trade_decision
    if upstream.candidate_id != candidate.candidate_id:
        raise ExpiryNoChaseError("no-trade decision candidate identity mismatch")
    if upstream.decision not in {"TIMING_ELIGIBLE", "NO_TRADE"}:
        raise ExpiryNoChaseError("unknown upstream no-trade decision")
    if upstream.decision == "TIMING_ELIGIBLE" and upstream.reason_codes:
        raise ExpiryNoChaseError("TIMING_ELIGIBLE cannot carry no-trade reasons")
    if upstream.decision == "NO_TRADE" and not upstream.reason_codes:
        raise ExpiryNoChaseError("NO_TRADE must carry at least one reason")
    if upstream.decision == "TIMING_ELIGIBLE" and not candidate.eligible:
        raise ExpiryNoChaseError("non-eligible candidate cannot be TIMING_ELIGIBLE")

    observed = _integer(context.observed_at_ns, field="observed_at_ns")
    expires = _integer(context.expires_at_ns, field="expires_at_ns")
    as_of = _integer(context.as_of_ns, field="as_of_ns")
    if observed < 0 or expires < 0 or as_of < 0:
        raise ExpiryNoChaseError("timestamps must be non-negative")
    if expires <= observed:
        raise ExpiryNoChaseError("expires_at_ns must be after observed_at_ns")
    if as_of < observed:
        raise ExpiryNoChaseError("as_of_ns cannot be before observed_at_ns")

    displacement = _integer(context.price_displacement_bps, field="price_displacement_bps")
    chase_limit = _integer(context.maximum_chase_bps, field="maximum_chase_bps")
    if not policy.displacement_min_bps <= displacement <= policy.displacement_max_bps:
        raise ExpiryNoChaseError("price_displacement_bps outside governed unsigned scale")
    if not policy.displacement_min_bps <= chase_limit <= policy.displacement_max_bps:
        raise ExpiryNoChaseError("maximum_chase_bps outside governed unsigned scale")

    age = as_of - observed
    remaining = max(0, expires - as_of)
    if upstream.decision == "NO_TRADE":
        state = "BLOCKED_BY_NO_TRADE"
    elif as_of >= expires:
        state = "EXPIRED"
    elif displacement > chase_limit:
        state = "NO_CHASE"
    else:
        state = "ACTIVE"

    return ExpiryNoChaseAssessment(
        candidate_id=candidate.candidate_id,
        state=state,
        observed_at_ns=observed,
        expires_at_ns=expires,
        as_of_ns=as_of,
        age_ns=age,
        remaining_ns=remaining,
        price_displacement_bps=displacement,
        maximum_chase_bps=chase_limit,
        upstream_no_trade_reason_codes=upstream.reason_codes,
    )
