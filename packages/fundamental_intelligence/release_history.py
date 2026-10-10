from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.historical_data.macro_vintage import (
    MacroVintage,
    MacroVintagePolicy,
    MacroVintageStore,
)

from .economic_events import (
    EconomicCalendarEvent,
    EconomicEventPolicy,
    validate_economic_event,
)
from .source_registry import OfficialSourceRegistry


class ReleaseHistoryError(ValueError):
    """Raised when P10-C release-history invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ReleaseHistoryError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseHistoryError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ReleaseHistoryError(f"{field} must be boolean")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ReleaseHistoryError(f"{field} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class ReleaseHistoryPolicy:
    previous_at_time_anchor: str
    as_of_rule: str
    revision_rule: str
    require_released_event: bool
    require_event_actual_release_matches_revision_zero: bool
    full_history_use: str
    production_revision_provider: str
    forecast_values_in_scope: bool
    surprise_in_scope: bool
    network_required: bool
    credentials_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ReleaseHistoryPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise ReleaseHistoryError("unsupported release-history policy schema_version")
        policy = cls(
            previous_at_time_anchor=_text(raw.get("previous_at_time_anchor"), field="previous_at_time_anchor"),
            as_of_rule=_text(raw.get("as_of_rule"), field="as_of_rule"),
            revision_rule=_text(raw.get("revision_rule"), field="revision_rule"),
            require_released_event=_boolean(raw.get("require_released_event"), field="require_released_event"),
            require_event_actual_release_matches_revision_zero=_boolean(
                raw.get("require_event_actual_release_matches_revision_zero"),
                field="require_event_actual_release_matches_revision_zero",
            ),
            full_history_use=_text(raw.get("full_history_use"), field="full_history_use"),
            production_revision_provider=_text(raw.get("production_revision_provider"), field="production_revision_provider"),
            forecast_values_in_scope=_boolean(raw.get("forecast_values_in_scope"), field="forecast_values_in_scope"),
            surprise_in_scope=_boolean(raw.get("surprise_in_scope"), field="surprise_in_scope"),
            network_required=_boolean(raw.get("network_required"), field="network_required"),
            credentials_required=_boolean(raw.get("credentials_required"), field="credentials_required"),
            live_trading=_text(raw.get("live_trading"), field="live_trading"),
            auto_trading=_text(raw.get("auto_trading"), field="auto_trading"),
        )
        if policy.previous_at_time_anchor != "FIRST_RELEASE_OBSERVED_AT":
            raise ReleaseHistoryError("previous-at-time anchor drift")
        if policy.as_of_rule != "RELEASE_AND_OBSERVED_AT_NOT_AFTER_DECISION_TIME":
            raise ReleaseHistoryError("as-of rule drift")
        if policy.revision_rule != "ZERO_BASED_CONTIGUOUS_PER_OBSERVATION":
            raise ReleaseHistoryError("revision rule drift")
        if not policy.require_released_event or not policy.require_event_actual_release_matches_revision_zero:
            raise ReleaseHistoryError("P10-C release/event guards must remain enabled")
        if policy.full_history_use != "AUDIT_ONLY_NOT_REPLAY":
            raise ReleaseHistoryError("full revision history must remain audit-only")
        if policy.production_revision_provider != "NOT_SELECTED":
            raise ReleaseHistoryError("P10-C cannot select a production revision provider")
        if policy.forecast_values_in_scope or policy.surprise_in_scope:
            raise ReleaseHistoryError("forecast/surprise belong outside P10-C")
        if policy.network_required or policy.credentials_required:
            raise ReleaseHistoryError("P10-C canonical model must remain offline")
        if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
            raise ReleaseHistoryError("P10-C cannot enable trading")
        return policy


@dataclass(frozen=True, slots=True)
class ReleaseHistorySnapshot:
    history_id: str
    event_id: str
    series_id: str
    current_observation_time_ns: int
    decision_time_ns: int
    current_vintage_id: str | None
    previous_vintage_id: str | None
    first_release_vintage_id: str
    store_fingerprint: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0",
            "history_id":self.history_id,
            "event_id":self.event_id,
            "series_id":self.series_id,
            "current_observation_time_ns":self.current_observation_time_ns,
            "decision_time_ns":self.decision_time_ns,
            "current_vintage_id":self.current_vintage_id,
            "previous_vintage_id":self.previous_vintage_id,
            "first_release_vintage_id":self.first_release_vintage_id,
            "store_fingerprint":self.store_fingerprint,
        }


class EconomicReleaseHistory:
    def __init__(
        self,
        *,
        event: EconomicCalendarEvent,
        vintages: Sequence[MacroVintage],
        current_observation_time_ns: int,
        policy: ReleaseHistoryPolicy,
        event_policy: EconomicEventPolicy,
        source_registry: OfficialSourceRegistry,
        macro_policy: MacroVintagePolicy,
    ) -> None:
        validated_event = validate_economic_event(
            event,
            policy=event_policy,
            source_registry=source_registry,
        )
        if validated_event.status != "RELEASED" or validated_event.actual_release_time_ns is None:
            raise ReleaseHistoryError("P10-C requires a RELEASED economic event")

        frozen = tuple(vintages)
        if not frozen:
            raise ReleaseHistoryError("release history requires at least one macro vintage")
        current_observation = _non_negative_int(
            current_observation_time_ns,
            field="current_observation_time_ns",
        )
        series_ids = {item.series_id for item in frozen}
        if len(series_ids) != 1:
            raise ReleaseHistoryError("release history must contain exactly one macro series")
        series_id = next(iter(series_ids))
        if any(item.source != validated_event.source_id for item in frozen):
            raise ReleaseHistoryError("macro vintage source must match economic event source")

        store = MacroVintageStore(frozen, macro_policy)
        current_revisions = tuple(
            sorted(
                (item for item in frozen if item.observation_time_ns == current_observation),
                key=lambda item: item.revision_number,
            )
        )
        if not current_revisions or current_revisions[0].revision_number != 0:
            raise ReleaseHistoryError("current observation requires revision zero first release")
        first = current_revisions[0]
        if first.release_time_ns != validated_event.actual_release_time_ns:
            raise ReleaseHistoryError("event actual release must match current revision-zero release time")

        self._event = validated_event
        self._vintages = frozen
        self._current_observation = current_observation
        self._series_id = series_id
        self._store = store
        self._current_revisions = current_revisions
        self._policy = policy
        self._history_id = hashlib.sha256(
            _canonical_bytes(
                {
                    "schema_version":"1.0",
                    "event_id":validated_event.event_id,
                    "series_id":series_id,
                    "current_observation_time_ns":current_observation,
                    "store_fingerprint":store.fingerprint,
                    "previous_at_time_anchor":policy.previous_at_time_anchor,
                }
            )
        ).hexdigest()

    @property
    def history_id(self) -> str:
        return self._history_id

    @property
    def series_id(self) -> str:
        return self._series_id

    @property
    def first_release(self) -> MacroVintage:
        return self._current_revisions[0]

    def resolve_current_as_of(self, *, decision_time_ns: int) -> MacroVintage | None:
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        return self._store.resolve(
            series_id=self._series_id,
            observation_time_ns=self._current_observation,
            decision_time_ns=decision,
        )

    def revision_history_as_of(self, *, decision_time_ns: int) -> tuple[MacroVintage, ...]:
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        return tuple(
            item
            for item in self._current_revisions
            if item.release_time_ns <= decision and item.observed_at_ns <= decision
        )

    def audit_full_revision_history(self) -> tuple[MacroVintage, ...]:
        """Audit/latest context only. Replay callers must use revision_history_as_of."""
        return self._current_revisions

    def previous_at(self, *, decision_time_ns: int) -> MacroVintage | None:
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        snapshot = self._store.snapshot_as_of(
            series_id=self._series_id,
            decision_time_ns=decision,
        )
        prior = tuple(
            item
            for item in snapshot.vintages
            if item.observation_time_ns < self._current_observation
        )
        return prior[-1] if prior else None

    @property
    def previous_at_first_release(self) -> MacroVintage | None:
        return self.previous_at(decision_time_ns=self.first_release.observed_at_ns)

    def snapshot_as_of(self, *, decision_time_ns: int) -> ReleaseHistorySnapshot:
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        current = self.resolve_current_as_of(decision_time_ns=decision)
        previous = self.previous_at(decision_time_ns=decision)
        return ReleaseHistorySnapshot(
            history_id=self._history_id,
            event_id=self._event.event_id,
            series_id=self._series_id,
            current_observation_time_ns=self._current_observation,
            decision_time_ns=decision,
            current_vintage_id=current.vintage_id if current is not None else None,
            previous_vintage_id=previous.vintage_id if previous is not None else None,
            first_release_vintage_id=self.first_release.vintage_id,
            store_fingerprint=self._store.fingerprint,
        )


def assert_no_release_history_forecast_surprise_trade_fields() -> None:
    forbidden={
        "forecast_value","consensus_value","surprise","probability","recommendation",
        "order","quantity","leverage","entry","exit","risk_approval",
    }
    fields_seen={field.name for field in fields(ReleaseHistorySnapshot)}
    if forbidden & fields_seen:
        raise ReleaseHistoryError("P10-C contract exposes forecast/surprise/trade authority fields")
