from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class DerivativesCrowdingError(ValueError):
    """Raised when P09-F derivatives/crowding invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DerivativesCrowdingError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise DerivativesCrowdingError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DerivativesCrowdingError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise DerivativesCrowdingError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DerivativesCrowdingError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DerivativesCrowdingError(f"{field} must be a non-negative integer")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise DerivativesCrowdingError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DerivativesCrowdingError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise DerivativesCrowdingError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise DerivativesCrowdingError(f"{field} must be lowercase sha256 hex")
    return text


@dataclass(frozen=True, slots=True)
class DerivativesCrowdingPolicy:
    allowed_market_classes: tuple[str, ...]
    allowed_metric_kinds: tuple[str, ...]
    funding_allowed_market_classes: tuple[str, ...]
    funding_unit: str
    require_same_provider_venue_instrument: bool
    require_same_as_of_time: bool
    cross_provider_aggregation_allowed: bool
    spot_fx_derivatives_metric_allowed: bool
    crowding_score_allowed: bool
    liquidation_forecast_allowed: bool
    direct_trade_output_allowed: bool
    production_derivatives_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "DerivativesCrowdingPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise DerivativesCrowdingError("unsupported policy schema_version")

        markets = tuple(
            _text(item, field="allowed_market_class")
            for item in _object_list(raw.get("allowed_market_classes"), field="allowed_market_classes")
        )
        metrics = tuple(
            _text(item, field="allowed_metric_kind")
            for item in _object_list(raw.get("allowed_metric_kinds"), field="allowed_metric_kinds")
        )
        funding_markets = tuple(
            _text(item, field="funding_allowed_market_class")
            for item in _object_list(
                raw.get("funding_allowed_market_classes"),
                field="funding_allowed_market_classes",
            )
        )
        funding_unit = _text(raw.get("funding_unit"), field="funding_unit")
        same_stream = _boolean(
            raw.get("require_same_provider_venue_instrument"),
            field="require_same_provider_venue_instrument",
        )
        same_as_of = _boolean(raw.get("require_same_as_of_time"), field="require_same_as_of_time")
        cross_provider = _boolean(
            raw.get("cross_provider_aggregation_allowed"),
            field="cross_provider_aggregation_allowed",
        )
        spot_fx = _boolean(
            raw.get("spot_fx_derivatives_metric_allowed"),
            field="spot_fx_derivatives_metric_allowed",
        )
        score = _boolean(raw.get("crowding_score_allowed"), field="crowding_score_allowed")
        forecast = _boolean(
            raw.get("liquidation_forecast_allowed"),
            field="liquidation_forecast_allowed",
        )
        direct = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(raw.get("production_derivatives_vendor"), field="production_derivatives_vendor")

        if not markets or not metrics or not funding_markets:
            raise DerivativesCrowdingError("policy enumerations must be non-empty")
        if not same_stream or not same_as_of:
            raise DerivativesCrowdingError("P09-F requires same-stream and same-as-of crowding evidence")
        if cross_provider:
            raise DerivativesCrowdingError("P09-F forbids cross-provider aggregation")
        if spot_fx:
            raise DerivativesCrowdingError("P09-F forbids synthetic spot-FX derivatives metrics")
        if score:
            raise DerivativesCrowdingError("P09-F forbids unvalidated crowding scores")
        if forecast:
            raise DerivativesCrowdingError("P09-F forbids liquidation forecasts")
        if direct:
            raise DerivativesCrowdingError("P09-F forbids direct trade output")

        return cls(
            allowed_market_classes=markets,
            allowed_metric_kinds=metrics,
            funding_allowed_market_classes=funding_markets,
            funding_unit=funding_unit,
            require_same_provider_venue_instrument=same_stream,
            require_same_as_of_time=same_as_of,
            cross_provider_aggregation_allowed=cross_provider,
            spot_fx_derivatives_metric_allowed=spot_fx,
            crowding_score_allowed=score,
            liquidation_forecast_allowed=forecast,
            direct_trade_output_allowed=direct,
            production_derivatives_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class DerivativesObservation:
    symbol: str
    market_class: str
    metric_kind: str
    provider: str
    venue: str
    value_text: str
    value_unit: str
    event_time_ns: int
    as_of_time_ns: int
    sequence: int
    coverage_scope: str
    source_dataset_version: str
    quality_evidence_sha256: str
    funding_interval_seconds: int | None = None

    @property
    def value(self) -> Decimal:
        return Decimal(self.value_text)

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "market_class": self.market_class,
            "metric_kind": self.metric_kind,
            "provider": self.provider,
            "venue": self.venue,
            "value_text": self.value_text,
            "value_unit": self.value_unit,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "sequence": self.sequence,
            "coverage_scope": self.coverage_scope,
            "source_dataset_version": self.source_dataset_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
            "funding_interval_seconds": self.funding_interval_seconds,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class CrowdingEvidenceSnapshot:
    symbol: str
    market_class: str
    provider: str
    venue: str
    coverage_scope: str
    as_of_time_ns: int
    funding_observation_id: str
    open_interest_observation_id: str
    long_liquidation_observation_id: str
    short_liquidation_observation_id: str
    funding_rate_text: str
    funding_interval_seconds: int
    open_interest_text: str
    open_interest_unit: str
    long_liquidation_text: str
    short_liquidation_text: str
    liquidation_unit: str
    total_liquidation_text: str
    liquidation_activity_present: bool
    liquidation_imbalance_bps: int | None
    evidence_complete: bool

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "market_class": self.market_class,
            "provider": self.provider,
            "venue": self.venue,
            "coverage_scope": self.coverage_scope,
            "as_of_time_ns": self.as_of_time_ns,
            "funding_observation_id": self.funding_observation_id,
            "open_interest_observation_id": self.open_interest_observation_id,
            "long_liquidation_observation_id": self.long_liquidation_observation_id,
            "short_liquidation_observation_id": self.short_liquidation_observation_id,
            "funding_rate_text": self.funding_rate_text,
            "funding_interval_seconds": self.funding_interval_seconds,
            "open_interest_text": self.open_interest_text,
            "open_interest_unit": self.open_interest_unit,
            "long_liquidation_text": self.long_liquidation_text,
            "short_liquidation_text": self.short_liquidation_text,
            "liquidation_unit": self.liquidation_unit,
            "total_liquidation_text": self.total_liquidation_text,
            "liquidation_activity_present": self.liquidation_activity_present,
            "liquidation_imbalance_bps": self.liquidation_imbalance_bps,
            "evidence_complete": self.evidence_complete,
        }

    @property
    def evidence_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_derivatives_observation(
    observation: DerivativesObservation,
    *,
    policy: DerivativesCrowdingPolicy,
) -> DerivativesObservation:
    symbol = _text(observation.symbol, field="symbol")
    market_class = _text(observation.market_class, field="market_class")
    metric_kind = _text(observation.metric_kind, field="metric_kind")
    provider = _text(observation.provider, field="provider")
    venue = _text(observation.venue, field="venue")
    value_unit = _text(observation.value_unit, field="value_unit")
    coverage_scope = _text(observation.coverage_scope, field="coverage_scope")
    event_time = _non_negative_int(observation.event_time_ns, field="event_time_ns")
    as_of_time = _non_negative_int(observation.as_of_time_ns, field="as_of_time_ns")
    sequence = _positive_int(observation.sequence, field="sequence")
    dataset = _sha256_text(observation.source_dataset_version, field="source_dataset_version")
    quality = _sha256_text(observation.quality_evidence_sha256, field="quality_evidence_sha256")
    value = _decimal(observation.value_text, field="value")

    if event_time > as_of_time:
        raise DerivativesCrowdingError("event_time_ns cannot exceed as_of_time_ns")
    if market_class not in policy.allowed_market_classes:
        raise DerivativesCrowdingError("market_class is not allowed for P09-F derivatives metrics")
    if metric_kind not in policy.allowed_metric_kinds:
        raise DerivativesCrowdingError("metric_kind is not allowed by P09-F policy")

    interval = observation.funding_interval_seconds
    if metric_kind == "FUNDING_RATE":
        if market_class not in policy.funding_allowed_market_classes:
            raise DerivativesCrowdingError("funding rate is not allowed for this market class")
        if value_unit != policy.funding_unit:
            raise DerivativesCrowdingError("funding rate must use the governed funding unit")
        if interval is None:
            raise DerivativesCrowdingError("funding rate requires funding_interval_seconds")
        interval = _positive_int(interval, field="funding_interval_seconds")
    else:
        if interval is not None:
            raise DerivativesCrowdingError("non-funding metric must not carry funding_interval_seconds")
        if value < 0:
            raise DerivativesCrowdingError("open-interest and liquidation values must be non-negative")

    return DerivativesObservation(
        symbol=symbol,
        market_class=market_class,
        metric_kind=metric_kind,
        provider=provider,
        venue=venue,
        value_text=_decimal_text(value),
        value_unit=value_unit,
        event_time_ns=event_time,
        as_of_time_ns=as_of_time,
        sequence=sequence,
        coverage_scope=coverage_scope,
        source_dataset_version=dataset,
        quality_evidence_sha256=quality,
        funding_interval_seconds=interval,
    )


def build_crowding_evidence(
    observations: Sequence[DerivativesObservation],
    *,
    policy: DerivativesCrowdingPolicy,
) -> CrowdingEvidenceSnapshot:
    required = {"FUNDING_RATE", "OPEN_INTEREST", "LONG_LIQUIDATION", "SHORT_LIQUIDATION"}
    validated = [validate_derivatives_observation(item, policy=policy) for item in observations]
    by_kind: dict[str, DerivativesObservation] = {}
    for item in validated:
        if item.metric_kind in by_kind:
            raise DerivativesCrowdingError("crowding evidence cannot contain duplicate metric kinds")
        by_kind[item.metric_kind] = item
    if set(by_kind) != required:
        raise DerivativesCrowdingError("crowding evidence requires exactly Funding/OI/Long/Short Liquidation metrics")

    funding = by_kind["FUNDING_RATE"]
    oi = by_kind["OPEN_INTEREST"]
    long_liq = by_kind["LONG_LIQUIDATION"]
    short_liq = by_kind["SHORT_LIQUIDATION"]

    stream_key = (
        funding.symbol,
        funding.market_class,
        funding.provider,
        funding.venue,
        funding.coverage_scope,
        funding.as_of_time_ns,
    )
    for item in (oi, long_liq, short_liq):
        if (
            item.symbol,
            item.market_class,
            item.provider,
            item.venue,
            item.coverage_scope,
            item.as_of_time_ns,
        ) != stream_key:
            raise DerivativesCrowdingError("crowding evidence requires same stream and as-of time")

    if long_liq.value_unit != short_liq.value_unit:
        raise DerivativesCrowdingError("long/short liquidation units must match")

    total = long_liq.value + short_liq.value
    activity = total > 0
    if activity:
        raw_imbalance = (long_liq.value - short_liq.value) * Decimal(10_000) / total
        imbalance = int(raw_imbalance.to_integral_value(rounding=ROUND_HALF_EVEN))
        imbalance = min(10_000, max(-10_000, imbalance))
    else:
        imbalance = None

    interval = funding.funding_interval_seconds
    if interval is None:
        raise DerivativesCrowdingError("validated funding interval is unexpectedly unavailable")

    return CrowdingEvidenceSnapshot(
        symbol=funding.symbol,
        market_class=funding.market_class,
        provider=funding.provider,
        venue=funding.venue,
        coverage_scope=funding.coverage_scope,
        as_of_time_ns=funding.as_of_time_ns,
        funding_observation_id=funding.observation_id,
        open_interest_observation_id=oi.observation_id,
        long_liquidation_observation_id=long_liq.observation_id,
        short_liquidation_observation_id=short_liq.observation_id,
        funding_rate_text=funding.value_text,
        funding_interval_seconds=interval,
        open_interest_text=oi.value_text,
        open_interest_unit=oi.value_unit,
        long_liquidation_text=long_liq.value_text,
        short_liquidation_text=short_liq.value_text,
        liquidation_unit=long_liq.value_unit,
        total_liquidation_text=_decimal_text(total),
        liquidation_activity_present=activity,
        liquidation_imbalance_bps=imbalance,
        evidence_complete=True,
    )


def assert_no_crowding_trade_authority_fields() -> None:
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
        "crowding_score",
        "crowding_label",
        "liquidation_forecast",
    }
    contract_fields = (
        {field.name for field in fields(DerivativesObservation)}
        | {field.name for field in fields(CrowdingEvidenceSnapshot)}
    )
    if forbidden & contract_fields:
        raise DerivativesCrowdingError("P09-F contracts must not expose unvalidated trade/crowding authority fields")
