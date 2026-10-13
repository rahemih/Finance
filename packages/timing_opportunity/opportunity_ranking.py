from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .opportunity_scanner import OpportunityCandidate


class OpportunityRankingError(ValueError):
    """P13-D ranking input or policy violates governed invariants."""


@dataclass(frozen=True, slots=True)
class OpportunityRankingPolicy:
    rankable_scanner_state: str
    timing_class_priority: tuple[str, ...]
    ranking_key: tuple[str, ...]
    exclude_non_eligible: bool
    ranking_is_probability: bool
    hard_no_trade_authority: bool
    signal_expiry_in_scope: bool
    signal_probability_in_scope: bool
    risk_approval_in_scope: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "OpportunityRankingPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise OpportunityRankingError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_ORDINAL_OPPORTUNITY_RANKING":
            raise OpportunityRankingError("unsupported P13-D policy")
        if raw.get("rankable_scanner_state") != "ELIGIBLE_TIMING_CONTEXT":
            raise OpportunityRankingError("unexpected rankable scanner state")

        priority_value = raw.get("timing_class_priority")
        if not isinstance(priority_value, list):
            raise OpportunityRankingError("timing_class_priority must be list")
        priority = tuple(str(item).strip().upper() for item in cast(list[object], priority_value))
        if priority != ("PREFERRED", "STANDARD"):
            raise OpportunityRankingError("unexpected timing class priority")

        key_value = raw.get("ranking_key")
        if not isinstance(key_value, list):
            raise OpportunityRankingError("ranking_key must be list")
        ranking_key = tuple(str(item).strip().upper() for item in cast(list[object], key_value))
        expected_key = ("TIMING_CLASS_PRIORITY", "ADJUSTED_EDGE_DESC", "SAMPLE_COUNT_DESC", "CANDIDATE_ID_ASC")
        if ranking_key != expected_key:
            raise OpportunityRankingError("unexpected ranking key")

        if raw.get("exclude_non_eligible") is not True:
            raise OpportunityRankingError("non-eligible candidates must be excluded from ranking")
        for key, owner in (
            ("ranking_is_probability", "P14"),
            ("hard_no_trade_authority", "P13-E"),
            ("signal_expiry_in_scope", "P13-F"),
            ("signal_probability_in_scope", "P14"),
            ("risk_approval_in_scope", "P15/P16"),
        ):
            if raw.get(key) is not False:
                raise OpportunityRankingError(f"{key} must remain false; owned by {owner}")
        if raw.get("canonical_tests_network_required") is not False:
            raise OpportunityRankingError("canonical P13-D tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise OpportunityRankingError("P13-D cannot enable trading")

        return cls(
            rankable_scanner_state="ELIGIBLE_TIMING_CONTEXT",
            timing_class_priority=priority,
            ranking_key=ranking_key,
            exclude_non_eligible=True,
            ranking_is_probability=False,
            hard_no_trade_authority=False,
            signal_expiry_in_scope=False,
            signal_probability_in_scope=False,
            risk_approval_in_scope=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class RankedOpportunity:
    rank_position: int
    candidate: OpportunityCandidate


@dataclass(frozen=True, slots=True)
class OpportunityRankingResult:
    ranked: tuple[RankedOpportunity, ...]
    excluded_candidate_ids: tuple[str, ...]


def rank_opportunities(
    candidates: Sequence[OpportunityCandidate],
    *,
    policy: OpportunityRankingPolicy,
) -> OpportunityRankingResult:
    if not candidates:
        raise OpportunityRankingError("ranking input must be non-empty")
    ids = [item.candidate_id for item in candidates]
    if len(ids) != len(set(ids)):
        raise OpportunityRankingError("duplicate candidate_id")

    priority = {name: index for index, name in enumerate(policy.timing_class_priority)}
    rankable: list[OpportunityCandidate] = []
    excluded: list[str] = []
    for item in candidates:
        if item.scanner_state == policy.rankable_scanner_state:
            if not item.eligible:
                raise OpportunityRankingError("rankable scanner state requires eligible candidate")
            if item.timing_class not in priority:
                raise OpportunityRankingError("rankable candidate has unsupported timing class")
            rankable.append(item)
        else:
            if item.eligible:
                raise OpportunityRankingError("eligible candidate must use rankable scanner state")
            excluded.append(item.candidate_id)

    ordered = sorted(
        rankable,
        key=lambda item: (
            priority[item.timing_class],
            -item.adjusted_edge_bps,
            -item.sample_count,
            item.candidate_id,
        ),
    )
    ranked = tuple(
        RankedOpportunity(rank_position=index + 1, candidate=item)
        for index, item in enumerate(ordered)
    )
    return OpportunityRankingResult(
        ranked=ranked,
        excluded_candidate_ids=tuple(sorted(excluded)),
    )
