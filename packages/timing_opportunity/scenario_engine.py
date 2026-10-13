from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .expiry_no_chase import ExpiryNoChaseAssessment
from .no_trade import NoTradeDecision
from .opportunity_scanner import OpportunityCandidate


class ScenarioEngineError(ValueError):
    """P13-G scenario input or policy violates governed invariants."""


@dataclass(frozen=True, slots=True)
class ScenarioEnginePolicy:
    scenario_kinds: tuple[str, ...]
    actionable_expiry_state: str
    required_upstream_decision: str
    blocked_expiry_states: tuple[str, ...]
    scenario_probability_in_scope: bool
    confidence_score_in_scope: bool
    price_target_in_scope: bool
    position_sizing_in_scope: bool
    risk_approval_in_scope: bool
    execution_authority: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ScenarioEnginePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise ScenarioEngineError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_CONDITIONAL_SCENARIO_FRAMING":
            raise ScenarioEngineError("unsupported P13-G policy")

        kinds_value = raw.get("scenario_kinds")
        if not isinstance(kinds_value, list):
            raise ScenarioEngineError("scenario_kinds must be list")
        kinds = tuple(str(item).strip().upper() for item in cast(list[object], kinds_value))
        if kinds != ("CONTINUATION", "DETERIORATION", "INVALIDATION"):
            raise ScenarioEngineError("unexpected scenario kinds")
        if raw.get("actionable_expiry_state") != "ACTIVE":
            raise ScenarioEngineError("scenario framing requires ACTIVE expiry state")
        if raw.get("required_upstream_decision") != "TIMING_ELIGIBLE":
            raise ScenarioEngineError("scenario framing requires TIMING_ELIGIBLE upstream decision")

        blocked_value = raw.get("blocked_expiry_states")
        if not isinstance(blocked_value, list):
            raise ScenarioEngineError("blocked_expiry_states must be list")
        blocked = tuple(str(item).strip().upper() for item in cast(list[object], blocked_value))
        if blocked != ("EXPIRED", "NO_CHASE", "BLOCKED_BY_NO_TRADE"):
            raise ScenarioEngineError("unexpected blocked expiry states")

        for key, owner in (
            ("scenario_probability_in_scope", "P14"),
            ("confidence_score_in_scope", "P14"),
            ("price_target_in_scope", "P14/P15 research"),
            ("position_sizing_in_scope", "P15"),
            ("risk_approval_in_scope", "P16"),
            ("execution_authority", "P20"),
        ):
            if raw.get(key) is not False:
                raise ScenarioEngineError(f"{key} must remain false; owned by {owner}")
        if raw.get("canonical_tests_network_required") is not False:
            raise ScenarioEngineError("canonical P13-G tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise ScenarioEngineError("P13-G cannot enable trading")

        return cls(
            scenario_kinds=kinds,
            actionable_expiry_state="ACTIVE",
            required_upstream_decision="TIMING_ELIGIBLE",
            blocked_expiry_states=blocked,
            scenario_probability_in_scope=False,
            confidence_score_in_scope=False,
            price_target_in_scope=False,
            position_sizing_in_scope=False,
            risk_approval_in_scope=False,
            execution_authority=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class ScenarioFrame:
    scenario_id: str
    candidate_id: str
    scenario_kind: str
    condition_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioSet:
    candidate_id: str
    state: str
    upstream_expiry_state: str
    frames: tuple[ScenarioFrame, ...]
    block_reason: str | None


_CONDITIONS: dict[str, tuple[str, ...]] = {
    "CONTINUATION": (
        "TIMING_CONTEXT_REMAINS_ELIGIBLE",
        "VALIDITY_WINDOW_REMAINS_ACTIVE",
        "CHASE_LIMIT_REMAINS_UNBREACHED",
    ),
    "DETERIORATION": (
        "TIMING_CONTEXT_WEAKENS_OR_DATA_DEGRADES",
    ),
    "INVALIDATION": (
        "NO_TRADE_VETO_OR_EXPIRY_OR_NO_CHASE_TRIGGERS",
    ),
}


def _scenario_id(candidate_id: str, kind: str, conditions: tuple[str, ...]) -> str:
    payload = {
        "candidate_id": candidate_id,
        "scenario_kind": kind,
        "condition_codes": list(conditions),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_scenarios(
    candidate: OpportunityCandidate,
    no_trade_decision: NoTradeDecision,
    expiry_assessment: ExpiryNoChaseAssessment,
    *,
    policy: ScenarioEnginePolicy,
) -> ScenarioSet:
    candidate_id = candidate.candidate_id
    if not candidate_id:
        raise ScenarioEngineError("candidate_id must be non-empty")
    if no_trade_decision.candidate_id != candidate_id:
        raise ScenarioEngineError("no-trade candidate identity mismatch")
    if expiry_assessment.candidate_id != candidate_id:
        raise ScenarioEngineError("expiry candidate identity mismatch")

    decision = no_trade_decision.decision
    expiry_state = expiry_assessment.state
    if decision == "TIMING_ELIGIBLE":
        if no_trade_decision.reason_codes:
            raise ScenarioEngineError("TIMING_ELIGIBLE cannot carry no-trade reasons")
        if not candidate.eligible:
            raise ScenarioEngineError("TIMING_ELIGIBLE requires eligible candidate")
        if expiry_state == "BLOCKED_BY_NO_TRADE":
            raise ScenarioEngineError("TIMING_ELIGIBLE cannot be BLOCKED_BY_NO_TRADE")
    elif decision == "NO_TRADE":
        if not no_trade_decision.reason_codes:
            raise ScenarioEngineError("NO_TRADE requires reason codes")
        if expiry_state != "BLOCKED_BY_NO_TRADE":
            raise ScenarioEngineError("NO_TRADE must map to BLOCKED_BY_NO_TRADE")
    else:
        raise ScenarioEngineError("unknown upstream no-trade decision")

    if expiry_state in policy.blocked_expiry_states:
        return ScenarioSet(
            candidate_id=candidate_id,
            state="NON_ACTIONABLE",
            upstream_expiry_state=expiry_state,
            frames=(),
            block_reason=expiry_state,
        )
    if expiry_state != policy.actionable_expiry_state:
        raise ScenarioEngineError("unknown expiry/no-chase state")
    if decision != policy.required_upstream_decision:
        raise ScenarioEngineError("ACTIVE scenario context requires TIMING_ELIGIBLE")

    frames = tuple(
        ScenarioFrame(
            scenario_id=_scenario_id(candidate_id, kind, _CONDITIONS[kind]),
            candidate_id=candidate_id,
            scenario_kind=kind,
            condition_codes=_CONDITIONS[kind],
        )
        for kind in policy.scenario_kinds
    )
    return ScenarioSet(
        candidate_id=candidate_id,
        state="CONDITIONAL_SCENARIOS",
        upstream_expiry_state=expiry_state,
        frames=frames,
        block_reason=None,
    )
