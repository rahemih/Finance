from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Sequence


class CounterpartyCapitalError(ValueError):
    """P15-G counterparty/capital allocation input violates governed invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CounterpartyRule:
    counterparty_id: str
    max_allocation_bps: int

    def __post_init__(self) -> None:
        if not self.counterparty_id.strip():
            raise CounterpartyCapitalError("counterparty_id must be non-empty")
        if not 0 <= self.max_allocation_bps <= 10_000:
            raise CounterpartyCapitalError(
                "counterparty max_allocation_bps must be within [0, 10000]"
            )


@dataclass(frozen=True)
class CapitalSegmentRule:
    segment_id: str
    max_allocation_bps: int

    def __post_init__(self) -> None:
        if not self.segment_id.strip():
            raise CounterpartyCapitalError("segment_id must be non-empty")
        if not 0 <= self.max_allocation_bps <= 10_000:
            raise CounterpartyCapitalError(
                "segment max_allocation_bps must be within [0, 10000]"
            )


@dataclass(frozen=True)
class CounterpartyCapitalPolicy:
    policy_version: str
    counterparties: tuple[CounterpartyRule, ...]
    segments: tuple[CapitalSegmentRule, ...]
    policy_id: str

    @classmethod
    def build(
        cls,
        *,
        policy_version: str,
        counterparties: Sequence[CounterpartyRule],
        segments: Sequence[CapitalSegmentRule],
    ) -> "CounterpartyCapitalPolicy":
        if not policy_version.strip():
            raise CounterpartyCapitalError("policy_version must be non-empty")
        ordered_counterparties = tuple(
            sorted(counterparties, key=lambda item: item.counterparty_id)
        )
        ordered_segments = tuple(sorted(segments, key=lambda item: item.segment_id))
        if not ordered_counterparties:
            raise CounterpartyCapitalError("at least one counterparty rule is required")
        if not ordered_segments:
            raise CounterpartyCapitalError("at least one capital segment is required")
        if len({item.counterparty_id for item in ordered_counterparties}) != len(
            ordered_counterparties
        ):
            raise CounterpartyCapitalError("duplicate counterparty rule")
        if len({item.segment_id for item in ordered_segments}) != len(ordered_segments):
            raise CounterpartyCapitalError("duplicate capital segment rule")
        payload = {
            "policy_version": policy_version,
            "counterparties": [
                {
                    "counterparty_id": item.counterparty_id,
                    "max_allocation_bps": item.max_allocation_bps,
                }
                for item in ordered_counterparties
            ],
            "segments": [
                {
                    "segment_id": item.segment_id,
                    "max_allocation_bps": item.max_allocation_bps,
                }
                for item in ordered_segments
            ],
        }
        return cls(
            policy_version=policy_version,
            counterparties=ordered_counterparties,
            segments=ordered_segments,
            policy_id=_sha256(payload),
        )


@dataclass(frozen=True)
class CounterpartyCapitalRequest:
    request_id: str
    upstream_drawdown_decision_id: str
    upstream_drawdown_status: str
    counterparty_id: str
    segment_id: str
    current_total_allocated_bps: int
    current_counterparty_allocated_bps: int
    current_segment_allocated_bps: int
    candidate_allocation_bps: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise CounterpartyCapitalError("request_id must be non-empty")
        if not self.upstream_drawdown_decision_id.strip():
            raise CounterpartyCapitalError(
                "upstream_drawdown_decision_id must be non-empty"
            )
        if not self.counterparty_id.strip():
            raise CounterpartyCapitalError("counterparty_id must be non-empty")
        if not self.segment_id.strip():
            raise CounterpartyCapitalError("segment_id must be non-empty")
        for field, value in (
            ("current_total_allocated_bps", self.current_total_allocated_bps),
            (
                "current_counterparty_allocated_bps",
                self.current_counterparty_allocated_bps,
            ),
            ("current_segment_allocated_bps", self.current_segment_allocated_bps),
        ):
            if not 0 <= value <= 10_000:
                raise CounterpartyCapitalError(f"{field} must be within [0, 10000]")
        if not 1 <= self.candidate_allocation_bps <= 10_000:
            raise CounterpartyCapitalError(
                "candidate_allocation_bps must be within [1, 10000]"
            )
        if self.as_of_ns < 0:
            raise CounterpartyCapitalError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class CounterpartyCapitalDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    total_after_bps: int
    counterparty_after_bps: int
    segment_after_bps: int
    upstream_drawdown_status: str
    venue_routing_authority: bool = False
    execution_authority: bool = False


def evaluate_counterparty_capital(
    *,
    policy: CounterpartyCapitalPolicy,
    request: CounterpartyCapitalRequest,
) -> CounterpartyCapitalDecision:
    counterparty_rules = {
        item.counterparty_id: item for item in policy.counterparties
    }
    segment_rules = {item.segment_id: item for item in policy.segments}
    counterparty = counterparty_rules.get(request.counterparty_id)
    segment = segment_rules.get(request.segment_id)
    if counterparty is None:
        raise CounterpartyCapitalError("missing counterparty rule")
    if segment is None:
        raise CounterpartyCapitalError("missing capital segment rule")

    total_after = request.current_total_allocated_bps + request.candidate_allocation_bps
    counterparty_after = (
        request.current_counterparty_allocated_bps + request.candidate_allocation_bps
    )
    segment_after = (
        request.current_segment_allocated_bps + request.candidate_allocation_bps
    )

    reasons: list[str] = []
    if request.upstream_drawdown_status == "VETO":
        reasons.append("UPSTREAM_DRAWDOWN_RUIN_VETO")
    elif request.upstream_drawdown_status not in {
        "WITHIN_LIMITS",
        "DE_RISK_REQUIRED",
    }:
        reasons.append("UNKNOWN_UPSTREAM_DRAWDOWN_STATE")
    if total_after > 10_000:
        reasons.append("TOTAL_CAPITAL_ALLOCATION_EXCEEDED")
    if counterparty_after > counterparty.max_allocation_bps:
        reasons.append("COUNTERPARTY_ALLOCATION_LIMIT_EXCEEDED")
    if segment_after > segment.max_allocation_bps:
        reasons.append("CAPITAL_SEGMENT_LIMIT_EXCEEDED")

    status = "VETO" if reasons else "CAPITAL_SEGMENT_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_drawdown_decision_id": request.upstream_drawdown_decision_id,
        "upstream_drawdown_status": request.upstream_drawdown_status,
        "counterparty_id": request.counterparty_id,
        "segment_id": request.segment_id,
        "current_total_allocated_bps": request.current_total_allocated_bps,
        "current_counterparty_allocated_bps": request.current_counterparty_allocated_bps,
        "current_segment_allocated_bps": request.current_segment_allocated_bps,
        "candidate_allocation_bps": request.candidate_allocation_bps,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "total_after_bps": total_after,
        "counterparty_after_bps": counterparty_after,
        "segment_after_bps": segment_after,
        "venue_routing_authority": False,
        "execution_authority": False,
    }
    return CounterpartyCapitalDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        total_after_bps=total_after,
        counterparty_after_bps=counterparty_after,
        segment_after_bps=segment_after,
        upstream_drawdown_status=request.upstream_drawdown_status,
    )
