from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Mapping, cast

from .entity_mapping import MappingResult
from .ingestion import RawNewsItem


class NewsClassificationError(ValueError):
    """Raised when P11-D classification invariants fail closed."""


def _norm(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<!\\w)" + re.escape(term) + r"(?!\\w)"
    return re.search(pattern, text, flags=re.UNICODE) is not None


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise NewsClassificationError(f"{field} must be a non-empty list")
    normalized = tuple(_norm(str(item)) for item in cast(list[object], value))
    if any(not item for item in normalized) or len(set(normalized)) != len(normalized):
        raise NewsClassificationError(f"{field} must contain unique non-empty values")
    return normalized


@dataclass(frozen=True, slots=True)
class ClassificationPolicy:
    topic_rules: tuple[tuple[str, tuple[str, ...]], ...]
    positive_terms: tuple[str, ...]
    negative_terms: tuple[str, ...]
    high_importance_terms: tuple[str, ...]
    medium_importance_terms: tuple[str, ...]
    sentiment_labels: tuple[str, ...]
    importance_bands: tuple[str, ...]
    fallback_topic: str
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ClassificationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise NewsClassificationError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise NewsClassificationError("unsupported classification policy schema_version")

        topic_value = raw.get("topic_rules")
        if not isinstance(topic_value, Mapping) or not topic_value:
            raise NewsClassificationError("topic_rules must be a non-empty object")
        topic_map = cast(Mapping[object, object], topic_value)
        topic_rules: list[tuple[str, tuple[str, ...]]] = []
        for topic_value_raw, terms_value in topic_map.items():
            topic = str(topic_value_raw).strip().upper()
            if not topic:
                raise NewsClassificationError("topic name must be non-empty")
            topic_rules.append((topic, _string_tuple(terms_value, field=f"topic_rules.{topic}")))
        topic_rules.sort(key=lambda item: item[0])

        positive = _string_tuple(raw.get("positive_terms"), field="positive_terms")
        negative = _string_tuple(raw.get("negative_terms"), field="negative_terms")
        high = _string_tuple(raw.get("high_importance_terms"), field="high_importance_terms")
        medium = _string_tuple(raw.get("medium_importance_terms"), field="medium_importance_terms")

        labels_value = raw.get("sentiment_labels")
        bands_value = raw.get("importance_bands")
        if not isinstance(labels_value, list) or not isinstance(bands_value, list):
            raise NewsClassificationError("sentiment_labels and importance_bands must be lists")
        labels = tuple(str(value).strip().upper() for value in cast(list[object], labels_value))
        bands = tuple(str(value).strip().upper() for value in cast(list[object], bands_value))
        if set(labels) != {"POSITIVE", "NEGATIVE", "MIXED", "NEUTRAL"}:
            raise NewsClassificationError("unexpected sentiment labels")
        if set(bands) != {"HIGH", "MEDIUM", "LOW"}:
            raise NewsClassificationError("unexpected importance bands")

        fallback = str(raw.get("fallback_topic", "")).strip().upper()
        if not fallback:
            raise NewsClassificationError("fallback_topic must be non-empty")
        if raw.get("canonical_tests_network_required") is not False:
            raise NewsClassificationError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise NewsClassificationError("classification policy cannot enable trading")

        return cls(
            topic_rules=tuple(topic_rules),
            positive_terms=positive,
            negative_terms=negative,
            high_importance_terms=high,
            medium_importance_terms=medium,
            sentiment_labels=labels,
            importance_bands=bands,
            fallback_topic=fallback,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    news_content_id: str
    entity_ids: tuple[str, ...]
    topics: tuple[str, ...]
    sentiment: str
    importance: str
    evidence_terms: tuple[str, ...]
    reason_codes: tuple[str, ...]


def _matched_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(term for term in terms if _contains_term(text, term)))


def classify_news_item(
    item: RawNewsItem,
    *,
    mapping: MappingResult,
    policy: ClassificationPolicy,
) -> ClassificationResult:
    if mapping.news_content_id != item.content_id:
        raise NewsClassificationError("mapping content identity mismatch")
    if mapping.state not in {"MAPPED", "NONE"}:
        raise NewsClassificationError("unsupported mapping state")

    text = _norm(f"{item.normalized_title} {item.normalized_body}")

    topic_hits: list[str] = []
    evidence: set[str] = set()
    reasons: set[str] = set()
    for topic, terms in policy.topic_rules:
        matched = _matched_terms(text, terms)
        if matched:
            topic_hits.append(topic)
            evidence.update(matched)
            reasons.add(f"TOPIC:{topic}")
    topics = tuple(sorted(topic_hits)) if topic_hits else (policy.fallback_topic,)
    if not topic_hits:
        reasons.add("TOPIC:FALLBACK")

    positive = _matched_terms(text, policy.positive_terms)
    negative = _matched_terms(text, policy.negative_terms)
    evidence.update(positive)
    evidence.update(negative)
    if positive and negative:
        sentiment = "MIXED"
    elif positive:
        sentiment = "POSITIVE"
    elif negative:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    reasons.add(f"SENTIMENT:{sentiment}")

    high = _matched_terms(text, policy.high_importance_terms)
    medium = _matched_terms(text, policy.medium_importance_terms)
    evidence.update(high)
    evidence.update(medium)
    entity_count = len(mapping.matches)
    if high:
        importance = "HIGH"
        reasons.add("IMPORTANCE:HIGH_TERM")
    elif medium or entity_count >= 2:
        importance = "MEDIUM"
        reasons.add("IMPORTANCE:MEDIUM_TERM_OR_MULTI_ENTITY")
    else:
        importance = "LOW"
        reasons.add("IMPORTANCE:LOW_BASELINE")

    entity_ids = tuple(sorted(match.entity_id for match in mapping.matches))
    return ClassificationResult(
        news_content_id=item.content_id,
        entity_ids=entity_ids,
        topics=topics,
        sentiment=sentiment,
        importance=importance,
        evidence_terms=tuple(sorted(evidence)),
        reason_codes=tuple(sorted(reasons)),
    )
