from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TypeAlias


class MarketEventKind(StrEnum):
    TRADE = "TRADE"
    ORDER_BOOK = "ORDER_BOOK"
    QUOTE = "QUOTE"
    CONTEXT_TOP_OF_BOOK = "CONTEXT_TOP_OF_BOOK"


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


class QuoteSizeSemantics(StrEnum):
    PROVIDER_QUOTE_SIZE_NOT_GLOBAL_SPOT_FX_VOLUME = (
        "PROVIDER_QUOTE_SIZE_NOT_GLOBAL_SPOT_FX_VOLUME"
    )


class ContextQuantitySemantics(StrEnum):
    CENTRALIZED_FUTURES_VENUE_QUANTITY = "CENTRALIZED_FUTURES_VENUE_QUANTITY"


class ContextMarketRole(StrEnum):
    CONTEXT_ONLY = "CONTEXT_ONLY"


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


@dataclass(frozen=True, slots=True)
class QuotePayload:
    bid_time: ProviderTimestamp
    ask_time: ProviderTimestamp
    bid_exchange_code: str | None
    ask_exchange_code: str | None
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal | None
    ask_size: Decimal | None
    time_nano_part: int
    size_semantics: QuoteSizeSemantics


@dataclass(frozen=True, slots=True)
class ContextTopOfBookPayload:
    action: str
    side: str
    depth: int
    event_price: Decimal | None
    event_size: int
    bid_price: Decimal | None
    ask_price: Decimal | None
    bid_size: int
    ask_size: int
    bid_count: int
    ask_count: int
    flags: int
    ts_in_delta_ns: int
    quantity_semantics: ContextQuantitySemantics
    role: ContextMarketRole


MarketPayload: TypeAlias = TradePayload | OrderBookPayload | QuotePayload | ContextTopOfBookPayload


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


@dataclass(frozen=True, slots=True)
class ProviderQuoteEnvelope:
    kind: MarketEventKind
    instrument: ProviderInstrument
    sequence_id: str
    provider_event_time: ProviderTimestamp | None
    received_at_ns: int
    payload: QuotePayload
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderContextEnvelope:
    kind: MarketEventKind
    instrument: ProviderInstrument
    sequence_id: str
    provider_event_time: ProviderTimestamp | None
    provider_receive_time: ProviderTimestamp
    received_at_ns: int
    publisher_id: int
    provider_instrument_id: int
    payload: ContextTopOfBookPayload
    metadata: tuple[tuple[str, str], ...] = ()


ProviderMarketEnvelope: TypeAlias = (
    ProviderEventEnvelope | ProviderQuoteEnvelope | ProviderContextEnvelope
)
