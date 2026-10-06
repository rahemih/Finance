from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, cast

from packages.contracts.market_data import (
    ContextMarketRole,
    ContextQuantitySemantics,
    ContextTopOfBookPayload,
    MarketEventKind,
    ProviderContextEnvelope,
    ProviderInstrument,
    ProviderTimestamp,
)


UNDEF_PRICE = 9_223_372_036_854_775_807
UNDEF_TIMESTAMP = 18_446_744_073_709_551_615
PRICE_SCALE = Decimal("1000000000")


class DatabentoAdapterError(ValueError):
    """Databento record/configuration is invalid for the governed P05-C contract."""


@dataclass(frozen=True, slots=True)
class DatabentoContextSubscription:
    canonical_id: str = "COMMODITY:GOLD:GC:FUTURES:COMEX"
    dataset: str = "GLBX.MDP3"
    schema: str = "mbp-1"
    symbol: str = "GC.v.0"
    stype_in: str = "continuous"
    credential_ref: str | None = None

    def __post_init__(self) -> None:
        for field, value in (
            ("canonical_id", self.canonical_id),
            ("dataset", self.dataset),
            ("schema", self.schema),
            ("symbol", self.symbol),
            ("stype_in", self.stype_in),
        ):
            _require_text(value, field=field)
        if self.credential_ref is not None:
            _require_secret_ref(self.credential_ref)


@dataclass(frozen=True, slots=True)
class DatabentoSubscriptionSpec:
    transport: str
    dataset: str
    schema: str
    symbol: str
    stype_in: str
    endpoint_ref: str | None
    credential_ref: str | None
    intended_use: str
    roll_lifecycle: str


def _require_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DatabentoAdapterError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatabentoAdapterError(f"{field} must be a non-empty string")
    return value.strip()


def _require_secret_ref(value: object) -> str:
    text = _require_text(value, field="credential_ref")
    if not text.startswith("secret://") or text == "secret://":
        raise DatabentoAdapterError(
            "credential_ref must be a non-empty secret:// handle; raw keys are forbidden"
        )
    return text


def _require_int(
    value: object,
    *,
    field: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DatabentoAdapterError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise DatabentoAdapterError(f"{field} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise DatabentoAdapterError(f"{field} must be <= {maximum}")
    return value


def _uint8(value: object, *, field: str) -> int:
    return _require_int(value, field=field, minimum=0, maximum=(1 << 8) - 1)


def _uint16(value: object, *, field: str, allow_zero: bool = True) -> int:
    return _require_int(
        value,
        field=field,
        minimum=0 if allow_zero else 1,
        maximum=(1 << 16) - 1,
    )


def _uint32(value: object, *, field: str, allow_zero: bool = True) -> int:
    return _require_int(
        value,
        field=field,
        minimum=0 if allow_zero else 1,
        maximum=(1 << 32) - 1,
    )


def _uint64(value: object, *, field: str, allow_zero: bool = True) -> int:
    return _require_int(
        value,
        field=field,
        minimum=0 if allow_zero else 1,
        maximum=(1 << 64) - 1,
    )


def _int32(value: object, *, field: str) -> int:
    return _require_int(
        value,
        field=field,
        minimum=-(1 << 31),
        maximum=(1 << 31) - 1,
    )


def _timestamp(value: object, *, field: str, allow_undefined: bool) -> ProviderTimestamp | None:
    raw = _uint64(value, field=field)
    if raw == UNDEF_TIMESTAMP:
        if allow_undefined:
            return None
        raise DatabentoAdapterError(f"{field} must be defined")
    return ProviderTimestamp(raw=f"{raw}ns", epoch_ns=raw)


def _price(value: object, *, field: str) -> Decimal | None:
    raw = _require_int(
        value,
        field=field,
        minimum=-(1 << 63),
        maximum=(1 << 63) - 1,
    )
    if raw == UNDEF_PRICE:
        return None
    price = Decimal(raw) / PRICE_SCALE
    if price <= 0:
        raise DatabentoAdapterError(f"{field} must be > 0 when defined")
    return price


def _action(value: object) -> str:
    action = _require_text(value, field="action").upper()
    if action not in {"A", "C", "M", "R", "T"}:
        raise DatabentoAdapterError("action must be one of A, C, M, R, T")
    return action


def _side(value: object) -> str:
    side = _require_text(value, field="side").upper()
    if side not in {"A", "B", "N"}:
        raise DatabentoAdapterError("side must be one of A, B, N")
    return side


class DatabentoGoldContextAdapter:
    def __init__(self, subscription: DatabentoContextSubscription | None = None) -> None:
        self.subscription = subscription or DatabentoContextSubscription()

    def subscription_spec(self) -> DatabentoSubscriptionSpec:
        return DatabentoSubscriptionSpec(
            transport="DATABENTO_LIVE_REFERENCE",
            dataset=self.subscription.dataset,
            schema=self.subscription.schema,
            symbol=self.subscription.symbol,
            stype_in=self.subscription.stype_in,
            endpoint_ref=None,
            credential_ref=self.subscription.credential_ref,
            intended_use="OFFLINE_CONTRACT_ONLY",
            roll_lifecycle="EXPLICIT_MAPPING_AND_RESUBSCRIBE_REQUIRED_LATER",
        )

    def parse_mbp1(
        self,
        message: Mapping[str, object],
        *,
        mapped_symbol: str,
        received_at_ns: int,
    ) -> ProviderContextEnvelope:
        record = _require_mapping(message, field="message")
        mapped = _require_text(mapped_symbol, field="mapped_symbol")
        if mapped == self.subscription.symbol:
            raise DatabentoAdapterError(
                "mapped_symbol must be a concrete contract, not the continuous subscription symbol"
            )
        local_receive = _uint64(received_at_ns, field="received_at_ns")
        if local_receive == UNDEF_TIMESTAMP:
            raise DatabentoAdapterError("received_at_ns must be defined")

        rtype = _uint8(record.get("rtype"), field="rtype")
        if rtype != 1:
            raise DatabentoAdapterError("rtype must be 1 for the MBP-1 baseline")

        ts_event = _timestamp(record.get("ts_event"), field="ts_event", allow_undefined=True)
        ts_recv = _timestamp(record.get("ts_recv"), field="ts_recv", allow_undefined=False)
        assert ts_recv is not None

        sequence = _uint32(record.get("sequence"), field="sequence")
        publisher_id = _uint16(record.get("publisher_id"), field="publisher_id", allow_zero=False)
        instrument_id = _uint32(record.get("instrument_id"), field="instrument_id", allow_zero=False)
        depth = _uint8(record.get("depth"), field="depth")
        if depth != 0:
            raise DatabentoAdapterError("depth must be 0 for the MBP-1 top-of-book baseline")
        flags = _uint8(record.get("flags"), field="flags")
        ts_in_delta = _int32(record.get("ts_in_delta"), field="ts_in_delta")
        action = _action(record.get("action"))
        side = _side(record.get("side"))
        event_size = _uint32(record.get("size"), field="size")

        levels_value = record.get("levels")
        if not isinstance(levels_value, list) or not levels_value:
            raise DatabentoAdapterError("levels must be a non-empty array")
        levels = cast(list[object], levels_value)
        level = _require_mapping(levels[0], field="levels[0]")

        bid_px = _price(level.get("bid_px"), field="bid_px")
        ask_px = _price(level.get("ask_px"), field="ask_px")
        bid_sz = _uint32(level.get("bid_sz"), field="bid_sz")
        ask_sz = _uint32(level.get("ask_sz"), field="ask_sz")
        bid_ct = _uint32(level.get("bid_ct"), field="bid_ct")
        ask_ct = _uint32(level.get("ask_ct"), field="ask_ct")
        if bid_px is not None and ask_px is not None and bid_px > ask_px:
            raise DatabentoAdapterError("defined bid price must be <= defined ask price")

        payload = ContextTopOfBookPayload(
            action=action,
            side=side,
            depth=depth,
            event_price=_price(record.get("price"), field="price"),
            event_size=event_size,
            bid_price=bid_px,
            ask_price=ask_px,
            bid_size=bid_sz,
            ask_size=ask_sz,
            bid_count=bid_ct,
            ask_count=ask_ct,
            flags=flags,
            ts_in_delta_ns=ts_in_delta,
            quantity_semantics=ContextQuantitySemantics.CENTRALIZED_FUTURES_VENUE_QUANTITY,
            role=ContextMarketRole.CONTEXT_ONLY,
        )

        return ProviderContextEnvelope(
            kind=MarketEventKind.CONTEXT_TOP_OF_BOOK,
            instrument=ProviderInstrument(
                provider="databento",
                exchange="COMEX",
                instrument_class="futures_context",
                code=mapped,
            ),
            sequence_id=str(sequence),
            provider_event_time=ts_event,
            provider_receive_time=ts_recv,
            received_at_ns=local_receive,
            publisher_id=publisher_id,
            provider_instrument_id=instrument_id,
            payload=payload,
            metadata=(
                ("canonical_id", self.subscription.canonical_id),
                ("dataset", self.subscription.dataset),
                ("schema", self.subscription.schema),
                ("subscription_symbol", self.subscription.symbol),
                ("stype_in", self.subscription.stype_in),
                ("mapped_symbol", mapped),
                ("continuous_mapping", "EXPLICIT"),
                ("trading_authority", "NONE"),
            ),
        )
