from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class TradeFlowError(ValueError):
    """Raised when P09-B trade-flow invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TradeFlowError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TradeFlowError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TradeFlowError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise TradeFlowError(f"{field} must be boolean")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TradeFlowError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise TradeFlowError(f"{field} must be a positive integer")
    return value


def _bps(value: object, *, field: str, maximum: int = 10_000) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise TradeFlowError(f"{field} must be integer basis points in [0,{maximum}]")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise TradeFlowError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise TradeFlowError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise TradeFlowError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise TradeFlowError(f"{field} must be lowercase sha256 hex")
    return text


@dataclass(frozen=True, slots=True)
class TradeFlowPolicy:
    allowed_market_classes: tuple[str, ...]
    allowed_trade_source_kinds: tuple[str, ...]
    forex_spot_allowed_trade_source_kinds: tuple[str, ...]
    allowed_classification_methods: tuple[str, ...]
    max_classification_confidence_bps: int
    require_contiguous_sequence_for_cvd: bool
    quote_updates_as_trade_prints_allowed: bool
    tick_volume_as_trade_prints_allowed: bool
    forex_spot_global_flow_claim_allowed: bool
    direct_trade_output_allowed: bool
    production_order_flow_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "TradeFlowPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise TradeFlowError("unsupported policy schema_version")

        market_classes = tuple(
            _text(item, field="allowed_market_class")
            for item in _object_list(raw.get("allowed_market_classes"), field="allowed_market_classes")
        )
        source_kinds = tuple(
            _text(item, field="allowed_trade_source_kind")
            for item in _object_list(
                raw.get("allowed_trade_source_kinds"),
                field="allowed_trade_source_kinds",
            )
        )
        forex_source_kinds = tuple(
            _text(item, field="forex_spot_allowed_trade_source_kind")
            for item in _object_list(
                raw.get("forex_spot_allowed_trade_source_kinds"),
                field="forex_spot_allowed_trade_source_kinds",
            )
        )
        methods = tuple(
            _text(item, field="allowed_classification_method")
            for item in _object_list(
                raw.get("allowed_classification_methods"),
                field="allowed_classification_methods",
            )
        )
        if not market_classes or not source_kinds or not forex_source_kinds or not methods:
            raise TradeFlowError("policy enumerations must be non-empty")

        max_confidence = _bps(
            raw.get("max_classification_confidence_bps"),
            field="max_classification_confidence_bps",
        )
        contiguous = _boolean(
            raw.get("require_contiguous_sequence_for_cvd"),
            field="require_contiguous_sequence_for_cvd",
        )
        quote_as_trade = _boolean(
            raw.get("quote_updates_as_trade_prints_allowed"),
            field="quote_updates_as_trade_prints_allowed",
        )
        tick_as_trade = _boolean(
            raw.get("tick_volume_as_trade_prints_allowed"),
            field="tick_volume_as_trade_prints_allowed",
        )
        global_fx = _boolean(
            raw.get("forex_spot_global_flow_claim_allowed"),
            field="forex_spot_global_flow_claim_allowed",
        )
        direct_trade = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(raw.get("production_order_flow_vendor"), field="production_order_flow_vendor")

        if quote_as_trade or tick_as_trade:
            raise TradeFlowError("P09-B forbids quote/tick proxies from becoming trade prints")
        if global_fx:
            raise TradeFlowError("P09-B forbids global/consolidated spot-FX flow claims")
        if direct_trade:
            raise TradeFlowError("P09-B forbids direct trade output")

        return cls(
            allowed_market_classes=market_classes,
            allowed_trade_source_kinds=source_kinds,
            forex_spot_allowed_trade_source_kinds=forex_source_kinds,
            allowed_classification_methods=methods,
            max_classification_confidence_bps=max_confidence,
            require_contiguous_sequence_for_cvd=contiguous,
            quote_updates_as_trade_prints_allowed=quote_as_trade,
            tick_volume_as_trade_prints_allowed=tick_as_trade,
            forex_spot_global_flow_claim_allowed=global_fx,
            direct_trade_output_allowed=direct_trade,
            production_order_flow_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class TradePrint:
    symbol: str
    market_class: str
    source_kind: str
    provider: str
    venue: str
    price_text: str
    size_text: str
    event_time_ns: int
    sequence: int
    coverage_scope: str
    source_dataset_version: str
    quality_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text(self.symbol, field="symbol"))
        object.__setattr__(self, "market_class", _text(self.market_class, field="market_class"))
        object.__setattr__(self, "source_kind", _text(self.source_kind, field="source_kind"))
        object.__setattr__(self, "provider", _text(self.provider, field="provider"))
        object.__setattr__(self, "venue", _text(self.venue, field="venue"))
        price = _decimal(self.price_text, field="price")
        size = _decimal(self.size_text, field="size")
        if price <= 0:
            raise TradeFlowError("trade price must be positive")
        if size <= 0:
            raise TradeFlowError("trade size must be positive")
        object.__setattr__(self, "price_text", _decimal_text(price))
        object.__setattr__(self, "size_text", _decimal_text(size))
        object.__setattr__(self, "event_time_ns", _non_negative_int(self.event_time_ns, field="event_time_ns"))
        object.__setattr__(self, "sequence", _positive_int(self.sequence, field="sequence"))
        object.__setattr__(self, "coverage_scope", _text(self.coverage_scope, field="coverage_scope"))
        object.__setattr__(
            self,
            "source_dataset_version",
            _sha256_text(self.source_dataset_version, field="source_dataset_version"),
        )
        object.__setattr__(
            self,
            "quality_evidence_sha256",
            _sha256_text(self.quality_evidence_sha256, field="quality_evidence_sha256"),
        )

    @property
    def price(self) -> Decimal:
        return Decimal(self.price_text)

    @property
    def size(self) -> Decimal:
        return Decimal(self.size_text)

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "market_class": self.market_class,
            "source_kind": self.source_kind,
            "provider": self.provider,
            "venue": self.venue,
            "price_text": self.price_text,
            "size_text": self.size_text,
            "event_time_ns": self.event_time_ns,
            "sequence": self.sequence,
            "coverage_scope": self.coverage_scope,
            "source_dataset_version": self.source_dataset_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
        }

    @property
    def trade_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class QuoteContext:
    bid_text: str
    ask_text: str
    as_of_time_ns: int

    def __post_init__(self) -> None:
        bid = _decimal(self.bid_text, field="bid")
        ask = _decimal(self.ask_text, field="ask")
        if bid <= 0 or ask <= 0 or bid > ask:
            raise TradeFlowError("quote must satisfy 0 < bid <= ask")
        object.__setattr__(self, "bid_text", _decimal_text(bid))
        object.__setattr__(self, "ask_text", _decimal_text(ask))
        object.__setattr__(self, "as_of_time_ns", _non_negative_int(self.as_of_time_ns, field="as_of_time_ns"))

    @property
    def bid(self) -> Decimal:
        return Decimal(self.bid_text)

    @property
    def ask(self) -> Decimal:
        return Decimal(self.ask_text)


@dataclass(frozen=True, slots=True)
class ClassifiedTrade:
    trade: TradePrint
    aggressor_side: str
    classification_method: str
    classification_confidence_bps: int

    def __post_init__(self) -> None:
        side = _text(self.aggressor_side, field="aggressor_side").upper()
        method = _text(self.classification_method, field="classification_method").upper()
        if side not in {"BUY", "SELL", "UNKNOWN"}:
            raise TradeFlowError("aggressor_side must be BUY, SELL or UNKNOWN")
        confidence = _bps(self.classification_confidence_bps, field="classification_confidence_bps")
        if side == "UNKNOWN" and (method != "UNCLASSIFIED" or confidence != 0):
            raise TradeFlowError("UNKNOWN aggressor side must be UNCLASSIFIED with zero confidence")
        if side != "UNKNOWN" and method == "UNCLASSIFIED":
            raise TradeFlowError("classified aggressor side cannot use UNCLASSIFIED method")
        object.__setattr__(self, "aggressor_side", side)
        object.__setattr__(self, "classification_method", method)
        object.__setattr__(self, "classification_confidence_bps", confidence)

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "trade_id": self.trade.trade_id,
            "aggressor_side": self.aggressor_side,
            "classification_method": self.classification_method,
            "classification_confidence_bps": self.classification_confidence_bps,
        }

    @property
    def classification_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class FlowSnapshot:
    symbol: str
    provider: str
    venue: str
    source_kind: str
    coverage_scope: str
    stream_id: str
    first_sequence: int
    last_sequence: int
    trade_count: int
    buy_volume_text: str
    sell_volume_text: str
    unclassified_volume_text: str
    delta_text: str
    cvd_start_text: str
    cvd_end_text: str
    classification_coverage_bps: int
    weighted_classification_confidence_bps: int

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "provider": self.provider,
            "venue": self.venue,
            "source_kind": self.source_kind,
            "coverage_scope": self.coverage_scope,
            "stream_id": self.stream_id,
            "first_sequence": self.first_sequence,
            "last_sequence": self.last_sequence,
            "trade_count": self.trade_count,
            "buy_volume_text": self.buy_volume_text,
            "sell_volume_text": self.sell_volume_text,
            "unclassified_volume_text": self.unclassified_volume_text,
            "delta_text": self.delta_text,
            "cvd_start_text": self.cvd_start_text,
            "cvd_end_text": self.cvd_end_text,
            "classification_coverage_bps": self.classification_coverage_bps,
            "weighted_classification_confidence_bps": self.weighted_classification_confidence_bps,
        }

    @property
    def snapshot_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_trade_print(trade: TradePrint, *, policy: TradeFlowPolicy) -> TradePrint:
    if trade.market_class not in policy.allowed_market_classes:
        raise TradeFlowError("market_class is not allowed by policy")
    if trade.source_kind not in policy.allowed_trade_source_kinds:
        raise TradeFlowError("source_kind is not a governed trade-print source")

    if trade.market_class == "FOREX_SPOT":
        if trade.source_kind not in policy.forex_spot_allowed_trade_source_kinds:
            raise TradeFlowError("spot-FX trade flow must be broker/ECN scoped")
        scope_upper = trade.coverage_scope.upper()
        if "GLOBAL" in scope_upper or "CONSOLIDATED" in scope_upper or "TOTAL_MARKET" in scope_upper:
            raise TradeFlowError("spot-FX trade flow cannot claim global/consolidated coverage")

    return trade


def _classified(
    trade: TradePrint,
    *,
    side: str,
    method: str,
    confidence_bps: int,
    policy: TradeFlowPolicy,
) -> ClassifiedTrade:
    validate_trade_print(trade, policy=policy)
    if method not in policy.allowed_classification_methods:
        raise TradeFlowError("classification method is not allowed by policy")
    if confidence_bps > policy.max_classification_confidence_bps:
        raise TradeFlowError("classification confidence exceeds policy maximum")
    return ClassifiedTrade(
        trade=trade,
        aggressor_side=side,
        classification_method=method,
        classification_confidence_bps=confidence_bps,
    )


def classify_native_aggressor(
    trade: TradePrint,
    *,
    side: str,
    confidence_bps: int,
    policy: TradeFlowPolicy,
) -> ClassifiedTrade:
    normalized = side.upper()
    if normalized not in {"BUY", "SELL"}:
        raise TradeFlowError("native aggressor flag must be BUY or SELL")
    return _classified(
        trade,
        side=normalized,
        method="NATIVE_AGGRESSOR_FLAG",
        confidence_bps=confidence_bps,
        policy=policy,
    )


def classify_quote_test(
    trade: TradePrint,
    *,
    quote: QuoteContext,
    confidence_bps: int,
    policy: TradeFlowPolicy,
) -> ClassifiedTrade:
    validate_trade_print(trade, policy=policy)
    if quote.as_of_time_ns > trade.event_time_ns:
        raise TradeFlowError("quote-test context cannot come from the future")
    if trade.price >= quote.ask:
        side = "BUY"
    elif trade.price <= quote.bid:
        side = "SELL"
    else:
        return _classified(
            trade,
            side="UNKNOWN",
            method="UNCLASSIFIED",
            confidence_bps=0,
            policy=policy,
        )
    return _classified(
        trade,
        side=side,
        method="QUOTE_TEST",
        confidence_bps=confidence_bps,
        policy=policy,
    )


def classify_tick_rule(
    trade: TradePrint,
    *,
    previous_trade: TradePrint,
    confidence_bps: int,
    policy: TradeFlowPolicy,
) -> ClassifiedTrade:
    validate_trade_print(trade, policy=policy)
    validate_trade_print(previous_trade, policy=policy)
    if (
        trade.symbol != previous_trade.symbol
        or trade.provider != previous_trade.provider
        or trade.venue != previous_trade.venue
        or trade.source_kind != previous_trade.source_kind
    ):
        raise TradeFlowError("tick-rule context must belong to the same source stream")
    if previous_trade.sequence >= trade.sequence or previous_trade.event_time_ns > trade.event_time_ns:
        raise TradeFlowError("tick-rule context must strictly precede the trade")
    if trade.price > previous_trade.price:
        side = "BUY"
    elif trade.price < previous_trade.price:
        side = "SELL"
    else:
        return _classified(
            trade,
            side="UNKNOWN",
            method="UNCLASSIFIED",
            confidence_bps=0,
            policy=policy,
        )
    return _classified(
        trade,
        side=side,
        method="TICK_RULE",
        confidence_bps=confidence_bps,
        policy=policy,
    )


def classify_unknown(trade: TradePrint, *, policy: TradeFlowPolicy) -> ClassifiedTrade:
    return _classified(
        trade,
        side="UNKNOWN",
        method="UNCLASSIFIED",
        confidence_bps=0,
        policy=policy,
    )


def build_flow_snapshot(
    trades: Sequence[ClassifiedTrade],
    *,
    stream_id: str,
    cvd_start_text: str,
    policy: TradeFlowPolicy,
) -> FlowSnapshot:
    if not trades:
        raise TradeFlowError("trade-flow snapshot requires at least one trade")
    stream = _text(stream_id, field="stream_id")
    cvd_start = _decimal(cvd_start_text, field="cvd_start")

    first = trades[0]
    validate_trade_print(first.trade, policy=policy)
    symbol = first.trade.symbol
    provider = first.trade.provider
    venue = first.trade.venue
    source_kind = first.trade.source_kind
    coverage_scope = first.trade.coverage_scope

    buy = Decimal("0")
    sell = Decimal("0")
    unknown = Decimal("0")
    weighted_confidence = Decimal("0")
    classified = Decimal("0")
    total = Decimal("0")
    previous_sequence: int | None = None
    previous_event_time: int | None = None

    for item in trades:
        validate_trade_print(item.trade, policy=policy)
        if item.classification_method not in policy.allowed_classification_methods:
            raise TradeFlowError("classification method is not allowed by policy")
        if item.classification_confidence_bps > policy.max_classification_confidence_bps:
            raise TradeFlowError("classification confidence exceeds policy maximum")
        if (
            item.trade.symbol != symbol
            or item.trade.provider != provider
            or item.trade.venue != venue
            or item.trade.source_kind != source_kind
            or item.trade.coverage_scope != coverage_scope
        ):
            raise TradeFlowError("trade-flow snapshot cannot mix source streams")

        if previous_sequence is not None:
            if item.trade.sequence <= previous_sequence:
                raise TradeFlowError("trade sequence must be strictly increasing")
            if policy.require_contiguous_sequence_for_cvd and item.trade.sequence != previous_sequence + 1:
                raise TradeFlowError("CVD reference stream requires contiguous sequence")
        if previous_event_time is not None and item.trade.event_time_ns < previous_event_time:
            raise TradeFlowError("trade event time must be non-decreasing")

        size = item.trade.size
        total += size
        if item.aggressor_side == "BUY":
            buy += size
            classified += size
            weighted_confidence += size * Decimal(item.classification_confidence_bps)
        elif item.aggressor_side == "SELL":
            sell += size
            classified += size
            weighted_confidence += size * Decimal(item.classification_confidence_bps)
        else:
            unknown += size

        previous_sequence = item.trade.sequence
        previous_event_time = item.trade.event_time_ns

    delta = buy - sell
    cvd_end = cvd_start + delta
    coverage_bps = int(((classified * Decimal(10_000)) / total).to_integral_value(rounding=ROUND_FLOOR))
    if classified == 0:
        confidence_bps = 0
    else:
        confidence_bps = int((weighted_confidence / classified).to_integral_value(rounding=ROUND_FLOOR))

    return FlowSnapshot(
        symbol=symbol,
        provider=provider,
        venue=venue,
        source_kind=source_kind,
        coverage_scope=coverage_scope,
        stream_id=stream,
        first_sequence=trades[0].trade.sequence,
        last_sequence=trades[-1].trade.sequence,
        trade_count=len(trades),
        buy_volume_text=_decimal_text(buy),
        sell_volume_text=_decimal_text(sell),
        unclassified_volume_text=_decimal_text(unknown),
        delta_text=_decimal_text(delta),
        cvd_start_text=_decimal_text(cvd_start),
        cvd_end_text=_decimal_text(cvd_end),
        classification_coverage_bps=coverage_bps,
        weighted_classification_confidence_bps=confidence_bps,
    )


def assert_no_trade_authority_fields() -> None:
    forbidden = {"order", "quantity", "leverage", "stop_loss", "take_profit", "recommendation", "probability"}
    contract_fields = {field.name for field in fields(TradePrint)} | {field.name for field in fields(FlowSnapshot)}
    if forbidden & contract_fields:
        raise TradeFlowError("trade-flow contracts must not expose trade/order authority fields")
