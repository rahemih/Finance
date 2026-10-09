from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast

from .provenance_confidence import EligibilityStatus, ProvenanceConfidenceResult


class QuarantineRoutingError(ValueError):
    """Quarantine-routing policy, request or stored record is invalid."""


class QuarantineRecordIntegrityError(QuarantineRoutingError):
    """Serialized quarantine record does not match its content identity."""


class RouteDisposition(StrEnum):
    ACCEPTED_DOWNSTREAM = "ACCEPTED_DOWNSTREAM"
    QUARANTINED = "QUARANTINED"
    BLOCKED_UNKNOWN = "BLOCKED_UNKNOWN"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise QuarantineRoutingError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuarantineRoutingError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise QuarantineRoutingError(f"{field} must be a positive integer")
    return value


def _sha256(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise QuarantineRoutingError(f"{field} must be lowercase SHA-256")
    return text


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class QuarantineRoutingPolicy:
    policy_version: str
    max_reason_codes: int
    reason_code_pattern: str
    production_quarantine_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "QuarantineRoutingPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise QuarantineRoutingError(f"invalid quarantine-routing policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise QuarantineRoutingError("unsupported policy schema_version")
        if raw.get("mode") != "P07E_AUTHORITY_FAIL_CLOSED_ROUTING":
            raise QuarantineRoutingError("unsupported routing mode")
        if raw.get("eligible_without_critical_reason") != "ACCEPTED_DOWNSTREAM":
            raise QuarantineRoutingError("ELIGIBLE routing must be ACCEPTED_DOWNSTREAM")
        if raw.get("ineligible_disposition") != "QUARANTINED":
            raise QuarantineRoutingError("INELIGIBLE must route to QUARANTINED")
        if raw.get("unknown_disposition") != "BLOCKED_UNKNOWN":
            raise QuarantineRoutingError("UNKNOWN must route to BLOCKED_UNKNOWN")
        if raw.get("critical_reason_behavior") != "FORCE_QUARANTINED":
            raise QuarantineRoutingError("critical reasons must force quarantine")
        if raw.get("non_accepted_downstream_allowed") is not False:
            raise QuarantineRoutingError("non-accepted routes must deny downstream")
        if raw.get("accepted_quarantine_record") is not False:
            raise QuarantineRoutingError("accepted routes must not create quarantine records")
        if raw.get("non_accepted_quarantine_record") is not True:
            raise QuarantineRoutingError("non-accepted routes must create quarantine records")
        if raw.get("destructive_delete_allowed") is not False:
            raise QuarantineRoutingError("destructive deletion is forbidden")
        if raw.get("silent_bypass_allowed") is not False:
            raise QuarantineRoutingError("silent bypass is forbidden")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise QuarantineRoutingError("reference routing must be offline")

        pattern = _text(raw.get("reason_code_pattern"), field="reason_code_pattern")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise QuarantineRoutingError("invalid reason_code_pattern") from exc

        return cls(
            policy_version=_text(raw.get("policy_version"), field="policy_version"),
            max_reason_codes=_positive_int(raw.get("max_reason_codes"), field="max_reason_codes"),
            reason_code_pattern=pattern,
            production_quarantine_storage_vendor=_text(
                raw.get("production_quarantine_storage_vendor"),
                field="production_quarantine_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    subject_id: str
    disposition: RouteDisposition
    quality_status: EligibilityStatus
    quality_policy_version: str
    quality_evidence_sha256: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.subject_id, field="subject_id")
        _text(self.quality_policy_version, field="quality_policy_version")
        _sha256(self.quality_evidence_sha256, field="quality_evidence_sha256")
        if self.disposition is RouteDisposition.ACCEPTED_DOWNSTREAM:
            raise QuarantineRoutingError("accepted dispositions cannot be quarantine records")
        if not self.reason_codes:
            raise QuarantineRoutingError("quarantine record must preserve at least one reason code")
        if tuple(sorted(set(self.reason_codes))) != self.reason_codes:
            raise QuarantineRoutingError("reason_codes must be sorted and unique")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "subject_id": self.subject_id,
            "disposition": self.disposition.value,
            "quality_status": self.quality_status.value,
            "quality_policy_version": self.quality_policy_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
            "reason_codes": list(self.reason_codes),
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def to_bytes(self) -> bytes:
        payload = self.payload() | {"record_id": self.record_id}
        return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "QuarantineRecord":
        if not data:
            raise QuarantineRecordIntegrityError("quarantine record bytes must be non-empty")
        try:
            raw_value: object = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise QuarantineRecordIntegrityError(f"invalid quarantine record JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise QuarantineRecordIntegrityError("unsupported quarantine record schema_version")
        reasons_raw = raw.get("reason_codes")
        if not isinstance(reasons_raw, list):
            raise QuarantineRecordIntegrityError("reason_codes must be a list")
        try:
            disposition = RouteDisposition(_text(raw.get("disposition"), field="disposition"))
            quality_status = EligibilityStatus(_text(raw.get("quality_status"), field="quality_status"))
        except ValueError as exc:
            raise QuarantineRecordIntegrityError("invalid routing enum value") from exc
        record = cls(
            subject_id=_text(raw.get("subject_id"), field="subject_id"),
            disposition=disposition,
            quality_status=quality_status,
            quality_policy_version=_text(raw.get("quality_policy_version"), field="quality_policy_version"),
            quality_evidence_sha256=_sha256(raw.get("quality_evidence_sha256"), field="quality_evidence_sha256"),
            reason_codes=tuple(_text(item, field="reason_code") for item in cast(list[object], reasons_raw)),
        )
        declared = _sha256(raw.get("record_id"), field="record_id")
        if declared != record.record_id:
            raise QuarantineRecordIntegrityError("quarantine record identity mismatch")
        return record


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    subject_id: str
    disposition: RouteDisposition
    downstream_allowed: bool
    quality_status: EligibilityStatus
    quality_policy_version: str
    quality_evidence_sha256: str
    reason_codes: tuple[str, ...]
    quarantine_record: QuarantineRecord | None

    @property
    def decision_id(self) -> str:
        payload = {
            "schema_version": "1.0",
            "subject_id": self.subject_id,
            "disposition": self.disposition.value,
            "downstream_allowed": self.downstream_allowed,
            "quality_status": self.quality_status.value,
            "quality_policy_version": self.quality_policy_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
            "reason_codes": list(self.reason_codes),
            "quarantine_record_id": (
                self.quarantine_record.record_id if self.quarantine_record is not None else None
            ),
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class QuarantineRouter:
    def __init__(self, policy: QuarantineRoutingPolicy) -> None:
        self._policy = policy
        self._reason_pattern = re.compile(policy.reason_code_pattern)

    def _normalize_reasons(self, reasons: tuple[str, ...]) -> tuple[str, ...]:
        if len(reasons) > self._policy.max_reason_codes:
            raise QuarantineRoutingError("reason code count exceeds policy limit")
        cleaned = tuple(reason.strip() for reason in reasons)
        if any(not reason for reason in cleaned):
            raise QuarantineRoutingError("reason codes must be non-empty")
        if len(cleaned) != len(set(cleaned)):
            raise QuarantineRoutingError("reason codes must be unique")
        for reason in cleaned:
            if self._reason_pattern.fullmatch(reason) is None:
                raise QuarantineRoutingError(f"unsafe reason code: {reason}")
        return tuple(sorted(cleaned))

    def route(
        self,
        *,
        subject_id: str,
        quality: ProvenanceConfidenceResult,
        critical_reason_codes: tuple[str, ...] = (),
    ) -> RoutingDecision:
        subject = _text(subject_id, field="subject_id")
        critical = self._normalize_reasons(critical_reason_codes)
        evidence_id = quality.evidence_identity

        if critical:
            disposition = RouteDisposition.QUARANTINED
            reasons = critical
        elif quality.status is EligibilityStatus.ELIGIBLE:
            disposition = RouteDisposition.ACCEPTED_DOWNSTREAM
            reasons = ()
        elif quality.status is EligibilityStatus.INELIGIBLE:
            disposition = RouteDisposition.QUARANTINED
            reasons = ("QUALITY_INELIGIBLE",)
        else:
            disposition = RouteDisposition.BLOCKED_UNKNOWN
            reasons = ("QUALITY_UNKNOWN",)

        downstream_allowed = disposition is RouteDisposition.ACCEPTED_DOWNSTREAM
        quarantine_record: QuarantineRecord | None = None
        if not downstream_allowed:
            quarantine_record = QuarantineRecord(
                subject_id=subject,
                disposition=disposition,
                quality_status=quality.status,
                quality_policy_version=quality.policy_version,
                quality_evidence_sha256=evidence_id,
                reason_codes=reasons,
            )

        return RoutingDecision(
            subject_id=subject,
            disposition=disposition,
            downstream_allowed=downstream_allowed,
            quality_status=quality.status,
            quality_policy_version=quality.policy_version,
            quality_evidence_sha256=evidence_id,
            reason_codes=reasons,
            quarantine_record=quarantine_record,
        )
