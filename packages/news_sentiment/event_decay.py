from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Mapping, cast

from .classification import ClassificationResult
from .ingestion import RawNewsItem
from .reliability import ReliabilityAssessment


class EventDecayError(ValueError):
    """Raised when P11-F event-horizon/decay invariants fail closed."""


def _instant(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventDecayError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise EventDecayError(f"{field} must include timezone")
    return parsed


def _int_map(value: object, *, field: str, allow_zero: bool = False) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, Mapping) or not value:
        raise EventDecayError(f"{field} must be a non-empty object")
    items: list[tuple[str, int]] = []
    for key, raw_value in cast(Mapping[object, object], value).items():
        if not isinstance(raw_value, int) or isinstance(raw_value, bool):
            raise EventDecayError(f"{field} values must be integers")
        if raw_value < 0 or (raw_value == 0 and not allow_zero):
            raise EventDecayError(f"{field} values must be positive")
        normalized_key = str(key).strip().upper()
        if not normalized_key:
            raise EventDecayError(f"{field} keys must be non-empty")
        items.append((normalized_key, raw_value))
    if len({key for key, _ in items}) != len(items):
        raise EventDecayError(f"{field} keys must be unique")
    return tuple(sorted(items))


@dataclass(frozen=True, slots=True)
class EventDecayPolicy:
    importance_horizon_minutes: tuple[tuple[str, int], ...]
    topic_minimum_horizon_minutes: tuple[tuple[str, int], ...]
    reliability_multiplier_bps: tuple[tuple[str, int], ...]
    fresh_threshold_bps: int
    freshness_states: tuple[str, ...]
    canonical_tests_network_required: bool
    production_news_vendor: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "EventDecayPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise EventDecayError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise EventDecayError("unsupported event decay policy schema_version")

        importance = _int_map(raw.get("importance_horizon_minutes"), field="importance_horizon_minutes")
        topic = _int_map(raw.get("topic_minimum_horizon_minutes"), field="topic_minimum_horizon_minutes")
        reliability = _int_map(
            raw.get("reliability_multiplier_bps"),
            field="reliability_multiplier_bps",
            allow_zero=True,
        )
        if {key for key, _ in importance} != {"HIGH", "MEDIUM", "LOW"}:
            raise EventDecayError("unexpected importance horizon keys")
        if {key for key, _ in reliability} != {"HIGH", "MEDIUM", "LOW", "BLOCKED"}:
            raise EventDecayError("unexpected reliability multiplier keys")
        if dict(reliability)["BLOCKED"] != 0:
            raise EventDecayError("BLOCKED reliability multiplier must be zero")
        if any(value > 10000 for _, value in reliability):
            raise EventDecayError("reliability multiplier cannot exceed 10000 bps")

        threshold = raw.get("fresh_threshold_bps")
        if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 < threshold <= 10000:
            raise EventDecayError("fresh_threshold_bps must be integer in (0,10000]")

        states_value = raw.get("freshness_states")
        if not isinstance(states_value, list):
            raise EventDecayError("freshness_states must be a list")
        states = tuple(str(value).strip().upper() for value in cast(list[object], states_value))
        if set(states) != {"FRESH", "DECAYING", "EXPIRED", "BLOCKED"}:
            raise EventDecayError("unexpected freshness states")

        if raw.get("canonical_tests_network_required") is not False:
            raise EventDecayError("canonical tests must remain offline")
        if raw.get("production_news_vendor") != "NOT_SELECTED":
            raise EventDecayError("P11-F cannot select production news vendor")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise EventDecayError("P11-F cannot enable trading")

        return cls(
            importance_horizon_minutes=importance,
            topic_minimum_horizon_minutes=topic,
            reliability_multiplier_bps=reliability,
            fresh_threshold_bps=threshold,
            freshness_states=states,
            canonical_tests_network_required=False,
            production_news_vendor="NOT_SELECTED",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    def importance_horizon(self, importance: str) -> int:
        try:
            return dict(self.importance_horizon_minutes)[importance]
        except KeyError as exc:
            raise EventDecayError("importance has no horizon") from exc

    def topic_minimum_horizon(self, topic: str) -> int:
        try:
            return dict(self.topic_minimum_horizon_minutes)[topic]
        except KeyError as exc:
            raise EventDecayError("topic has no minimum horizon") from exc

    def reliability_multiplier(self, reliability_band: str) -> int:
        try:
            return dict(self.reliability_multiplier_bps)[reliability_band]
        except KeyError as exc:
            raise EventDecayError("reliability band has no horizon multiplier") from exc


@dataclass(frozen=True, slots=True)
class EventDecayAssessment:
    news_content_id: str
    observed_at: str
    as_of: str
    base_horizon_minutes: int
    topic_minimum_horizon_minutes: int
    effective_horizon_minutes: int
    age_seconds: int
    decay_basis_points: int
    freshness_state: str
    reason_codes: tuple[str, ...]


def assess_event_decay(
    item: RawNewsItem,
    *,
    classification: ClassificationResult,
    reliability: ReliabilityAssessment,
    policy: EventDecayPolicy,
    as_of: str,
) -> EventDecayAssessment:
    if classification.news_content_id != item.content_id:
        raise EventDecayError("classification content identity mismatch")
    if reliability.news_content_id != item.content_id:
        raise EventDecayError("reliability content identity mismatch")

    observed = _instant(item.source.observed_at, field="observed_at")
    evaluation = _instant(as_of, field="as_of")
    if evaluation < observed:
        raise EventDecayError("as_of cannot be before observed_at")
    age_seconds = int((evaluation - observed).total_seconds())

    reasons: set[str] = {
        f"IMPORTANCE:{classification.importance}",
        f"RELIABILITY:{reliability.reliability_band}",
        f"REVIEW_STATE:{reliability.review_state}",
    }

    base_horizon = policy.importance_horizon(classification.importance)
    topic_horizons = tuple(policy.topic_minimum_horizon(topic) for topic in classification.topics)
    topic_minimum = max(topic_horizons)

    if reliability.reliability_band == "BLOCKED" or reliability.review_state == "QUARANTINED":
        reasons.add("FAIL_CLOSED:RELIABILITY_BLOCK")
        return EventDecayAssessment(
            news_content_id=item.content_id,
            observed_at=item.source.observed_at,
            as_of=as_of,
            base_horizon_minutes=base_horizon,
            topic_minimum_horizon_minutes=topic_minimum,
            effective_horizon_minutes=0,
            age_seconds=age_seconds,
            decay_basis_points=0,
            freshness_state="BLOCKED",
            reason_codes=tuple(sorted(reasons)),
        )

    pre_reliability_horizon = max(base_horizon, topic_minimum)
    multiplier = policy.reliability_multiplier(reliability.reliability_band)
    effective_horizon = max(1, (pre_reliability_horizon * multiplier) // 10000)
    horizon_seconds = effective_horizon * 60

    reasons.add(f"BASE_HORIZON_MINUTES:{base_horizon}")
    reasons.add(f"TOPIC_MINIMUM_MINUTES:{topic_minimum}")
    reasons.add(f"RELIABILITY_MULTIPLIER_BPS:{multiplier}")
    reasons.add(f"EFFECTIVE_HORIZON_MINUTES:{effective_horizon}")

    if age_seconds >= horizon_seconds:
        freshness_state = "EXPIRED"
        decay_basis_points = 0
    else:
        remaining_seconds = horizon_seconds - age_seconds
        decay_basis_points = (remaining_seconds * 10000) // horizon_seconds
        decay_basis_points = max(1, min(10000, decay_basis_points))
        freshness_state = "FRESH" if decay_basis_points >= policy.fresh_threshold_bps else "DECAYING"

    reasons.add(f"FRESHNESS:{freshness_state}")
    return EventDecayAssessment(
        news_content_id=item.content_id,
        observed_at=item.source.observed_at,
        as_of=as_of,
        base_horizon_minutes=base_horizon,
        topic_minimum_horizon_minutes=topic_minimum,
        effective_horizon_minutes=effective_horizon,
        age_seconds=age_seconds,
        decay_basis_points=decay_basis_points,
        freshness_state=freshness_state,
        reason_codes=tuple(sorted(reasons)),
    )
