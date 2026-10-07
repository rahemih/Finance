from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, cast

from packages.contracts.market_data import (
    ContextTopOfBookPayload,
    MarketEventKind,
    OrderBookPayload,
    QuotePayload,
    TradePayload,
)
from packages.historical_data import (
    FeatureArtifactIntegrityError,
    FeatureMaterialization,
    FeatureMaterializationError,
    ReplaySnapshot,
    ReplaySnapshotError,
    ReplaySnapshotIntegrityError,
    ReplaySnapshotPolicy,
    TimeSeriesRecord,
)
from packages.market_data.normalization import CanonicalMarketEvent


class SchemaValidationError(ValueError):
    """Schema-validation policy or invocation is invalid."""


class ValidationOutcome(StrEnum):
    VALID = "VALID"
    INVALID_CRITICAL = "INVALID_CRITICAL"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _string_set(value: object, *, field: str) -> frozenset[str]:
    if not isinstance(value, list):
        raise SchemaValidationError(f"{field} must be a list")
    raw = cast(list[object], value)
    result: set[str] = set()
    for item in raw:
        result.add(_text(item, field=field))
    if not result:
        raise SchemaValidationError(f"{field} must not be empty")
    return frozenset(result)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class SchemaValidationPolicy:
    supported_historical_schema_versions: frozenset[str]
    allowed_historical_kinds: frozenset[str]
    require_historical_payload_object: bool
    require_market_provenance_consistency: bool
    production_data_quality_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "SchemaValidationPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise SchemaValidationError(f"invalid schema-validation policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise SchemaValidationError("unsupported schema-validation policy version")
        if raw.get("mode") != "DETERMINISTIC_FAIL_CLOSED_SCHEMA_VALIDATION":
            raise SchemaValidationError("unsupported schema-validation mode")
        if raw.get("critical_schema_violation_outcome") != "INVALID_CRITICAL":
            raise SchemaValidationError("critical violations must fail closed")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise SchemaValidationError("reference schema validation must be offline")
        return cls(
            supported_historical_schema_versions=_string_set(
                raw.get("supported_historical_schema_versions"),
                field="supported_historical_schema_versions",
            ),
            allowed_historical_kinds=_string_set(
                raw.get("allowed_historical_kinds"),
                field="allowed_historical_kinds",
            ),
            require_historical_payload_object=raw.get("require_historical_payload_object") is True,
            require_market_provenance_consistency=raw.get("require_market_provenance_consistency") is True,
            production_data_quality_vendor=_text(
                raw.get("production_data_quality_vendor"),
                field="production_data_quality_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class SchemaIssue:
    code: str
    field: str
    message: str
    critical: bool = True

    def payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "critical": self.critical,
        }


@dataclass(frozen=True, slots=True)
class SchemaValidationReport:
    contract: str
    identity: str
    outcome: ValidationOutcome
    issues: tuple[SchemaIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.outcome is ValidationOutcome.VALID

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": "1.0",
            "contract": self.contract,
            "identity": self.identity,
            "outcome": self.outcome.value,
            "issues": [issue.payload() for issue in self.issues],
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _report(contract: str, identity: str, issues: list[SchemaIssue]) -> SchemaValidationReport:
    ordered = tuple(sorted(issues, key=lambda item: (item.code, item.field, item.message)))
    outcome = ValidationOutcome.INVALID_CRITICAL if any(item.critical for item in ordered) else ValidationOutcome.VALID
    return SchemaValidationReport(contract=contract, identity=identity, outcome=outcome, issues=ordered)


def _issue(code: str, field: str, message: str) -> SchemaIssue:
    return SchemaIssue(code=code, field=field, message=message, critical=True)


def _safe_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and "." not in path.parts


class SchemaValidator:
    def __init__(self, policy: SchemaValidationPolicy) -> None:
        self._policy = policy

    def validate_market_event(self, event: CanonicalMarketEvent) -> SchemaValidationReport:
        issues: list[SchemaIssue] = []
        for field, value in (
            ("canonical_id", event.canonical_id),
            ("asset_class", event.asset_class),
            ("provider", event.provider),
            ("provider_exchange", event.provider_exchange),
            ("provider_instrument_class", event.provider_instrument_class),
            ("provider_symbol", event.provider_symbol),
            ("sequence_id", event.sequence_id),
        ):
            if not isinstance(value, str) or not value.strip():
                issues.append(_issue("REQUIRED_TEXT", field, f"{field} must be non-empty"))

        if isinstance(event.clock.local_receive_time_ns, bool) or event.clock.local_receive_time_ns < 0:
            issues.append(_issue("INVALID_TIME", "clock.local_receive_time_ns", "local receive time must be non-negative"))

        expected_payload = {
            MarketEventKind.TRADE: TradePayload,
            MarketEventKind.ORDER_BOOK: OrderBookPayload,
            MarketEventKind.QUOTE: QuotePayload,
            MarketEventKind.CONTEXT_TOP_OF_BOOK: ContextTopOfBookPayload,
        }[event.kind]
        if not isinstance(event.payload, expected_payload):
            issues.append(
                _issue(
                    "KIND_PAYLOAD_MISMATCH",
                    "payload",
                    f"{event.kind.value} requires {expected_payload.__name__}",
                )
            )

        provenance = dict(event.provenance)
        if len(provenance) != len(event.provenance):
            issues.append(_issue("DUPLICATE_PROVENANCE_KEY", "provenance", "provenance keys must be unique"))
        if self._policy.require_market_provenance_consistency:
            required = {
                "canonical_id": event.canonical_id,
                "provider": event.provider,
                "provider_exchange": event.provider_exchange,
                "provider_instrument_class": event.provider_instrument_class,
                "provider_symbol": event.provider_symbol,
            }
            for key, expected in required.items():
                if provenance.get(key) != expected:
                    issues.append(
                        _issue(
                            "PROVENANCE_MISMATCH",
                            f"provenance.{key}",
                            f"provenance {key} must match canonical event",
                        )
                    )

        identity = f"{event.canonical_id}:{event.provider}:{event.sequence_id}"
        return _report("CanonicalMarketEvent", identity, issues)

    def validate_time_series_record(self, record: TimeSeriesRecord) -> SchemaValidationReport:
        issues: list[SchemaIssue] = []
        for field, value in (
            ("record_id", record.record_id),
            ("canonical_id", record.canonical_id),
            ("provider", record.provider),
            ("sequence_id", record.sequence_id),
        ):
            if not isinstance(value, str) or not value.strip():
                issues.append(_issue("REQUIRED_TEXT", field, f"{field} must be non-empty"))

        if record.canonical_schema_version not in self._policy.supported_historical_schema_versions:
            issues.append(
                _issue(
                    "UNSUPPORTED_SCHEMA_VERSION",
                    "canonical_schema_version",
                    "historical canonical schema version is not supported",
                )
            )
        if record.kind not in self._policy.allowed_historical_kinds:
            issues.append(_issue("UNSUPPORTED_KIND", "kind", "historical event kind is not supported"))
        if _SHA256.fullmatch(record.source_payload_sha256) is None:
            issues.append(_issue("INVALID_SHA256", "source_payload_sha256", "source digest must be lowercase SHA-256"))
        if not _safe_path(record.source_object_relative_path):
            issues.append(_issue("UNSAFE_SOURCE_PATH", "source_object_relative_path", "source object path must be safe and relative"))

        try:
            payload: object = json.loads(record.canonical_payload_json)
        except Exception:
            payload = None
            issues.append(_issue("INVALID_JSON", "canonical_payload_json", "canonical payload must be valid JSON"))
        if (
            self._policy.require_historical_payload_object
            and payload is not None
            and not isinstance(payload, Mapping)
        ):
            issues.append(_issue("PAYLOAD_NOT_OBJECT", "canonical_payload_json", "canonical payload JSON must be an object"))

        return _report("TimeSeriesRecord", record.record_id, issues)

    def validate_feature_materialization(
        self,
        materialization: FeatureMaterialization,
    ) -> SchemaValidationReport:
        return self.validate_feature_bytes(
            materialization.to_bytes(),
            expected_identity=materialization.materialization_id,
        )

    def validate_feature_bytes(
        self,
        data: bytes,
        *,
        expected_identity: str | None = None,
    ) -> SchemaValidationReport:
        issues: list[SchemaIssue] = []
        identity = expected_identity or hashlib.sha256(data).hexdigest()
        try:
            restored = FeatureMaterialization.from_bytes(data)
            identity = restored.materialization_id
            if expected_identity is not None and restored.materialization_id != expected_identity:
                issues.append(_issue("IDENTITY_MISMATCH", "materialization_id", "feature materialization identity changed"))
        except (FeatureArtifactIntegrityError, FeatureMaterializationError) as exc:
            issues.append(_issue("INTEGRITY_FAILURE", "materialization", str(exc)))
        return _report("FeatureMaterialization", identity, issues)

    def validate_replay_snapshot(
        self,
        snapshot: ReplaySnapshot,
        replay_policy: ReplaySnapshotPolicy,
    ) -> SchemaValidationReport:
        return self.validate_replay_bytes(
            snapshot.to_bytes(),
            replay_policy,
            expected_identity=snapshot.snapshot_id,
        )

    def validate_replay_bytes(
        self,
        data: bytes,
        replay_policy: ReplaySnapshotPolicy,
        *,
        expected_identity: str | None = None,
    ) -> SchemaValidationReport:
        issues: list[SchemaIssue] = []
        identity = expected_identity or hashlib.sha256(data).hexdigest()
        try:
            restored = ReplaySnapshot.from_bytes(data, replay_policy)
            identity = restored.snapshot_id
            if expected_identity is not None and restored.snapshot_id != expected_identity:
                issues.append(_issue("IDENTITY_MISMATCH", "snapshot_id", "replay snapshot identity changed"))
        except (ReplaySnapshotIntegrityError, ReplaySnapshotError) as exc:
            issues.append(_issue("INTEGRITY_FAILURE", "snapshot", str(exc)))
        return _report("ReplaySnapshot", identity, issues)
