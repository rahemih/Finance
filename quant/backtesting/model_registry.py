from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATES = {"DRAFT", "RESEARCH", "VALIDATED", "RETIRED"}


class ModelRegistryError(ValueError):
    """P17-H model registry invariant failure."""


def _sha(value: str, field: str) -> str:
    v = value.strip().lower()
    if _SHA256.fullmatch(v) is None:
        raise ModelRegistryError(f"{field} must be lowercase SHA-256")
    return v


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ModelVersion:
    model_id: str
    version: str
    lifecycle_state: str
    model_artifact_sha256: str
    code_sha256: str
    config_sha256: str
    feature_schema_sha256: str
    training_dataset_sha256: str
    strategy_record_sha256: str
    walk_forward_certificate_sha256: str | None = None
    robustness_certificate_sha256: str | None = None

    def __post_init__(self) -> None:
        for field in ("model_id", "version"):
            if not str(getattr(self, field)).strip():
                raise ModelRegistryError(f"{field} must be non-empty")
        if self.lifecycle_state not in _STATES:
            raise ModelRegistryError("unsupported lifecycle_state")
        for field in (
            "model_artifact_sha256",
            "code_sha256",
            "config_sha256",
            "feature_schema_sha256",
            "training_dataset_sha256",
            "strategy_record_sha256",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field))
        for field in ("walk_forward_certificate_sha256", "robustness_certificate_sha256"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _sha(value, field))
        if self.lifecycle_state == "VALIDATED":
            if self.walk_forward_certificate_sha256 is None or self.robustness_certificate_sha256 is None:
                raise ModelRegistryError("VALIDATED model requires P17-D/E validation lineage")

    def payload(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "lifecycle_state": self.lifecycle_state,
            "model_artifact_sha256": self.model_artifact_sha256,
            "code_sha256": self.code_sha256,
            "config_sha256": self.config_sha256,
            "feature_schema_sha256": self.feature_schema_sha256,
            "training_dataset_sha256": self.training_dataset_sha256,
            "strategy_record_sha256": self.strategy_record_sha256,
            "walk_forward_certificate_sha256": self.walk_forward_certificate_sha256,
            "robustness_certificate_sha256": self.robustness_certificate_sha256,
        }

    @property
    def record_id(self) -> str:
        return _hash(self.payload())


@dataclass(frozen=True, slots=True)
class ModelRegistry:
    records: tuple[ModelVersion, ...]
    registry_id: str
    automatic_retraining: bool = False
    automatic_promotion: bool = False
    profitability_authority: bool = False
    g9_authority: bool = False
    execution_authority: bool = False


def build_model_registry(records: Iterable[ModelVersion]) -> ModelRegistry:
    by_key: dict[tuple[str, str], ModelVersion] = {}
    for record in records:
        key = (record.model_id, record.version)
        prior = by_key.get(key)
        if prior is not None and prior.record_id != record.record_id:
            raise ModelRegistryError("model version is immutable and cannot diverge")
        by_key[key] = record
    ordered = tuple(sorted(by_key.values(), key=lambda r: (r.model_id, r.version)))
    payload = {
        "schema_version": "1.0",
        "records": [r.payload() for r in ordered],
        "automatic_retraining": False,
        "automatic_promotion": False,
        "profitability_authority": False,
        "g9_authority": False,
        "execution_authority": False,
    }
    return ModelRegistry(records=ordered, registry_id=_hash(payload))
