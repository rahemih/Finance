from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence, cast


class FeatureMaterializationError(ValueError):
    """Feature definition, lineage, eligibility or materialization is invalid."""


class FeatureArtifactIntegrityError(FeatureMaterializationError):
    """Stored feature artifact does not match its content identity."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_ALLOWED_QUALITY = frozenset({"ELIGIBLE", "INELIGIBLE", "QUARANTINED", "UNKNOWN"})


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise FeatureMaterializationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise FeatureMaterializationError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FeatureMaterializationError(f"{field} must be a non-empty string")
    return value.strip()


def _name(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _NAME.fullmatch(text) is None:
        raise FeatureMaterializationError(f"{field} contains unsafe characters")
    return text


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise FeatureMaterializationError(f"{field} must be lowercase SHA-256")
    return text


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FeatureMaterializationError(f"{field} must be a non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    number = _non_negative_int(value, field=field)
    if number <= 0:
        raise FeatureMaterializationError(f"{field} must be a positive integer")
    return number


def _decimal_text(value: object) -> str:
    text = _text(value, field="value_text")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise FeatureMaterializationError("value_text must be a finite decimal") from exc
    if not number.is_finite():
        raise FeatureMaterializationError("value_text must be a finite decimal")
    return text


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class FeatureMaterializationPolicy:
    max_materializations_per_batch: int
    max_artifact_bytes: int
    production_feature_storage_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "FeatureMaterializationPolicy":
        try:
            raw_value: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise FeatureMaterializationError(f"invalid feature policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise FeatureMaterializationError("unsupported feature policy schema_version")
        if raw.get("mode") != "REFERENCE_FILESYSTEM_CONTENT_ADDRESSED_FEATURES":
            raise FeatureMaterializationError("unsupported feature materialization mode")
        if raw.get("quality_rule") != "MATERIALIZE_ONLY_EXPLICIT_ELIGIBLE":
            raise FeatureMaterializationError("unsupported feature quality rule")
        if raw.get("point_in_time_rule") != "EVENT_AND_SOURCE_CUTOFF_NOT_AFTER_AS_OF":
            raise FeatureMaterializationError("unsupported feature point-in-time rule")
        if raw.get("network_required") is not False:
            raise FeatureMaterializationError("reference feature model must not require network")
        if raw.get("credentials_required") is not False:
            raise FeatureMaterializationError("reference feature model must not require credentials")
        return cls(
            max_materializations_per_batch=_positive_int(
                raw.get("max_materializations_per_batch"),
                field="max_materializations_per_batch",
            ),
            max_artifact_bytes=_positive_int(raw.get("max_artifact_bytes"), field="max_artifact_bytes"),
            production_feature_storage_vendor=_text(
                raw.get("production_feature_storage_vendor"),
                field="production_feature_storage_vendor",
            ),
        )


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    feature_name: str
    definition_version: str
    output_type: str
    code_sha256: str
    config_sha256: str
    description: str

    def __post_init__(self) -> None:
        _name(self.feature_name, field="feature_name")
        _text(self.definition_version, field="definition_version")
        _name(self.output_type, field="output_type")
        _sha256_text(self.code_sha256, field="code_sha256")
        _sha256_text(self.config_sha256, field="config_sha256")
        _text(self.description, field="description")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "feature_name": self.feature_name,
            "definition_version": self.definition_version,
            "output_type": self.output_type,
            "code_sha256": self.code_sha256,
            "config_sha256": self.config_sha256,
            "description": self.description,
        }

    @property
    def definition_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def to_bytes(self) -> bytes:
        payload = self.payload() | {"definition_id": self.definition_id}
        return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "FeatureDefinition":
        if not data:
            raise FeatureArtifactIntegrityError("feature definition bytes must be non-empty")
        try:
            raw_value: object = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise FeatureArtifactIntegrityError(f"invalid feature definition JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise FeatureArtifactIntegrityError("unsupported feature definition schema_version")
        definition = cls(
            feature_name=_name(raw.get("feature_name"), field="feature_name"),
            definition_version=_text(raw.get("definition_version"), field="definition_version"),
            output_type=_name(raw.get("output_type"), field="output_type"),
            code_sha256=_sha256_text(raw.get("code_sha256"), field="code_sha256"),
            config_sha256=_sha256_text(raw.get("config_sha256"), field="config_sha256"),
            description=_text(raw.get("description"), field="description"),
        )
        declared = _sha256_text(raw.get("definition_id"), field="definition_id")
        if declared != definition.definition_id:
            raise FeatureArtifactIntegrityError("feature definition identity mismatch")
        return definition


@dataclass(frozen=True, slots=True)
class QualityEligibility:
    status: str
    quality_policy_version: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_QUALITY:
            raise FeatureMaterializationError("unsupported quality eligibility status")
        _text(self.quality_policy_version, field="quality_policy_version")
        _sha256_text(self.evidence_sha256, field="quality_evidence_sha256")

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "quality_policy_version": self.quality_policy_version,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class FeatureMaterialization:
    definition_id: str
    feature_name: str
    definition_version: str
    code_sha256: str
    config_sha256: str
    entity_id: str
    event_time_ns: int
    as_of_time_ns: int
    value_text: str
    source_dataset_version: str
    source_vintage_ids: tuple[str, ...]
    source_cutoff_ns: int
    quality_status: str
    quality_policy_version: str
    quality_evidence_sha256: str

    def __post_init__(self) -> None:
        _sha256_text(self.definition_id, field="definition_id")
        _name(self.feature_name, field="feature_name")
        _text(self.definition_version, field="definition_version")
        _sha256_text(self.code_sha256, field="code_sha256")
        _sha256_text(self.config_sha256, field="config_sha256")
        _name(self.entity_id, field="entity_id")
        _non_negative_int(self.event_time_ns, field="event_time_ns")
        _non_negative_int(self.as_of_time_ns, field="as_of_time_ns")
        _decimal_text(self.value_text)
        _sha256_text(self.source_dataset_version, field="source_dataset_version")
        for vintage_id in self.source_vintage_ids:
            _sha256_text(vintage_id, field="source_vintage_id")
        if tuple(sorted(set(self.source_vintage_ids))) != self.source_vintage_ids:
            raise FeatureMaterializationError("source_vintage_ids must be sorted and unique")
        _non_negative_int(self.source_cutoff_ns, field="source_cutoff_ns")
        if self.quality_status != "ELIGIBLE":
            raise FeatureMaterializationError("only ELIGIBLE data may be materialized")
        _text(self.quality_policy_version, field="quality_policy_version")
        _sha256_text(self.quality_evidence_sha256, field="quality_evidence_sha256")
        if self.event_time_ns > self.as_of_time_ns:
            raise FeatureMaterializationError("event_time_ns cannot exceed as_of_time_ns")
        if self.source_cutoff_ns > self.as_of_time_ns:
            raise FeatureMaterializationError("source_cutoff_ns cannot exceed as_of_time_ns")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "definition_id": self.definition_id,
            "feature_name": self.feature_name,
            "definition_version": self.definition_version,
            "code_sha256": self.code_sha256,
            "config_sha256": self.config_sha256,
            "entity_id": self.entity_id,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "value_text": self.value_text,
            "source_dataset_version": self.source_dataset_version,
            "source_vintage_ids": list(self.source_vintage_ids),
            "source_cutoff_ns": self.source_cutoff_ns,
            "quality_status": self.quality_status,
            "quality_policy_version": self.quality_policy_version,
            "quality_evidence_sha256": self.quality_evidence_sha256,
        }

    @property
    def materialization_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def to_bytes(self) -> bytes:
        payload = self.payload() | {"materialization_id": self.materialization_id}
        return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "FeatureMaterialization":
        if not data:
            raise FeatureArtifactIntegrityError("feature materialization bytes must be non-empty")
        try:
            raw_value: object = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise FeatureArtifactIntegrityError(f"invalid feature materialization JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise FeatureArtifactIntegrityError("unsupported feature materialization schema_version")
        raw_vintages = _object_list(raw.get("source_vintage_ids"), field="source_vintage_ids")
        vintages = tuple(_sha256_text(item, field="source_vintage_id") for item in raw_vintages)
        materialization = cls(
            definition_id=_sha256_text(raw.get("definition_id"), field="definition_id"),
            feature_name=_name(raw.get("feature_name"), field="feature_name"),
            definition_version=_text(raw.get("definition_version"), field="definition_version"),
            code_sha256=_sha256_text(raw.get("code_sha256"), field="code_sha256"),
            config_sha256=_sha256_text(raw.get("config_sha256"), field="config_sha256"),
            entity_id=_name(raw.get("entity_id"), field="entity_id"),
            event_time_ns=_non_negative_int(raw.get("event_time_ns"), field="event_time_ns"),
            as_of_time_ns=_non_negative_int(raw.get("as_of_time_ns"), field="as_of_time_ns"),
            value_text=_decimal_text(raw.get("value_text")),
            source_dataset_version=_sha256_text(
                raw.get("source_dataset_version"),
                field="source_dataset_version",
            ),
            source_vintage_ids=vintages,
            source_cutoff_ns=_non_negative_int(raw.get("source_cutoff_ns"), field="source_cutoff_ns"),
            quality_status=_text(raw.get("quality_status"), field="quality_status"),
            quality_policy_version=_text(
                raw.get("quality_policy_version"),
                field="quality_policy_version",
            ),
            quality_evidence_sha256=_sha256_text(
                raw.get("quality_evidence_sha256"),
                field="quality_evidence_sha256",
            ),
        )
        declared = _sha256_text(raw.get("materialization_id"), field="materialization_id")
        if declared != materialization.materialization_id:
            raise FeatureArtifactIntegrityError("feature materialization identity mismatch")
        return materialization


class FeatureMaterializer:
    @staticmethod
    def materialize(
        *,
        definition: FeatureDefinition,
        entity_id: str,
        event_time_ns: int,
        as_of_time_ns: int,
        value_text: str,
        source_dataset_version: str,
        source_vintage_ids: Sequence[str],
        source_cutoff_ns: int,
        quality: QualityEligibility,
    ) -> FeatureMaterialization:
        if quality.status != "ELIGIBLE":
            raise FeatureMaterializationError("only ELIGIBLE data may be materialized")
        vintages = tuple(sorted(set(source_vintage_ids)))
        return FeatureMaterialization(
            definition_id=definition.definition_id,
            feature_name=definition.feature_name,
            definition_version=definition.definition_version,
            code_sha256=definition.code_sha256,
            config_sha256=definition.config_sha256,
            entity_id=_name(entity_id, field="entity_id"),
            event_time_ns=_non_negative_int(event_time_ns, field="event_time_ns"),
            as_of_time_ns=_non_negative_int(as_of_time_ns, field="as_of_time_ns"),
            value_text=_decimal_text(value_text),
            source_dataset_version=_sha256_text(
                source_dataset_version,
                field="source_dataset_version",
            ),
            source_vintage_ids=vintages,
            source_cutoff_ns=_non_negative_int(source_cutoff_ns, field="source_cutoff_ns"),
            quality_status=quality.status,
            quality_policy_version=quality.quality_policy_version,
            quality_evidence_sha256=quality.evidence_sha256,
        )


@dataclass(frozen=True, slots=True)
class FeatureBatch:
    materializations: tuple[FeatureMaterialization, ...]
    fingerprint: str

    @classmethod
    def build(
        cls,
        values: Sequence[FeatureMaterialization],
        policy: FeatureMaterializationPolicy,
    ) -> "FeatureBatch":
        frozen = tuple(values)
        if len(frozen) > policy.max_materializations_per_batch:
            raise FeatureMaterializationError("feature batch exceeds policy")
        logical_keys = [
            (
                item.definition_id,
                item.entity_id,
                item.event_time_ns,
                item.as_of_time_ns,
            )
            for item in frozen
        ]
        if len(logical_keys) != len(set(logical_keys)):
            raise FeatureMaterializationError("duplicate logical feature materialization key")
        ordered = tuple(
            sorted(
                frozen,
                key=lambda item: (
                    item.definition_id,
                    item.entity_id,
                    item.event_time_ns,
                    item.as_of_time_ns,
                    item.materialization_id,
                ),
            )
        )
        fingerprint = hashlib.sha256(
            _canonical_bytes([item.materialization_id for item in ordered])
        ).hexdigest()
        return cls(materializations=ordered, fingerprint=fingerprint)


@dataclass(frozen=True, slots=True)
class StoredFeatureArtifact:
    relative_path: str
    content_id: str
    created: bool


class FilesystemFeatureArtifactStore:
    """Offline content-addressed feature artifact store; not a production vendor selection."""

    def __init__(self, root: Path, policy: FeatureMaterializationPolicy) -> None:
        self._root = Path(root)
        self._policy = policy

    def _save(self, *, relative: PurePosixPath, payload: bytes) -> StoredFeatureArtifact:
        if len(payload) > self._policy.max_artifact_bytes:
            raise FeatureMaterializationError("feature artifact exceeds policy")
        target = self._root / Path(*relative.parts)
        if target.exists():
            if target.read_bytes() != payload:
                raise FeatureArtifactIntegrityError("existing content-addressed feature artifact differs")
            return StoredFeatureArtifact(str(relative), target.stem, False)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        return StoredFeatureArtifact(str(relative), target.stem, True)

    def save_definition(self, definition: FeatureDefinition) -> StoredFeatureArtifact:
        relative = PurePosixPath("feature-definitions") / f"{definition.definition_id}.json"
        return self._save(relative=relative, payload=definition.to_bytes())

    def save_materialization(
        self,
        materialization: FeatureMaterialization,
    ) -> StoredFeatureArtifact:
        relative = (
            PurePosixPath("feature-materializations")
            / materialization.definition_id
            / f"{materialization.materialization_id}.json"
        )
        return self._save(relative=relative, payload=materialization.to_bytes())

    def load_definition(self, definition_id: str) -> FeatureDefinition:
        content_id = _sha256_text(definition_id, field="definition_id")
        target = self._root / "feature-definitions" / f"{content_id}.json"
        if not target.is_file():
            raise FeatureArtifactIntegrityError("feature definition artifact does not exist")
        definition = FeatureDefinition.from_bytes(target.read_bytes())
        if definition.definition_id != content_id:
            raise FeatureArtifactIntegrityError("feature definition path identity mismatch")
        return definition

    def load_materialization(
        self,
        definition_id: str,
        materialization_id: str,
    ) -> FeatureMaterialization:
        definition = _sha256_text(definition_id, field="definition_id")
        materialization = _sha256_text(materialization_id, field="materialization_id")
        target = (
            self._root
            / "feature-materializations"
            / definition
            / f"{materialization}.json"
        )
        if not target.is_file():
            raise FeatureArtifactIntegrityError("feature materialization artifact does not exist")
        value = FeatureMaterialization.from_bytes(target.read_bytes())
        if value.definition_id != definition or value.materialization_id != materialization:
            raise FeatureArtifactIntegrityError("feature materialization path identity mismatch")
        return value
