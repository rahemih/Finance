from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy, MacroVintageStore
from .source_registry import OfficialSourceRegistry


class RatesCurrencyMacroError(ValueError):
    """Raised when P10-E rates/yields/currency invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RatesCurrencyMacroError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RatesCurrencyMacroError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise RatesCurrencyMacroError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RatesCurrencyMacroError(f"{field} must be a positive integer")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    text = _text(value, field=field)
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise RatesCurrencyMacroError(f"{field} must be a finite decimal") from exc
    if not number.is_finite():
        raise RatesCurrencyMacroError(f"{field} must be a finite decimal")
    return number


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _currency(value: object) -> str:
    text = _text(value, field="currency")
    if len(text) != 3 or text.upper() != text or not all("A" <= ch <= "Z" for ch in text):
        raise RatesCurrencyMacroError("currency must be an uppercase three-letter code")
    return text


@dataclass(frozen=True, slots=True)
class RatesCurrencyMacroPolicy:
    allowed_metric_kinds: tuple[str, ...]
    allowed_units: tuple[str, ...]
    allowed_source_ids: tuple[str, ...]
    curve_spread_rule: str
    currency_differential_rule: str
    latest_as_of_rule: str
    production_source_mapping: str
    market_direction_interpretation_allowed: bool
    direct_trade_output_allowed: bool
    network_required: bool
    credentials_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "RatesCurrencyMacroPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise RatesCurrencyMacroError("unsupported rates/currency policy schema_version")
        metrics = raw.get("allowed_metric_kinds")
        units = raw.get("allowed_units")
        sources = raw.get("allowed_source_ids")
        if not isinstance(metrics, list) or not isinstance(units, list) or not isinstance(sources, list):
            raise RatesCurrencyMacroError("policy enumerations must be lists")
        policy = cls(
            tuple(_text(x, field="metric kind") for x in cast(list[object], metrics)),
            tuple(_text(x, field="unit") for x in cast(list[object], units)),
            tuple(_text(x, field="source id") for x in cast(list[object], sources)),
            _text(raw.get("curve_spread_rule"), field="curve_spread_rule"),
            _text(raw.get("currency_differential_rule"), field="currency_differential_rule"),
            _text(raw.get("latest_as_of_rule"), field="latest_as_of_rule"),
            _text(raw.get("production_source_mapping"), field="production_source_mapping"),
            _boolean(raw.get("market_direction_interpretation_allowed"), field="market_direction_interpretation_allowed"),
            _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed"),
            _boolean(raw.get("network_required"), field="network_required"),
            _boolean(raw.get("credentials_required"), field="credentials_required"),
            _text(raw.get("live_trading"), field="live_trading"),
            _text(raw.get("auto_trading"), field="auto_trading"),
        )
        if policy.allowed_metric_kinds != ("POLICY_RATE", "GOVERNMENT_YIELD"):
            raise RatesCurrencyMacroError("metric-kind policy drift")
        if policy.allowed_units != ("PERCENT",):
            raise RatesCurrencyMacroError("unit policy drift")
        if policy.allowed_source_ids != ("FRED_ALFRED", "ECB", "BOE", "BOJ", "BIS"):
            raise RatesCurrencyMacroError("source allowlist drift")
        if policy.curve_spread_rule != "LONGER_TENOR_MINUS_SHORTER_TENOR":
            raise RatesCurrencyMacroError("curve-spread rule drift")
        if policy.currency_differential_rule != "BASE_MINUS_QUOTE":
            raise RatesCurrencyMacroError("currency-differential rule drift")
        if policy.latest_as_of_rule != "LATEST_OBSERVATION_WITH_RELEASE_AND_OBSERVED_AT_NOT_AFTER_DECISION_TIME":
            raise RatesCurrencyMacroError("latest-as-of rule drift")
        if policy.production_source_mapping != "NOT_SELECTED":
            raise RatesCurrencyMacroError("production source mapping cannot be selected in P10-E")
        if policy.market_direction_interpretation_allowed or policy.direct_trade_output_allowed:
            raise RatesCurrencyMacroError("P10-E must remain descriptive and non-trading")
        if policy.network_required or policy.credentials_required:
            raise RatesCurrencyMacroError("P10-E canonical model must remain offline")
        if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
            raise RatesCurrencyMacroError("P10-E cannot enable trading")
        return policy


@dataclass(frozen=True, slots=True)
class RateYieldPoint:
    vintage: MacroVintage
    metric_kind: str
    currency: str
    jurisdiction: str
    tenor_months: int | None = None

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "vintage": self.vintage.identity_payload(),
            "metric_kind": self.metric_kind,
            "currency": self.currency,
            "jurisdiction": self.jurisdiction,
            "tenor_months": self.tenor_months,
        }

    @property
    def point_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_rate_yield_point(point: RateYieldPoint, *, policy: RatesCurrencyMacroPolicy, source_registry: OfficialSourceRegistry) -> RateYieldPoint:
    metric = _text(point.metric_kind, field="metric_kind")
    if metric not in policy.allowed_metric_kinds:
        raise RatesCurrencyMacroError("unsupported rate/yield metric kind")
    _currency(point.currency)
    _text(point.jurisdiction, field="jurisdiction")
    if point.vintage.unit not in policy.allowed_units:
        raise RatesCurrencyMacroError("rate/yield point unit is not allowed")
    if point.vintage.source not in policy.allowed_source_ids:
        raise RatesCurrencyMacroError("rate/yield source is not allowed for P10-E")
    try:
        source_registry.get(point.vintage.source)
    except Exception as exc:
        raise RatesCurrencyMacroError("point source is not in official registry") from exc
    if metric == "POLICY_RATE":
        if point.tenor_months is not None:
            raise RatesCurrencyMacroError("policy rate must not declare tenor")
    else:
        if point.tenor_months is None:
            raise RatesCurrencyMacroError("government yield requires tenor")
        _positive_int(point.tenor_months, field="tenor_months")
    return point


class RatesMacroStore:
    def __init__(self, points: Sequence[RateYieldPoint], *, policy: RatesCurrencyMacroPolicy, source_registry: OfficialSourceRegistry, macro_policy: MacroVintagePolicy) -> None:
        frozen = tuple(points)
        if not frozen:
            raise RatesCurrencyMacroError("rates macro store requires at least one point")
        metadata: dict[str, tuple[str, str, str, int | None]] = {}
        for point in frozen:
            valid = validate_rate_yield_point(point, policy=policy, source_registry=source_registry)
            meta = (valid.metric_kind, valid.currency, valid.jurisdiction, valid.tenor_months)
            old = metadata.get(valid.vintage.series_id)
            if old is not None and old != meta:
                raise RatesCurrencyMacroError("series metadata cannot drift across vintages")
            metadata[valid.vintage.series_id] = meta
        self._metadata = metadata
        self._store = MacroVintageStore(tuple(point.vintage for point in frozen), macro_policy)
        ordered = [point.payload() for point in sorted(frozen, key=lambda item: item.point_id)]
        self._fingerprint = hashlib.sha256(_canonical_bytes(ordered)).hexdigest()

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def resolve_latest_as_of(self, *, series_id: str, decision_time_ns: int) -> RateYieldPoint | None:
        snapshot = self._store.snapshot_as_of(series_id=series_id, decision_time_ns=decision_time_ns)
        if not snapshot.vintages:
            return None
        vintage = snapshot.vintages[-1]
        meta = self._metadata.get(series_id)
        if meta is None:
            raise RatesCurrencyMacroError("series metadata missing")
        return RateYieldPoint(vintage, meta[0], meta[1], meta[2], meta[3])


@dataclass(frozen=True, slots=True)
class YieldCurveSpread:
    decision_time_ns: int
    currency: str
    jurisdiction: str
    short_series_id: str
    short_tenor_months: int
    short_observation_time_ns: int
    short_vintage_id: str
    short_value_text: str
    long_series_id: str
    long_tenor_months: int
    long_observation_time_ns: int
    long_vintage_id: str
    long_value_text: str
    spread_value_text: str
    unit: str
    store_fingerprint: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "decision_time_ns": self.decision_time_ns,
            "currency": self.currency,
            "jurisdiction": self.jurisdiction,
            "short_series_id": self.short_series_id,
            "short_tenor_months": self.short_tenor_months,
            "short_observation_time_ns": self.short_observation_time_ns,
            "short_vintage_id": self.short_vintage_id,
            "short_value_text": self.short_value_text,
            "long_series_id": self.long_series_id,
            "long_tenor_months": self.long_tenor_months,
            "long_observation_time_ns": self.long_observation_time_ns,
            "long_vintage_id": self.long_vintage_id,
            "long_value_text": self.long_value_text,
            "spread_value_text": self.spread_value_text,
            "unit": self.unit,
            "store_fingerprint": self.store_fingerprint,
        }

    @property
    def spread_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class CurrencyMacroDifferential:
    decision_time_ns: int
    metric_kind: str
    tenor_months: int | None
    base_currency: str
    base_jurisdiction: str
    base_series_id: str
    base_observation_time_ns: int
    base_vintage_id: str
    base_value_text: str
    quote_currency: str
    quote_jurisdiction: str
    quote_series_id: str
    quote_observation_time_ns: int
    quote_vintage_id: str
    quote_value_text: str
    differential_value_text: str
    unit: str
    store_fingerprint: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "decision_time_ns": self.decision_time_ns,
            "metric_kind": self.metric_kind,
            "tenor_months": self.tenor_months,
            "base_currency": self.base_currency,
            "base_jurisdiction": self.base_jurisdiction,
            "base_series_id": self.base_series_id,
            "base_observation_time_ns": self.base_observation_time_ns,
            "base_vintage_id": self.base_vintage_id,
            "base_value_text": self.base_value_text,
            "quote_currency": self.quote_currency,
            "quote_jurisdiction": self.quote_jurisdiction,
            "quote_series_id": self.quote_series_id,
            "quote_observation_time_ns": self.quote_observation_time_ns,
            "quote_vintage_id": self.quote_vintage_id,
            "quote_value_text": self.quote_value_text,
            "differential_value_text": self.differential_value_text,
            "unit": self.unit,
            "store_fingerprint": self.store_fingerprint,
        }

    @property
    def differential_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def compute_yield_curve_spread(*, store: RatesMacroStore, short_series_id: str, long_series_id: str, decision_time_ns: int) -> YieldCurveSpread:
    short = store.resolve_latest_as_of(series_id=short_series_id, decision_time_ns=decision_time_ns)
    long = store.resolve_latest_as_of(series_id=long_series_id, decision_time_ns=decision_time_ns)
    if short is None or long is None:
        raise RatesCurrencyMacroError("yield-curve legs unavailable as-of decision time")
    if short.metric_kind != "GOVERNMENT_YIELD" or long.metric_kind != "GOVERNMENT_YIELD":
        raise RatesCurrencyMacroError("yield curve requires government yields")
    if short.currency != long.currency or short.jurisdiction != long.jurisdiction or short.vintage.unit != long.vintage.unit:
        raise RatesCurrencyMacroError("yield-curve legs must share currency, jurisdiction and unit")
    if short.tenor_months is None or long.tenor_months is None or short.tenor_months >= long.tenor_months:
        raise RatesCurrencyMacroError("yield-curve tenors must be strictly ordered")
    short_value = _decimal(short.vintage.value_text, field="short yield")
    long_value = _decimal(long.vintage.value_text, field="long yield")
    return YieldCurveSpread(
        decision_time_ns, short.currency, short.jurisdiction,
        short.vintage.series_id, short.tenor_months, short.vintage.observation_time_ns, short.vintage.vintage_id, _decimal_text(short_value),
        long.vintage.series_id, long.tenor_months, long.vintage.observation_time_ns, long.vintage.vintage_id, _decimal_text(long_value),
        _decimal_text(long_value - short_value), short.vintage.unit, store.fingerprint,
    )


def compute_currency_macro_differential(*, store: RatesMacroStore, base_series_id: str, quote_series_id: str, decision_time_ns: int) -> CurrencyMacroDifferential:
    base = store.resolve_latest_as_of(series_id=base_series_id, decision_time_ns=decision_time_ns)
    quote = store.resolve_latest_as_of(series_id=quote_series_id, decision_time_ns=decision_time_ns)
    if base is None or quote is None:
        raise RatesCurrencyMacroError("currency macro legs unavailable as-of decision time")
    if base.currency == quote.currency:
        raise RatesCurrencyMacroError("base and quote currency must differ")
    if base.metric_kind != quote.metric_kind or base.vintage.unit != quote.vintage.unit:
        raise RatesCurrencyMacroError("currency macro legs must share metric kind and unit")
    if base.metric_kind == "GOVERNMENT_YIELD" and base.tenor_months != quote.tenor_months:
        raise RatesCurrencyMacroError("cross-currency yields require matched tenor")
    base_value = _decimal(base.vintage.value_text, field="base value")
    quote_value = _decimal(quote.vintage.value_text, field="quote value")
    return CurrencyMacroDifferential(
        decision_time_ns, base.metric_kind, base.tenor_months,
        base.currency, base.jurisdiction, base.vintage.series_id, base.vintage.observation_time_ns, base.vintage.vintage_id, _decimal_text(base_value),
        quote.currency, quote.jurisdiction, quote.vintage.series_id, quote.vintage.observation_time_ns, quote.vintage.vintage_id, _decimal_text(quote_value),
        _decimal_text(base_value - quote_value), base.vintage.unit, store.fingerprint,
    )


def assert_no_rates_currency_trade_authority_fields() -> None:
    forbidden = {"trade_direction","signal_probability","success_probability","recommendation","risk_approval","execution_authority","order_intent","entry_price","stop_loss","take_profit"}
    for cls in (YieldCurveSpread, CurrencyMacroDifferential):
        overlap = sorted({field.name for field in fields(cls)} & forbidden)
        if overlap:
            raise RatesCurrencyMacroError(f"P10-E trade-authority field leak: {overlap}")
