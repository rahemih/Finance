from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Mapping, cast

from .source_policy import NewsSourcePolicy, NewsSourceRecord, validate_source_record


class NewsIngestionError(ValueError):
    """Raised when P11-B ingestion/dedup invariants fail closed."""


def _instant(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NewsIngestionError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise NewsIngestionError(f"{field} must include timezone")
    return parsed


def _normalize_text(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NewsIngestionError("news text must be non-empty")
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split())


def _fingerprint_tokens(value: str) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKC", value).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    tokens = tuple(token for token in text.split() if token)
    return tuple(sorted(tokens))


def _digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class IngestionPolicy:
    ngram_size: int
    min_shared_ratio: float
    canonical_tests_network_required: bool
    production_news_vendor: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "IngestionPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise NewsIngestionError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise NewsIngestionError("unsupported ingestion policy schema_version")
        near_value = raw.get("near_duplicate")
        if not isinstance(near_value, Mapping):
            raise NewsIngestionError("near_duplicate must be an object")
        near = cast(Mapping[str, object], near_value)
        ngram = near.get("token_ngram_size")
        ratio = near.get("min_shared_ratio")
        network = raw.get("canonical_tests_network_required")
        vendor = raw.get("production_news_vendor")
        live = raw.get("live_trading")
        auto = raw.get("auto_trading")
        if not isinstance(ngram, int) or ngram < 1:
            raise NewsIngestionError("token_ngram_size must be positive integer")
        if not isinstance(ratio, (int, float)) or not 0.0 < float(ratio) <= 1.0:
            raise NewsIngestionError("min_shared_ratio must be in (0,1]")
        if network is not False:
            raise NewsIngestionError("canonical tests must remain offline")
        if vendor != "NOT_SELECTED":
            raise NewsIngestionError("P11-B cannot select a production vendor")
        if live != "DISABLED" or auto != "DISABLED":
            raise NewsIngestionError("P11-B cannot enable trading")
        return cls(
            ngram_size=ngram,
            min_shared_ratio=float(ratio),
            canonical_tests_network_required=False,
            production_news_vendor="NOT_SELECTED",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class RawNewsItem:
    source: NewsSourceRecord
    title: str
    body: str

    @property
    def normalized_title(self) -> str:
        return _normalize_text(self.title)

    @property
    def normalized_body(self) -> str:
        return _normalize_text(self.body)

    @property
    def content_id(self) -> str:
        return _digest({
            "source_id": self.source.source_id,
            "published_at": self.source.published_at,
            "normalized_title": self.normalized_title,
            "normalized_body": self.normalized_body,
        })

    @property
    def fingerprint_id(self) -> str:
        return _digest({
            "tokens": _fingerprint_tokens(f"{self.normalized_title} {self.normalized_body}"),
        })


def validate_raw_news_item(
    item: RawNewsItem,
    *,
    source_policy: NewsSourcePolicy,
) -> None:
    validate_source_record(item.source, policy=source_policy)
    _normalize_text(item.title)
    _normalize_text(item.body)
    if _instant(item.source.published_at, field="published_at") > _instant(
        item.source.observed_at,
        field="observed_at",
    ):
        raise NewsIngestionError("published_at cannot be after observed_at")


@dataclass(frozen=True, slots=True)
class DedupGroup:
    content_ids: tuple[str, ...]
    fingerprint_ids: tuple[str, ...]

    @property
    def group_id(self) -> str:
        return _digest({
            "content_ids": sorted(self.content_ids),
            "fingerprint_ids": sorted(self.fingerprint_ids),
        })


def exact_duplicate(left: RawNewsItem, right: RawNewsItem) -> bool:
    return left.content_id == right.content_id


def near_duplicate_ratio(left: RawNewsItem, right: RawNewsItem) -> float:
    left_tokens = set(_fingerprint_tokens(f"{left.normalized_title} {left.normalized_body}"))
    right_tokens = set(_fingerprint_tokens(f"{right.normalized_title} {right.normalized_body}"))
    if not left_tokens or not right_tokens:
        return 0.0
    shared = len(left_tokens & right_tokens)
    return shared / max(len(left_tokens), len(right_tokens))


def near_duplicate(left: RawNewsItem, right: RawNewsItem, *, policy: IngestionPolicy) -> bool:
    return near_duplicate_ratio(left, right) >= policy.min_shared_ratio


def build_dedup_group(items: tuple[RawNewsItem, ...]) -> DedupGroup:
    if not items:
        raise NewsIngestionError("dedup group requires at least one item")
    return DedupGroup(
        content_ids=tuple(sorted(item.content_id for item in items)),
        fingerprint_ids=tuple(sorted(item.fingerprint_id for item in items)),
    )
