from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy, MacroVintageStore
from .source_registry import OfficialSourceRegistry


class CommodityContextError(ValueError):
    """Raised when P10-F commodity-context invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CommodityContextError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise CommodityContextError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CommodityContextError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise CommodityContextError(f"{field} must be boolean")
    return value


def _text_tuple(value: object, *, field: str) -> tuple[str, ...]:
    return tuple(_text(item, field=field) for item in _object_list(value, field=field))


def _decimal(value: object, *, field: str) -> Decimal:
    text = _text(value, field=field)
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise CommodityContextError(f"{field} must be a finite decimal") from exc
    if not number.is_finite():
        raise CommodityContextError(f"{field} must be a finite decimal")
    return number


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True, slots=True)
class CommodityMetricRule:
    metric_kind: str
    commodity_id: str
    allowed_units: tuple[str, ...]
    allowed_source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommodityContextPolicy:
    metric_rules: tuple[CommodityMetricRule, ...]
    latest_as_of_rule: str
    oil_balance_rule: str
    production_source_mapping: str
    market_direction_interpretation_allowed: bool
    causal_market_impact_claim_allowed: bool
    direct_trade_output_allowed: bool
    network_required: bool
    credentials_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "CommodityContextPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise CommodityContextError("unsupported commodity policy schema_version")
        rules = tuple(
            CommodityMetricRule(
                metric_kind=_text(item.get("metric_kind"), field="metric_kind"),
                commodity_id=_text(item.get("commodity_id"), field="commodity_id"),
                allowed_units=_text_tuple(item.get("allowed_units"), field="allowed_units"),
                allowed_source_ids=_text_tuple(item.get("allowed_source_ids"), field="allowed_source_ids"),
            )
            for item in (
                _mapping(value, field="metric rule")
                for value in _object_list(raw.get("metric_rules"), field="metric_rules")
            )
        )
        policy = cls(
            metric_rules=rules,
            latest_as_of_rule=_text(raw.get("latest_as_of_rule"), field="latest_as_of_rule"),
            oil_balance_rule=_text(raw.get("oil_balance_rule"), field="oil_balance_rule"),
            production_source_mapping=_text(raw.get("production_source_mapping"), field="production_source_mapping"),
            market_direction_interpretation_allowed=_boolean(
                raw.get("market_direction_interpretation_allowed"),
                field="market_direction_interpretation_allowed",
            ),
            causal_market_impact_claim_allowed=_boolean(
                raw.get("causal_market_impact_claim_allowed"),
                field="causal_market_impact_claim_allowed",
            ),
            direct_trade_output_allowed=_boolean(
                raw.get("direct_trade_output_allowed"),
                field="direct_trade_output_allowed",
            ),
            network_required=_boolean(raw.get("network_required"), field="network_required"),
            credentials_required=_boolean(raw.get("credentials_required"), field="credentials_required"),
            live_trading=_text(raw.get("live_trading"), field="live_trading"),
            auto_trading=_text(raw.get("auto_trading"), field="auto_trading"),
        )
        expected = {
            "OIL_INVENTORY_LEVEL": ("CRUDE_OIL", ("MILLION_BARRELS",), ("EIA", "OPEC", "IEA")),
            "OIL_SUPPLY_LEVEL": ("CRUDE_OIL", ("MILLION_BARRELS_PER_DAY",), ("EIA", "OPEC", "IEA")),
            "OIL_DEMAND_LEVEL": ("CRUDE_OIL", ("MILLION_BARRELS_PER_DAY",), ("EIA", "OPEC", "IEA")),
            "GOLD_SUPPLY_LEVEL": ("GOLD", ("TONNES",), ("WGC",)),
            "GOLD_DEMAND_LEVEL": ("GOLD", ("TONNES",), ("WGC",)),
            "GOLD_ETF_HOLDINGS": ("GOLD", ("TONNES",), ("WGC",)),
            "GOLD_RESERVES": ("GOLD", ("TONNES",), ("WGC",)),
            "GOLD_CLEARING_VOLUME": ("GOLD", ("TROY_OUNCES",), ("LBMA",)),
        }
        actual = {
            rule.metric_kind: (rule.commodity_id, rule.allowed_units, rule.allowed_source_ids)
            for rule in policy.metric_rules
        }
        if actual != expected or len(actual) != len(policy.metric_rules):
            raise CommodityContextError("commodity metric-rule policy drift")
        if policy.latest_as_of_rule != "LATEST_OBSERVATION_WITH_RELEASE_AND_OBSERVED_AT_NOT_AFTER_DECISION_TIME":
            raise CommodityContextError("latest-as-of rule drift")
        if policy.oil_balance_rule != "SUPPLY_MINUS_DEMAND":
            raise CommodityContextError("oil-balance rule drift")
        if policy.production_source_mapping != "NOT_SELECTED":
            raise CommodityContextError("production source mapping cannot be selected in P10-F")
        if (
            policy.market_direction_interpretation_allowed
            or policy.causal_market_impact_claim_allowed
            or policy.direct_trade_output_allowed
        ):
            raise CommodityContextError("P10-F must remain descriptive and non-trading")
        if policy.network_required or policy.credentials_required:
            raise CommodityContextError("P10-F canonical model must remain offline")
        if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
            raise CommodityContextError("P10-F cannot enable trading")
        return policy

    def rule_for(self, metric_kind: str) -> CommodityMetricRule:
        for rule in self.metric_rules:
            if rule.metric_kind == metric_kind:
                return rule
        raise CommodityContextError("unsupported commodity metric kind")


@dataclass(frozen=True, slots=True)
class CommodityFundamentalPoint:
    vintage: MacroVintage
    commodity_id: str
    metric_kind: str
    geography: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "vintage": self.vintage.identity_payload(),
            "commodity_id": self.commodity_id,
            "metric_kind": self.metric_kind,
            "geography": self.geography,
        }

    @property
    def point_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_commodity_point(
    point: CommodityFundamentalPoint,
    *,
    policy: CommodityContextPolicy,
    source_registry: OfficialSourceRegistry,
) -> CommodityFundamentalPoint:
    metric = _text(point.metric_kind, field="metric_kind")
    commodity = _text(point.commodity_id, field="commodity_id")
    _text(point.geography, field="geography")
    rule = policy.rule_for(metric)
    if commodity != rule.commodity_id:
        raise CommodityContextError("commodity_id does not match metric rule")
    if point.vintage.unit not in rule.allowed_units:
        raise CommodityContextError("commodity point unit is not allowed for metric")
    if point.vintage.source not in rule.allowed_source_ids:
        raise CommodityContextError("commodity source is not allowed for metric")
    try:
        source_registry.get(point.vintage.source)
    except Exception as exc:
        raise CommodityContextError("commodity source is not in official registry") from exc
    return point


class CommodityContextStore:
    def __init__(
        self,
        points: Sequence[CommodityFundamentalPoint],
        *,
        policy: CommodityContextPolicy,
        source_registry: OfficialSourceRegistry,
        macro_policy: MacroVintagePolicy,
    ) -> None:
        frozen = tuple(points)
        if not frozen:
            raise CommodityContextError("commodity context store requires at least one point")
        metadata: dict[str, tuple[str, str, str]] = {}
        for point in frozen:
            valid = validate_commodity_point(point, policy=policy, source_registry=source_registry)
            meta = (valid.commodity_id, valid.metric_kind, valid.geography)
            old = metadata.get(valid.vintage.series_id)
            if old is not None and old != meta:
                raise CommodityContextError("series metadata cannot drift across vintages")
            metadata[valid.vintage.series_id] = meta
        self._metadata = metadata
        self._store = MacroVintageStore(tuple(point.vintage for point in frozen), macro_policy)
        ordered = [point.payload() for point in sorted(frozen, key=lambda item: item.point_id)]
        self._fingerprint = hashlib.sha256(_canonical_bytes(ordered)).hexdigest()

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def resolve_latest_as_of(
        self,
        *,
        series_id: str,
        decision_time_ns: int,
    ) -> CommodityFundamentalPoint | None:
        snapshot = self._store.snapshot_as_of(series_id=series_id, decision_time_ns=decision_time_ns)
        if not snapshot.vintages:
            return None
        vintage = snapshot.vintages[-1]
        meta = self._metadata.get(series_id)
        if meta is None:
            raise CommodityContextError("series metadata missing")
        return CommodityFundamentalPoint(vintage, meta[0], meta[1], meta[2])


@dataclass(frozen=True, slots=True)
class OilBalanceContext:
    decision_time_ns: int
    geography: str
    supply_series_id: str
    supply_observation_time_ns: int
    supply_vintage_id: str
    supply_value_text: str
    demand_series_id: str
    demand_observation_time_ns: int
    demand_vintage_id: str
    demand_value_text: str
    balance_value_text: str
    unit: str
    store_fingerprint: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "decision_time_ns": self.decision_time_ns,
            "geography": self.geography,
            "supply_series_id": self.supply_series_id,
            "supply_observation_time_ns": self.supply_observation_time_ns,
            "supply_vintage_id": self.supply_vintage_id,
            "supply_value_text": self.supply_value_text,
            "demand_series_id": self.demand_series_id,
            "demand_observation_time_ns": self.demand_observation_time_ns,
            "demand_vintage_id": self.demand_vintage_id,
            "demand_value_text": self.demand_value_text,
            "balance_value_text": self.balance_value_text,
            "unit": self.unit,
            "store_fingerprint": self.store_fingerprint,
        }

    @property
    def context_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def compute_oil_balance(
    *,
    store: CommodityContextStore,
    supply_series_id: str,
    demand_series_id: str,
    decision_time_ns: int,
) -> OilBalanceContext:
    supply = store.resolve_latest_as_of(series_id=supply_series_id, decision_time_ns=decision_time_ns)
    demand = store.resolve_latest_as_of(series_id=demand_series_id, decision_time_ns=decision_time_ns)
    if supply is None or demand is None:
        raise CommodityContextError("oil-balance legs unavailable as-of decision time")
    if supply.commodity_id != "CRUDE_OIL" or demand.commodity_id != "CRUDE_OIL":
        raise CommodityContextError("oil balance requires CRUDE_OIL legs")
    if supply.metric_kind != "OIL_SUPPLY_LEVEL" or demand.metric_kind != "OIL_DEMAND_LEVEL":
        raise CommodityContextError("oil balance requires supply and demand metrics")
    if supply.geography != demand.geography:
        raise CommodityContextError("oil-balance legs must share geography")
    if supply.vintage.unit != demand.vintage.unit:
        raise CommodityContextError("oil-balance legs must share unit")
    supply_value = _decimal(supply.vintage.value_text, field="oil supply")
    demand_value = _decimal(demand.vintage.value_text, field="oil demand")
    return OilBalanceContext(
        decision_time_ns=decision_time_ns,
        geography=supply.geography,
        supply_series_id=supply.vintage.series_id,
        supply_observation_time_ns=supply.vintage.observation_time_ns,
        supply_vintage_id=supply.vintage.vintage_id,
        supply_value_text=_decimal_text(supply_value),
        demand_series_id=demand.vintage.series_id,
        demand_observation_time_ns=demand.vintage.observation_time_ns,
        demand_vintage_id=demand.vintage.vintage_id,
        demand_value_text=_decimal_text(demand_value),
        balance_value_text=_decimal_text(supply_value - demand_value),
        unit=supply.vintage.unit,
        store_fingerprint=store.fingerprint,
    )


def assert_no_commodity_trade_authority_fields() -> None:
    forbidden = {
        "trade_direction",
        "signal_probability",
        "success_probability",
        "recommendation",
        "risk_approval",
        "execution_authority",
        "order_intent",
        "entry_price",
        "stop_loss",
        "take_profit",
        "bullish",
        "bearish",
    }
    for cls in (CommodityFundamentalPoint, OilBalanceContext):
        overlap = sorted({field.name for field in fields(cls)} & forbidden)
        if overlap:
            raise CommodityContextError(f"P10-F trade-authority field leak: {overlap}")
