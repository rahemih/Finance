from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import re
from typing import Mapping, Sequence, cast

from packages.contracts.market_data import (
    MarketEventKind,
    OrderBookLevel,
    OrderBookPayload,
    OrderBookUpdateType,
    ProviderEventEnvelope,
    ProviderInstrument,
    ProviderTimestamp,
    SequenceDisposition,
    TradePayload,
    TradeSide,
)


TRADE_ENDPOINT = "https://gateway-v0-http.kaiko.ovh/api/stream/market_update_v1"
ORDER_BOOK_L2_ENDPOINT = "https://gateway-v0-http.kaiko.ovh/api/stream/orderbookl2_v1"
API_KEY_HEADER = "X-Api-Key"

_TIMESTAMP_RE = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<fraction>\d{1,9}))?"
    r"(?P<zone>Z|[+-]\d{2}:\d{2})$"
)


class KaikoAdapterError(ValueError):
    """Provider payload/configuration is invalid for the Kaiko adapter contract."""


@dataclass(frozen=True, slots=True)
class KaikoSubscription:
    exchange: str
    instrument_class: str
    code: str
    credential_ref: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("exchange", self.exchange),
            ("instrument_class", self.instrument_class),
            ("code", self.code),
        ):
            if not value.strip():
                raise KaikoAdapterError(f"{field_name} must be non-empty")
        if not self.credential_ref.startswith("secret://"):
            raise KaikoAdapterError(
                "credential_ref must be a secret:// handle; raw API keys are forbidden"
            )


@dataclass(frozen=True, slots=True)
class KaikoRequestSpec:
    method: str
    url: str
    api_key_header: str
    credential_ref: str
    body_json: str


def _require_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise KaikoAdapterError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _require_sequence(value: object, *, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise KaikoAdapterError(f"{field} must be an array")
    return cast(Sequence[object], value)


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KaikoAdapterError(f"{field} must be a non-empty string")
    return value


def _optional_text(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise KaikoAdapterError(f"{field} must be a string when present")
    stripped = value.strip()
    return stripped or None


def _decimal(value: object, *, field: str, allow_zero: bool) -> Decimal:
    if isinstance(value, bool):
        raise KaikoAdapterError(f"{field} must be numeric")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise KaikoAdapterError(f"{field} must be numeric") from None
    if not number.is_finite():
        raise KaikoAdapterError(f"{field} must be finite")
    if allow_zero:
        if number < 0:
            raise KaikoAdapterError(f"{field} must be >= 0")
    elif number <= 0:
        raise KaikoAdapterError(f"{field} must be > 0")
    return number


def _timestamp_text(value: object, *, field: str) -> str:
    if isinstance(value, str):
        return _require_text(value, field=field)
    mapping = _require_mapping(value, field=field)
    return _require_text(mapping.get("value"), field=f"{field}.value")


def parse_provider_timestamp(value: object, *, field: str) -> ProviderTimestamp:
    raw = _timestamp_text(value, field=field)
    match = _TIMESTAMP_RE.fullmatch(raw)
    if match is None:
        raise KaikoAdapterError(f"{field} must be RFC3339 with <=9 fractional digits")

    zone = match.group("zone")
    normalized_zone = "+00:00" if zone == "Z" else zone
    try:
        dt = datetime.fromisoformat(match.group("base") + normalized_zone)
    except ValueError:
        raise KaikoAdapterError(f"{field} is not a valid calendar timestamp") from None

    utc_seconds = calendar.timegm(dt.utctimetuple())
    fraction = (match.group("fraction") or "").ljust(9, "0")
    epoch_ns = utc_seconds * 1_000_000_000 + int(fraction or "0")
    return ProviderTimestamp(raw=raw, epoch_ns=epoch_ns)


def _metadata(value: object) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    mapping = _require_mapping(value, field="additionalProperties")
    encoded: list[tuple[str, str]] = []
    for key in sorted(mapping):
        encoded.append(
            (
                key,
                json.dumps(
                    mapping[key],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
            )
        )
    return tuple(encoded)


def _trade_side(value: object) -> TradeSide:
    text = _require_text(value, field="side").upper()
    if text in {"BUY", "BID"}:
        return TradeSide.BUY
    if text in {"SELL", "ASK"}:
        return TradeSide.SELL
    return TradeSide.UNKNOWN


def _book_levels(value: object, *, field: str) -> tuple[OrderBookLevel, ...]:
    levels = _require_sequence(value, field=field)
    parsed: list[OrderBookLevel] = []
    for index, item in enumerate(levels):
        row = _require_mapping(item, field=f"{field}[{index}]")
        price = _decimal(row.get("price"), field=f"{field}[{index}].price", allow_zero=False)
        amount = _decimal(row.get("amount"), field=f"{field}[{index}].amount", allow_zero=True)
        parsed.append(OrderBookLevel(price=price, amount=amount))
    return tuple(parsed)


def _update_type(value: object) -> OrderBookUpdateType:
    text = _require_text(value, field="updateType").upper()
    if text == "SNAPSHOT":
        return OrderBookUpdateType.SNAPSHOT
    if text in {"UPDATE", "UPDATED"}:
        return OrderBookUpdateType.UPDATE
    raise KaikoAdapterError(f"unsupported updateType: {text}")


class KaikoLexicographicSequenceGuard:
    def __init__(self) -> None:
        self._last_by_stream: dict[str, str] = {}

    def observe(self, stream_id: str, sequence_id: str) -> SequenceDisposition:
        stream = _require_text(stream_id, field="stream_id")
        sequence = _require_text(sequence_id, field="sequence_id")
        previous = self._last_by_stream.get(stream)
        if previous is None:
            self._last_by_stream[stream] = sequence
            return SequenceDisposition.FIRST
        if sequence == previous:
            return SequenceDisposition.DUPLICATE
        if sequence < previous:
            return SequenceDisposition.OUT_OF_ORDER
        self._last_by_stream[stream] = sequence
        return SequenceDisposition.ADVANCING


class KaikoAdapter:
    def __init__(self, subscription: KaikoSubscription) -> None:
        self.subscription = subscription

    def _instrument(self, message: Mapping[str, object]) -> ProviderInstrument:
        exchange = _require_text(message.get("exchange"), field="exchange")
        instrument_class = _require_text(message.get("class"), field="class")
        code = _require_text(message.get("code"), field="code")
        if (
            exchange != self.subscription.exchange
            or instrument_class != self.subscription.instrument_class
            or code != self.subscription.code
        ):
            raise KaikoAdapterError(
                "provider message instrument does not match configured subscription"
            )
        return ProviderInstrument(
            provider="kaiko",
            exchange=exchange,
            instrument_class=instrument_class,
            code=code,
        )

    def _base_fields(
        self,
        message: Mapping[str, object],
        *,
        received_at_ns: int,
    ) -> tuple[
        ProviderInstrument,
        str,
        ProviderTimestamp,
        ProviderTimestamp,
        ProviderTimestamp,
        tuple[tuple[str, str], ...],
    ]:
        if isinstance(received_at_ns, bool) or received_at_ns < 0:
            raise KaikoAdapterError("received_at_ns must be a non-negative integer")
        instrument = self._instrument(message)
        sequence_id = _require_text(message.get("sequenceId"), field="sequenceId")
        return (
            instrument,
            sequence_id,
            parse_provider_timestamp(message.get("tsExchange"), field="tsExchange"),
            parse_provider_timestamp(message.get("tsCollection"), field="tsCollection"),
            parse_provider_timestamp(message.get("tsEvent"), field="tsEvent"),
            _metadata(message.get("additionalProperties")),
        )

    def parse_trade(
        self,
        message: Mapping[str, object],
        *,
        received_at_ns: int,
    ) -> ProviderEventEnvelope:
        (
            instrument,
            sequence_id,
            ts_exchange,
            ts_collection,
            ts_event,
            metadata,
        ) = self._base_fields(message, received_at_ns=received_at_ns)

        payload = TradePayload(
            trade_id=_optional_text(message.get("id"), field="id"),
            price=_decimal(message.get("price"), field="price", allow_zero=False),
            amount=_decimal(message.get("amount"), field="amount", allow_zero=False),
            side=_trade_side(message.get("side")),
        )
        return ProviderEventEnvelope(
            kind=MarketEventKind.TRADE,
            instrument=instrument,
            sequence_id=sequence_id,
            ts_exchange=ts_exchange,
            ts_collection=ts_collection,
            ts_event=ts_event,
            received_at_ns=received_at_ns,
            payload=payload,
            metadata=metadata,
        )

    def parse_order_book(
        self,
        message: Mapping[str, object],
        *,
        received_at_ns: int,
    ) -> ProviderEventEnvelope:
        (
            instrument,
            sequence_id,
            ts_exchange,
            ts_collection,
            ts_event,
            metadata,
        ) = self._base_fields(message, received_at_ns=received_at_ns)

        payload = OrderBookPayload(
            update_type=_update_type(message.get("updateType")),
            asks=_book_levels(message.get("asks"), field="asks"),
            bids=_book_levels(message.get("bids"), field="bids"),
        )
        return ProviderEventEnvelope(
            kind=MarketEventKind.ORDER_BOOK,
            instrument=instrument,
            sequence_id=sequence_id,
            ts_exchange=ts_exchange,
            ts_collection=ts_collection,
            ts_event=ts_event,
            received_at_ns=received_at_ns,
            payload=payload,
            metadata=metadata,
        )

    def trade_request_spec(self) -> KaikoRequestSpec:
        return self._request_spec(TRADE_ENDPOINT)

    def order_book_request_spec(self) -> KaikoRequestSpec:
        return self._request_spec(ORDER_BOOK_L2_ENDPOINT)

    def _request_spec(self, url: str) -> KaikoRequestSpec:
        body = {
            "data": {
                "callback_url": "http://localhost:0000/callback",
                "query": {
                    "instruments": [
                        {
                            "exchange": self.subscription.exchange,
                            "class": self.subscription.instrument_class,
                            "code": self.subscription.code,
                        }
                    ]
                },
            }
        }
        return KaikoRequestSpec(
            method="POST",
            url=url,
            api_key_header=API_KEY_HEADER,
            credential_ref=self.subscription.credential_ref,
            body_json=json.dumps(body, sort_keys=True, separators=(",", ":")),
        )
