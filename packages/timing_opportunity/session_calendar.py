from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping, cast


class SessionCalendarError(ValueError):
    """P13-A session/calendar input or policy violates governed invariants."""


_NANOSECONDS_PER_SECOND = 1_000_000_000
_MINUTES_PER_DAY = 1440


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SessionCalendarError(f"{field} must be integer")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SessionCalendarError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class SessionWindow:
    name: str
    start_minute_utc: int
    end_minute_utc: int

    def contains(self, minute_of_day_utc: int) -> bool:
        return self.start_minute_utc <= minute_of_day_utc < self.end_minute_utc


@dataclass(frozen=True, slots=True)
class SessionCalendarPolicy:
    calendar_timezone: str
    calendar_version: str
    market_kinds: tuple[str, ...]
    regional_sessions: tuple[SessionWindow, ...]
    forex_sunday_open_minute_utc: int
    forex_friday_close_minute_utc: int
    crypto_24_7: bool
    holiday_calendar_in_scope: bool
    dynamic_dst_adjustment_in_scope: bool
    production_calendar_vendor: str
    best_trading_time_in_scope: bool
    opportunity_ranking_in_scope: bool
    signal_probability_in_scope: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "SessionCalendarPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise SessionCalendarError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "UTC_VENDOR_NEUTRAL_SESSION_CALENDAR":
            raise SessionCalendarError("unsupported P13-A policy")
        if raw.get("calendar_timezone") != "UTC":
            raise SessionCalendarError("canonical calendar timezone must be UTC")

        version = _text(raw.get("calendar_version"), field="calendar_version")
        markets_value = raw.get("market_kinds")
        if not isinstance(markets_value, list):
            raise SessionCalendarError("market_kinds must be list")
        markets = tuple(str(item).strip().upper() for item in cast(list[object], markets_value))
        expected_markets = {"CRYPTO_SPOT", "CRYPTO_FUTURES", "FOREX_SPOT"}
        if set(markets) != expected_markets or len(markets) != len(expected_markets):
            raise SessionCalendarError("unexpected market_kinds")

        sessions_value = raw.get("regional_sessions")
        if not isinstance(sessions_value, list):
            raise SessionCalendarError("regional_sessions must be list")
        sessions: list[SessionWindow] = []
        for item_value in cast(list[object], sessions_value):
            if not isinstance(item_value, Mapping):
                raise SessionCalendarError("regional session must be object")
            item = cast(Mapping[str, object], item_value)
            name = _text(item.get("name"), field="session name").upper()
            start = _integer(item.get("start_minute_utc"), field="start_minute_utc")
            end = _integer(item.get("end_minute_utc"), field="end_minute_utc")
            if not 0 <= start < end <= _MINUTES_PER_DAY:
                raise SessionCalendarError("regional session bounds are invalid")
            sessions.append(SessionWindow(name, start, end))
        if tuple(item.name for item in sessions) != ("ASIA", "EUROPE", "US"):
            raise SessionCalendarError("regional session order/names are not canonical")

        sunday_open = _integer(raw.get("forex_sunday_open_minute_utc"), field="forex_sunday_open_minute_utc")
        friday_close = _integer(raw.get("forex_friday_close_minute_utc"), field="forex_friday_close_minute_utc")
        if not 0 <= sunday_open < _MINUTES_PER_DAY or not 0 < friday_close <= _MINUTES_PER_DAY:
            raise SessionCalendarError("forex weekly boundaries are invalid")

        if raw.get("crypto_24_7") is not True:
            raise SessionCalendarError("crypto_24_7 must remain true")
        if raw.get("holiday_calendar_in_scope") is not False:
            raise SessionCalendarError("production holiday calendars are outside P13-A baseline")
        if raw.get("dynamic_dst_adjustment_in_scope") is not False:
            raise SessionCalendarError("dynamic DST adjustment requires a governed production calendar source")
        if raw.get("production_calendar_vendor") != "NOT_SELECTED":
            raise SessionCalendarError("production calendar vendor must remain NOT_SELECTED")
        if raw.get("best_trading_time_in_scope") is not False:
            raise SessionCalendarError("best trading time belongs to P13-B")
        if raw.get("opportunity_ranking_in_scope") is not False:
            raise SessionCalendarError("opportunity ranking belongs to P13-D")
        if raw.get("signal_probability_in_scope") is not False:
            raise SessionCalendarError("signal probability belongs to P14")
        if raw.get("canonical_tests_network_required") is not False:
            raise SessionCalendarError("canonical P13-A tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise SessionCalendarError("P13-A cannot enable trading")

        return cls(
            calendar_timezone="UTC",
            calendar_version=version,
            market_kinds=markets,
            regional_sessions=tuple(sessions),
            forex_sunday_open_minute_utc=sunday_open,
            forex_friday_close_minute_utc=friday_close,
            crypto_24_7=True,
            holiday_calendar_in_scope=False,
            dynamic_dst_adjustment_in_scope=False,
            production_calendar_vendor="NOT_SELECTED",
            best_trading_time_in_scope=False,
            opportunity_ranking_in_scope=False,
            signal_probability_in_scope=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class SessionContext:
    timestamp_ns: int
    calendar_version: str
    market_kind: str
    weekday_utc: int
    minute_of_day_utc: int
    is_market_open: bool
    active_sessions: tuple[str, ...]
    overlap_count: int
    state: str


def _market_open(market_kind: str, weekday_utc: int, minute_of_day_utc: int, policy: SessionCalendarPolicy) -> bool:
    if market_kind in {"CRYPTO_SPOT", "CRYPTO_FUTURES"}:
        return True
    if market_kind != "FOREX_SPOT":
        raise SessionCalendarError("unknown market_kind")
    if weekday_utc == 5:
        return False
    if weekday_utc == 6:
        return minute_of_day_utc >= policy.forex_sunday_open_minute_utc
    if weekday_utc == 4:
        return minute_of_day_utc < policy.forex_friday_close_minute_utc
    return True


def evaluate_session(
    timestamp_ns: int,
    *,
    market_kind: str,
    policy: SessionCalendarPolicy,
) -> SessionContext:
    stamp = _integer(timestamp_ns, field="timestamp_ns")
    if stamp < 0:
        raise SessionCalendarError("timestamp_ns must be non-negative")
    market = _text(market_kind, field="market_kind").upper()
    if market not in policy.market_kinds:
        raise SessionCalendarError("market_kind is not governed")

    seconds = stamp // _NANOSECONDS_PER_SECOND
    instant = datetime.fromtimestamp(seconds, tz=timezone.utc)
    minute = instant.hour * 60 + instant.minute
    weekday = instant.weekday()
    is_open = _market_open(market, weekday, minute, policy)
    sessions = tuple(
        window.name
        for window in policy.regional_sessions
        if is_open and window.contains(minute)
    )
    overlap_count = len(sessions)
    if not is_open:
        state = "CLOSED"
    elif overlap_count >= 2:
        state = "OVERLAP"
    elif overlap_count == 1:
        state = "SINGLE_SESSION"
    else:
        state = "OPEN_NO_NAMED_SESSION"

    return SessionContext(
        timestamp_ns=stamp,
        calendar_version=policy.calendar_version,
        market_kind=market,
        weekday_utc=weekday,
        minute_of_day_utc=minute,
        is_market_open=is_open,
        active_sessions=sessions,
        overlap_count=overlap_count,
        state=state,
    )
