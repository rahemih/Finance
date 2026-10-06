from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .raw_archive import (
    ArchivedRawEvidence,
    FilesystemRawArchive,
    RawArchiveError,
    RawEvidence,
    RightsState,
)


class HistoricalBackfillError(RawArchiveError):
    """Historical backfill request, page sequence or policy is invalid."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise HistoricalBackfillError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalBackfillError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise HistoricalBackfillError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class BackfillPolicy:
    max_pages_per_run: int
    max_total_bytes_per_run: int
    require_contiguous_ordinals: bool
    production_historical_provider_entitlement: str
    production_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "BackfillPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise HistoricalBackfillError(f"invalid backfill policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise HistoricalBackfillError("unsupported backfill policy schema_version")
        if raw.get("mode") != "REFERENCE_OFFLINE_PAGED_PAYLOADS_ONLY":
            raise HistoricalBackfillError("unsupported backfill mode")
        if raw.get("window_semantics") != "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE":
            raise HistoricalBackfillError("unsupported historical window semantics")
        contiguous = raw.get("require_contiguous_ordinals")
        if contiguous is not True:
            raise HistoricalBackfillError("reference backfill requires contiguous ordinals")
        if raw.get("archive_exact_provider_payload_bytes") is not True:
            raise HistoricalBackfillError("reference backfill must preserve exact provider payload bytes")
        if raw.get("network_required") is not False:
            raise HistoricalBackfillError("reference backfill must not require network")
        if raw.get("credentials_required") is not False:
            raise HistoricalBackfillError("reference backfill must not require credentials")
        return cls(
            max_pages_per_run=_positive_int(raw.get("max_pages_per_run"), field="max_pages_per_run"),
            max_total_bytes_per_run=_positive_int(raw.get("max_total_bytes_per_run"), field="max_total_bytes_per_run"),
            require_contiguous_ordinals=True,
            production_historical_provider_entitlement=_text(
                raw.get("production_historical_provider_entitlement"),
                field="production_historical_provider_entitlement",
            ),
            production_storage_vendor=_text(raw.get("production_storage_vendor"), field="production_storage_vendor"),
        )


@dataclass(frozen=True, slots=True)
class BackfillRequest:
    provider: str
    source_stream: str
    window_start_ns: int
    window_end_ns: int
    rights_state: RightsState
    retention_class: str
    media_type: str
    retention_expires_at: str | None = None

    def __post_init__(self) -> None:
        _text(self.provider, field="provider")
        _text(self.source_stream, field="source_stream")
        if isinstance(self.window_start_ns, bool) or self.window_start_ns < 0:
            raise HistoricalBackfillError("window_start_ns must be a non-negative integer")
        if isinstance(self.window_end_ns, bool) or self.window_end_ns <= self.window_start_ns:
            raise HistoricalBackfillError("window_end_ns must be greater than window_start_ns")
        _text(self.retention_class, field="retention_class")
        _text(self.media_type, field="media_type")
        if self.retention_expires_at is not None:
            _text(self.retention_expires_at, field="retention_expires_at")


@dataclass(frozen=True, slots=True)
class BackfillPage:
    ordinal: int
    payload: bytes
    captured_at_ns: int
    source_event_id: str | None = None
    source_timestamp: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or self.ordinal < 0:
            raise HistoricalBackfillError("ordinal must be a non-negative integer")
        if not self.payload:
            raise HistoricalBackfillError("historical page payload must be non-empty")
        if isinstance(self.captured_at_ns, bool) or self.captured_at_ns < 0:
            raise HistoricalBackfillError("captured_at_ns must be a non-negative integer")
        if self.source_event_id is not None:
            _text(self.source_event_id, field="source_event_id")
        if self.source_timestamp is not None:
            _text(self.source_timestamp, field="source_timestamp")


@dataclass(frozen=True, slots=True)
class BackfilledPage:
    ordinal: int
    payload_sha256: str
    payload_size: int
    object_relative_path: str
    metadata_relative_path: str
    created: bool


@dataclass(frozen=True, slots=True)
class BackfillRunResult:
    request_fingerprint: str
    page_count: int
    total_bytes: int
    created_pages: int
    idempotent_pages: int
    pages: tuple[BackfilledPage, ...]


class HistoricalBackfillRunner:
    """Offline reference backfill runner. It does not acquire provider data."""

    def __init__(self, archive: FilesystemRawArchive, policy: BackfillPolicy) -> None:
        self._archive = archive
        self._policy = policy

    def _validate_pages(self, pages: Sequence[BackfillPage]) -> tuple[BackfillPage, ...]:
        frozen = tuple(pages)
        if not frozen:
            raise HistoricalBackfillError("historical backfill requires at least one page")
        if len(frozen) > self._policy.max_pages_per_run:
            raise HistoricalBackfillError("historical backfill page count exceeds policy")
        total_bytes = sum(len(page.payload) for page in frozen)
        if total_bytes > self._policy.max_total_bytes_per_run:
            raise HistoricalBackfillError("historical backfill byte count exceeds policy")
        ordinals = [page.ordinal for page in frozen]
        if self._policy.require_contiguous_ordinals and ordinals != list(range(len(frozen))):
            raise HistoricalBackfillError("historical backfill page ordinals must be contiguous from zero")
        return frozen

    @staticmethod
    def _fingerprint(request: BackfillRequest, pages: Sequence[BackfillPage]) -> str:
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "provider": request.provider,
            "source_stream": request.source_stream,
            "window_start_ns": request.window_start_ns,
            "window_end_ns": request.window_end_ns,
            "rights_state": request.rights_state.value,
            "retention_class": request.retention_class,
            "retention_expires_at": request.retention_expires_at,
            "media_type": request.media_type,
            "pages": [
                {
                    "ordinal": page.ordinal,
                    "payload_sha256": hashlib.sha256(page.payload).hexdigest(),
                    "payload_size": len(page.payload),
                    "captured_at_ns": page.captured_at_ns,
                    "source_event_id": page.source_event_id,
                    "source_timestamp": page.source_timestamp,
                }
                for page in pages
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def run(self, request: BackfillRequest, pages: Sequence[BackfillPage]) -> BackfillRunResult:
        frozen = self._validate_pages(pages)
        fingerprint = self._fingerprint(request, frozen)
        archived: list[BackfilledPage] = []
        for page in frozen:
            evidence = RawEvidence(
                provider=request.provider,
                source_stream=request.source_stream,
                captured_at_ns=page.captured_at_ns,
                rights_state=request.rights_state,
                retention_class=request.retention_class,
                media_type=request.media_type,
                source_event_id=page.source_event_id,
                source_timestamp=page.source_timestamp,
                retention_expires_at=request.retention_expires_at,
            )
            raw: ArchivedRawEvidence = self._archive.archive(page.payload, evidence)
            archived.append(
                BackfilledPage(
                    ordinal=page.ordinal,
                    payload_sha256=raw.payload_sha256,
                    payload_size=raw.payload_size,
                    object_relative_path=raw.object_relative_path,
                    metadata_relative_path=raw.metadata_relative_path,
                    created=raw.created,
                )
            )
        total_bytes = sum(page.payload_size for page in archived)
        created_pages = sum(1 for page in archived if page.created)
        return BackfillRunResult(
            request_fingerprint=fingerprint,
            page_count=len(archived),
            total_bytes=total_bytes,
            created_pages=created_pages,
            idempotent_pages=len(archived) - created_pages,
            pages=tuple(archived),
        )
