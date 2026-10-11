from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .classification import ClassificationResult
from .event_decay import EventDecayAssessment
from .ingestion import RawNewsItem
from .reliability import ReliabilityAssessment


class AlertNarrativeError(ValueError):
    """Raised when P11-G alert/narrative invariants fail closed."""


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AlertNarrativeError(f"{field} must be a non-empty list")
    items = tuple(str(item).strip().upper() for item in cast(list[object], value))
    if any(not item for item in items) or len(set(items)) != len(items):
        raise AlertNarrativeError(f"{field} must contain unique non-empty values")
    return items


@dataclass(frozen=True, slots=True)
class AlertNarrativePolicy:
    severities: tuple[str, ...]
    suppress_freshness_states: tuple[str, ...]
    suppress_review_states: tuple[str, ...]
    suppress_reliability_bands: tuple[str, ...]
    critical_importance: tuple[str, ...]
    critical_reliability: tuple[str, ...]
    critical_freshness: tuple[str, ...]
    important_importance: tuple[str, ...]
    important_reliability: tuple[str, ...]
    important_freshness: tuple[str, ...]
    grouping_schema: str
    canonical_tests_network_required: bool
    llm_narrative_required: bool
    channel_delivery_enabled: bool
    production_news_vendor: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "AlertNarrativePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise AlertNarrativeError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise AlertNarrativeError("unsupported alerting policy schema_version")

        severities = _string_tuple(raw.get("severities"), field="severities")
        if set(severities) != {"INFORMATIONAL", "IMPORTANT", "CRITICAL", "SUPPRESSED"}:
            raise AlertNarrativeError("unexpected alert severities")

        grouping_schema = str(raw.get("grouping_schema", "")).strip().upper()
        if not grouping_schema:
            raise AlertNarrativeError("grouping_schema must be non-empty")
        if raw.get("canonical_tests_network_required") is not False:
            raise AlertNarrativeError("canonical tests must remain offline")
        if raw.get("llm_narrative_required") is not False:
            raise AlertNarrativeError("canonical P11-G cannot require LLM narrative")
        if raw.get("channel_delivery_enabled") is not False:
            raise AlertNarrativeError("P11-G cannot enable notification channel delivery")
        if raw.get("production_news_vendor") != "NOT_SELECTED":
            raise AlertNarrativeError("P11-G cannot select production news vendor")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise AlertNarrativeError("P11-G cannot enable trading")

        return cls(
            severities=severities,
            suppress_freshness_states=_string_tuple(
                raw.get("suppress_freshness_states"), field="suppress_freshness_states"
            ),
            suppress_review_states=_string_tuple(
                raw.get("suppress_review_states"), field="suppress_review_states"
            ),
            suppress_reliability_bands=_string_tuple(
                raw.get("suppress_reliability_bands"), field="suppress_reliability_bands"
            ),
            critical_importance=_string_tuple(raw.get("critical_importance"), field="critical_importance"),
            critical_reliability=_string_tuple(raw.get("critical_reliability"), field="critical_reliability"),
            critical_freshness=_string_tuple(raw.get("critical_freshness"), field="critical_freshness"),
            important_importance=_string_tuple(raw.get("important_importance"), field="important_importance"),
            important_reliability=_string_tuple(raw.get("important_reliability"), field="important_reliability"),
            important_freshness=_string_tuple(raw.get("important_freshness"), field="important_freshness"),
            grouping_schema=grouping_schema,
            canonical_tests_network_required=False,
            llm_narrative_required=False,
            channel_delivery_enabled=False,
            production_news_vendor="NOT_SELECTED",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class AlertNarrativeInput:
    news_content_id: str
    source_id: str
    entity_ids: tuple[str, ...]
    topics: tuple[str, ...]
    sentiment: str
    importance: str
    reliability_band: str
    rumor_state: str
    review_state: str
    freshness_state: str
    decay_basis_points: int
    eligible: bool
    severity: str
    grouping_key: str
    reason_codes: tuple[str, ...]


def _grouping_key(
    *,
    policy: AlertNarrativePolicy,
    item: RawNewsItem,
    classification: ClassificationResult,
    severity: str,
) -> str:
    payload = {
        "schema": policy.grouping_schema,
        "source_id": item.source.source_id,
        "entity_ids": sorted(classification.entity_ids),
        "topics": sorted(classification.topics),
        "severity": severity,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_alert_narrative_input(
    item: RawNewsItem,
    *,
    classification: ClassificationResult,
    reliability: ReliabilityAssessment,
    decay: EventDecayAssessment,
    policy: AlertNarrativePolicy,
) -> AlertNarrativeInput:
    if classification.news_content_id != item.content_id:
        raise AlertNarrativeError("classification content identity mismatch")
    if reliability.news_content_id != item.content_id:
        raise AlertNarrativeError("reliability content identity mismatch")
    if decay.news_content_id != item.content_id:
        raise AlertNarrativeError("decay content identity mismatch")

    reasons: set[str] = {
        f"IMPORTANCE:{classification.importance}",
        f"RELIABILITY:{reliability.reliability_band}",
        f"RUMOR_STATE:{reliability.rumor_state}",
        f"REVIEW_STATE:{reliability.review_state}",
        f"FRESHNESS:{decay.freshness_state}",
    }

    suppressed = (
        decay.freshness_state in policy.suppress_freshness_states
        or reliability.review_state in policy.suppress_review_states
        or reliability.reliability_band in policy.suppress_reliability_bands
    )

    if suppressed:
        eligible = False
        severity = "SUPPRESSED"
        reasons.add("ALERT:SUPPRESSED")
    elif (
        classification.importance in policy.critical_importance
        and reliability.reliability_band in policy.critical_reliability
        and decay.freshness_state in policy.critical_freshness
    ):
        eligible = True
        severity = "CRITICAL"
        reasons.add("ALERT:CRITICAL")
    elif (
        classification.importance in policy.important_importance
        and reliability.reliability_band in policy.important_reliability
        and decay.freshness_state in policy.important_freshness
    ):
        eligible = True
        severity = "IMPORTANT"
        reasons.add("ALERT:IMPORTANT")
    else:
        eligible = True
        severity = "INFORMATIONAL"
        reasons.add("ALERT:INFORMATIONAL")

    if severity not in policy.severities:
        raise AlertNarrativeError("derived severity is not allowed")

    group_key = _grouping_key(
        policy=policy,
        item=item,
        classification=classification,
        severity=severity,
    )
    reasons.add(f"GROUPING_SCHEMA:{policy.grouping_schema}")

    return AlertNarrativeInput(
        news_content_id=item.content_id,
        source_id=item.source.source_id,
        entity_ids=tuple(sorted(classification.entity_ids)),
        topics=tuple(sorted(classification.topics)),
        sentiment=classification.sentiment,
        importance=classification.importance,
        reliability_band=reliability.reliability_band,
        rumor_state=reliability.rumor_state,
        review_state=reliability.review_state,
        freshness_state=decay.freshness_state,
        decay_basis_points=decay.decay_basis_points,
        eligible=eligible,
        severity=severity,
        grouping_key=group_key,
        reason_codes=tuple(sorted(reasons)),
    )
