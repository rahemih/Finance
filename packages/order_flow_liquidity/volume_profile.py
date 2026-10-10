from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .trade_flow import TradeFlowPolicy, TradePrint, validate_trade_print


class VolumeProfileError(ValueError):
    """Raised when P09-C Volume Profile invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VolumeProfileError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VolumeProfileError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise VolumeProfileError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise VolumeProfileError(f"{field} must be a positive integer")
    return value


def _bps(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10_000:
        raise VolumeProfileError(f"{field} must be integer basis points in [1,10000]")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise VolumeProfileError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise VolumeProfileError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise VolumeProfileError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class VolumeProfilePolicy:
    value_area_target_bps: int
    max_profile_bucket_count: int
    require_contiguous_sequence: bool
    require_actual_trade_prints: bool
    poc_tie_break: str
    value_area_tie_break: str
    quote_activity_profile_allowed: bool
    tick_volume_profile_allowed: bool
    forex_spot_global_profile_claim_allowed: bool
    direct_trade_output_allowed: bool
    production_order_flow_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "VolumeProfilePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise VolumeProfileError("unsupported policy schema_version")

        target = _bps(raw.get("value_area_target_bps"), field="value_area_target_bps")
        max_buckets = _positive_int(raw.get("max_profile_bucket_count"), field="max_profile_bucket_count")
        contiguous = _boolean(raw.get("require_contiguous_sequence"), field="require_contiguous_sequence")
        actual = _boolean(raw.get("require_actual_trade_prints"), field="require_actual_trade_prints")
        poc_tie = _text(raw.get("poc_tie_break"), field="poc_tie_break").upper()
        va_tie = _text(raw.get("value_area_tie_break"), field="value_area_tie_break").upper()
        quote_proxy = _boolean(raw.get("quote_activity_profile_allowed"), field="quote_activity_profile_allowed")
        tick_proxy = _boolean(raw.get("tick_volume_profile_allowed"), field="tick_volume_profile_allowed")
        fx_global = _boolean(
            raw.get("forex_spot_global_profile_claim_allowed"),
            field="forex_spot_global_profile_claim_allowed",
        )
        direct = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(raw.get("production_order_flow_vendor"), field="production_order_flow_vendor")

        if not actual:
            raise VolumeProfileError("P09-C requires actual trade prints")
        if poc_tie != "LOWEST_PRICE":
            raise VolumeProfileError("unsupported POC tie-break")
        if va_tie != "LOWER_PRICE":
            raise VolumeProfileError("unsupported value-area tie-break")
        if quote_proxy or tick_proxy:
            raise VolumeProfileError("P09-C forbids quote/tick proxy profiles")
        if fx_global:
            raise VolumeProfileError("P09-C forbids global/consolidated spot-FX profile claims")
        if direct:
            raise VolumeProfileError("P09-C forbids direct trade output")

        return cls(
            value_area_target_bps=target,
            max_profile_bucket_count=max_buckets,
            require_contiguous_sequence=contiguous,
            require_actual_trade_prints=actual,
            poc_tie_break=poc_tie,
            value_area_tie_break=va_tie,
            quote_activity_profile_allowed=quote_proxy,
            tick_volume_profile_allowed=tick_proxy,
            forex_spot_global_profile_claim_allowed=fx_global,
            direct_trade_output_allowed=direct,
            production_order_flow_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class VolumeProfileBucket:
    bucket_index: int
    lower_price_text: str
    upper_price_text: str
    volume_text: str

    @property
    def volume(self) -> Decimal:
        return Decimal(self.volume_text)

    def payload(self) -> dict[str, object]:
        return {
            "bucket_index": self.bucket_index,
            "lower_price_text": self.lower_price_text,
            "upper_price_text": self.upper_price_text,
            "volume_text": self.volume_text,
        }


@dataclass(frozen=True, slots=True)
class VolumeProfileSnapshot:
    symbol: str
    market_class: str
    provider: str
    venue: str
    source_kind: str
    coverage_scope: str
    profile_id: str
    first_sequence: int
    last_sequence: int
    trade_count: int
    bucket_size_text: str
    bucket_origin_text: str
    total_volume_text: str
    min_price_text: str
    max_price_text: str
    poc_price_text: str
    value_area_low_text: str
    value_area_high_text: str
    value_area_target_bps: int
    value_area_achieved_bps: int
    buckets: tuple[VolumeProfileBucket, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "market_class": self.market_class,
            "provider": self.provider,
            "venue": self.venue,
            "source_kind": self.source_kind,
            "coverage_scope": self.coverage_scope,
            "profile_id": self.profile_id,
            "first_sequence": self.first_sequence,
            "last_sequence": self.last_sequence,
            "trade_count": self.trade_count,
            "bucket_size_text": self.bucket_size_text,
            "bucket_origin_text": self.bucket_origin_text,
            "total_volume_text": self.total_volume_text,
            "min_price_text": self.min_price_text,
            "max_price_text": self.max_price_text,
            "poc_price_text": self.poc_price_text,
            "value_area_low_text": self.value_area_low_text,
            "value_area_high_text": self.value_area_high_text,
            "value_area_target_bps": self.value_area_target_bps,
            "value_area_achieved_bps": self.value_area_achieved_bps,
            "buckets": [bucket.payload() for bucket in self.buckets],
        }

    @property
    def snapshot_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def build_volume_profile(
    trades: Sequence[TradePrint],
    *,
    profile_id: str,
    bucket_size_text: str,
    bucket_origin_text: str,
    profile_policy: VolumeProfilePolicy,
    trade_policy: TradeFlowPolicy,
) -> VolumeProfileSnapshot:
    if not trades:
        raise VolumeProfileError("Volume Profile requires at least one trade print")

    profile_name = _text(profile_id, field="profile_id")
    bucket_size = _decimal(bucket_size_text, field="bucket_size")
    bucket_origin = _decimal(bucket_origin_text, field="bucket_origin")
    if bucket_size <= 0:
        raise VolumeProfileError("bucket_size must be positive")

    first = validate_trade_print(trades[0], policy=trade_policy)
    symbol = first.symbol
    market_class = first.market_class
    provider = first.provider
    venue = first.venue
    source_kind = first.source_kind
    coverage_scope = first.coverage_scope

    volumes: dict[int, Decimal] = {}
    total = Decimal("0")
    min_price = first.price
    max_price = first.price
    previous_sequence: int | None = None
    previous_event_time: int | None = None

    for trade in trades:
        validate_trade_print(trade, policy=trade_policy)
        if (
            trade.symbol != symbol
            or trade.market_class != market_class
            or trade.provider != provider
            or trade.venue != venue
            or trade.source_kind != source_kind
            or trade.coverage_scope != coverage_scope
        ):
            raise VolumeProfileError("Volume Profile cannot mix source streams")

        if previous_sequence is not None:
            if trade.sequence <= previous_sequence:
                raise VolumeProfileError("trade sequence must be strictly increasing")
            if profile_policy.require_contiguous_sequence and trade.sequence != previous_sequence + 1:
                raise VolumeProfileError("Volume Profile reference stream requires contiguous sequence")
        if previous_event_time is not None and trade.event_time_ns < previous_event_time:
            raise VolumeProfileError("trade event time must be non-decreasing")

        relative = (trade.price - bucket_origin) / bucket_size
        bucket_index = int(relative.to_integral_value(rounding=ROUND_FLOOR))
        volumes[bucket_index] = volumes.get(bucket_index, Decimal("0")) + trade.size
        total += trade.size
        min_price = min(min_price, trade.price)
        max_price = max(max_price, trade.price)
        previous_sequence = trade.sequence
        previous_event_time = trade.event_time_ns

    min_index = min(volumes)
    max_index = max(volumes)
    bucket_count = max_index - min_index + 1
    if bucket_count > profile_policy.max_profile_bucket_count:
        raise VolumeProfileError("Volume Profile bucket span exceeds policy maximum")

    buckets: list[VolumeProfileBucket] = []
    for index in range(min_index, max_index + 1):
        lower = bucket_origin + (bucket_size * Decimal(index))
        upper = lower + bucket_size
        volume = volumes.get(index, Decimal("0"))
        buckets.append(
            VolumeProfileBucket(
                bucket_index=index,
                lower_price_text=_decimal_text(lower),
                upper_price_text=_decimal_text(upper),
                volume_text=_decimal_text(volume),
            )
        )

    max_volume = max(bucket.volume for bucket in buckets)
    poc_position = next(i for i, bucket in enumerate(buckets) if bucket.volume == max_volume)

    selected = {poc_position}
    cumulative = buckets[poc_position].volume
    left = poc_position - 1
    right = poc_position + 1
    while cumulative * Decimal(10_000) < total * Decimal(profile_policy.value_area_target_bps):
        left_volume = buckets[left].volume if left >= 0 else Decimal("-1")
        right_volume = buckets[right].volume if right < len(buckets) else Decimal("-1")
        if left_volume < 0 and right_volume < 0:
            raise VolumeProfileError("value-area target cannot be satisfied")

        if left_volume >= right_volume:
            selected.add(left)
            cumulative += left_volume
            left -= 1
        else:
            selected.add(right)
            cumulative += right_volume
            right += 1

    low_position = min(selected)
    high_position = max(selected)
    achieved_bps = int(
        ((cumulative * Decimal(10_000)) / total).to_integral_value(rounding=ROUND_FLOOR)
    )

    return VolumeProfileSnapshot(
        symbol=symbol,
        market_class=market_class,
        provider=provider,
        venue=venue,
        source_kind=source_kind,
        coverage_scope=coverage_scope,
        profile_id=profile_name,
        first_sequence=trades[0].sequence,
        last_sequence=trades[-1].sequence,
        trade_count=len(trades),
        bucket_size_text=_decimal_text(bucket_size),
        bucket_origin_text=_decimal_text(bucket_origin),
        total_volume_text=_decimal_text(total),
        min_price_text=_decimal_text(min_price),
        max_price_text=_decimal_text(max_price),
        poc_price_text=buckets[poc_position].lower_price_text,
        value_area_low_text=buckets[low_position].lower_price_text,
        value_area_high_text=buckets[high_position].upper_price_text,
        value_area_target_bps=profile_policy.value_area_target_bps,
        value_area_achieved_bps=achieved_bps,
        buckets=tuple(buckets),
    )


def assert_no_profile_trade_authority_fields() -> None:
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
    }
    contract_fields = {field.name for field in fields(VolumeProfileSnapshot)}
    if forbidden & contract_fields:
        raise VolumeProfileError("Volume Profile contract must not expose trade/order authority fields")
