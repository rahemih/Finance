from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence, cast


class MacroVintageError(ValueError):
    """Macro-vintage input, policy or timeline state is invalid."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SERIES_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise MacroVintageError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MacroVintageError(f"{field} must be a non-empty string")
    return value.strip()


def _series_id(value: object) -> str:
    text = _text(value, field="series_id")
    if _SERIES_ID.fullmatch(text) is None:
        raise MacroVintageError("series_id contains unsafe characters")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MacroVintageError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    number = _non_negative_int(value, field=field)
    if number <= 0:
        raise MacroVintageError(f"{field} must be a positive integer")
    return number


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise MacroVintageError(f"{field} must be lowercase SHA-256")
    return text


def _safe_relative_path(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise MacroVintageError(f"{field} must be a safe relative path")
    return text


def _decimal_text(value: object) -> str:
    text = _text(value, field="value_text")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise MacroVintageError("value_text must be a finite decimal") from exc
    if not number.is_finite():
        raise MacroVintageError("value_text must be a finite decimal")
    return text


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class MacroVintagePolicy:
    max_vintages_per_store: int
    production_macro_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "MacroVintagePolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise MacroVintageError(f"invalid macro-vintage policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise MacroVintageError("unsupported macro-vintage policy schema_version")
        if raw.get("mode") != "REFERENCE_IN_MEMORY_REVISION_AWARE_VINTAGES":
            raise MacroVintageError("unsupported macro-vintage mode")
        if raw.get("as_of_rule") != "RELEASE_AND_OBSERVED_AT_NOT_AFTER_DECISION_TIME":
            raise MacroVintageError("unsupported macro-vintage as-of rule")
        if raw.get("revision_rule") != "ZERO_BASED_CONTIGUOUS_PER_OBSERVATION":
            raise MacroVintageError("unsupported macro-vintage revision rule")
        if raw.get("time_rule") != "NON_DECREASING_RELEASE_AND_OBSERVED_AT_ACROSS_REVISIONS":
            raise MacroVintageError("unsupported macro-vintage time rule")
        if raw.get("network_required") is not False:
            raise MacroVintageError("reference macro-vintage model must not require network")
        if raw.get("credentials_required") is not False:
            raise MacroVintageError("reference macro-vintage model must not require credentials")
        return cls(
            max_vintages_per_store=_positive_int(
                raw.get("max_vintages_per_store"),
                field="max_vintages_per_store",
            ),
            production_macro_storage_vendor=_text(
                raw.get("production_macro_storage_vendor"),
                field="production_macro_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class MacroVintage:
    series_id: str
    observation_time_ns: int
    release_time_ns: int
    observed_at_ns: int
    revision_number: int
    value_text: str
    unit: str
    source: str
    source_dataset_version: str
    source_payload_sha256: str
    source_object_relative_path: str
    source_revision_id: str | None = None

    def __post_init__(self) -> None:
        _series_id(self.series_id)
        _non_negative_int(self.observation_time_ns, field="observation_time_ns")
        _non_negative_int(self.release_time_ns, field="release_time_ns")
        _non_negative_int(self.observed_at_ns, field="observed_at_ns")
        _non_negative_int(self.revision_number, field="revision_number")
        _decimal_text(self.value_text)
        _text(self.unit, field="unit")
        _text(self.source, field="source")
        _sha256_text(self.source_dataset_version, field="source_dataset_version")
        _sha256_text(self.source_payload_sha256, field="source_payload_sha256")
        _safe_relative_path(
            self.source_object_relative_path,
            field="source_object_relative_path",
        )
        if self.observed_at_ns < self.release_time_ns:
            raise MacroVintageError("observed_at_ns cannot precede release_time_ns")
        if self.source_revision_id is not None:
            _text(self.source_revision_id, field="source_revision_id")

    def identity_payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "series_id": self.series_id,
            "observation_time_ns": self.observation_time_ns,
            "release_time_ns": self.release_time_ns,
            "observed_at_ns": self.observed_at_ns,
            "revision_number": self.revision_number,
            "value_text": self.value_text,
            "unit": self.unit,
            "source": self.source,
            "source_dataset_version": self.source_dataset_version,
            "source_payload_sha256": self.source_payload_sha256,
            "source_object_relative_path": self.source_object_relative_path,
            "source_revision_id": self.source_revision_id,
        }

    @property
    def vintage_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.identity_payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class MacroAsOfSnapshot:
    series_id: str
    decision_time_ns: int
    vintages: tuple[MacroVintage, ...]
    store_fingerprint: str


class MacroVintageStore:
    """Immutable revision-aware reference store for anti-lookahead replay."""

    def __init__(self, vintages: Sequence[MacroVintage], policy: MacroVintagePolicy) -> None:
        frozen = tuple(vintages)
        if len(frozen) > policy.max_vintages_per_store:
            raise MacroVintageError("macro vintage count exceeds policy")

        keys = [
            (vintage.series_id, vintage.observation_time_ns, vintage.revision_number)
            for vintage in frozen
        ]
        if len(keys) != len(set(keys)):
            raise MacroVintageError("duplicate macro series/observation/revision identity")

        groups: dict[tuple[str, int], list[MacroVintage]] = {}
        for vintage in frozen:
            groups.setdefault((vintage.series_id, vintage.observation_time_ns), []).append(vintage)

        canonical_groups: dict[tuple[str, int], tuple[MacroVintage, ...]] = {}
        for key, values in groups.items():
            ordered = tuple(sorted(values, key=lambda item: item.revision_number))
            revisions = [item.revision_number for item in ordered]
            if revisions != list(range(len(ordered))):
                raise MacroVintageError("macro revisions must be zero-based and contiguous")
            for previous, current in zip(ordered, ordered[1:], strict=False):
                if current.release_time_ns < previous.release_time_ns:
                    raise MacroVintageError("macro revision release_time_ns cannot move backward")
                if current.observed_at_ns < previous.observed_at_ns:
                    raise MacroVintageError("macro revision observed_at_ns cannot move backward")
            canonical_groups[key] = ordered

        self._policy = policy
        self._groups = canonical_groups
        self._series_ids = tuple(sorted({vintage.series_id for vintage in frozen}))
        self._fingerprint = self._build_fingerprint(frozen)

    @staticmethod
    def _build_fingerprint(vintages: Sequence[MacroVintage]) -> str:
        ordered = sorted(
            vintages,
            key=lambda item: (
                item.series_id,
                item.observation_time_ns,
                item.revision_number,
                item.vintage_id,
            ),
        )
        return hashlib.sha256(
            _canonical_bytes([item.identity_payload() | {"vintage_id": item.vintage_id} for item in ordered])
        ).hexdigest()

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @property
    def vintage_count(self) -> int:
        return sum(len(values) for values in self._groups.values())

    def resolve(
        self,
        *,
        series_id: str,
        observation_time_ns: int,
        decision_time_ns: int,
    ) -> MacroVintage | None:
        safe_series = _series_id(series_id)
        observation = _non_negative_int(observation_time_ns, field="observation_time_ns")
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        values = self._groups.get((safe_series, observation), ())
        eligible = [
            vintage
            for vintage in values
            if vintage.release_time_ns <= decision and vintage.observed_at_ns <= decision
        ]
        if not eligible:
            return None
        return eligible[-1]

    def snapshot_as_of(self, *, series_id: str, decision_time_ns: int) -> MacroAsOfSnapshot:
        safe_series = _series_id(series_id)
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        resolved: list[MacroVintage] = []
        observations = sorted(
            observation
            for series, observation in self._groups
            if series == safe_series
        )
        for observation in observations:
            vintage = self.resolve(
                series_id=safe_series,
                observation_time_ns=observation,
                decision_time_ns=decision,
            )
            if vintage is not None:
                resolved.append(vintage)
        return MacroAsOfSnapshot(
            series_id=safe_series,
            decision_time_ns=decision,
            vintages=tuple(resolved),
            store_fingerprint=self._fingerprint,
        )

    def latest_projection(self, *, series_id: str) -> tuple[MacroVintage, ...]:
        """Current projection only; callers must use snapshot_as_of for replay."""
        safe_series = _series_id(series_id)
        latest = [
            values[-1]
            for (series, _), values in self._groups.items()
            if series == safe_series
        ]
        return tuple(sorted(latest, key=lambda item: item.observation_time_ns))
