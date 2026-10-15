from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Sequence

from packages.data_quality.quality_slo import SloStatus
from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent
from packages.market_data.recovery import RecoveryState
from packages.market_data.streaming import StreamHealth


class PreTradeHealthError(ValueError):
    """P16-E event/data/broker/system health input violates firewall invariants."""


SYSTEM_STATES = {
    "NORMAL",
    "DEGRADED",
    "SAFE_MODE",
    "HALTED",
    "EMERGENCY",
    "RECOVERY",
}


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PreTradeHealthPolicy:
    policy_version: str
    event_block_before_ns: int
    event_block_after_ns: int
    max_event_observation_age_ns: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise PreTradeHealthError("policy_version must be non-empty")
        for field, value in (
            ("event_block_before_ns", self.event_block_before_ns),
            ("event_block_after_ns", self.event_block_after_ns),
            ("max_event_observation_age_ns", self.max_event_observation_age_ns),
        ):
            if value < 0:
                raise PreTradeHealthError(f"{field} must be non-negative")

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "event_block_before_ns": self.event_block_before_ns,
                "event_block_after_ns": self.event_block_after_ns,
                "max_event_observation_age_ns": self.max_event_observation_age_ns,
            }
        )


@dataclass(frozen=True)
class PreTradeHealthRequest:
    request_id: str
    upstream_liquidity_decision_id: str
    upstream_liquidity_status: str
    economic_events: tuple[EconomicCalendarEvent, ...]
    data_slo_status: SloStatus
    stream_health: StreamHealth
    recovery_state: RecoveryState
    system_state: str
    as_of_ns: int

    @classmethod
    def build(
        cls,
        *,
        request_id: str,
        upstream_liquidity_decision_id: str,
        upstream_liquidity_status: str,
        economic_events: Sequence[EconomicCalendarEvent],
        data_slo_status: SloStatus,
        stream_health: StreamHealth,
        recovery_state: RecoveryState,
        system_state: str,
        as_of_ns: int,
    ) -> "PreTradeHealthRequest":
        return cls(
            request_id=request_id,
            upstream_liquidity_decision_id=upstream_liquidity_decision_id,
            upstream_liquidity_status=upstream_liquidity_status,
            economic_events=tuple(
                sorted(
                    economic_events,
                    key=lambda item: (
                        item.scheduled_release_time_ns,
                        item.source_id,
                        item.source_event_id,
                    ),
                )
            ),
            data_slo_status=data_slo_status,
            stream_health=stream_health,
            recovery_state=recovery_state,
            system_state=system_state,
            as_of_ns=as_of_ns,
        )

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PreTradeHealthError("request_id must be non-empty")
        if not self.upstream_liquidity_decision_id.strip():
            raise PreTradeHealthError(
                "upstream_liquidity_decision_id must be non-empty"
            )
        if self.upstream_liquidity_status not in {"PRETRADE_D_ELIGIBLE", "VETO"}:
            raise PreTradeHealthError("unknown upstream_liquidity_status")
        if self.system_state not in SYSTEM_STATES:
            raise PreTradeHealthError("unknown system_state")
        if self.as_of_ns < 0:
            raise PreTradeHealthError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class PreTradeHealthDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    blocking_event_ids: tuple[str, ...]
    g8_authority: bool = False
    execution_authority: bool = False


def _effective_event_time(event: EconomicCalendarEvent) -> int:
    if event.status == "RELEASED" and event.actual_release_time_ns is not None:
        return event.actual_release_time_ns
    return event.scheduled_release_time_ns


def evaluate_pretrade_health(
    *,
    policy: PreTradeHealthPolicy,
    request: PreTradeHealthRequest,
) -> PreTradeHealthDecision:
    reasons: set[str] = set()
    blocking_event_ids: list[str] = []

    if request.upstream_liquidity_status == "VETO":
        reasons.add("UPSTREAM_LIQUIDITY_CAPACITY_VETO")

    for event in request.economic_events:
        if event.observed_at_ns > request.as_of_ns:
            reasons.add("FUTURE_EVENT_OBSERVATION")
            continue
        observation_age = request.as_of_ns - event.observed_at_ns
        if observation_age > policy.max_event_observation_age_ns:
            reasons.add("STALE_EVENT_OBSERVATION")
        if event.status == "CANCELLED":
            continue

        event_time = _effective_event_time(event)
        window_start = max(0, event_time - policy.event_block_before_ns)
        window_end = event_time + policy.event_block_after_ns
        if window_start <= request.as_of_ns <= window_end:
            reasons.add("EVENT_RISK_WINDOW_BLOCKED")
            blocking_event_ids.append(event.event_id)

    if request.data_slo_status is not SloStatus.HEALTHY:
        reasons.add(f"DATA_HEALTH_{request.data_slo_status.value}")
    if request.stream_health is not StreamHealth.HEALTHY:
        reasons.add(f"BROKER_STREAM_{request.stream_health.value}")
    if request.recovery_state is not RecoveryState.ACTIVE:
        reasons.add(f"BROKER_RECOVERY_{request.recovery_state.value}")
    if request.system_state != "NORMAL":
        reasons.add(f"SYSTEM_STATE_{request.system_state}")

    reason_codes = tuple(sorted(reasons))
    blocking = tuple(sorted(blocking_event_ids))
    status = "VETO" if reason_codes else "PRETRADE_E_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_liquidity_decision_id": request.upstream_liquidity_decision_id,
        "upstream_liquidity_status": request.upstream_liquidity_status,
        "event_ids": [item.event_id for item in request.economic_events],
        "data_slo_status": request.data_slo_status.value,
        "stream_health": request.stream_health.value,
        "recovery_state": request.recovery_state.value,
        "system_state": request.system_state,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reason_codes,
        "blocking_event_ids": blocking,
        "g8_authority": False,
        "execution_authority": False,
    }
    return PreTradeHealthDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=reason_codes,
        blocking_event_ids=blocking,
    )
