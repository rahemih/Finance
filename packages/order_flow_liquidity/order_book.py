from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class OrderBookError(ValueError):
    """Raised when P09-D Order Book invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise OrderBookError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise OrderBookError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrderBookError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise OrderBookError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise OrderBookError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise OrderBookError(f"{field} must be a non-negative integer")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise OrderBookError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OrderBookError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise OrderBookError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise OrderBookError(f"{field} must be lowercase sha256 hex")
    return text


@dataclass(frozen=True, slots=True)
class OrderBookPolicy:
    allowed_market_classes: tuple[str, ...]
    allowed_source_kinds: tuple[str, ...]
    forex_spot_allowed_source_kinds: tuple[str, ...]
    max_levels_per_side: int
    locked_or_crossed_book_allowed: bool
    forex_spot_global_book_claim_allowed: bool
    direct_trade_output_allowed: bool
    production_order_flow_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "OrderBookPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise OrderBookError("unsupported policy schema_version")
        markets = tuple(
            _text(item, field="allowed_market_class")
            for item in _object_list(raw.get("allowed_market_classes"), field="allowed_market_classes")
        )
        sources = tuple(
            _text(item, field="allowed_source_kind")
            for item in _object_list(raw.get("allowed_source_kinds"), field="allowed_source_kinds")
        )
        fx_sources = tuple(
            _text(item, field="forex_spot_allowed_source_kind")
            for item in _object_list(
                raw.get("forex_spot_allowed_source_kinds"),
                field="forex_spot_allowed_source_kinds",
            )
        )
        max_levels = _positive_int(raw.get("max_levels_per_side"), field="max_levels_per_side")
        crossed = _boolean(raw.get("locked_or_crossed_book_allowed"), field="locked_or_crossed_book_allowed")
        fx_global = _boolean(
            raw.get("forex_spot_global_book_claim_allowed"),
            field="forex_spot_global_book_claim_allowed",
        )
        direct = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(raw.get("production_order_flow_vendor"), field="production_order_flow_vendor")
        if not markets or not sources or not fx_sources:
            raise OrderBookError("policy enumerations must be non-empty")
        if crossed:
            raise OrderBookError("P09-D requires locked/crossed books to fail closed")
        if fx_global:
            raise OrderBookError("P09-D forbids global/consolidated spot-FX book claims")
        if direct:
            raise OrderBookError("P09-D forbids direct trade output")
        return cls(
            allowed_market_classes=markets,
            allowed_source_kinds=sources,
            forex_spot_allowed_source_kinds=fx_sources,
            max_levels_per_side=max_levels,
            locked_or_crossed_book_allowed=crossed,
            forex_spot_global_book_claim_allowed=fx_global,
            direct_trade_output_allowed=direct,
            production_order_flow_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    price_text: str
    size_text: str

    def __post_init__(self) -> None:
        price = _decimal(self.price_text, field="level price")
        size = _decimal(self.size_text, field="level size")
        if price <= 0 or size <= 0:
            raise OrderBookError("book level price and size must be positive")
        object.__setattr__(self, "price_text", _decimal_text(price))
        object.__setattr__(self, "size_text", _decimal_text(size))

    @property
    def price(self) -> Decimal:
        return Decimal(self.price_text)

    @property
    def size(self) -> Decimal:
        return Decimal(self.size_text)

    def payload(self) -> dict[str, object]:
        return {"price_text": self.price_text, "size_text": self.size_text}


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    symbol: str
    market_class: str
    source_kind: str
    provider: str
    venue: str
    event_time_ns: int
    as_of_time_ns: int
    sequence: int
    coverage_scope: str
    source_dataset_version: str
    quality_evidence_sha256: str
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "market_class": self.market_class,
            "source_kind": self.source_kind,
            "provider": self.provider,
            "venue": self.venue,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "sequence": self.sequence,
            "coverage_scope": self.coverage_scope,
            "source_dataset_version": self.source_dataset_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
            "bids": [level.payload() for level in self.bids],
            "asks": [level.payload() for level in self.asks],
        }

    @property
    def snapshot_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class OrderBookMetrics:
    snapshot_id: str
    depth_levels: int
    best_bid_text: str
    best_ask_text: str
    mid_price_text: str
    spread_text: str
    spread_bps: int
    bid_depth_text: str
    ask_depth_text: str
    imbalance_bps: int

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "snapshot_id": self.snapshot_id,
            "depth_levels": self.depth_levels,
            "best_bid_text": self.best_bid_text,
            "best_ask_text": self.best_ask_text,
            "mid_price_text": self.mid_price_text,
            "spread_text": self.spread_text,
            "spread_bps": self.spread_bps,
            "bid_depth_text": self.bid_depth_text,
            "ask_depth_text": self.ask_depth_text,
            "imbalance_bps": self.imbalance_bps,
        }

    @property
    def metrics_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_order_book(snapshot: OrderBookSnapshot, *, policy: OrderBookPolicy) -> OrderBookSnapshot:
    symbol = _text(snapshot.symbol, field="symbol")
    market_class = _text(snapshot.market_class, field="market_class")
    source_kind = _text(snapshot.source_kind, field="source_kind")
    provider = _text(snapshot.provider, field="provider")
    venue = _text(snapshot.venue, field="venue")
    coverage_scope = _text(snapshot.coverage_scope, field="coverage_scope")
    event_time = _non_negative_int(snapshot.event_time_ns, field="event_time_ns")
    as_of_time = _non_negative_int(snapshot.as_of_time_ns, field="as_of_time_ns")
    sequence = _positive_int(snapshot.sequence, field="sequence")
    dataset = _sha256_text(snapshot.source_dataset_version, field="source_dataset_version")
    quality = _sha256_text(snapshot.quality_evidence_sha256, field="quality_evidence_sha256")

    if event_time > as_of_time:
        raise OrderBookError("event_time_ns cannot exceed as_of_time_ns")
    if market_class not in policy.allowed_market_classes:
        raise OrderBookError("market_class is not allowed by policy")
    if source_kind not in policy.allowed_source_kinds:
        raise OrderBookError("source_kind is not allowed by policy")
    if not snapshot.bids or not snapshot.asks:
        raise OrderBookError("order book requires at least one bid and one ask")
    if len(snapshot.bids) > policy.max_levels_per_side or len(snapshot.asks) > policy.max_levels_per_side:
        raise OrderBookError("order book level count exceeds policy maximum")

    bid_prices = [level.price for level in snapshot.bids]
    ask_prices = [level.price for level in snapshot.asks]
    if any(bid_prices[i] <= bid_prices[i + 1] for i in range(len(bid_prices) - 1)):
        raise OrderBookError("bids must be strictly descending with unique prices")
    if any(ask_prices[i] >= ask_prices[i + 1] for i in range(len(ask_prices) - 1)):
        raise OrderBookError("asks must be strictly ascending with unique prices")
    if bid_prices[0] >= ask_prices[0]:
        raise OrderBookError("locked or crossed order book is not allowed")

    if market_class == "FOREX_SPOT":
        if source_kind not in policy.forex_spot_allowed_source_kinds:
            raise OrderBookError("spot-FX order book must be broker/ECN scoped")
        scope_upper = coverage_scope.upper()
        if "GLOBAL" in scope_upper or "CONSOLIDATED" in scope_upper or "TOTAL_MARKET" in scope_upper:
            raise OrderBookError("spot-FX order book cannot claim global/consolidated coverage")

    return OrderBookSnapshot(
        symbol=symbol,
        market_class=market_class,
        source_kind=source_kind,
        provider=provider,
        venue=venue,
        event_time_ns=event_time,
        as_of_time_ns=as_of_time,
        sequence=sequence,
        coverage_scope=coverage_scope,
        source_dataset_version=dataset,
        quality_evidence_sha256=quality,
        bids=tuple(snapshot.bids),
        asks=tuple(snapshot.asks),
    )


def compute_order_book_metrics(
    snapshot: OrderBookSnapshot,
    *,
    depth_levels: int,
    policy: OrderBookPolicy,
) -> OrderBookMetrics:
    book = validate_order_book(snapshot, policy=policy)
    depth = _positive_int(depth_levels, field="depth_levels")
    if depth > len(book.bids) or depth > len(book.asks):
        raise OrderBookError("depth_levels requires enough levels on both sides")

    best_bid = book.bids[0].price
    best_ask = book.asks[0].price
    spread = best_ask - best_bid
    mid = (best_ask + best_bid) / Decimal("2")
    spread_bps = int(
        ((spread * Decimal(10_000)) / mid).to_integral_value(rounding=ROUND_HALF_EVEN)
    )
    bid_depth = sum((level.size for level in book.bids[:depth]), Decimal("0"))
    ask_depth = sum((level.size for level in book.asks[:depth]), Decimal("0"))
    total_depth = bid_depth + ask_depth
    if total_depth <= 0:
        raise OrderBookError("combined depth must be positive")
    imbalance = (bid_depth - ask_depth) * Decimal(10_000) / total_depth
    imbalance_bps = int(imbalance.to_integral_value(rounding=ROUND_HALF_EVEN))
    if not -10_000 <= imbalance_bps <= 10_000:
        raise OrderBookError("imbalance basis points out of bounds")

    return OrderBookMetrics(
        snapshot_id=book.snapshot_id,
        depth_levels=depth,
        best_bid_text=_decimal_text(best_bid),
        best_ask_text=_decimal_text(best_ask),
        mid_price_text=_decimal_text(mid),
        spread_text=_decimal_text(spread),
        spread_bps=spread_bps,
        bid_depth_text=_decimal_text(bid_depth),
        ask_depth_text=_decimal_text(ask_depth),
        imbalance_bps=imbalance_bps,
    )


def assert_no_order_book_trade_authority_fields() -> None:
    forbidden = {
        "order",
        "quantity",
        "leverage",
        "stop_loss",
        "take_profit",
        "recommendation",
        "probability",
        "entry",
        "exit",
        "slippage",
        "market_impact",
    }
    contract_fields = (
        {field.name for field in fields(OrderBookSnapshot)}
        | {field.name for field in fields(OrderBookMetrics)}
    )
    if forbidden & contract_fields:
        raise OrderBookError("Order Book contracts must not expose trade/order authority fields")
