from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast
from urllib.parse import urlparse


class NewsSourcePolicyError(ValueError):
    """Raised when P11-A source/license invariants fail closed."""


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NewsSourcePolicyError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise NewsSourcePolicyError(f"{field} must be boolean")
    return value


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise NewsSourcePolicyError(f"{field} must be a non-empty list")
    values = cast(list[object], value)
    items = tuple(_text(item, field=field) for item in values)
    if len(set(items)) != len(items):
        raise NewsSourcePolicyError(f"{field} values must be unique")
    return items


def _instant(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NewsSourcePolicyError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise NewsSourcePolicyError(f"{field} must include timezone")
    return parsed


@dataclass(frozen=True, slots=True)
class NewsSourcePolicy:
    allowed_source_classes: tuple[str, ...]
    allowed_access_kinds: tuple[str, ...]
    allowed_license_states: tuple[str, ...]
    allowed_admissibility_states: tuple[str, ...]
    https_required: bool
    attribution_required: bool
    canonical_tests_network_required: bool
    production_news_vendor: str
    unconfirmed_news_trade_authority: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "NewsSourcePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise NewsSourcePolicyError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise NewsSourcePolicyError("unsupported policy schema_version")
        policy = cls(
            allowed_source_classes=_string_tuple(raw.get("allowed_source_classes"), field="allowed_source_classes"),
            allowed_access_kinds=_string_tuple(raw.get("allowed_access_kinds"), field="allowed_access_kinds"),
            allowed_license_states=_string_tuple(raw.get("allowed_license_states"), field="allowed_license_states"),
            allowed_admissibility_states=_string_tuple(raw.get("allowed_admissibility_states"), field="allowed_admissibility_states"),
            https_required=_boolean(raw.get("https_required"), field="https_required"),
            attribution_required=_boolean(raw.get("attribution_required"), field="attribution_required"),
            canonical_tests_network_required=_boolean(raw.get("canonical_tests_network_required"), field="canonical_tests_network_required"),
            production_news_vendor=_text(raw.get("production_news_vendor"), field="production_news_vendor"),
            unconfirmed_news_trade_authority=_boolean(raw.get("unconfirmed_news_trade_authority"), field="unconfirmed_news_trade_authority"),
            live_trading=_text(raw.get("live_trading"), field="live_trading"),
            auto_trading=_text(raw.get("auto_trading"), field="auto_trading"),
        )
        if not policy.https_required or not policy.attribution_required:
            raise NewsSourcePolicyError("P11-A requires HTTPS and attribution")
        if policy.canonical_tests_network_required:
            raise NewsSourcePolicyError("P11-A canonical tests must remain offline")
        if policy.production_news_vendor != "NOT_SELECTED":
            raise NewsSourcePolicyError("P11-A cannot select a production vendor")
        if policy.unconfirmed_news_trade_authority:
            raise NewsSourcePolicyError("unconfirmed news cannot grant trade authority")
        if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
            raise NewsSourcePolicyError("P11-A cannot enable trading")
        return policy


@dataclass(frozen=True, slots=True)
class NewsSourceRecord:
    source_id: str
    source_class: str
    source_name: str
    source_url: str
    access_kind: str
    license_state: str
    admissibility_state: str
    attribution: str
    published_at: str
    observed_at: str
    corroborating_source_ids: tuple[str, ...] = ()

    def payload(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_class": self.source_class,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "access_kind": self.access_kind,
            "license_state": self.license_state,
            "admissibility_state": self.admissibility_state,
            "attribution": self.attribution,
            "published_at": self.published_at,
            "observed_at": self.observed_at,
            "corroborating_source_ids": list(self.corroborating_source_ids),
        }

    @property
    def record_id(self) -> str:
        encoded = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def validate_source_record(record: NewsSourceRecord, *, policy: NewsSourcePolicy) -> None:
    for field_name in ("source_id", "source_name", "source_url", "attribution"):
        _text(getattr(record, field_name), field=field_name)
    if record.source_class not in policy.allowed_source_classes:
        raise NewsSourcePolicyError("source_class is not allowed")
    if record.access_kind not in policy.allowed_access_kinds:
        raise NewsSourcePolicyError("access_kind is not allowed")
    if record.license_state not in policy.allowed_license_states:
        raise NewsSourcePolicyError("license_state is not allowed")
    if record.admissibility_state not in policy.allowed_admissibility_states:
        raise NewsSourcePolicyError("admissibility_state is not allowed")

    parsed = urlparse(record.source_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise NewsSourcePolicyError("source_url must be credential-free HTTPS")

    published = _instant(record.published_at, field="published_at")
    observed = _instant(record.observed_at, field="observed_at")
    if published > observed:
        raise NewsSourcePolicyError("published_at cannot be after observed_at")

    corroborators = tuple(item.strip() for item in record.corroborating_source_ids if item.strip())
    if len(corroborators) != len(record.corroborating_source_ids) or len(set(corroborators)) != len(corroborators):
        raise NewsSourcePolicyError("corroborating_source_ids must be non-empty and unique")

    if record.source_class in {"COMMUNITY", "SOCIAL"} and record.admissibility_state == "CONFIRMED" and not corroborators:
        raise NewsSourcePolicyError("community/social source cannot be confirmed without corroboration")
    if record.admissibility_state == "CORROBORATED" and not corroborators:
        raise NewsSourcePolicyError("corroborated content requires corroborating sources")


def can_grant_trade_authority(record: NewsSourceRecord, *, policy: NewsSourcePolicy) -> bool:
    validate_source_record(record, policy=policy)
    if record.admissibility_state == "UNCONFIRMED":
        return False
    return False


def record_with(record: NewsSourceRecord, **changes: object) -> NewsSourceRecord:
    return replace(record, **changes)
