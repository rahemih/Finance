from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class VolumeOntologyError(ValueError):
    """Raised when P09-A volume/proxy ontology invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VolumeOntologyError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise VolumeOntologyError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VolumeOntologyError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise VolumeOntologyError(f"{field} must be boolean")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise VolumeOntologyError(f"{field} must be a non-negative integer")
    return value


def _bps(value: object, *, field: str, maximum: int = 10_000) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise VolumeOntologyError(f"{field} must be integer basis points in [0,{maximum}]")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise VolumeOntologyError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise VolumeOntologyError(f"{field} must be decimal-compatible") from exc
    if not result.is_finite():
        raise VolumeOntologyError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise VolumeOntologyError(f"{field} must be lowercase sha256 hex")
    return text


@dataclass(frozen=True, slots=True)
class VolumeProxyPolicy:
    allowed_market_classes: tuple[str, ...]
    allowed_volume_kinds: tuple[str, ...]
    forex_spot_allowed_volume_kinds: tuple[str, ...]
    max_coverage_confidence_bps: int
    point_in_time_required: bool
    trusted_provenance_required: bool
    forex_spot_consolidated_volume_claim_allowed: bool
    direct_trade_output_allowed: bool
    production_order_flow_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "VolumeProxyPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise VolumeOntologyError("unsupported policy schema_version")
        market_classes = tuple(
            _text(item, field="allowed_market_class")
            for item in _object_list(raw.get("allowed_market_classes"), field="allowed_market_classes")
        )
        volume_kinds = tuple(
            _text(item, field="allowed_volume_kind")
            for item in _object_list(raw.get("allowed_volume_kinds"), field="allowed_volume_kinds")
        )
        forex_kinds = tuple(
            _text(item, field="forex_spot_allowed_volume_kind")
            for item in _object_list(
                raw.get("forex_spot_allowed_volume_kinds"),
                field="forex_spot_allowed_volume_kinds",
            )
        )
        if not market_classes or not volume_kinds or not forex_kinds:
            raise VolumeOntologyError("policy enumerations must be non-empty")
        maximum = _bps(
            raw.get("max_coverage_confidence_bps"),
            field="max_coverage_confidence_bps",
        )
        point_in_time = _boolean(raw.get("point_in_time_required"), field="point_in_time_required")
        trusted = _boolean(raw.get("trusted_provenance_required"), field="trusted_provenance_required")
        consolidated = _boolean(
            raw.get("forex_spot_consolidated_volume_claim_allowed"),
            field="forex_spot_consolidated_volume_claim_allowed",
        )
        direct_trade = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(raw.get("production_order_flow_vendor"), field="production_order_flow_vendor")
        if consolidated:
            raise VolumeOntologyError("P09-A forbids consolidated spot-FX volume claims")
        if direct_trade:
            raise VolumeOntologyError("P09-A forbids direct trade output")
        if any(not item.endswith("_PROXY") for item in forex_kinds):
            raise VolumeOntologyError("all spot-FX volume kinds must be explicit proxies")
        return cls(
            allowed_market_classes=market_classes,
            allowed_volume_kinds=volume_kinds,
            forex_spot_allowed_volume_kinds=forex_kinds,
            max_coverage_confidence_bps=maximum,
            point_in_time_required=point_in_time,
            trusted_provenance_required=trusted,
            forex_spot_consolidated_volume_claim_allowed=consolidated,
            direct_trade_output_allowed=direct_trade,
            production_order_flow_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class VolumeObservation:
    symbol: str
    market_class: str
    volume_kind: str
    provider: str
    venue: str
    value_text: str
    event_time_ns: int
    as_of_time_ns: int
    coverage_confidence_bps: int
    coverage_scope: str
    proxy_target: str
    source_dataset_version: str
    quality_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text(self.symbol, field="symbol"))
        object.__setattr__(self, "market_class", _text(self.market_class, field="market_class"))
        object.__setattr__(self, "volume_kind", _text(self.volume_kind, field="volume_kind"))
        object.__setattr__(self, "provider", _text(self.provider, field="provider"))
        object.__setattr__(self, "venue", _text(self.venue, field="venue"))
        value = _decimal(self.value_text, field="value")
        if value < 0:
            raise VolumeOntologyError("volume value cannot be negative")
        object.__setattr__(self, "value_text", _decimal_text(value))
        event_time = _non_negative_int(self.event_time_ns, field="event_time_ns")
        as_of_time = _non_negative_int(self.as_of_time_ns, field="as_of_time_ns")
        if event_time > as_of_time:
            raise VolumeOntologyError("event_time_ns cannot exceed as_of_time_ns")
        object.__setattr__(
            self,
            "coverage_confidence_bps",
            _bps(self.coverage_confidence_bps, field="coverage_confidence_bps"),
        )
        object.__setattr__(self, "coverage_scope", _text(self.coverage_scope, field="coverage_scope"))
        object.__setattr__(self, "proxy_target", _text(self.proxy_target, field="proxy_target"))
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
    def freshness_ns(self) -> int:
        return self.as_of_time_ns - self.event_time_ns

    @property
    def is_proxy(self) -> bool:
        return self.volume_kind.endswith("_PROXY")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "symbol": self.symbol,
            "market_class": self.market_class,
            "volume_kind": self.volume_kind,
            "provider": self.provider,
            "venue": self.venue,
            "value_text": self.value_text,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "freshness_ns": self.freshness_ns,
            "coverage_confidence_bps": self.coverage_confidence_bps,
            "coverage_scope": self.coverage_scope,
            "proxy_target": self.proxy_target,
            "source_dataset_version": self.source_dataset_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_volume_observation(
    observation: VolumeObservation,
    *,
    policy: VolumeProxyPolicy,
) -> VolumeObservation:
    if observation.market_class not in policy.allowed_market_classes:
        raise VolumeOntologyError("market_class is not allowed by policy")
    if observation.volume_kind not in policy.allowed_volume_kinds:
        raise VolumeOntologyError("volume_kind is not allowed by policy")
    if observation.coverage_confidence_bps > policy.max_coverage_confidence_bps:
        raise VolumeOntologyError("coverage confidence exceeds policy maximum")

    if observation.market_class == "FOREX_SPOT":
        if observation.volume_kind not in policy.forex_spot_allowed_volume_kinds:
            raise VolumeOntologyError("spot-FX volume must use an explicit proxy kind")
        if not observation.is_proxy:
            raise VolumeOntologyError("spot-FX volume must be marked as proxy")
        if observation.proxy_target.upper() not in {"SPOT_FX_MARKET_ACTIVITY", "SPOT_FX_LIQUIDITY"}:
            raise VolumeOntologyError("spot-FX proxy_target must state the proxied concept")
        scope_upper = observation.coverage_scope.upper()
        if "GLOBAL" in scope_upper or "CONSOLIDATED" in scope_upper or "TOTAL_MARKET" in scope_upper:
            raise VolumeOntologyError("spot-FX proxy cannot claim global/consolidated market coverage")
    else:
        if observation.volume_kind in {"NATIVE_VENUE_VOLUME", "AGGREGATED_VENUE_VOLUME"}:
            if observation.proxy_target.upper() != "NONE":
                raise VolumeOntologyError("native/aggregated venue volume must not declare a proxy target")

    return observation
