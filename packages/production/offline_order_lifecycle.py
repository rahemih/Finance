"""Pure offline order-lifecycle reference. No network, credentials, adapters or execution authority.

This is a proposal for D02 synthetic verification, NOT a broker-certified OMS.
"""
from dataclasses import dataclass
from enum import Enum


class LifecycleError(ValueError):
    pass


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class State(str, Enum):
    NEW = "NEW"
    SENT_UNKNOWN = "SENT_UNKNOWN"
    ACKED = "ACKED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"


@dataclass
class OfflineOrder:
    client_id: str
    requested_units: int
    filled_units: int = 0
    state: State = State.NEW
    side: Side = Side.BUY

    def __post_init__(self) -> None:
        if (type(self.client_id) is not str or not self.client_id.strip()
                or type(self.requested_units) is not int or self.requested_units <= 0
                or type(self.filled_units) is not int or self.filled_units != 0
                or self.state is not State.NEW or type(self.side) is not Side):
            raise LifecycleError("invalid synthetic intent")

    def submit_unknown(self) -> None:
        if self.state != State.NEW:
            raise LifecycleError("cannot resubmit ambiguous intent")
        self.state = State.SENT_UNKNOWN

    def acknowledge(self, client_id: str) -> None:
        if client_id != self.client_id or self.state not in (State.SENT_UNKNOWN, State.ACKED, State.PARTIAL):
            raise LifecycleError("unexpected acknowledgement")
        # A delayed ACK must never erase an already reconciled partial fill.
        if self.state is not State.PARTIAL:
            self.state = State.ACKED

    def reconcile(self, client_id: str, cumulative_filled: int, canceled: bool = False) -> None:
        if type(canceled) is not bool:
            raise LifecycleError("invalid cancel flag")
        if client_id != self.client_id or self.state == State.NEW:
            raise LifecycleError("unrecognized order")
        if type(cumulative_filled) is not int or not self.filled_units <= cumulative_filled <= self.requested_units:
            raise LifecycleError("invalid or regressed fill")
        if self.state in (State.FILLED, State.CANCELED):
            if cumulative_filled != self.filled_units or canceled != (self.state == State.CANCELED):
                raise LifecycleError("terminal order changed")
            return
        # Reject contradictory terminal evidence before mutating state.
        if cumulative_filled == self.requested_units and canceled:
            raise LifecycleError("filled order cannot cancel")
        self.filled_units = cumulative_filled
        if cumulative_filled == self.requested_units:
            self.state = State.FILLED
        elif canceled:
            self.state = State.CANCELED
        elif cumulative_filled:
            self.state = State.PARTIAL
        elif self.state is not State.SENT_UNKNOWN:
            # Zero-fill observations are not proof of an ACK.
            self.state = State.ACKED

    @property
    def may_submit_again(self) -> bool:
        # Unknown ACK is never permission to send a second external order.
        return False
