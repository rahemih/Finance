"""Pure, per-instrument synthetic tick-order gate; no network or order execution."""
from dataclasses import dataclass
from enum import Enum


class TickDecision(str, Enum):
    ACCEPT = "ACCEPT"
    STALE = "STALE"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INVALID = "INVALID"


@dataclass
class TickOrderGate:
    max_age_ns: int
    last_sequence: int | None = None
    last_event_ns: int | None = None
    last_now_ns: int | None = None

    def __post_init__(self) -> None:
        if type(self.max_age_ns) is not int or self.max_age_ns < 0:
            raise ValueError("max_age_ns must be a nonnegative integer")

    def inspect(self, *, sequence: int, event_ns: int, now_ns: int) -> TickDecision:
        if any(type(v) is not int or v < 0 for v in (sequence, event_ns, now_ns)):
            return TickDecision.INVALID
        if self.last_now_ns is not None and now_ns < self.last_now_ns:
            return TickDecision.INVALID
        if event_ns > now_ns or now_ns - event_ns > self.max_age_ns:
            return TickDecision.STALE
        if self.last_sequence is not None:
            if sequence == self.last_sequence:
                return TickDecision.DUPLICATE
            if sequence < self.last_sequence:
                return TickDecision.OUT_OF_ORDER
            if self.last_event_ns is not None and event_ns < self.last_event_ns:
                return TickDecision.OUT_OF_ORDER
        self.last_sequence, self.last_event_ns, self.last_now_ns = sequence, event_ns, now_ns
        return TickDecision.ACCEPT
