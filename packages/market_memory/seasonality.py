from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isqrt
import json
from pathlib import Path
import re
from typing import Mapping, Sequence, cast

from .knowledge_graph import KnowledgeGraphPolicy


class SeasonalityError(ValueError):
    """P12-F seasonality policy or evidence violates governed invariants."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NANOSECONDS_PER_SECOND = 1_000_000_000


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SeasonalityError(f"{field} must be integer")
    return value


def _positive_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number <= 0:
        raise SeasonalityError(f"{field} must be positive")
    return number


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SeasonalityError(f"{field} must be non-empty text")
    return value.strip()


def _trunc_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise SeasonalityError("division denominator must be positive")
    if numerator < 0:
        return -((-numerator) // denominator)
    return numerator // denominator


@dataclass(frozen=True, slots=True)
class SeasonalityPolicy:
    bucket_kinds: tuple[str, ...]
    minimum_sample_count: int
    return_min_bps: int
    return_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    calendar_timezone: str
    session_calendar_in_scope: bool
    seasonality_is_causation: bool
    seasonality_is_probability: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "SeasonalityPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise SeasonalityError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "UTC_REGIME_CONDITIONAL_SEASONALITY":
            raise SeasonalityError("unsupported P12-F policy")

        kinds_value = raw.get("bucket_kinds")
        if not isinstance(kinds_value, list):
            raise SeasonalityError("bucket_kinds must be list")
        kinds = tuple(str(item).strip().upper() for item in cast(list[object], kinds_value))
        if set(kinds) != {"HOUR_OF_DAY_UTC", "DAY_OF_WEEK_UTC", "MONTH_OF_YEAR_UTC"}:
            raise SeasonalityError("unexpected seasonality bucket kinds")

        minimum = _positive_integer(raw.get("minimum_sample_count"), field="minimum_sample_count")
        if minimum < 3:
            raise SeasonalityError("minimum_sample_count must be >= 3")

        return_min = _integer(raw.get("return_min_bps"), field="return_min_bps")
        return_max = _integer(raw.get("return_max_bps"), field="return_max_bps")
        if (return_min, return_max) != (-10000, 10000):
            raise SeasonalityError("return scale must be signed basis points")

        uncertainty_min = _integer(raw.get("uncertainty_min_bps"), field="uncertainty_min_bps")
        uncertainty_max = _integer(raw.get("uncertainty_max_bps"), field="uncertainty_max_bps")
        if (uncertainty_min, uncertainty_max) != (0, 10000):
            raise SeasonalityError("uncertainty scale must be unsigned basis points")

        if raw.get("calendar_timezone") != "UTC":
            raise SeasonalityError("P12-F calendar timezone must remain UTC")
        if raw.get("session_calendar_in_scope") is not False:
            raise SeasonalityError("session calendar belongs to P13-A")
        if raw.get("seasonality_is_causation") is not False:
            raise SeasonalityError("seasonality cannot be causation")
        if raw.get("seasonality_is_probability") is not False:
            raise SeasonalityError("seasonality cannot be probability")
        if raw.get("canonical_tests_network_required") is not False:
            raise SeasonalityError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise SeasonalityError("P12-F cannot enable trading")

        return cls(
            bucket_kinds=kinds,
            minimum_sample_count=minimum,
            return_min_bps=return_min,
            return_max_bps=return_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            calendar_timezone="UTC",
            session_calendar_in_scope=False,
            seasonality_is_causation=False,
            seasonality_is_probability=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class SeasonalityObservation:
    timestamp_ns: int
    return_bps: int
    regime_label: str


@dataclass(frozen=True, slots=True)
class SeasonalityResult:
    bucket_kind: str
    bucket_value: int
    regime_label: str
    sample_count: int
    mean_return_bps: int
    dispersion_bps: int
    sampling_uncertainty_bps: int
    valid_from_ns: int
    valid_to_ns: int
    provenance_sha256: tuple[str, ...]
    source_dataset_versions: tuple[str, ...]


def _bucket_value(timestamp_ns: int, bucket_kind: str) -> int:
    seconds = timestamp_ns // _NANOSECONDS_PER_SECOND
    instant = datetime.fromtimestamp(seconds, tz=timezone.utc)
    if bucket_kind == "HOUR_OF_DAY_UTC":
        return instant.hour
    if bucket_kind == "DAY_OF_WEEK_UTC":
        return instant.weekday()
    if bucket_kind == "MONTH_OF_YEAR_UTC":
        return instant.month
    raise SeasonalityError("unknown bucket_kind")


def _validate_bucket_value(bucket_kind: str, bucket_value: int) -> None:
    ranges = {
        "HOUR_OF_DAY_UTC": (0, 23),
        "DAY_OF_WEEK_UTC": (0, 6),
        "MONTH_OF_YEAR_UTC": (1, 12),
    }
    low, high = ranges[bucket_kind]
    if not low <= bucket_value <= high:
        raise SeasonalityError("bucket_value outside governed range")


def compute_seasonality(
    observations: Sequence[SeasonalityObservation],
    *,
    bucket_kind: str,
    bucket_value: int,
    regime_label: str | None,
    provenance_sha256: Sequence[str],
    source_dataset_versions: Sequence[str],
    graph_policy: KnowledgeGraphPolicy,
    policy: SeasonalityPolicy,
) -> SeasonalityResult:
    kind = bucket_kind.upper()
    if kind not in policy.bucket_kinds:
        raise SeasonalityError("bucket_kind is not governed")
    value = _integer(bucket_value, field="bucket_value")
    _validate_bucket_value(kind, value)

    normalized_regime = regime_label.upper() if regime_label is not None else "UNSPECIFIED"
    if normalized_regime not in graph_policy.regime_labels:
        raise SeasonalityError("unknown regime_label")

    ordered = tuple(sorted(observations, key=lambda item: item.timestamp_ns))
    if not ordered:
        raise SeasonalityError("seasonality observations must be non-empty")
    timestamps = [item.timestamp_ns for item in ordered]
    if len(timestamps) != len(set(timestamps)):
        raise SeasonalityError("duplicate observation timestamp")

    qualifying: list[SeasonalityObservation] = []
    for item in ordered:
        if item.timestamp_ns < 0:
            raise SeasonalityError("timestamp_ns must be non-negative")
        if not policy.return_min_bps <= item.return_bps <= policy.return_max_bps:
            raise SeasonalityError("return_bps outside governed bounds")
        item_regime = _text(item.regime_label, field="regime_label").upper()
        if item_regime not in graph_policy.regime_labels:
            raise SeasonalityError("observation regime is unknown")
        if regime_label is not None and item_regime != normalized_regime:
            continue
        if _bucket_value(item.timestamp_ns, kind) == value:
            qualifying.append(item)

    if len(qualifying) < policy.minimum_sample_count:
        raise SeasonalityError("insufficient qualifying seasonality sample count")

    returns = tuple(item.return_bps for item in qualifying)
    mean_return = _trunc_div(sum(returns), len(returns))
    dispersion = _trunc_div(sum(abs(item - mean_return) for item in returns), len(returns))
    sampling = 10000 // max(1, isqrt(len(returns)))
    uncertainty = min(
        policy.uncertainty_max_bps,
        max(policy.uncertainty_min_bps, dispersion, sampling),
    )

    provenance = tuple(sorted({_text(item, field="provenance_sha256") for item in provenance_sha256}))
    if not provenance or any(_SHA256.fullmatch(item) is None for item in provenance):
        raise SeasonalityError("valid provenance SHA-256 is required")
    versions = tuple(sorted({_text(item, field="source_dataset_version") for item in source_dataset_versions}))
    if not versions:
        raise SeasonalityError("source dataset versions are required")

    return SeasonalityResult(
        bucket_kind=kind,
        bucket_value=value,
        regime_label=normalized_regime,
        sample_count=len(qualifying),
        mean_return_bps=mean_return,
        dispersion_bps=dispersion,
        sampling_uncertainty_bps=uncertainty,
        valid_from_ns=qualifying[0].timestamp_ns,
        valid_to_ns=qualifying[-1].timestamp_ns + 1,
        provenance_sha256=provenance,
        source_dataset_versions=versions,
    )
