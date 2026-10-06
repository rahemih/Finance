from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
from typing import Mapping, cast


class RetentionCapacityError(ValueError):
    """Retention, capacity, compaction or cost input is invalid."""


_ALLOWED_RIGHTS = frozenset(
    {
        "RETENTION_ALLOWED",
        "RETENTION_ALLOWED_WITH_LIMIT",
        "RETENTION_FORBIDDEN",
        "RETENTION_UNVERIFIED",
    }
)
_ALLOWED_TIERS = frozenset({"HOT", "WARM", "COLD"})
_COST_UNRESOLVED = "UNRESOLVED_RATE_REQUIRED"


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RetentionCapacityError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RetentionCapacityError(f"{field} must be a non-empty string")
    return value.strip()


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RetentionCapacityError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    number = _non_negative_int(value, field=field)
    if number <= 0:
        raise RetentionCapacityError(f"{field} must be a positive integer")
    return number


def _positive_decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise RetentionCapacityError(f"{field} must be a positive decimal")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RetentionCapacityError(f"{field} must be a positive decimal") from exc
    if not number.is_finite() or number <= 0:
        raise RetentionCapacityError(f"{field} must be a positive decimal")
    return number


def _non_negative_decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise RetentionCapacityError(f"{field} must be a non-negative decimal")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RetentionCapacityError(f"{field} must be a non-negative decimal") from exc
    if not number.is_finite() or number < 0:
        raise RetentionCapacityError(f"{field} must be a non-negative decimal")
    return number


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return "0" if text == "-0" else text


@dataclass(frozen=True, slots=True)
class RetentionCapacityPolicy:
    seconds_per_day: int
    decimal_bytes_per_gb: int
    decimal_bytes_per_tb: int
    hot_days: int
    warm_min_days: int
    warm_max_days: int
    cold_min_days: int
    planning_compression_ratios: tuple[Decimal, ...]
    storage_growth_review_deviation_percent: Decimal
    reference_partition_seconds: int
    replay_scan_floor_mib_per_sec: Decimal
    feature_rebuild_floor_per_sec: Decimal
    production_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "RetentionCapacityPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise RetentionCapacityError(f"invalid retention-capacity policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise RetentionCapacityError("unsupported retention-capacity policy schema_version")
        if raw.get("mode") != "OFFLINE_REFERENCE_CAPACITY_CERTIFICATION":
            raise RetentionCapacityError("unsupported retention-capacity mode")
        if raw.get("cost_mode") != "PARAMETRIC_NO_VENDOR_PRICE":
            raise RetentionCapacityError("unsupported retention-capacity cost mode")
        if raw.get("production_cost_rates") != _COST_UNRESOLVED:
            raise RetentionCapacityError("production cost rates must remain unresolved")
        if raw.get("network_required") is not False:
            raise RetentionCapacityError("reference certification must not require network")
        if raw.get("credentials_required") is not False:
            raise RetentionCapacityError("reference certification must not require credentials")
        if raw.get("production_mutation") is not False:
            raise RetentionCapacityError("reference certification must not mutate production")

        tiers = _mapping(raw.get("retention_tiers"), field="retention_tiers")
        hot = _mapping(tiers.get("HOT"), field="HOT")
        warm = _mapping(tiers.get("WARM"), field="WARM")
        cold = _mapping(tiers.get("COLD"), field="COLD")
        ratios_value = raw.get("planning_compression_ratios")
        if not isinstance(ratios_value, list):
            raise RetentionCapacityError("planning_compression_ratios must be a list")
        ratios = tuple(
            _positive_decimal(item, field="planning_compression_ratio")
            for item in cast(list[object], ratios_value)
        )
        if not ratios:
            raise RetentionCapacityError("planning_compression_ratios must not be empty")

        floors = _mapping(raw.get("reference_performance_floors"), field="reference_performance_floors")
        return cls(
            seconds_per_day=_positive_int(raw.get("seconds_per_day"), field="seconds_per_day"),
            decimal_bytes_per_gb=_positive_int(
                raw.get("decimal_bytes_per_gb"),
                field="decimal_bytes_per_gb",
            ),
            decimal_bytes_per_tb=_positive_int(
                raw.get("decimal_bytes_per_tb"),
                field="decimal_bytes_per_tb",
            ),
            hot_days=_positive_int(hot.get("provisional_days"), field="HOT.provisional_days"),
            warm_min_days=_positive_int(
                warm.get("provisional_min_days"),
                field="WARM.provisional_min_days",
            ),
            warm_max_days=_positive_int(
                warm.get("provisional_max_days"),
                field="WARM.provisional_max_days",
            ),
            cold_min_days=_positive_int(
                cold.get("provisional_min_days"),
                field="COLD.provisional_min_days",
            ),
            planning_compression_ratios=ratios,
            storage_growth_review_deviation_percent=_positive_decimal(
                raw.get("storage_growth_review_deviation_percent"),
                field="storage_growth_review_deviation_percent",
            ),
            reference_partition_seconds=_positive_int(
                raw.get("reference_partition_seconds"),
                field="reference_partition_seconds",
            ),
            replay_scan_floor_mib_per_sec=_positive_decimal(
                floors.get("replay_scan_mib_per_sec"),
                field="replay_scan_mib_per_sec",
            ),
            feature_rebuild_floor_per_sec=_positive_decimal(
                floors.get("feature_rebuild_per_sec"),
                field="feature_rebuild_per_sec",
            ),
            production_storage_vendor=_text(
                raw.get("production_storage_vendor"),
                field="production_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class RetentionRights:
    rights_state: str
    max_retention_days: int | None = None

    def __post_init__(self) -> None:
        if self.rights_state not in _ALLOWED_RIGHTS:
            raise RetentionCapacityError("unsupported retention rights_state")
        if self.max_retention_days is not None:
            _positive_int(self.max_retention_days, field="max_retention_days")
        if self.rights_state == "RETENTION_ALLOWED_WITH_LIMIT" and self.max_retention_days is None:
            raise RetentionCapacityError("limited retention requires max_retention_days")
        if self.rights_state != "RETENTION_ALLOWED_WITH_LIMIT" and self.max_retention_days is not None:
            raise RetentionCapacityError("max_retention_days is only valid for limited retention")


@dataclass(frozen=True, slots=True)
class RetentionPlan:
    tier: str
    requested_days: int
    action: str
    effective_days: int
    rights_state: str
    production_mutation: bool = False


def plan_raw_retention(
    *,
    tier: str,
    requested_days: int,
    rights: RetentionRights,
    policy: RetentionCapacityPolicy,
) -> RetentionPlan:
    if tier not in _ALLOWED_TIERS:
        raise RetentionCapacityError("unsupported retention tier")
    days = _positive_int(requested_days, field="requested_days")
    if rights.rights_state in {"RETENTION_FORBIDDEN", "RETENTION_UNVERIFIED"}:
        raise RetentionCapacityError("raw retention is not permitted by rights state")
    if rights.rights_state == "RETENTION_ALLOWED_WITH_LIMIT":
        limit = rights.max_retention_days
        if limit is None:
            raise RetentionCapacityError("limited retention is missing max_retention_days")
        if days > limit:
            raise RetentionCapacityError("requested raw retention exceeds rights limit")
        action = "KEEP_RAW_UNTIL_RIGHTS_LIMIT"
    else:
        action = "KEEP_RAW_WITHIN_GOVERNED_TIER"

    if tier == "HOT" and days > policy.hot_days:
        raise RetentionCapacityError("HOT requested_days exceeds provisional tier")
    if tier == "WARM" and not (policy.warm_min_days <= days <= policy.warm_max_days):
        raise RetentionCapacityError("WARM requested_days is outside provisional tier")
    if tier == "COLD" and days < policy.cold_min_days:
        raise RetentionCapacityError("COLD requested_days is below provisional tier")

    return RetentionPlan(
        tier=tier,
        requested_days=days,
        action=action,
        effective_days=days,
        rights_state=rights.rights_state,
        production_mutation=False,
    )


@dataclass(frozen=True, slots=True)
class CapacityEstimate:
    events_per_sec: int
    event_bytes: int
    retention_days: int
    compression_ratio: Decimal
    partition_seconds: int
    raw_bytes_per_day: int
    compressed_bytes_per_day: Decimal
    raw_gb_per_day: Decimal
    compressed_gb_per_day: Decimal
    retained_compressed_gb: Decimal
    raw_tb_for_retention: Decimal
    partition_compressed_gb: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "events_per_sec": self.events_per_sec,
            "event_bytes": self.event_bytes,
            "retention_days": self.retention_days,
            "compression_ratio": _decimal_text(self.compression_ratio),
            "partition_seconds": self.partition_seconds,
            "raw_bytes_per_day": self.raw_bytes_per_day,
            "compressed_bytes_per_day": _decimal_text(self.compressed_bytes_per_day),
            "raw_gb_per_day": _decimal_text(self.raw_gb_per_day),
            "compressed_gb_per_day": _decimal_text(self.compressed_gb_per_day),
            "retained_compressed_gb": _decimal_text(self.retained_compressed_gb),
            "raw_tb_for_retention": _decimal_text(self.raw_tb_for_retention),
            "partition_compressed_gb": _decimal_text(self.partition_compressed_gb),
        }


def estimate_capacity(
    *,
    events_per_sec: int,
    event_bytes: int,
    retention_days: int,
    compression_ratio: Decimal | int | str,
    partition_seconds: int,
    policy: RetentionCapacityPolicy,
) -> CapacityEstimate:
    eps = _positive_int(events_per_sec, field="events_per_sec")
    size = _positive_int(event_bytes, field="event_bytes")
    days = _positive_int(retention_days, field="retention_days")
    ratio = _positive_decimal(compression_ratio, field="compression_ratio")
    partition = _positive_int(partition_seconds, field="partition_seconds")
    raw_per_day = eps * size * policy.seconds_per_day
    raw_decimal = Decimal(raw_per_day)
    compressed_per_day = raw_decimal / ratio
    raw_gb = raw_decimal / Decimal(policy.decimal_bytes_per_gb)
    compressed_gb = compressed_per_day / Decimal(policy.decimal_bytes_per_gb)
    retained_compressed_gb = compressed_gb * Decimal(days)
    raw_tb_retention = raw_decimal * Decimal(days) / Decimal(policy.decimal_bytes_per_tb)
    partition_compressed_gb = (
        Decimal(eps * size * partition)
        / ratio
        / Decimal(policy.decimal_bytes_per_gb)
    )
    return CapacityEstimate(
        events_per_sec=eps,
        event_bytes=size,
        retention_days=days,
        compression_ratio=ratio,
        partition_seconds=partition,
        raw_bytes_per_day=raw_per_day,
        compressed_bytes_per_day=compressed_per_day,
        raw_gb_per_day=raw_gb,
        compressed_gb_per_day=compressed_gb,
        retained_compressed_gb=retained_compressed_gb,
        raw_tb_for_retention=raw_tb_retention,
        partition_compressed_gb=partition_compressed_gb,
    )


@dataclass(frozen=True, slots=True)
class CompactionMeasurement:
    input_bytes: int
    output_bytes: int
    compression_ratio: Decimal
    meets_reference_lower_bound: bool


def measure_compaction(
    *,
    input_bytes: int,
    output_bytes: int,
    policy: RetentionCapacityPolicy,
) -> CompactionMeasurement:
    source = _positive_int(input_bytes, field="input_bytes")
    compacted = _positive_int(output_bytes, field="output_bytes")
    if compacted > source:
        raise RetentionCapacityError("compacted output cannot exceed reference input")
    ratio = Decimal(source) / Decimal(compacted)
    lower_bound = min(policy.planning_compression_ratios)
    return CompactionMeasurement(
        input_bytes=source,
        output_bytes=compacted,
        compression_ratio=ratio,
        meets_reference_lower_bound=ratio >= lower_bound,
    )


@dataclass(frozen=True, slots=True)
class GrowthDeviation:
    forecast_gb: Decimal
    actual_gb: Decimal
    deviation_percent: Decimal
    architecture_review_required: bool


def evaluate_growth_deviation(
    *,
    forecast_gb: Decimal | int | str,
    actual_gb: Decimal | int | str,
    policy: RetentionCapacityPolicy,
) -> GrowthDeviation:
    forecast = _positive_decimal(forecast_gb, field="forecast_gb")
    actual = _non_negative_decimal(actual_gb, field="actual_gb")
    deviation = (abs(actual - forecast) / forecast) * Decimal("100")
    return GrowthDeviation(
        forecast_gb=forecast,
        actual_gb=actual,
        deviation_percent=deviation,
        architecture_review_required=deviation > policy.storage_growth_review_deviation_percent,
    )


@dataclass(frozen=True, slots=True)
class CostRateSet:
    currency_or_unit: str
    storage_gb_month_rate: Decimal
    replay_scan_gb_rate: Decimal
    egress_gb_rate: Decimal
    provenance: str
    production_authoritative: bool

    def __post_init__(self) -> None:
        _text(self.currency_or_unit, field="currency_or_unit")
        _non_negative_decimal(self.storage_gb_month_rate, field="storage_gb_month_rate")
        _non_negative_decimal(self.replay_scan_gb_rate, field="replay_scan_gb_rate")
        _non_negative_decimal(self.egress_gb_rate, field="egress_gb_rate")
        _text(self.provenance, field="provenance")


@dataclass(frozen=True, slots=True)
class CostEstimate:
    status: str
    currency_or_unit: str | None
    storage_cost: Decimal | None
    replay_scan_cost: Decimal | None
    egress_cost: Decimal | None
    total_cost: Decimal | None
    provenance: str | None
    production_authoritative: bool

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "currency_or_unit": self.currency_or_unit,
            "storage_cost": None if self.storage_cost is None else _decimal_text(self.storage_cost),
            "replay_scan_cost": (
                None if self.replay_scan_cost is None else _decimal_text(self.replay_scan_cost)
            ),
            "egress_cost": None if self.egress_cost is None else _decimal_text(self.egress_cost),
            "total_cost": None if self.total_cost is None else _decimal_text(self.total_cost),
            "provenance": self.provenance,
            "production_authoritative": self.production_authoritative,
        }


def estimate_cost(
    *,
    retained_gb_month: Decimal | int | str,
    replay_scan_gb: Decimal | int | str,
    egress_gb: Decimal | int | str,
    rates: CostRateSet | None,
) -> CostEstimate:
    retained = _non_negative_decimal(retained_gb_month, field="retained_gb_month")
    scan = _non_negative_decimal(replay_scan_gb, field="replay_scan_gb")
    egress = _non_negative_decimal(egress_gb, field="egress_gb")
    if rates is None:
        return CostEstimate(
            status=_COST_UNRESOLVED,
            currency_or_unit=None,
            storage_cost=None,
            replay_scan_cost=None,
            egress_cost=None,
            total_cost=None,
            provenance=None,
            production_authoritative=False,
        )
    storage_cost = retained * rates.storage_gb_month_rate
    scan_cost = scan * rates.replay_scan_gb_rate
    egress_cost = egress * rates.egress_gb_rate
    total = storage_cost + scan_cost + egress_cost
    return CostEstimate(
        status="PARAMETRIC_ESTIMATE",
        currency_or_unit=rates.currency_or_unit,
        storage_cost=storage_cost,
        replay_scan_cost=scan_cost,
        egress_cost=egress_cost,
        total_cost=total,
        provenance=rates.provenance,
        production_authoritative=rates.production_authoritative,
    )


def quantize_rate(value: Decimal) -> Decimal:
    """Stable helper for benchmark/report presentation only."""
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
