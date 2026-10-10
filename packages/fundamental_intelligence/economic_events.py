from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .source_registry import OfficialSourceRegistry


class EconomicEventError(ValueError):
    """Raised when P10-B economic-event invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise EconomicEventError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise EconomicEventError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EconomicEventError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise EconomicEventError(f"{field} must be boolean")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EconomicEventError(f"{field} must be a non-negative integer")
    return value


def _optional_non_negative_int(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value, field=field)


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise EconomicEventError(f"{field} must be lowercase sha256 hex")
    return text


def _iana_timezone(value: object) -> str:
    text = _text(value, field="release_timezone")
    try:
        ZoneInfo(text)
    except ZoneInfoNotFoundError as exc:
        raise EconomicEventError("release_timezone must be a valid IANA timezone") from exc
    return text


@dataclass(frozen=True, slots=True)
class EconomicEventPolicy:
    allowed_event_kinds: tuple[str, ...]
    allowed_statuses: tuple[str, ...]
    iana_timezone_required: bool
    numeric_release_values_allowed: bool
    forecast_values_allowed: bool
    previous_values_allowed: bool
    production_calendar_provider: str
    direct_trade_output_allowed: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "EconomicEventPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise EconomicEventError("unsupported policy schema_version")
        kinds = tuple(_text(item, field="event kind") for item in _object_list(raw.get("allowed_event_kinds"), field="allowed_event_kinds"))
        statuses = tuple(_text(item, field="event status") for item in _object_list(raw.get("allowed_statuses"), field="allowed_statuses"))
        if not kinds or len(set(kinds)) != len(kinds):
            raise EconomicEventError("allowed_event_kinds must be non-empty and unique")
        if statuses != ("SCHEDULED", "RELEASED", "RESCHEDULED", "CANCELLED"):
            raise EconomicEventError("P10-B lifecycle statuses are fixed")
        timezone_required = _boolean(raw.get("iana_timezone_required"), field="iana_timezone_required")
        numeric = _boolean(raw.get("numeric_release_values_allowed"), field="numeric_release_values_allowed")
        forecast = _boolean(raw.get("forecast_values_allowed"), field="forecast_values_allowed")
        previous = _boolean(raw.get("previous_values_allowed"), field="previous_values_allowed")
        provider = _text(raw.get("production_calendar_provider"), field="production_calendar_provider")
        direct = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        live = _text(raw.get("live_trading"), field="live_trading")
        auto = _text(raw.get("auto_trading"), field="auto_trading")
        if not timezone_required or numeric or forecast or previous:
            raise EconomicEventError("P10-B must require timezone and forbid release/forecast/previous values")
        if provider != "NOT_SELECTED" or direct or live != "DISABLED" or auto != "DISABLED":
            raise EconomicEventError("P10-B safety policy drift")
        return cls(kinds,statuses,timezone_required,numeric,forecast,previous,provider,direct,live,auto)


@dataclass(frozen=True, slots=True)
class EconomicCalendarEvent:
    source_id: str
    source_event_id: str
    event_name: str
    event_kind: str
    jurisdiction: str
    reference_period: str
    scheduled_release_time_ns: int
    release_timezone: str
    status: str
    observed_at_ns: int
    source_dataset_version: str
    quality_evidence_sha256: str
    actual_release_time_ns: int | None = None
    rescheduled_from_ns: int | None = None
    cancellation_reason: str | None = None

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0","source_id":self.source_id,"source_event_id":self.source_event_id,
            "event_name":self.event_name,"event_kind":self.event_kind,"jurisdiction":self.jurisdiction,
            "reference_period":self.reference_period,"scheduled_release_time_ns":self.scheduled_release_time_ns,
            "release_timezone":self.release_timezone,"status":self.status,"observed_at_ns":self.observed_at_ns,
            "source_dataset_version":self.source_dataset_version,"quality_evidence_sha256":self.quality_evidence_sha256,
            "actual_release_time_ns":self.actual_release_time_ns,"rescheduled_from_ns":self.rescheduled_from_ns,
            "cancellation_reason":self.cancellation_reason,
        }

    @property
    def event_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_economic_event(
    event: EconomicCalendarEvent,
    *,
    policy: EconomicEventPolicy,
    source_registry: OfficialSourceRegistry,
) -> EconomicCalendarEvent:
    source_id=_text(event.source_id,field="source_id")
    source_registry.get(source_id)
    source_event_id=_text(event.source_event_id,field="source_event_id")
    event_name=_text(event.event_name,field="event_name")
    event_kind=_text(event.event_kind,field="event_kind")
    jurisdiction=_text(event.jurisdiction,field="jurisdiction")
    reference_period=_text(event.reference_period,field="reference_period")
    scheduled=_non_negative_int(event.scheduled_release_time_ns,field="scheduled_release_time_ns")
    timezone=_iana_timezone(event.release_timezone)
    status=_text(event.status,field="status")
    observed=_non_negative_int(event.observed_at_ns,field="observed_at_ns")
    dataset=_sha256_text(event.source_dataset_version,field="source_dataset_version")
    quality=_sha256_text(event.quality_evidence_sha256,field="quality_evidence_sha256")
    actual=_optional_non_negative_int(event.actual_release_time_ns,field="actual_release_time_ns")
    rescheduled=_optional_non_negative_int(event.rescheduled_from_ns,field="rescheduled_from_ns")
    cancellation=event.cancellation_reason.strip() if isinstance(event.cancellation_reason,str) and event.cancellation_reason.strip() else None

    if event_kind not in policy.allowed_event_kinds:
        raise EconomicEventError("event_kind is not allowed by policy")
    if status not in policy.allowed_statuses:
        raise EconomicEventError("status is not allowed by policy")

    if status == "SCHEDULED":
        if actual is not None or rescheduled is not None or cancellation is not None:
            raise EconomicEventError("SCHEDULED event carries incompatible lifecycle fields")
    elif status == "RELEASED":
        if actual is None:
            raise EconomicEventError("RELEASED event requires actual_release_time_ns")
        if actual > observed:
            raise EconomicEventError("actual release cannot be after calendar observed_at")
        if rescheduled is not None or cancellation is not None:
            raise EconomicEventError("RELEASED event carries incompatible lifecycle fields")
    elif status == "RESCHEDULED":
        if rescheduled is None or rescheduled == scheduled:
            raise EconomicEventError("RESCHEDULED event requires distinct rescheduled_from_ns")
        if actual is not None or cancellation is not None:
            raise EconomicEventError("RESCHEDULED event carries incompatible lifecycle fields")
    elif status == "CANCELLED":
        if cancellation is None:
            raise EconomicEventError("CANCELLED event requires cancellation_reason")
        if actual is not None or rescheduled is not None:
            raise EconomicEventError("CANCELLED event carries incompatible lifecycle fields")

    return EconomicCalendarEvent(
        source_id,source_event_id,event_name,event_kind,jurisdiction,reference_period,scheduled,timezone,status,
        observed,dataset,quality,actual,rescheduled,cancellation,
    )


def assert_no_event_value_or_trade_authority_fields() -> None:
    forbidden={"actual_value","forecast_value","previous_value","surprise","probability","recommendation","order","quantity","leverage","entry","exit","risk_approval"}
    contract_fields={field.name for field in fields(EconomicCalendarEvent)}
    if forbidden & contract_fields:
        raise EconomicEventError("P10-B event contract exposes value/surprise/trade authority fields")
