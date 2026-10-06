from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence, cast

from .query_layer import TimeSeriesRecord


class DatasetManifestError(ValueError):
    """Dataset manifest input, policy or integrity state is invalid."""


class DatasetManifestIntegrityError(DatasetManifestError):
    """Dataset manifest bytes do not match their declared content identity."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATASET_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DatasetManifestError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise DatasetManifestError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetManifestError(f"{field} must be a non-empty string")
    return value.strip()


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise DatasetManifestError(f"{field} must be lowercase SHA-256")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DatasetManifestError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    number = _non_negative_int(value, field=field)
    if number <= 0:
        raise DatasetManifestError(f"{field} must be a positive integer")
    return number


def _dataset_name(value: object) -> str:
    text = _text(value, field="dataset_name")
    if _DATASET_NAME.fullmatch(text) is None:
        raise DatasetManifestError("dataset_name contains unsafe characters")
    return text


def _safe_relative_path(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise DatasetManifestError(f"{field} must be a safe relative path")
    return text


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DatasetManifestPolicy:
    max_members_per_manifest: int
    max_manifest_bytes: int
    production_manifest_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "DatasetManifestPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise DatasetManifestError(f"invalid dataset-manifest policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise DatasetManifestError("unsupported dataset-manifest policy schema_version")
        if raw.get("mode") != "REFERENCE_FILESYSTEM_CONTENT_ADDRESSED_MANIFESTS":
            raise DatasetManifestError("unsupported dataset-manifest mode")
        if raw.get("version_algorithm") != "SHA256_CANONICAL_MANIFEST_BODY":
            raise DatasetManifestError("unsupported dataset version algorithm")
        if raw.get("membership_root_algorithm") != "SHA256_SORTED_MEMBER_DIGESTS":
            raise DatasetManifestError("unsupported membership root algorithm")
        if raw.get("window_semantics") != "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE":
            raise DatasetManifestError("unsupported dataset window semantics")
        if raw.get("require_non_empty_dataset") is not True:
            raise DatasetManifestError("reference manifests require non-empty datasets")
        if raw.get("network_required") is not False:
            raise DatasetManifestError("reference manifest store must not require network")
        if raw.get("credentials_required") is not False:
            raise DatasetManifestError("reference manifest store must not require credentials")
        return cls(
            max_members_per_manifest=_positive_int(
                raw.get("max_members_per_manifest"),
                field="max_members_per_manifest",
            ),
            max_manifest_bytes=_positive_int(raw.get("max_manifest_bytes"), field="max_manifest_bytes"),
            production_manifest_storage_vendor=_text(
                raw.get("production_manifest_storage_vendor"),
                field="production_manifest_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class DatasetMember:
    record_id: str
    canonical_id: str
    event_time_ns: int
    record_digest: str
    source_payload_sha256: str
    source_object_relative_path: str

    def __post_init__(self) -> None:
        _text(self.record_id, field="record_id")
        _text(self.canonical_id, field="canonical_id")
        _non_negative_int(self.event_time_ns, field="event_time_ns")
        _sha256_text(self.record_digest, field="record_digest")
        _sha256_text(self.source_payload_sha256, field="source_payload_sha256")
        _safe_relative_path(self.source_object_relative_path, field="source_object_relative_path")

    @classmethod
    def from_record(cls, record: TimeSeriesRecord) -> "DatasetMember":
        record_payload: dict[str, object] = {
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
        return cls(
            record_id=record.record_id,
            canonical_id=record.canonical_id,
            event_time_ns=record.event_time_ns,
            record_digest=hashlib.sha256(_canonical_bytes(record_payload)).hexdigest(),
            source_payload_sha256=record.source_payload_sha256,
            source_object_relative_path=record.source_object_relative_path,
        )

    @classmethod
    def from_mapping(cls, value: object) -> "DatasetMember":
        raw = _mapping(value, field="member")
        return cls(
            record_id=_text(raw.get("record_id"), field="record_id"),
            canonical_id=_text(raw.get("canonical_id"), field="canonical_id"),
            event_time_ns=_non_negative_int(raw.get("event_time_ns"), field="event_time_ns"),
            record_digest=_sha256_text(raw.get("record_digest"), field="record_digest"),
            source_payload_sha256=_sha256_text(
                raw.get("source_payload_sha256"),
                field="source_payload_sha256",
            ),
            source_object_relative_path=_safe_relative_path(
                raw.get("source_object_relative_path"),
                field="source_object_relative_path",
            ),
        )

    def payload(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "canonical_id": self.canonical_id,
            "event_time_ns": self.event_time_ns,
            "record_digest": self.record_digest,
            "source_payload_sha256": self.source_payload_sha256,
            "source_object_relative_path": self.source_object_relative_path,
        }

    @property
    def member_digest(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_name: str
    dataset_schema_version: str
    window_start_ns: int
    window_end_ns: int
    rights_class: str
    query_index_fingerprint: str
    members: tuple[DatasetMember, ...]
    membership_root_sha256: str
    dataset_version: str

    @staticmethod
    def _member_sort_key(member: DatasetMember) -> tuple[int, str, str]:
        return (member.event_time_ns, member.canonical_id, member.record_id)

    @classmethod
    def build(
        cls,
        *,
        dataset_name: str,
        dataset_schema_version: str,
        window_start_ns: int,
        window_end_ns: int,
        rights_class: str,
        query_index_fingerprint: str,
        records: Sequence[TimeSeriesRecord],
        policy: DatasetManifestPolicy,
    ) -> "DatasetManifest":
        safe_name = _dataset_name(dataset_name)
        schema = _text(dataset_schema_version, field="dataset_schema_version")
        start = _non_negative_int(window_start_ns, field="window_start_ns")
        end = _non_negative_int(window_end_ns, field="window_end_ns")
        if end <= start:
            raise DatasetManifestError("window_end_ns must be greater than window_start_ns")
        rights = _text(rights_class, field="rights_class")
        index_fingerprint = _sha256_text(
            query_index_fingerprint,
            field="query_index_fingerprint",
        )
        frozen = tuple(records)
        if not frozen:
            raise DatasetManifestError("dataset manifest requires at least one record")
        if len(frozen) > policy.max_members_per_manifest:
            raise DatasetManifestError("dataset member count exceeds policy")
        ids = [record.record_id for record in frozen]
        if len(ids) != len(set(ids)):
            raise DatasetManifestError("dataset record_id values must be unique")

        members = tuple(sorted((DatasetMember.from_record(record) for record in frozen), key=cls._member_sort_key))
        for member in members:
            if not (start <= member.event_time_ns < end):
                raise DatasetManifestError("dataset member is outside the half-open manifest window")

        root = hashlib.sha256(
            "\n".join(member.member_digest for member in members).encode("ascii")
        ).hexdigest()
        body: dict[str, object] = {
            "schema_version": "1.0",
            "dataset_name": safe_name,
            "dataset_schema_version": schema,
            "window_start_ns": start,
            "window_end_ns": end,
            "rights_class": rights,
            "query_index_fingerprint": index_fingerprint,
            "member_count": len(members),
            "membership_root_sha256": root,
            "members": [member.payload() | {"member_digest": member.member_digest} for member in members],
        }
        version = hashlib.sha256(_canonical_bytes(body)).hexdigest()
        manifest = cls(
            dataset_name=safe_name,
            dataset_schema_version=schema,
            window_start_ns=start,
            window_end_ns=end,
            rights_class=rights,
            query_index_fingerprint=index_fingerprint,
            members=members,
            membership_root_sha256=root,
            dataset_version=version,
        )
        if len(manifest.to_bytes()) > policy.max_manifest_bytes:
            raise DatasetManifestError("serialized dataset manifest exceeds policy")
        return manifest

    def body_payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "dataset_name": self.dataset_name,
            "dataset_schema_version": self.dataset_schema_version,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
            "rights_class": self.rights_class,
            "query_index_fingerprint": self.query_index_fingerprint,
            "member_count": len(self.members),
            "membership_root_sha256": self.membership_root_sha256,
            "members": [
                member.payload() | {"member_digest": member.member_digest}
                for member in self.members
            ],
        }

    def to_bytes(self) -> bytes:
        payload = self.body_payload() | {"dataset_version": self.dataset_version}
        return (
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes, policy: DatasetManifestPolicy) -> "DatasetManifest":
        if not data:
            raise DatasetManifestIntegrityError("dataset manifest bytes must be non-empty")
        if len(data) > policy.max_manifest_bytes:
            raise DatasetManifestIntegrityError("dataset manifest bytes exceed policy")
        try:
            parsed: object = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise DatasetManifestIntegrityError(f"invalid dataset manifest JSON: {exc}") from exc
        raw = _mapping(parsed, field="root")
        if raw.get("schema_version") != "1.0":
            raise DatasetManifestIntegrityError("unsupported dataset manifest schema_version")

        declared_count = _non_negative_int(raw.get("member_count"), field="member_count")
        raw_members = _object_list(raw.get("members"), field="members")
        if declared_count != len(raw_members):
            raise DatasetManifestIntegrityError("dataset member_count mismatch")
        if declared_count == 0:
            raise DatasetManifestIntegrityError("dataset manifest must be non-empty")
        if declared_count > policy.max_members_per_manifest:
            raise DatasetManifestIntegrityError("dataset member count exceeds policy")

        members_list: list[DatasetMember] = []
        for item in raw_members:
            member_raw = _mapping(item, field="member")
            member = DatasetMember.from_mapping(member_raw)
            declared_member_digest = _sha256_text(
                member_raw.get("member_digest"),
                field="member_digest",
            )
            if declared_member_digest != member.member_digest:
                raise DatasetManifestIntegrityError("dataset member digest mismatch")
            members_list.append(member)
        members = tuple(members_list)
        if members != tuple(sorted(members, key=cls._member_sort_key)):
            raise DatasetManifestIntegrityError("dataset members are not in canonical order")
        ids = [member.record_id for member in members]
        if len(ids) != len(set(ids)):
            raise DatasetManifestIntegrityError("dataset record_id values must be unique")

        start = _non_negative_int(raw.get("window_start_ns"), field="window_start_ns")
        end = _non_negative_int(raw.get("window_end_ns"), field="window_end_ns")
        if end <= start:
            raise DatasetManifestIntegrityError("invalid dataset window")
        for member in members:
            if not (start <= member.event_time_ns < end):
                raise DatasetManifestIntegrityError("dataset member outside declared window")

        root = hashlib.sha256(
            "\n".join(member.member_digest for member in members).encode("ascii")
        ).hexdigest()
        declared_root = _sha256_text(
            raw.get("membership_root_sha256"),
            field="membership_root_sha256",
        )
        if root != declared_root:
            raise DatasetManifestIntegrityError("dataset membership root mismatch")

        body: dict[str, object] = {
            "schema_version": "1.0",
            "dataset_name": _dataset_name(raw.get("dataset_name")),
            "dataset_schema_version": _text(
                raw.get("dataset_schema_version"),
                field="dataset_schema_version",
            ),
            "window_start_ns": start,
            "window_end_ns": end,
            "rights_class": _text(raw.get("rights_class"), field="rights_class"),
            "query_index_fingerprint": _sha256_text(
                raw.get("query_index_fingerprint"),
                field="query_index_fingerprint",
            ),
            "member_count": len(members),
            "membership_root_sha256": root,
            "members": [
                member.payload() | {"member_digest": member.member_digest}
                for member in members
            ],
        }
        expected_version = hashlib.sha256(_canonical_bytes(body)).hexdigest()
        declared_version = _sha256_text(raw.get("dataset_version"), field="dataset_version")
        if expected_version != declared_version:
            raise DatasetManifestIntegrityError("dataset version mismatch")

        return cls(
            dataset_name=cast(str, body["dataset_name"]),
            dataset_schema_version=cast(str, body["dataset_schema_version"]),
            window_start_ns=start,
            window_end_ns=end,
            rights_class=cast(str, body["rights_class"]),
            query_index_fingerprint=cast(str, body["query_index_fingerprint"]),
            members=members,
            membership_root_sha256=root,
            dataset_version=expected_version,
        )


@dataclass(frozen=True, slots=True)
class StoredDatasetManifest:
    relative_path: str
    dataset_version: str
    created: bool


class FilesystemDatasetManifestStore:
    """Offline content-addressed manifest store; not a production storage selection."""

    def __init__(self, root: Path, policy: DatasetManifestPolicy) -> None:
        self._root = Path(root)
        self._policy = policy

    def save(self, manifest: DatasetManifest) -> StoredDatasetManifest:
        safe_name = _dataset_name(manifest.dataset_name)
        version = _sha256_text(manifest.dataset_version, field="dataset_version")
        relative = PurePosixPath("manifests") / safe_name / f"{version}.json"
        target = self._root / Path(*relative.parts)
        payload = manifest.to_bytes()
        if len(payload) > self._policy.max_manifest_bytes:
            raise DatasetManifestError("serialized dataset manifest exceeds policy")
        if target.exists():
            if target.read_bytes() != payload:
                raise DatasetManifestIntegrityError("existing content-addressed manifest differs")
            DatasetManifest.from_bytes(payload, self._policy)
            return StoredDatasetManifest(str(relative), version, False)

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        return StoredDatasetManifest(str(relative), version, True)

    def load(self, dataset_name: str, dataset_version: str) -> DatasetManifest:
        safe_name = _dataset_name(dataset_name)
        version = _sha256_text(dataset_version, field="dataset_version")
        relative = PurePosixPath("manifests") / safe_name / f"{version}.json"
        target = self._root / Path(*relative.parts)
        if not target.is_file():
            raise DatasetManifestIntegrityError("dataset manifest does not exist")
        manifest = DatasetManifest.from_bytes(target.read_bytes(), self._policy)
        if manifest.dataset_name != safe_name or manifest.dataset_version != version:
            raise DatasetManifestIntegrityError("stored manifest path identity mismatch")
        return manifest
