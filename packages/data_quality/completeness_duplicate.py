from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence, cast

from packages.historical_data import TimeSeriesRecord


class CompletenessDuplicateError(ValueError):
    """Completeness/duplicate policy or batch input is invalid."""


class DuplicateClass(StrEnum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"


class CompletenessDuplicateOutcome(StrEnum):
    VALID = "VALID"
    INVALID_CRITICAL = "INVALID_CRITICAL"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CompletenessDuplicateError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CompletenessDuplicateError(f"{field} must be a positive integer")
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class CompletenessDuplicatePolicy:
    max_records_per_batch: int
    production_data_quality_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "CompletenessDuplicatePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CompletenessDuplicateError(f"invalid completeness/duplicate policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise CompletenessDuplicateError("unsupported policy schema_version")
        if raw.get("mode") != "EXPLICIT_EXPECTATION_FAIL_CLOSED":
            raise CompletenessDuplicateError("unsupported completeness/duplicate mode")
        if raw.get("missing_expected_record_outcome") != "INVALID_CRITICAL":
            raise CompletenessDuplicateError("missing expected records must fail closed")
        if raw.get("exact_duplicate_outcome") != "INVALID_CRITICAL":
            raise CompletenessDuplicateError("exact duplicates must fail closed")
        if raw.get("conflicting_duplicate_outcome") != "INVALID_CRITICAL":
            raise CompletenessDuplicateError("conflicting duplicates must fail closed")
        if raw.get("unexpected_record_behavior") != "REPORT_ONLY":
            raise CompletenessDuplicateError("unexpected-record behavior must be REPORT_ONLY")
        if raw.get("infer_sequence_gaps") is not False:
            raise CompletenessDuplicateError("P07-B must not infer sequence gaps")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise CompletenessDuplicateError("reference completeness/duplicate checks must be offline")
        vendor = raw.get("production_data_quality_vendor")
        if not isinstance(vendor, str) or not vendor.strip():
            raise CompletenessDuplicateError("production_data_quality_vendor must be non-empty")
        return cls(
            max_records_per_batch=_positive_int(raw.get("max_records_per_batch"), field="max_records_per_batch"),
            production_data_quality_vendor=vendor.strip(),
        )


@dataclass(frozen=True, slots=True)
class CompletenessExpectation:
    expected_record_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized = tuple(value.strip() for value in self.expected_record_ids)
        if any(not value for value in normalized):
            raise CompletenessDuplicateError("expected_record_ids must be non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise CompletenessDuplicateError("expected_record_ids must be unique")
        object.__setattr__(self, "expected_record_ids", normalized)


@dataclass(frozen=True, slots=True)
class CompletenessDuplicateBatch:
    records: tuple[TimeSeriesRecord, ...]
    schema_validation_evidence_sha256: str

    def __post_init__(self) -> None:
        if _SHA256.fullmatch(self.schema_validation_evidence_sha256) is None:
            raise CompletenessDuplicateError(
                "schema_validation_evidence_sha256 must be lowercase SHA-256"
            )


@dataclass(frozen=True, slots=True)
class DuplicateFinding:
    key_type: str
    key: str
    classification: DuplicateClass
    occurrence_count: int
    record_ids: tuple[str, ...]
    fingerprints: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "key_type": self.key_type,
            "key": self.key,
            "classification": self.classification.value,
            "occurrence_count": self.occurrence_count,
            "record_ids": list(self.record_ids),
            "fingerprints": list(self.fingerprints),
        }


@dataclass(frozen=True, slots=True)
class CompletenessDuplicateReport:
    outcome: CompletenessDuplicateOutcome
    observed_record_count: int
    expected_record_count: int
    missing_record_ids: tuple[str, ...]
    unexpected_record_ids: tuple[str, ...]
    duplicate_findings: tuple[DuplicateFinding, ...]
    schema_validation_evidence_sha256: str

    @property
    def is_valid(self) -> bool:
        return self.outcome is CompletenessDuplicateOutcome.VALID

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": "1.0",
            "outcome": self.outcome.value,
            "observed_record_count": self.observed_record_count,
            "expected_record_count": self.expected_record_count,
            "missing_record_ids": list(self.missing_record_ids),
            "unexpected_record_ids": list(self.unexpected_record_ids),
            "duplicate_findings": [finding.payload() for finding in self.duplicate_findings],
            "schema_validation_evidence_sha256": self.schema_validation_evidence_sha256,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _record_payload(record: TimeSeriesRecord, *, include_record_id: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "canonical_id": record.canonical_id,
        "kind": record.kind,
        "provider": record.provider,
        "event_time_ns": record.event_time_ns,
        "receive_time_ns": record.receive_time_ns,
        "sequence_id": record.sequence_id,
        "canonical_schema_version": record.canonical_schema_version,
        "canonical_payload_json": record.canonical_payload_json,
        "source_payload_sha256": record.source_payload_sha256,
        "source_object_relative_path": record.source_object_relative_path,
        "provenance": list(record.provenance),
    }
    if include_record_id:
        payload["record_id"] = record.record_id
    return payload


def _fingerprint(record: TimeSeriesRecord, *, include_record_id: bool) -> str:
    return hashlib.sha256(_canonical_bytes(_record_payload(record, include_record_id=include_record_id))).hexdigest()


def _logical_key(record: TimeSeriesRecord) -> str:
    return "|".join(
        (
            record.canonical_id,
            record.provider,
            str(record.event_time_ns),
            record.sequence_id,
        )
    )


class CompletenessDuplicateAnalyzer:
    def __init__(self, policy: CompletenessDuplicatePolicy) -> None:
        self._policy = policy

    def analyze(
        self,
        batch: CompletenessDuplicateBatch,
        expectation: CompletenessExpectation,
    ) -> CompletenessDuplicateReport:
        records = batch.records
        if len(records) > self._policy.max_records_per_batch:
            raise CompletenessDuplicateError("record count exceeds policy max_records_per_batch")

        expected = frozenset(expectation.expected_record_ids)
        observed_ids = frozenset(record.record_id for record in records)
        missing = tuple(sorted(expected - observed_ids))
        unexpected = tuple(sorted(observed_ids - expected))

        findings: list[DuplicateFinding] = []

        by_record_id: dict[str, list[TimeSeriesRecord]] = {}
        for record in records:
            by_record_id.setdefault(record.record_id, []).append(record)
        for record_id, group in sorted(by_record_id.items()):
            if len(group) < 2:
                continue
            fingerprints = tuple(sorted({_fingerprint(item, include_record_id=True) for item in group}))
            classification = (
                DuplicateClass.EXACT_DUPLICATE
                if len(fingerprints) == 1
                else DuplicateClass.CONFLICTING_DUPLICATE
            )
            findings.append(
                DuplicateFinding(
                    key_type="RECORD_ID",
                    key=record_id,
                    classification=classification,
                    occurrence_count=len(group),
                    record_ids=(record_id,),
                    fingerprints=fingerprints,
                )
            )

        by_logical: dict[str, list[TimeSeriesRecord]] = {}
        for record in records:
            by_logical.setdefault(_logical_key(record), []).append(record)
        for key, group in sorted(by_logical.items()):
            record_ids = tuple(sorted({item.record_id for item in group}))
            if len(record_ids) < 2:
                continue
            fingerprints = tuple(sorted({_fingerprint(item, include_record_id=False) for item in group}))
            classification = (
                DuplicateClass.EXACT_DUPLICATE
                if len(fingerprints) == 1
                else DuplicateClass.CONFLICTING_DUPLICATE
            )
            findings.append(
                DuplicateFinding(
                    key_type="LOGICAL_EVENT",
                    key=key,
                    classification=classification,
                    occurrence_count=len(group),
                    record_ids=record_ids,
                    fingerprints=fingerprints,
                )
            )

        ordered_findings = tuple(
            sorted(
                findings,
                key=lambda item: (
                    item.key_type,
                    item.key,
                    item.classification.value,
                    item.record_ids,
                ),
            )
        )
        outcome = (
            CompletenessDuplicateOutcome.INVALID_CRITICAL
            if missing or ordered_findings
            else CompletenessDuplicateOutcome.VALID
        )
        return CompletenessDuplicateReport(
            outcome=outcome,
            observed_record_count=len(records),
            expected_record_count=len(expected),
            missing_record_ids=missing,
            unexpected_record_ids=unexpected,
            duplicate_findings=ordered_findings,
            schema_validation_evidence_sha256=batch.schema_validation_evidence_sha256,
        )
