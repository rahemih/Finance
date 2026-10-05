from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TypeAlias


class MarketEventKind(StrEnum):
    TRADE = "TRADE"
    ORDER_BOOK = "ORDER_BOOK"


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class OrderBookUpdateType(StrEnum):
    SNAPSHOT = "SNAPSHOT"
    UPDATE = "UPDATE"


class SequenceDisposition(StrEnum):
    FIRST = "FIRST"
    ADVANCING = "ADVANCING"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"


@dataclass(frozen=True, slots=True)
class ProviderTimestamp:
    raw: str
    epoch_ns: int


@dataclass(frozen=True, slots=True)
class ProviderInstrument:
    provider: str
    exchange: str
    instrument_class: str
    code: str


@dataclass(frozen=True, slots=True)
class TradePayload:
    trade_id: str | None
    price: Decimal
    amount: Decimal
    side: TradeSide


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    price: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class OrderBookPayload:
    update_type: OrderBookUpdateType
    asks: tuple[OrderBookLevel, ...]
    bids: tuple[OrderBookLevel, ...]


MarketPayload: TypeAlias = TradePayload | OrderBookPayload


@dataclass(frozen=True, slots=True)
class ProviderEventEnvelope:
    kind: MarketEventKind
    instrument: ProviderInstrument
    sequence_id: str
    ts_exchange: ProviderTimestamp
    ts_collection: ProviderTimestamp
    ts_event: ProviderTimestamp
    received_at_ns: int
    payload: MarketPayload
    metadata: tuple[tuple[str, str], ...] = ()
