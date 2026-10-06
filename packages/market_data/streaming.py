from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Mapping, cast

from packages.market_data.normalization import CanonicalMarketEvent


class StreamingError(ValueError):
    """Provider-neutral streaming input or state is invalid."""


class BackpressureError(StreamingError):
    """The bounded stream buffer is full and the event was not accepted."""


class BufferPressure(StrEnum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    FULL = "FULL"


class StreamHealth(StrEnum):
    NEVER_SEEN = "NEVER_SEEN"
    HEALTHY = "HEALTHY"
    STALE = "STALE"


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise StreamingError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise StreamingError(f"{field} must be a positive integer")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StreamingError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class StreamKey:
    provider: str
    canonical_id: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise StreamingError("stream provider must be non-empty")
        if not self.canonical_id.strip():
            raise StreamingError("stream canonical_id must be non-empty")


@dataclass(frozen=True, slots=True)
class StreamingPolicy:
    max_buffer_events: int
    high_watermark_events: int
    critical_watermark_events: int
    heartbeat_timeout_ns: int

    def __post_init__(self) -> None:
        values = (
            ("max_buffer_events", self.max_buffer_events),
            ("high_watermark_events", self.high_watermark_events),
            ("critical_watermark_events", self.critical_watermark_events),
            ("heartbeat_timeout_ns", self.heartbeat_timeout_ns),
        )
        for field, value in values:
            if isinstance(value, bool) or value <= 0:
                raise StreamingError(f"{field} must be a positive integer")
        if not self.high_watermark_events < self.critical_watermark_events < self.max_buffer_events:
            raise StreamingError(
                "buffer thresholds must satisfy high < critical < max"
            )

    @classmethod
    def from_path(cls, path: Path) -> "StreamingPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise StreamingError(f"invalid streaming policy JSON: {exc}") from exc

        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise StreamingError("unsupported streaming policy schema_version")

        runtime = _mapping(raw.get("runtime_policy"), field="runtime_policy")
        if _text(runtime.get("overflow_policy"), field="overflow_policy") != "REJECT_EXPLICIT_NO_SILENT_DROP":
            raise StreamingError("unsupported overflow policy")
        if _text(runtime.get("ordering"), field="ordering") != "FIFO":
            raise StreamingError("unsupported ordering policy")
        if _text(runtime.get("heartbeat_clock"), field="heartbeat_clock") != "CANONICAL_LOCAL_RECEIVE_TIME":
            raise StreamingError("unsupported heartbeat clock")

        return cls(
            max_buffer_events=_positive_int(
                runtime.get("max_buffer_events"),
                field="max_buffer_events",
            ),
            high_watermark_events=_positive_int(
                runtime.get("high_watermark_events"),
                field="high_watermark_events",
            ),
            critical_watermark_events=_positive_int(
                runtime.get("critical_watermark_events"),
                field="critical_watermark_events",
            ),
            heartbeat_timeout_ns=_positive_int(
                runtime.get("heartbeat_timeout_ns"),
                field="heartbeat_timeout_ns",
            ),
        )


@dataclass(frozen=True, slots=True)
class BufferedCanonicalEvent:
    key: StreamKey
    event: CanonicalMarketEvent


@dataclass(frozen=True, slots=True)
class StreamSnapshot:
    key: StreamKey
    queue_depth: int
    high_watermark_seen: int
    rejected_events: int
    pressure: BufferPressure
    health: StreamHealth
    last_accepted_receive_ns: int | None


class CanonicalStreamBus:
    def __init__(self, policy: StreamingPolicy) -> None:
        self._policy = policy
        self._queue: deque[BufferedCanonicalEvent] = deque()
        self._last_accepted_receive_ns: dict[StreamKey, int] = {}
        self._high_watermark_seen = 0
        self._rejected_events = 0

    @property
    def policy(self) -> StreamingPolicy:
        return self._policy

    @property
    def queue_depth(self) -> int:
        return len(self._queue)

    @property
    def high_watermark_seen(self) -> int:
        return self._high_watermark_seen

    @property
    def rejected_events(self) -> int:
        return self._rejected_events

    @property
    def pressure(self) -> BufferPressure:
        depth = len(self._queue)
        if depth >= self._policy.max_buffer_events:
            return BufferPressure.FULL
        if depth >= self._policy.critical_watermark_events:
            return BufferPressure.CRITICAL
        if depth >= self._policy.high_watermark_events:
            return BufferPressure.HIGH
        return BufferPressure.NORMAL

    @staticmethod
    def key_for(event: CanonicalMarketEvent) -> StreamKey:
        return StreamKey(provider=event.provider, canonical_id=event.canonical_id)

    def publish(self, event: CanonicalMarketEvent) -> None:
        key = self.key_for(event)
        observed_ns = event.clock.local_receive_time_ns
        previous_ns = self._last_accepted_receive_ns.get(key)
        if previous_ns is not None and observed_ns < previous_ns:
            raise StreamingError(
                "per-stream local receive time regression is forbidden"
            )

        if len(self._queue) >= self._policy.max_buffer_events:
            self._rejected_events += 1
            raise BackpressureError(
                "stream buffer full; event rejected without silent drop"
            )

        self._queue.append(BufferedCanonicalEvent(key=key, event=event))
        self._last_accepted_receive_ns[key] = observed_ns
        if len(self._queue) > self._high_watermark_seen:
            self._high_watermark_seen = len(self._queue)

    def consume(self) -> CanonicalMarketEvent | None:
        if not self._queue:
            return None
        return self._queue.popleft().event

    def health(self, key: StreamKey, *, now_ns: int) -> StreamHealth:
        if isinstance(now_ns, bool) or now_ns < 0:
            raise StreamingError("now_ns must be a non-negative integer")

        last_ns = self._last_accepted_receive_ns.get(key)
        if last_ns is None:
            return StreamHealth.NEVER_SEEN
        if now_ns < last_ns:
            raise StreamingError(
                "heartbeat observation cannot precede last accepted receive time"
            )
        if now_ns - last_ns > self._policy.heartbeat_timeout_ns:
            return StreamHealth.STALE
        return StreamHealth.HEALTHY

    def snapshot(self, key: StreamKey, *, now_ns: int) -> StreamSnapshot:
        return StreamSnapshot(
            key=key,
            queue_depth=len(self._queue),
            high_watermark_seen=self._high_watermark_seen,
            rejected_events=self._rejected_events,
            pressure=self.pressure,
            health=self.health(key, now_ns=now_ns),
            last_accepted_receive_ns=self._last_accepted_receive_ns.get(key),
        )
