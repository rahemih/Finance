from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast

from packages.historical_data import TimeSeriesRecord


class IntegrityCheckError(ValueError):
    """Integrity-check policy or invocation is invalid."""


class IntegrityOutcome(StrEnum):
    VALID = "VALID"
    INVALID_CRITICAL = "INVALID_CRITICAL"


class SequenceSemantics(StrEnum):
    NUMERIC_MONOTONIC_CONTIGUOUS = "NUMERIC_MONOTONIC_CONTIGUOUS"
    OPAQUE_NO_ORDER = "OPAQUE_NO_ORDER"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise IntegrityCheckError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise IntegrityCheckError(f"{field} must be a positive integer")
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class IntegrityCheckPolicy:
    max_records_per_batch: int
    allowed_sequence_semantics: frozenset[SequenceSemantics]
    production_data_quality_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "IntegrityCheckPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise IntegrityCheckError(f"invalid integrity-check policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise IntegrityCheckError("unsupported policy schema_version")
        if raw.get("mode") != "EXPLICIT_RULES_FAIL_CLOSED":
            raise IntegrityCheckError("unsupported integrity-check mode")
        for field in (
            "staleness_violation_outcome",
            "future_time_outcome",
            "outlier_violation_outcome",
            "sequence_violation_outcome",
        ):
            if raw.get(field) != "INVALID_CRITICAL":
                raise IntegrityCheckError(f"{field} must fail closed")
        if raw.get("adaptive_thresholds") is not False:
            raise IntegrityCheckError("adaptive thresholds are forbidden in P07-C")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise IntegrityCheckError("reference integrity checks must be offline")

        raw_semantics = raw.get("allowed_sequence_semantics")
        if not isinstance(raw_semantics, list) or not raw_semantics:
            raise IntegrityCheckError("allowed_sequence_semantics must be a non-empty list")
        semantics: set[SequenceSemantics] = set()
        for item in cast(list[object], raw_semantics):
            if not isinstance(item, str):
                raise IntegrityCheckError("sequence semantics must be strings")
            try:
                semantics.add(SequenceSemantics(item))
            except ValueError as exc:
                raise IntegrityCheckError(f"unsupported sequence semantics: {item}") from exc

        vendor = raw.get("production_data_quality_vendor")
        if not isinstance(vendor, str) or not vendor.strip():
            raise IntegrityCheckError("production_data_quality_vendor must be non-empty")

        return cls(
            max_records_per_batch=_positive_int(raw.get("max_records_per_batch"), field="max_records_per_batch"),
            allowed_sequence_semantics=frozenset(semantics),
            production_data_quality_vendor=vendor.strip(),
        )


@dataclass(frozen=True, slots=True)
class IntegrityBatch:
    records: tuple[TimeSeriesRecord, ...]
    upstream_quality_evidence_sha256: str

    def __post_init__(self) -> None:
        if _SHA256.fullmatch(self.upstream_quality_evidence_sha256) is None:
            raise IntegrityCheckError("upstream_quality_evidence_sha256 must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class FreshnessRule:
    kind: str
    max_event_age_ns: int
    max_receive_age_ns: int

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise IntegrityCheckError("freshness kind must be non-empty")
        if isinstance(self.max_event_age_ns, bool) or self.max_event_age_ns < 0:
            raise IntegrityCheckError("max_event_age_ns must be a non-negative integer")
        if isinstance(self.max_receive_age_ns, bool) or self.max_receive_age_ns < 0:
            raise IntegrityCheckError("max_receive_age_ns must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class NumericObservation:
    record_id: str
    metric: str
    event_time_ns: int
    value: Decimal

    def __post_init__(self) -> None:
        if not self.record_id.strip() or not self.metric.strip():
            raise IntegrityCheckError("observation record_id and metric must be non-empty")
        if isinstance(self.event_time_ns, bool) or self.event_time_ns < 0:
            raise IntegrityCheckError("observation event_time_ns must be non-negative")
        if not self.value.is_finite():
            raise IntegrityCheckError("observation value must be finite")


@dataclass(frozen=True, slots=True)
class OutlierRule:
    metric: str
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    max_abs_change: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise IntegrityCheckError("outlier metric must be non-empty")
        if self.minimum is None and self.maximum is None and self.max_abs_change is None:
            raise IntegrityCheckError("outlier rule must define at least one explicit bound")
        if self.minimum is not None and not self.minimum.is_finite():
            raise IntegrityCheckError("minimum must be finite")
        if self.maximum is not None and not self.maximum.is_finite():
            raise IntegrityCheckError("maximum must be finite")
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise IntegrityCheckError("maximum must be >= minimum")
        if self.max_abs_change is not None:
            if not self.max_abs_change.is_finite() or self.max_abs_change < 0:
                raise IntegrityCheckError("max_abs_change must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class SequenceRule:
    canonical_id: str
    provider: str
    semantics: SequenceSemantics

    def __post_init__(self) -> None:
        if not self.canonical_id.strip() or not self.provider.strip():
            raise IntegrityCheckError("sequence rule canonical_id/provider must be non-empty")


@dataclass(frozen=True, slots=True)
class IntegrityIssue:
    code: str
    record_id: str
    field: str
    message: str

    def payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "record_id": self.record_id,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    outcome: IntegrityOutcome
    issues: tuple[IntegrityIssue, ...]
    opaque_sequence_streams: tuple[str, ...]
    upstream_quality_evidence_sha256: str

    @property
    def is_valid(self) -> bool:
        return self.outcome is IntegrityOutcome.VALID

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": "1.0",
            "outcome": self.outcome.value,
            "issues": [issue.payload() for issue in self.issues],
            "opaque_sequence_streams": list(self.opaque_sequence_streams),
            "upstream_quality_evidence_sha256": self.upstream_quality_evidence_sha256,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _issue(code: str, record_id: str, field: str, message: str) -> IntegrityIssue:
    return IntegrityIssue(code=code, record_id=record_id, field=field, message=message)


def _stream_key(canonical_id: str, provider: str) -> str:
    return f"{canonical_id}|{provider}"


class IntegrityAnalyzer:
    def __init__(self, policy: IntegrityCheckPolicy) -> None:
        self._policy = policy

    def analyze(
        self,
        batch: IntegrityBatch,
        *,
        reference_time_ns: int,
        freshness_rules: tuple[FreshnessRule, ...],
        observations: tuple[NumericObservation, ...] = (),
        outlier_rules: tuple[OutlierRule, ...] = (),
        sequence_rules: tuple[SequenceRule, ...] = (),
    ) -> IntegrityReport:
        if isinstance(reference_time_ns, bool) or reference_time_ns < 0:
            raise IntegrityCheckError("reference_time_ns must be a non-negative integer")
        if len(batch.records) > self._policy.max_records_per_batch:
            raise IntegrityCheckError("record count exceeds policy max_records_per_batch")

        freshness_by_kind = {rule.kind: rule for rule in freshness_rules}
        if len(freshness_by_kind) != len(freshness_rules):
            raise IntegrityCheckError("freshness rule kinds must be unique")

        outlier_by_metric = {rule.metric: rule for rule in outlier_rules}
        if len(outlier_by_metric) != len(outlier_rules):
            raise IntegrityCheckError("outlier rule metrics must be unique")

        sequence_by_stream = {
            _stream_key(rule.canonical_id, rule.provider): rule for rule in sequence_rules
        }
        if len(sequence_by_stream) != len(sequence_rules):
            raise IntegrityCheckError("sequence rule streams must be unique")
        for rule in sequence_rules:
            if rule.semantics not in self._policy.allowed_sequence_semantics:
                raise IntegrityCheckError("sequence rule semantics not allowed by policy")

        issues: list[IntegrityIssue] = []

        # Freshness checks are rule-explicit by record kind.
        for record in batch.records:
            rule = freshness_by_kind.get(record.kind)
            if rule is None:
                issues.append(
                    _issue(
                        "MISSING_FRESHNESS_RULE",
                        record.record_id,
                        "kind",
                        f"no freshness rule declared for kind {record.kind}",
                    )
                )
                continue
            if record.event_time_ns > reference_time_ns:
                issues.append(
                    _issue("FUTURE_EVENT_TIME", record.record_id, "event_time_ns", "event time exceeds reference time")
                )
            elif reference_time_ns - record.event_time_ns > rule.max_event_age_ns:
                issues.append(
                    _issue("STALE_EVENT", record.record_id, "event_time_ns", "event age exceeds explicit threshold")
                )
            if record.receive_time_ns > reference_time_ns:
                issues.append(
                    _issue("FUTURE_RECEIVE_TIME", record.record_id, "receive_time_ns", "receive time exceeds reference time")
                )
            elif reference_time_ns - record.receive_time_ns > rule.max_receive_age_ns:
                issues.append(
                    _issue("STALE_RECEIVE", record.record_id, "receive_time_ns", "receive age exceeds explicit threshold")
                )

        # Outliers are checked only for explicitly supplied numeric observations/rules.
        record_ids = frozenset(record.record_id for record in batch.records)
        observations_by_metric: dict[str, list[NumericObservation]] = {}
        for observation in observations:
            if observation.record_id not in record_ids:
                issues.append(
                    _issue(
                        "UNKNOWN_OBSERVATION_RECORD",
                        observation.record_id,
                        "record_id",
                        "numeric observation does not reference a record in the batch",
                    )
                )
            observations_by_metric.setdefault(observation.metric, []).append(observation)

        for metric, values in sorted(observations_by_metric.items()):
            rule = outlier_by_metric.get(metric)
            if rule is None:
                for observation in values:
                    issues.append(
                        _issue(
                            "MISSING_OUTLIER_RULE",
                            observation.record_id,
                            "metric",
                            f"no explicit outlier rule declared for metric {metric}",
                        )
                    )
                continue
            ordered = sorted(values, key=lambda item: (item.event_time_ns, item.record_id))
            previous: NumericObservation | None = None
            for observation in ordered:
                if rule.minimum is not None and observation.value < rule.minimum:
                    issues.append(
                        _issue("OUTLIER_BELOW_MIN", observation.record_id, metric, "value is below explicit minimum")
                    )
                if rule.maximum is not None and observation.value > rule.maximum:
                    issues.append(
                        _issue("OUTLIER_ABOVE_MAX", observation.record_id, metric, "value is above explicit maximum")
                    )
                if previous is not None and rule.max_abs_change is not None:
                    if abs(observation.value - previous.value) > rule.max_abs_change:
                        issues.append(
                            _issue(
                                "OUTLIER_CHANGE",
                                observation.record_id,
                                metric,
                                "absolute change exceeds explicit threshold",
                            )
                        )
                previous = observation

        # Sequence checks are per stream and only when semantics are explicitly declared.
        streams: dict[str, list[TimeSeriesRecord]] = {}
        for record in batch.records:
            streams.setdefault(_stream_key(record.canonical_id, record.provider), []).append(record)

        opaque_streams: list[str] = []
        for key, records in sorted(streams.items()):
            rule = sequence_by_stream.get(key)
            if rule is None:
                for record in records:
                    issues.append(
                        _issue(
                            "MISSING_SEQUENCE_RULE",
                            record.record_id,
                            "sequence_id",
                            f"no sequence semantics declared for stream {key}",
                        )
                    )
                continue
            if rule.semantics is SequenceSemantics.OPAQUE_NO_ORDER:
                opaque_streams.append(key)
                continue

            ordered_records = sorted(
                records,
                key=lambda record: (record.receive_time_ns, record.event_time_ns, record.record_id),
            )
            previous_value: int | None = None
            for record in ordered_records:
                try:
                    current = int(record.sequence_id, 10)
                except ValueError:
                    issues.append(
                        _issue(
                            "SEQUENCE_PARSE_ERROR",
                            record.record_id,
                            "sequence_id",
                            "numeric sequence semantics declared but sequence_id is not an integer",
                        )
                    )
                    previous_value = None
                    continue
                if current < 0:
                    issues.append(
                        _issue(
                            "SEQUENCE_PARSE_ERROR",
                            record.record_id,
                            "sequence_id",
                            "numeric sequence_id must be non-negative",
                        )
                    )
                    previous_value = None
                    continue
                if previous_value is not None:
                    if current == previous_value:
                        issues.append(
                            _issue("SEQUENCE_DUPLICATE", record.record_id, "sequence_id", "numeric sequence value repeated")
                        )
                    elif current < previous_value:
                        issues.append(
                            _issue("SEQUENCE_OUT_OF_ORDER", record.record_id, "sequence_id", "numeric sequence moved backwards")
                        )
                    elif current > previous_value + 1:
                        issues.append(
                            _issue("SEQUENCE_GAP", record.record_id, "sequence_id", "numeric sequence gap detected")
                        )
                previous_value = current

        ordered_issues = tuple(
            sorted(issues, key=lambda item: (item.code, item.record_id, item.field, item.message))
        )
        outcome = IntegrityOutcome.INVALID_CRITICAL if ordered_issues else IntegrityOutcome.VALID
        return IntegrityReport(
            outcome=outcome,
            issues=ordered_issues,
            opaque_sequence_streams=tuple(sorted(opaque_streams)),
            upstream_quality_evidence_sha256=batch.upstream_quality_evidence_sha256,
        )
