from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .order_book import OrderBookPolicy, OrderBookSnapshot, validate_order_book


class LiquidityHeatmapError(ValueError):
    """Raised when P09-E liquidity heatmap invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LiquidityHeatmapError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise LiquidityHeatmapError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiquidityHeatmapError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise LiquidityHeatmapError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise LiquidityHeatmapError(f"{field} must be a positive integer")
    return value


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class LiquidityHeatmapPolicy:
    distance_bands_bps: tuple[int, ...]
    max_band_count: int
    require_in_scope_liquidity: bool
    displayed_capacity_only: bool
    hidden_liquidity_inference_allowed: bool
    fillability_claim_allowed: bool
    slippage_or_market_impact_claim_allowed: bool
    cross_provider_aggregation_allowed: bool
    forex_spot_global_liquidity_claim_allowed: bool
    direct_trade_output_allowed: bool
    production_order_flow_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "LiquidityHeatmapPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise LiquidityHeatmapError("unsupported policy schema_version")

        bands = tuple(
            _positive_int(item, field="distance_bands_bps item")
            for item in _object_list(raw.get("distance_bands_bps"), field="distance_bands_bps")
        )
        max_band_count = _positive_int(raw.get("max_band_count"), field="max_band_count")
        require_liquidity = _boolean(raw.get("require_in_scope_liquidity"), field="require_in_scope_liquidity")
        displayed_only = _boolean(raw.get("displayed_capacity_only"), field="displayed_capacity_only")
        hidden = _boolean(
            raw.get("hidden_liquidity_inference_allowed"),
            field="hidden_liquidity_inference_allowed",
        )
        fillability = _boolean(raw.get("fillability_claim_allowed"), field="fillability_claim_allowed")
        impact = _boolean(
            raw.get("slippage_or_market_impact_claim_allowed"),
            field="slippage_or_market_impact_claim_allowed",
        )
        cross_provider = _boolean(
            raw.get("cross_provider_aggregation_allowed"),
            field="cross_provider_aggregation_allowed",
        )
        fx_global = _boolean(
            raw.get("forex_spot_global_liquidity_claim_allowed"),
            field="forex_spot_global_liquidity_claim_allowed",
        )
        direct = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(raw.get("production_order_flow_vendor"), field="production_order_flow_vendor")

        if not bands:
            raise LiquidityHeatmapError("distance_bands_bps must be non-empty")
        if len(bands) > max_band_count:
            raise LiquidityHeatmapError("distance band count exceeds policy maximum")
        if any(bands[i] >= bands[i + 1] for i in range(len(bands) - 1)):
            raise LiquidityHeatmapError("distance bands must be strictly increasing")
        if not displayed_only:
            raise LiquidityHeatmapError("P09-E capacity must remain displayed-capacity only")
        if hidden:
            raise LiquidityHeatmapError("P09-E forbids hidden-liquidity inference")
        if fillability:
            raise LiquidityHeatmapError("P09-E forbids fillability claims")
        if impact:
            raise LiquidityHeatmapError("P09-E forbids slippage/market-impact claims")
        if cross_provider:
            raise LiquidityHeatmapError("P09-E forbids cross-provider aggregation")
        if fx_global:
            raise LiquidityHeatmapError("P09-E forbids global/consolidated spot-FX liquidity claims")
        if direct:
            raise LiquidityHeatmapError("P09-E forbids direct trade output")

        return cls(
            distance_bands_bps=bands,
            max_band_count=max_band_count,
            require_in_scope_liquidity=require_liquidity,
            displayed_capacity_only=displayed_only,
            hidden_liquidity_inference_allowed=hidden,
            fillability_claim_allowed=fillability,
            slippage_or_market_impact_claim_allowed=impact,
            cross_provider_aggregation_allowed=cross_provider,
            forex_spot_global_liquidity_claim_allowed=fx_global,
            direct_trade_output_allowed=direct,
            production_order_flow_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class LiquidityHeatmapBand:
    lower_distance_bps_exclusive: int
    upper_distance_bps_inclusive: int
    bid_size_text: str
    ask_size_text: str
    bid_notional_text: str
    ask_notional_text: str
    cumulative_bid_size_text: str
    cumulative_ask_size_text: str
    cumulative_bid_notional_text: str
    cumulative_ask_notional_text: str
    cumulative_total_notional_text: str
    bid_capacity_share_bps: int
    ask_capacity_share_bps: int

    def payload(self) -> dict[str, object]:
        return {
            "lower_distance_bps_exclusive": self.lower_distance_bps_exclusive,
            "upper_distance_bps_inclusive": self.upper_distance_bps_inclusive,
            "bid_size_text": self.bid_size_text,
            "ask_size_text": self.ask_size_text,
            "bid_notional_text": self.bid_notional_text,
            "ask_notional_text": self.ask_notional_text,
            "cumulative_bid_size_text": self.cumulative_bid_size_text,
            "cumulative_ask_size_text": self.cumulative_ask_size_text,
            "cumulative_bid_notional_text": self.cumulative_bid_notional_text,
            "cumulative_ask_notional_text": self.cumulative_ask_notional_text,
            "cumulative_total_notional_text": self.cumulative_total_notional_text,
            "bid_capacity_share_bps": self.bid_capacity_share_bps,
            "ask_capacity_share_bps": self.ask_capacity_share_bps,
        }


@dataclass(frozen=True, slots=True)
class LiquidityHeatmapSnapshot:
    source_snapshot_id: str
    symbol: str
    market_class: str
    provider: str
    venue: str
    source_kind: str
    coverage_scope: str
    event_time_ns: int
    as_of_time_ns: int
    mid_price_text: str
    max_distance_bps: int
    outside_bid_size_text: str
    outside_ask_size_text: str
    outside_bid_notional_text: str
    outside_ask_notional_text: str
    bands: tuple[LiquidityHeatmapBand, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "source_snapshot_id": self.source_snapshot_id,
            "symbol": self.symbol,
            "market_class": self.market_class,
            "provider": self.provider,
            "venue": self.venue,
            "source_kind": self.source_kind,
            "coverage_scope": self.coverage_scope,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "mid_price_text": self.mid_price_text,
            "max_distance_bps": self.max_distance_bps,
            "outside_bid_size_text": self.outside_bid_size_text,
            "outside_ask_size_text": self.outside_ask_size_text,
            "outside_bid_notional_text": self.outside_bid_notional_text,
            "outside_ask_notional_text": self.outside_ask_notional_text,
            "bands": [band.payload() for band in self.bands],
        }

    @property
    def heatmap_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _distance_bps(*, mid: Decimal, price: Decimal, side: str) -> Decimal:
    if side == "BID":
        distance = (mid - price) * Decimal(10_000) / mid
    elif side == "ASK":
        distance = (price - mid) * Decimal(10_000) / mid
    else:
        raise LiquidityHeatmapError("unsupported heatmap side")
    if distance < 0:
        raise LiquidityHeatmapError("book level is on the wrong side of midpoint")
    return distance


def build_liquidity_heatmap(
    snapshot: OrderBookSnapshot,
    *,
    heatmap_policy: LiquidityHeatmapPolicy,
    order_book_policy: OrderBookPolicy,
) -> LiquidityHeatmapSnapshot:
    book = validate_order_book(snapshot, policy=order_book_policy)
    best_bid = book.bids[0].price
    best_ask = book.asks[0].price
    mid = (best_bid + best_ask) / Decimal("2")
    bands = heatmap_policy.distance_bands_bps

    bid_size = [Decimal("0") for _ in bands]
    ask_size = [Decimal("0") for _ in bands]
    bid_notional = [Decimal("0") for _ in bands]
    ask_notional = [Decimal("0") for _ in bands]

    outside_bid_size = Decimal("0")
    outside_ask_size = Decimal("0")
    outside_bid_notional = Decimal("0")
    outside_ask_notional = Decimal("0")

    for side, levels in (("BID", book.bids), ("ASK", book.asks)):
        for level in levels:
            distance = _distance_bps(mid=mid, price=level.price, side=side)
            assigned: int | None = None
            for index, threshold in enumerate(bands):
                if distance <= Decimal(threshold):
                    assigned = index
                    break
            notional = level.price * level.size
            if assigned is None:
                if side == "BID":
                    outside_bid_size += level.size
                    outside_bid_notional += notional
                else:
                    outside_ask_size += level.size
                    outside_ask_notional += notional
                continue

            if side == "BID":
                bid_size[assigned] += level.size
                bid_notional[assigned] += notional
            else:
                ask_size[assigned] += level.size
                ask_notional[assigned] += notional

    cumulative_bid_size = Decimal("0")
    cumulative_ask_size = Decimal("0")
    cumulative_bid_notional = Decimal("0")
    cumulative_ask_notional = Decimal("0")
    output_bands: list[LiquidityHeatmapBand] = []

    for index, threshold in enumerate(bands):
        cumulative_bid_size += bid_size[index]
        cumulative_ask_size += ask_size[index]
        cumulative_bid_notional += bid_notional[index]
        cumulative_ask_notional += ask_notional[index]
        cumulative_total_notional = cumulative_bid_notional + cumulative_ask_notional

        if cumulative_total_notional > 0:
            bid_share = int(
                (
                    cumulative_bid_notional
                    * Decimal(10_000)
                    / cumulative_total_notional
                ).to_integral_value(rounding=ROUND_HALF_EVEN)
            )
            bid_share = min(10_000, max(0, bid_share))
            ask_share = 10_000 - bid_share
        else:
            bid_share = 0
            ask_share = 0

        output_bands.append(
            LiquidityHeatmapBand(
                lower_distance_bps_exclusive=0 if index == 0 else bands[index - 1],
                upper_distance_bps_inclusive=threshold,
                bid_size_text=_decimal_text(bid_size[index]),
                ask_size_text=_decimal_text(ask_size[index]),
                bid_notional_text=_decimal_text(bid_notional[index]),
                ask_notional_text=_decimal_text(ask_notional[index]),
                cumulative_bid_size_text=_decimal_text(cumulative_bid_size),
                cumulative_ask_size_text=_decimal_text(cumulative_ask_size),
                cumulative_bid_notional_text=_decimal_text(cumulative_bid_notional),
                cumulative_ask_notional_text=_decimal_text(cumulative_ask_notional),
                cumulative_total_notional_text=_decimal_text(cumulative_total_notional),
                bid_capacity_share_bps=bid_share,
                ask_capacity_share_bps=ask_share,
            )
        )

    if heatmap_policy.require_in_scope_liquidity:
        final_total = Decimal(output_bands[-1].cumulative_total_notional_text)
        if final_total <= 0:
            raise LiquidityHeatmapError("no displayed liquidity falls within the maximum distance band")

    return LiquidityHeatmapSnapshot(
        source_snapshot_id=book.snapshot_id,
        symbol=book.symbol,
        market_class=book.market_class,
        provider=book.provider,
        venue=book.venue,
        source_kind=book.source_kind,
        coverage_scope=book.coverage_scope,
        event_time_ns=book.event_time_ns,
        as_of_time_ns=book.as_of_time_ns,
        mid_price_text=_decimal_text(mid),
        max_distance_bps=bands[-1],
        outside_bid_size_text=_decimal_text(outside_bid_size),
        outside_ask_size_text=_decimal_text(outside_ask_size),
        outside_bid_notional_text=_decimal_text(outside_bid_notional),
        outside_ask_notional_text=_decimal_text(outside_ask_notional),
        bands=tuple(output_bands),
    )


def assert_no_heatmap_execution_authority_fields() -> None:
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
        "executable",
        "fill_probability",
        "fillability",
        "hidden_liquidity",
    }
    contract_fields = (
        {field.name for field in fields(LiquidityHeatmapBand)}
        | {field.name for field in fields(LiquidityHeatmapSnapshot)}
    )
    if forbidden & contract_fields:
        raise LiquidityHeatmapError("Liquidity Heatmap contracts must not expose execution-authority fields")
