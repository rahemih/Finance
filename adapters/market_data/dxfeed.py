from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping, cast

from packages.contracts.market_data import (
    MarketEventKind,
    ProviderInstrument,
    ProviderQuoteEnvelope,
    ProviderTimestamp,
    QuotePayload,
    QuoteSizeSemantics,
)


class DxFeedAdapterError(ValueError):
    """Provider payload/configuration is invalid for the dxFeed Quote contract."""


@dataclass(frozen=True, slots=True)
class DxFeedForexSubscription:
    symbol: str
    canonical_id: str
    credential_ref: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.symbol, field="symbol")
        _require_text(self.canonical_id, field="canonical_id")
        if self.credential_ref is not None:
            _require_secret_ref(self.credential_ref)


@dataclass(frozen=True, slots=True)
class DxFeedSubscriptionSpec:
    transport: str
    event_type: str
    symbol: str
    credential_ref: str | None
    endpoint_ref: str | None
    intended_use: str


def _require_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DxFeedAdapterError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DxFeedAdapterError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DxFeedAdapterError(f"{field} must be a string when present")
    stripped = value.strip()
    return stripped or None


def _require_secret_ref(value: object) -> str:
    text = _require_text(value, field="credential_ref")
    if not text.startswith("secret://") or text == "secret://":
        raise DxFeedAdapterError(
            "credential_ref must be a non-empty secret:// handle; raw tokens are forbidden"
        )
    return text


def _require_int(value: object, *, field: str, allow_zero: bool = True) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DxFeedAdapterError(f"{field} must be an integer")
    if allow_zero:
        if value < 0:
            raise DxFeedAdapterError(f"{field} must be >= 0")
    elif value <= 0:
        raise DxFeedAdapterError(f"{field} must be > 0")
    return value


def _price(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise DxFeedAdapterError(f"{field} must be numeric")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DxFeedAdapterError(f"{field} must be numeric") from None
    if not number.is_finite() or number <= 0:
        raise DxFeedAdapterError(f"{field} must be finite and > 0")
    return number


def _optional_size(value: object, *, field: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise DxFeedAdapterError(f"{field} must be numeric or NaN")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DxFeedAdapterError(f"{field} must be numeric or NaN") from None
    if number.is_nan():
        return None
    if not number.is_finite() or number < 0:
        raise DxFeedAdapterError(f"{field} must be finite and >= 0, or NaN")
    return number


def _millisecond_timestamp(value: object, *, field: str) -> ProviderTimestamp:
    milliseconds = _require_int(value, field=field)
    return ProviderTimestamp(raw=f"{milliseconds}ms", epoch_ns=milliseconds * 1_000_000)


def _event_time(value: object) -> ProviderTimestamp | None:
    milliseconds = _require_int(value, field="eventTime")
    if milliseconds == 0:
        return None
    return ProviderTimestamp(raw=f"{milliseconds}ms", epoch_ns=milliseconds * 1_000_000)


def _received_at(value: object) -> int:
    return _require_int(value, field="received_at_ns")


class DxFeedForexQuoteAdapter:
    def __init__(self, subscription: DxFeedForexSubscription) -> None:
        self.subscription = subscription

    def subscription_spec(self) -> DxFeedSubscriptionSpec:
        return DxFeedSubscriptionSpec(
            transport="DXLINK_WEBSOCKET_REFERENCE",
            event_type="Quote",
            symbol=self.subscription.symbol,
            credential_ref=self.subscription.credential_ref,
            endpoint_ref=None,
            intended_use="OFFLINE_CONTRACT_ONLY",
        )

    def _unwrap_quote(self, message: Mapping[str, object]) -> Mapping[str, object]:
        if "eventSymbol" in message:
            return message

        quote_bucket = _require_mapping(message.get("Quote"), field="Quote")
        candidate = quote_bucket.get(self.subscription.symbol)
        return _require_mapping(candidate, field=f"Quote[{self.subscription.symbol}]")

    def parse_quote(
        self,
        message: Mapping[str, object],
        *,
        received_at_ns: int,
    ) -> ProviderQuoteEnvelope:
        quote = self._unwrap_quote(message)
        symbol = _require_text(quote.get("eventSymbol"), field="eventSymbol")
        if symbol != self.subscription.symbol:
            raise DxFeedAdapterError(
                f"provider symbol mismatch: expected {self.subscription.symbol}, got {symbol}"
            )

        sequence = _require_int(quote.get("sequence"), field="sequence")
        time_nano_part = _require_int(quote.get("timeNanoPart"), field="timeNanoPart")

        payload = QuotePayload(
            bid_time=_millisecond_timestamp(quote.get("bidTime"), field="bidTime"),
            ask_time=_millisecond_timestamp(quote.get("askTime"), field="askTime"),
            bid_exchange_code=_optional_text(
                quote.get("bidExchangeCode"),
                field="bidExchangeCode",
            ),
            ask_exchange_code=_optional_text(
                quote.get("askExchangeCode"),
                field="askExchangeCode",
            ),
            bid_price=_price(quote.get("bidPrice"), field="bidPrice"),
            ask_price=_price(quote.get("askPrice"), field="askPrice"),
            bid_size=_optional_size(quote.get("bidSize"), field="bidSize"),
            ask_size=_optional_size(quote.get("askSize"), field="askSize"),
            time_nano_part=time_nano_part,
            size_semantics=QuoteSizeSemantics.PROVIDER_QUOTE_SIZE_NOT_GLOBAL_SPOT_FX_VOLUME,
        )

        return ProviderQuoteEnvelope(
            kind=MarketEventKind.QUOTE,
            instrument=ProviderInstrument(
                provider="dxfeed",
                exchange="COMPOSITE_OTC",
                instrument_class="forex_spot_otc",
                code=symbol,
            ),
            sequence_id=str(sequence),
            provider_event_time=_event_time(quote.get("eventTime")),
            received_at_ns=_received_at(received_at_ns),
            payload=payload,
            metadata=(
                ("canonical_id", self.subscription.canonical_id),
                ("provider_role", "INDEPENDENT_FX_QUOTE_REFERENCE"),
                ("transport", "DXLINK_WEBSOCKET_REFERENCE"),
                ("global_spot_fx_volume", "FORBIDDEN"),
                ("timestamp_precision", "SOURCE_PRESERVED_NO_SYNTHETIC_PRECISION"),
            ),
        )
