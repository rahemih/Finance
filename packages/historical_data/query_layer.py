from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence, cast


class TimeSeriesQueryError(ValueError):
    """Time-series query-layer input, policy or index state is invalid."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TimeSeriesQueryError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TimeSeriesQueryError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TimeSeriesQueryError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise TimeSeriesQueryError(f"{field} must be a non-negative integer")
    return value


def _unique_text_tuple(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field=field) for value in values)
    if len(normalized) != len(set(normalized)):
        raise TimeSeriesQueryError(f"{field} values must be unique")
    return normalized


def _safe_archive_reference(value: str) -> str:
    text = _text(value, field="source_object_relative_path")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise TimeSeriesQueryError("source_object_relative_path must be a safe relative archive path")
    return text


@dataclass(frozen=True, slots=True)
class TimeSeriesQueryPolicy:
    partition_span_ns: int
    max_records_per_index: int
    max_query_limit: int
    max_partitions_per_query: int
    minimum_synthetic_queries_per_second: int
    production_query_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "TimeSeriesQueryPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise TimeSeriesQueryError(f"invalid query-layer policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise TimeSeriesQueryError("unsupported query-layer policy schema_version")
        if raw.get("mode") != "REFERENCE_IN_MEMORY_TIME_PARTITION_INDEX_ONLY":
            raise TimeSeriesQueryError("unsupported query-layer mode")
        if raw.get("window_semantics") != "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE":
            raise TimeSeriesQueryError("unsupported time-window semantics")
        if raw.get("query_order") != "ASCENDING_EVENT_TIME_STABLE_TIEBREAK":
            raise TimeSeriesQueryError("unsupported query order")
        if raw.get("network_required") is not False:
            raise TimeSeriesQueryError("reference query layer must not require network")
        if raw.get("credentials_required") is not False:
            raise TimeSeriesQueryError("reference query layer must not require credentials")
        return cls(
            partition_span_ns=_positive_int(raw.get("partition_span_ns"), field="partition_span_ns"),
            max_records_per_index=_positive_int(raw.get("max_records_per_index"), field="max_records_per_index"),
            max_query_limit=_positive_int(raw.get("max_query_limit"), field="max_query_limit"),
            max_partitions_per_query=_positive_int(raw.get("max_partitions_per_query"), field="max_partitions_per_query"),
            minimum_synthetic_queries_per_second=_positive_int(
                raw.get("minimum_synthetic_queries_per_second"),
                field="minimum_synthetic_queries_per_second",
            ),
            production_query_storage_vendor=_text(
                raw.get("production_query_storage_vendor"),
                field="production_query_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class TimeSeriesRecord:
    record_id: str
    canonical_id: str
    kind: str
    provider: str
    event_time_ns: int
    receive_time_ns: int
    sequence_id: str
    canonical_schema_version: str
    canonical_payload_json: str
    source_payload_sha256: str
    source_object_relative_path: str
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _text(self.record_id, field="record_id")
        _text(self.canonical_id, field="canonical_id")
        _text(self.kind, field="kind")
        _text(self.provider, field="provider")
        _non_negative_int(self.event_time_ns, field="event_time_ns")
        _non_negative_int(self.receive_time_ns, field="receive_time_ns")
        _text(self.sequence_id, field="sequence_id")
        _text(self.canonical_schema_version, field="canonical_schema_version")
        _text(self.canonical_payload_json, field="canonical_payload_json")
        if _SHA256.fullmatch(self.source_payload_sha256) is None:
            raise TimeSeriesQueryError("source_payload_sha256 must be lowercase SHA-256")
        _safe_archive_reference(self.source_object_relative_path)
        keys = [key for key, _ in self.provenance]
        if len(keys) != len(set(keys)):
            raise TimeSeriesQueryError("provenance keys must be unique")
        for key, value in self.provenance:
            _text(key, field="provenance key")
            _text(value, field="provenance value")


@dataclass(frozen=True, slots=True)
class TimeSeriesQuery:
    start_ns: int
    end_ns: int
    limit: int
    canonical_ids: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _non_negative_int(self.start_ns, field="start_ns")
        _non_negative_int(self.end_ns, field="end_ns")
        if self.end_ns <= self.start_ns:
            raise TimeSeriesQueryError("end_ns must be greater than start_ns")
        _positive_int(self.limit, field="limit")
        _unique_text_tuple(self.canonical_ids, field="canonical_ids")
        _unique_text_tuple(self.providers, field="providers")
        _unique_text_tuple(self.kinds, field="kinds")


@dataclass(frozen=True, slots=True)
class TimeSeriesQueryResult:
    records: tuple[TimeSeriesRecord, ...]
    matched_count: int
    candidate_count: int
    partitions_examined: int
    total_index_records: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class _Partition:
    records: tuple[TimeSeriesRecord, ...]
    times: tuple[int, ...]


def _record_sort_key(record: TimeSeriesRecord) -> tuple[int, str, str, str]:
    return (record.event_time_ns, record.canonical_id, record.sequence_id, record.record_id)


class TimeSeriesQueryIndex:
    """Deterministic reference index; not a production database selection."""

    def __init__(self, records: Sequence[TimeSeriesRecord], policy: TimeSeriesQueryPolicy) -> None:
        frozen = tuple(records)
        if len(frozen) > policy.max_records_per_index:
            raise TimeSeriesQueryError("record count exceeds query-layer policy")
        record_ids = [record.record_id for record in frozen]
        if len(record_ids) != len(set(record_ids)):
            raise TimeSeriesQueryError("record_id values must be unique")

        buckets: dict[tuple[str, int], list[TimeSeriesRecord]] = {}
        for record in frozen:
            partition_id = record.event_time_ns // policy.partition_span_ns
            buckets.setdefault((record.canonical_id, partition_id), []).append(record)

        partitions: dict[tuple[str, int], _Partition] = {}
        for key, values in buckets.items():
            ordered = tuple(sorted(values, key=_record_sort_key))
            partitions[key] = _Partition(
                records=ordered,
                times=tuple(record.event_time_ns for record in ordered),
            )

        self._policy = policy
        self._partitions = partitions
        self._canonical_ids = tuple(sorted({record.canonical_id for record in frozen}))
        self._total_records = len(frozen)
        self._fingerprint = self._build_fingerprint(frozen)

    @staticmethod
    def _build_fingerprint(records: Sequence[TimeSeriesRecord]) -> str:
        ordered = sorted(records, key=lambda record: (record.canonical_id, *_record_sort_key(record)))
        payload: list[dict[str, object]] = []
        for record in ordered:
            payload.append(
                {
                    "record_id": record.record_id,
                    "canonical_id": record.canonical_id,
                    "kind": record.kind,
                    "provider": record.provider,
                    "event_time_ns": record.event_time_ns,
                    "receive_time_ns": record.receive_time_ns,
                    "sequence_id": record.sequence_id,
                    "canonical_schema_version": record.canonical_schema_version,
                    "canonical_payload_sha256": hashlib.sha256(
                        record.canonical_payload_json.encode("utf-8")
                    ).hexdigest(),
                    "source_payload_sha256": record.source_payload_sha256,
                    "source_object_relative_path": record.source_object_relative_path,
                    "provenance": list(record.provenance),
                }
            )
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @property
    def total_records(self) -> int:
        return self._total_records

    @property
    def partition_count(self) -> int:
        return len(self._partitions)

    def query(self, query: TimeSeriesQuery) -> TimeSeriesQueryResult:
        if query.limit > self._policy.max_query_limit:
            raise TimeSeriesQueryError("query limit exceeds query-layer policy")

        first_partition = query.start_ns // self._policy.partition_span_ns
        last_partition = (query.end_ns - 1) // self._policy.partition_span_ns
        partition_span = last_partition - first_partition + 1
        if partition_span > self._policy.max_partitions_per_query:
            raise TimeSeriesQueryError("query time range exceeds partition policy")

        canonical_ids = query.canonical_ids or self._canonical_ids
        provider_filter = frozenset(query.providers)
        kind_filter = frozenset(query.kinds)
        selected: list[TimeSeriesRecord] = []
        candidate_count = 0
        partitions_examined = 0

        for canonical_id in canonical_ids:
            for partition_id in range(first_partition, last_partition + 1):
                partition = self._partitions.get((canonical_id, partition_id))
                if partition is None:
                    continue
                partitions_examined += 1
                left = bisect_left(partition.times, query.start_ns)
                right = bisect_left(partition.times, query.end_ns)
                candidate_count += right - left
                for record in partition.records[left:right]:
                    if provider_filter and record.provider not in provider_filter:
                        continue
                    if kind_filter and record.kind not in kind_filter:
                        continue
                    selected.append(record)

        ordered = tuple(sorted(selected, key=_record_sort_key))
        matched_count = len(ordered)
        return TimeSeriesQueryResult(
            records=ordered[: query.limit],
            matched_count=matched_count,
            candidate_count=candidate_count,
            partitions_examined=partitions_examined,
            total_index_records=self._total_records,
            truncated=matched_count > query.limit,
        )
