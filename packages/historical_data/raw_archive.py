from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast


class RawArchiveError(ValueError):
    """Raw archive input or on-disk state is invalid."""


class RawArchiveRightsError(RawArchiveError):
    """Raw retention is not authorized by the supplied rights state."""


class RawArchiveIntegrityError(RawArchiveError):
    """Existing archive evidence is incomplete, conflicting or tampered."""


class RightsState(StrEnum):
    RETENTION_ALLOWED = "RETENTION_ALLOWED"
    RETENTION_ALLOWED_WITH_LIMIT = "RETENTION_ALLOWED_WITH_LIMIT"
    RETENTION_FORBIDDEN = "RETENTION_FORBIDDEN"
    RETENTION_UNVERIFIED = "RETENTION_UNVERIFIED"


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RawArchiveError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RawArchiveError(f"{field} must be a non-empty string")
    return value.strip()


def _string_set(value: object, *, field: str) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise RawArchiveError(f"{field} must be a non-empty array")
    raw_items = cast(list[object], value)
    items: list[str] = []
    for index, item in enumerate(raw_items):
        items.append(_text(item, field=f"{field}[{index}]"))
    return frozenset(items)


def _safe_component(value: str, *, field: str) -> str:
    if _SAFE_COMPONENT.fullmatch(value) is None:
        raise RawArchiveError(f"{field} is not a safe archive path component")
    return value


@dataclass(frozen=True, slots=True)
class RawArchivePolicy:
    allowed_rights_states: frozenset[str]
    denied_rights_states: frozenset[str]
    limited_retention_requires_expiry: bool
    production_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "RawArchivePolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise RawArchiveError(f"invalid raw archive policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise RawArchiveError("unsupported raw archive policy schema_version")
        if raw.get("mode") != "REFERENCE_FILESYSTEM_OFFLINE_ONLY":
            raise RawArchiveError("unsupported raw archive mode")
        if raw.get("digest_algorithm") != "sha256":
            raise RawArchiveError("unsupported digest algorithm")
        if raw.get("network_required") is not False:
            raise RawArchiveError("reference raw archive must not require network")
        if raw.get("credentials_required") is not False:
            raise RawArchiveError("reference raw archive must not require credentials")
        limited = raw.get("limited_retention_requires_expiry")
        if not isinstance(limited, bool):
            raise RawArchiveError("limited_retention_requires_expiry must be boolean")
        return cls(
            allowed_rights_states=_string_set(raw.get("allowed_rights_states"), field="allowed_rights_states"),
            denied_rights_states=_string_set(raw.get("denied_rights_states"), field="denied_rights_states"),
            limited_retention_requires_expiry=limited,
            production_storage_vendor=_text(raw.get("production_storage_vendor"), field="production_storage_vendor"),
        )


@dataclass(frozen=True, slots=True)
class RawEvidence:
    provider: str
    source_stream: str
    captured_at_ns: int
    rights_state: RightsState
    retention_class: str
    media_type: str
    source_event_id: str | None = None
    source_timestamp: str | None = None
    retention_expires_at: str | None = None

    def __post_init__(self) -> None:
        _safe_component(_text(self.provider, field="provider"), field="provider")
        _text(self.source_stream, field="source_stream")
        if isinstance(self.captured_at_ns, bool) or self.captured_at_ns < 0:
            raise RawArchiveError("captured_at_ns must be a non-negative integer")
        _text(self.retention_class, field="retention_class")
        _text(self.media_type, field="media_type")
        if self.source_event_id is not None:
            _text(self.source_event_id, field="source_event_id")
        if self.source_timestamp is not None:
            _text(self.source_timestamp, field="source_timestamp")
        if self.retention_expires_at is not None:
            _text(self.retention_expires_at, field="retention_expires_at")


@dataclass(frozen=True, slots=True)
class ArchivedRawEvidence:
    payload_sha256: str
    payload_size: int
    object_relative_path: str
    metadata_relative_path: str
    created: bool


class FilesystemRawArchive:
    """Offline reference implementation. It is not a production storage selection."""

    def __init__(self, root: Path, policy: RawArchivePolicy) -> None:
        self._root = Path(root)
        self._policy = policy

    def _authorize(self, evidence: RawEvidence) -> None:
        state = evidence.rights_state.value
        if state in self._policy.denied_rights_states:
            raise RawArchiveRightsError(f"raw retention denied for rights_state={state}")
        if state not in self._policy.allowed_rights_states:
            raise RawArchiveRightsError(f"raw retention is not explicitly allowed for rights_state={state}")
        if evidence.rights_state is RightsState.RETENTION_ALLOWED_WITH_LIMIT and self._policy.limited_retention_requires_expiry and evidence.retention_expires_at is None:
            raise RawArchiveRightsError("limited raw retention requires retention_expires_at")

    @staticmethod
    def _metadata(evidence: RawEvidence, *, payload_sha256: str, payload_size: int, object_relative_path: str) -> dict[str, object]:
        return {
            "schema_version":"1.0","kind":"NEXUS_QUANT_RAW_EVIDENCE",
            "provider":evidence.provider,"source_stream":evidence.source_stream,"captured_at_ns":evidence.captured_at_ns,
            "rights_state":evidence.rights_state.value,"retention_class":evidence.retention_class,
            "retention_expires_at":evidence.retention_expires_at,"media_type":evidence.media_type,
            "source_event_id":evidence.source_event_id,"source_timestamp":evidence.source_timestamp,
            "payload_sha256":payload_sha256,"payload_size":payload_size,"object_relative_path":object_relative_path,
        }

    def archive(self, payload: bytes, evidence: RawEvidence) -> ArchivedRawEvidence:
        if not payload:
            raise RawArchiveError("payload must be non-empty bytes")
        self._authorize(evidence)
        digest = hashlib.sha256(payload).hexdigest()
        captured = datetime.fromtimestamp(evidence.captured_at_ns // 1_000_000_000, tz=timezone.utc)
        provider = _safe_component(evidence.provider, field="provider")
        source_hash = hashlib.sha256(evidence.source_stream.encode("utf-8")).hexdigest()[:16]
        relative_dir = Path(provider, f"{captured.year:04d}", f"{captured.month:02d}", f"{captured.day:02d}", source_hash)
        object_relative = (relative_dir / f"{digest}.raw").as_posix()
        metadata_relative = (relative_dir / f"{digest}.metadata.json").as_posix()
        object_path = self._root / object_relative
        metadata_path = self._root / metadata_relative
        metadata = self._metadata(evidence, payload_sha256=digest, payload_size=len(payload), object_relative_path=object_relative)
        metadata_bytes = (json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

        object_exists = object_path.exists()
        metadata_exists = metadata_path.exists()
        if object_exists != metadata_exists:
            raise RawArchiveIntegrityError("raw archive object/metadata pair is incomplete")
        if object_exists and metadata_exists:
            if object_path.read_bytes() != payload:
                raise RawArchiveIntegrityError("existing content-addressed raw object failed integrity check")
            if metadata_path.read_bytes() != metadata_bytes:
                raise RawArchiveIntegrityError("existing raw metadata conflicts with requested evidence")
            return ArchivedRawEvidence(digest, len(payload), object_relative, metadata_relative, False)

        object_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with object_path.open("xb") as handle:
                handle.write(payload)
            with metadata_path.open("xb") as handle:
                handle.write(metadata_bytes)
        except FileExistsError as exc:
            raise RawArchiveIntegrityError("concurrent/conflicting archive creation detected") from exc
        except Exception:
            if metadata_path.exists():
                metadata_path.unlink()
            if object_path.exists():
                object_path.unlink()
            raise
        return ArchivedRawEvidence(digest, len(payload), object_relative, metadata_relative, True)
