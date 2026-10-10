from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .release_history import EconomicReleaseHistory


class MacroSurpriseError(ValueError):
    """Raised when P10-D macro-surprise invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MacroSurpriseError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MacroSurpriseError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise MacroSurpriseError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MacroSurpriseError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MacroSurpriseError(f"{field} must be a non-negative integer")
    return value


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise MacroSurpriseError(f"{field} must be lowercase SHA-256")
    return text


def _decimal(value: object, *, field: str) -> Decimal:
    text = _text(value, field=field)
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise MacroSurpriseError(f"{field} must be a finite decimal") from exc
    if not number.is_finite():
        raise MacroSurpriseError(f"{field} must be a finite decimal")
    return number


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True, slots=True)
class MacroSurprisePolicy:
    allowed_consensus_methods: tuple[str, ...]
    minimum_consensus_sample_size: int
    consensus_time_rule: str
    actual_rule: str
    surprise_rule: str
    direction_labels: tuple[str, ...]
    market_direction_interpretation_allowed: bool
    standardized_surprise_in_scope: bool
    production_consensus_provider: str
    network_required: bool
    credentials_required: bool
    direct_trade_output_allowed: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "MacroSurprisePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise MacroSurpriseError("unsupported macro-surprise policy schema_version")
        methods_value = raw.get("allowed_consensus_methods")
        labels_value = raw.get("direction_labels")
        if not isinstance(methods_value, list) or not isinstance(labels_value, list):
            raise MacroSurpriseError("policy methods and direction labels must be lists")
        methods = tuple(_text(item, field="consensus method") for item in cast(list[object], methods_value))
        labels = tuple(_text(item, field="direction label") for item in cast(list[object], labels_value))
        policy = cls(
            allowed_consensus_methods=methods,
            minimum_consensus_sample_size=_positive_int(raw.get("minimum_consensus_sample_size"), field="minimum_consensus_sample_size"),
            consensus_time_rule=_text(raw.get("consensus_time_rule"), field="consensus_time_rule"),
            actual_rule=_text(raw.get("actual_rule"), field="actual_rule"),
            surprise_rule=_text(raw.get("surprise_rule"), field="surprise_rule"),
            direction_labels=labels,
            market_direction_interpretation_allowed=_boolean(raw.get("market_direction_interpretation_allowed"), field="market_direction_interpretation_allowed"),
            standardized_surprise_in_scope=_boolean(raw.get("standardized_surprise_in_scope"), field="standardized_surprise_in_scope"),
            production_consensus_provider=_text(raw.get("production_consensus_provider"), field="production_consensus_provider"),
            network_required=_boolean(raw.get("network_required"), field="network_required"),
            credentials_required=_boolean(raw.get("credentials_required"), field="credentials_required"),
            direct_trade_output_allowed=_boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed"),
            live_trading=_text(raw.get("live_trading"), field="live_trading"),
            auto_trading=_text(raw.get("auto_trading"), field="auto_trading"),
        )
        if policy.allowed_consensus_methods != ("CONSENSUS_MEDIAN", "CONSENSUS_MEAN"):
            raise MacroSurpriseError("consensus-method policy drift")
        if policy.minimum_consensus_sample_size < 2:
            raise MacroSurpriseError("consensus sample size must be at least two")
        if policy.consensus_time_rule != "OBSERVED_AT_STRICTLY_BEFORE_FIRST_RELEASE_TIME":
            raise MacroSurpriseError("consensus time rule drift")
        if policy.actual_rule != "P10C_REVISION_ZERO_FIRST_RELEASE_ONLY":
            raise MacroSurpriseError("actual-value rule drift")
        if policy.surprise_rule != "ACTUAL_MINUS_CONSENSUS":
            raise MacroSurpriseError("surprise rule drift")
        if policy.direction_labels != ("ABOVE_CONSENSUS", "BELOW_CONSENSUS", "AT_CONSENSUS"):
            raise MacroSurpriseError("direction label drift")
        if policy.market_direction_interpretation_allowed or policy.standardized_surprise_in_scope:
            raise MacroSurpriseError("P10-D raw surprise must remain descriptive only")
        if policy.production_consensus_provider != "NOT_SELECTED":
            raise MacroSurpriseError("P10-D cannot select a production consensus provider")
        if policy.network_required or policy.credentials_required or policy.direct_trade_output_allowed:
            raise MacroSurpriseError("P10-D must remain offline and non-trading")
        if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
            raise MacroSurpriseError("P10-D cannot enable trading")
        return policy


@dataclass(frozen=True, slots=True)
class ConsensusSnapshot:
    series_id: str
    provider_id: str
    method: str
    value_text: str
    unit: str
    observed_at_ns: int
    sample_size: int
    source_dataset_version: str
    source_payload_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0",
            "series_id":self.series_id,
            "provider_id":self.provider_id,
            "method":self.method,
            "value_text":self.value_text,
            "unit":self.unit,
            "observed_at_ns":self.observed_at_ns,
            "sample_size":self.sample_size,
            "source_dataset_version":self.source_dataset_version,
            "source_payload_sha256":self.source_payload_sha256,
        }

    @property
    def consensus_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class MacroSurpriseResult:
    surprise_id: str
    history_id: str
    series_id: str
    actual_vintage_id: str
    actual_value_text: str
    consensus_id: str
    consensus_value_text: str
    unit: str
    surprise_value_text: str
    direction: str
    first_release_time_ns: int
    first_release_observed_at_ns: int
    consensus_observed_at_ns: int
    previous_at_first_release_vintage_id: str | None

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0",
            "surprise_id":self.surprise_id,
            "history_id":self.history_id,
            "series_id":self.series_id,
            "actual_vintage_id":self.actual_vintage_id,
            "actual_value_text":self.actual_value_text,
            "consensus_id":self.consensus_id,
            "consensus_value_text":self.consensus_value_text,
            "unit":self.unit,
            "surprise_value_text":self.surprise_value_text,
            "direction":self.direction,
            "first_release_time_ns":self.first_release_time_ns,
            "first_release_observed_at_ns":self.first_release_observed_at_ns,
            "consensus_observed_at_ns":self.consensus_observed_at_ns,
            "previous_at_first_release_vintage_id":self.previous_at_first_release_vintage_id,
        }


def validate_consensus_snapshot(
    snapshot: ConsensusSnapshot,
    *,
    policy: MacroSurprisePolicy,
) -> ConsensusSnapshot:
    series_id = _text(snapshot.series_id, field="series_id")
    provider_id = _text(snapshot.provider_id, field="provider_id")
    method = _text(snapshot.method, field="method")
    if method not in policy.allowed_consensus_methods:
        raise MacroSurpriseError("consensus method is not allowed")
    value = _decimal(snapshot.value_text, field="value_text")
    unit = _text(snapshot.unit, field="unit")
    observed = _non_negative_int(snapshot.observed_at_ns, field="observed_at_ns")
    sample = _positive_int(snapshot.sample_size, field="sample_size")
    if sample < policy.minimum_consensus_sample_size:
        raise MacroSurpriseError("consensus sample size below policy minimum")
    dataset = _sha256_text(snapshot.source_dataset_version, field="source_dataset_version")
    payload = _sha256_text(snapshot.source_payload_sha256, field="source_payload_sha256")
    return ConsensusSnapshot(
        series_id=series_id,
        provider_id=provider_id,
        method=method,
        value_text=_decimal_text(value),
        unit=unit,
        observed_at_ns=observed,
        sample_size=sample,
        source_dataset_version=dataset,
        source_payload_sha256=payload,
    )


def compute_macro_surprise(
    *,
    history: EconomicReleaseHistory,
    consensus: ConsensusSnapshot,
    policy: MacroSurprisePolicy,
) -> MacroSurpriseResult:
    valid = validate_consensus_snapshot(consensus, policy=policy)
    actual = history.first_release

    if valid.series_id != history.series_id:
        raise MacroSurpriseError("consensus series must match P10-C history series")
    if valid.unit != actual.unit:
        raise MacroSurpriseError("consensus unit must match first-release actual unit")
    if valid.observed_at_ns >= actual.release_time_ns:
        raise MacroSurpriseError("consensus must be observed strictly before first-release time")

    actual_value = _decimal(actual.value_text, field="actual value")
    consensus_value = _decimal(valid.value_text, field="consensus value")
    raw = actual_value - consensus_value
    if raw > 0:
        direction = "ABOVE_CONSENSUS"
    elif raw < 0:
        direction = "BELOW_CONSENSUS"
    else:
        direction = "AT_CONSENSUS"

    previous = history.previous_at_first_release
    identity_payload: dict[str, object] = {
        "schema_version":"1.0",
        "history_id":history.history_id,
        "series_id":history.series_id,
        "actual_vintage_id":actual.vintage_id,
        "consensus_id":valid.consensus_id,
        "surprise_value_text":_decimal_text(raw),
        "direction":direction,
        "previous_at_first_release_vintage_id":previous.vintage_id if previous is not None else None,
    }
    surprise_id = hashlib.sha256(_canonical_bytes(identity_payload)).hexdigest()

    return MacroSurpriseResult(
        surprise_id=surprise_id,
        history_id=history.history_id,
        series_id=history.series_id,
        actual_vintage_id=actual.vintage_id,
        actual_value_text=_decimal_text(actual_value),
        consensus_id=valid.consensus_id,
        consensus_value_text=_decimal_text(consensus_value),
        unit=actual.unit,
        surprise_value_text=_decimal_text(raw),
        direction=direction,
        first_release_time_ns=actual.release_time_ns,
        first_release_observed_at_ns=actual.observed_at_ns,
        consensus_observed_at_ns=valid.observed_at_ns,
        previous_at_first_release_vintage_id=previous.vintage_id if previous is not None else None,
    )


def assert_no_surprise_trade_probability_fields() -> None:
    forbidden={
        "probability","success_probability","recommendation","bullish","bearish",
        "long","short","order","quantity","leverage","entry","exit","risk_approval",
    }
    fields_seen={field.name for field in fields(MacroSurpriseResult)}
    if forbidden & fields_seen:
        raise MacroSurpriseError("P10-D result exposes trade/probability/market-direction fields")
