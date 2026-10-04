"""Deterministic, offline-only engineering test primitives for NEXUS QUANT."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import socket
from typing import Any, Iterable


UTC = timezone.utc


class InvalidReplayError(ValueError):
    """Replay fixture violates deterministic ordering rules."""


class UnsafeRetryError(RuntimeError):
    """A submit was attempted while provider outcome is unresolved."""


class InvalidReconciliationError(ValueError):
    """Reconciliation outcome is not a proved provider state."""


class InjectedFailure(RuntimeError):
    """Deterministic failure injected by FailureInjector."""


class NetworkDeniedError(RuntimeError):
    """Network access attempted while NetworkDenyGuard is active."""


def _parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timezone-aware UTC datetime required")
    parsed = parsed.astimezone(UTC)
    return parsed


def _format_utc(value: datetime) -> str:
    value = value.astimezone(UTC)
    if value.microsecond:
        text = value.isoformat(timespec="microseconds")
    else:
        text = value.isoformat(timespec="seconds")
    return text.replace("+00:00", "Z")


class DeterministicClock:
    """UTC-only clock whose state changes only through explicit test actions."""

    def __init__(self, initial: str | datetime):
        self._now = _parse_utc(initial)

    def now(self) -> datetime:
        return self._now

    def now_iso(self) -> str:
        return _format_utc(self._now)

    def advance(self, delta: timedelta) -> datetime:
        if delta.total_seconds() < 0:
            raise ValueError("clock cannot advance by a negative duration")
        self._now = self._now + delta
        return self._now

    def set(self, value: str | datetime) -> datetime:
        candidate = _parse_utc(value)
        if candidate < self._now:
            raise ValueError("deterministic clock cannot move backwards")
        self._now = candidate
        return self._now


class DeterministicIdSequence:
    """Predictable correlation/test IDs from explicit prefix and counter."""

    def __init__(self, prefix: str, start: int = 1):
        if not prefix or any(ch.isspace() for ch in prefix):
            raise ValueError("non-empty whitespace-free prefix required")
        if start < 0:
            raise ValueError("start must be non-negative")
        self._prefix = prefix
        self._next = start

    def next(self) -> str:
        value = f"{self._prefix}-{self._next:06d}"
        self._next += 1
        return value


@dataclass(frozen=True)
class ReplayEvent:
    sequence: int
    event_time: datetime
    event_type: str
    payload: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReplayEvent":
        required = {"sequence", "event_time", "event_type", "payload"}
        keys = set(value)
        if keys != required:
            raise InvalidReplayError(
                f"replay event keys invalid missing={sorted(required-keys)} extra={sorted(keys-required)}"
            )
        if not isinstance(value["sequence"], int) or value["sequence"] < 0:
            raise InvalidReplayError("sequence must be a non-negative integer")
        if not isinstance(value["event_type"], str) or not value["event_type"]:
            raise InvalidReplayError("event_type must be a non-empty string")
        if not isinstance(value["payload"], dict):
            raise InvalidReplayError("payload must be an object")
        try:
            event_time = _parse_utc(value["event_time"])
        except Exception as exc:
            raise InvalidReplayError(f"invalid event_time: {exc}") from exc
        return cls(
            sequence=value["sequence"],
            event_time=event_time,
            event_type=value["event_type"],
            payload=value["payload"],
        )

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_time": _format_utc(self.event_time),
            "event_type": self.event_type,
            "payload": self.payload,
        }


class ReplayTape:
    """Validated deterministic event sequence."""

    def __init__(self, events: Iterable[ReplayEvent | dict[str, Any]]):
        normalized = [
            event if isinstance(event, ReplayEvent) else ReplayEvent.from_dict(event)
            for event in events
        ]
        self._validate(normalized)
        self._events = tuple(normalized)

    @staticmethod
    def _validate(events: list[ReplayEvent]) -> None:
        previous_sequence: int | None = None
        previous_time: datetime | None = None
        seen: set[int] = set()

        for event in events:
            if event.sequence in seen:
                raise InvalidReplayError(f"duplicate sequence={event.sequence}")
            seen.add(event.sequence)

            if previous_sequence is not None and event.sequence <= previous_sequence:
                raise InvalidReplayError(
                    f"non-monotonic sequence previous={previous_sequence} current={event.sequence}"
                )
            if previous_time is not None and event.event_time < previous_time:
                raise InvalidReplayError(
                    "event time moved backwards "
                    f"previous={_format_utc(previous_time)} current={_format_utc(event.event_time)}"
                )

            previous_sequence = event.sequence
            previous_time = event.event_time

    @classmethod
    def from_fixture(cls, path: Path) -> "ReplayTape":
        value = load_json_fixture(path)
        if not isinstance(value, dict) or set(value) != {"schema_version", "events"}:
            raise InvalidReplayError("fixture must contain schema_version and events only")
        if value["schema_version"] != "1.0":
            raise InvalidReplayError("unsupported replay fixture schema_version")
        if not isinstance(value["events"], list):
            raise InvalidReplayError("events must be an array")
        return cls(value["events"])

    def __iter__(self):
        return iter(self._events)

    def canonical_bytes(self) -> bytes:
        payload = [event.canonical_dict() for event in self._events]
        return (
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def normalized_events(self) -> list[dict[str, Any]]:
        return [event.canonical_dict() for event in self._events]


class ScriptedProviderSimulator:
    """Offline provider simulator preserving UNKNOWN/reconciliation semantics."""

    SUBMIT_OUTCOMES = {"ACKNOWLEDGED", "REJECTED", "TIMEOUT_UNKNOWN"}
    RECONCILIATION_OUTCOMES = {"ACKNOWLEDGED", "FILLED", "CANCELED", "REJECTED"}

    def __init__(self, outcomes: Iterable[str]):
        self._outcomes = list(outcomes)
        if not self._outcomes:
            raise ValueError("at least one scripted outcome is required")
        unknown = [item for item in self._outcomes if item not in self.SUBMIT_OUTCOMES]
        if unknown:
            raise ValueError(f"unsupported scripted outcomes={unknown}")
        self._index = 0
        self._unresolved: set[str] = set()
        self._history: list[dict[str, str]] = []

    @classmethod
    def from_fixture(cls, path: Path) -> "ScriptedProviderSimulator":
        value = load_json_fixture(path)
        if not isinstance(value, dict) or set(value) != {"schema_version", "submit_outcomes"}:
            raise ValueError("provider fixture must contain schema_version and submit_outcomes only")
        if value["schema_version"] != "1.0":
            raise ValueError("unsupported provider fixture schema_version")
        outcomes = value["submit_outcomes"]
        if not isinstance(outcomes, list) or not all(isinstance(x, str) for x in outcomes):
            raise ValueError("submit_outcomes must be an array of strings")
        return cls(outcomes)

    def submit(self, intent_id: str) -> str:
        if not intent_id:
            raise ValueError("intent_id required")
        if intent_id in self._unresolved:
            raise UnsafeRetryError(
                f"intent {intent_id} is unresolved; reconcile before retry/continuation"
            )
        if self._index >= len(self._outcomes):
            raise RuntimeError("scripted provider outcomes exhausted")

        outcome = self._outcomes[self._index]
        self._index += 1
        if outcome == "TIMEOUT_UNKNOWN":
            self._unresolved.add(intent_id)

        self._history.append(
            {"operation": "submit", "intent_id": intent_id, "outcome": outcome}
        )
        return outcome

    def reconcile(self, intent_id: str, provider_state: str) -> str:
        if intent_id not in self._unresolved:
            raise InvalidReconciliationError(
                f"intent {intent_id} has no unresolved provider outcome"
            )
        if provider_state not in self.RECONCILIATION_OUTCOMES:
            raise InvalidReconciliationError(
                f"provider state {provider_state} is not a proved reconciliation outcome"
            )

        self._unresolved.remove(intent_id)
        self._history.append(
            {"operation": "reconcile", "intent_id": intent_id, "outcome": provider_state}
        )
        return provider_state

    def unresolved(self, intent_id: str) -> bool:
        return intent_id in self._unresolved

    def history(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(item) for item in self._history)


class FailureInjector:
    """Deterministically raises at configured named checkpoint call numbers."""

    def __init__(self, plan: dict[str, int]):
        if not isinstance(plan, dict):
            raise TypeError("plan must be a mapping")
        for checkpoint, fire_on in plan.items():
            if not isinstance(checkpoint, str) or not checkpoint:
                raise ValueError("checkpoint names must be non-empty strings")
            if not isinstance(fire_on, int) or fire_on < 1:
                raise ValueError("fire_on must be a positive integer")
        self._plan = dict(plan)
        self._counts: dict[str, int] = {}

    def checkpoint(self, name: str) -> None:
        count = self._counts.get(name, 0) + 1
        self._counts[name] = count
        if self._plan.get(name) == count:
            raise InjectedFailure(f"injected failure checkpoint={name} call={count}")

    def count(self, name: str) -> int:
        return self._counts.get(name, 0)


class NetworkDenyGuard(AbstractContextManager["NetworkDenyGuard"]):
    """Temporarily deny outbound socket connect/create_connection calls."""

    def __init__(self):
        self._original_create_connection = None
        self._original_socket_connect = None

    @staticmethod
    def _deny(*_args, **_kwargs):
        raise NetworkDeniedError("network access denied by deterministic test harness")

    def __enter__(self) -> "NetworkDenyGuard":
        self._original_create_connection = socket.create_connection
        self._original_socket_connect = socket.socket.connect
        socket.create_connection = self._deny
        socket.socket.connect = self._deny
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._original_create_connection is not None:
            socket.create_connection = self._original_create_connection
        if self._original_socket_connect is not None:
            socket.socket.connect = self._original_socket_connect
        return False


def load_json_fixture(path: Path) -> Any:
    path = Path(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    return value
