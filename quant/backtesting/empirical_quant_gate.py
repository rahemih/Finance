from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_WORKSTREAMS = ("P17-A","P17-B","P17-C","P17-D","P17-E","P17-F","P17-G","P17-H")
_REQUIRED_CATEGORIES = ("OOS_EDGE","RISK","ROBUSTNESS","CAPACITY","EXECUTION_REALISM")
_COMPARATORS = {"GE","LE"}
_UNITS = {"BPS","PPM","COUNT","RATIO_PPM"}


class EmpiricalQuantGateError(ValueError):
    """P17 empirical G9 invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise EmpiricalQuantGateError(f"{field} must be lowercase SHA-256")
    # CI placeholders in the original P17 self-tests used repeated single hex chars.
    # Empirical certification rejects degenerate identities so those values cannot
    # accidentally be re-used as real provenance.
    if len(set(parsed)) < 4:
        raise EmpiricalQuantGateError(f"{field} is a degenerate placeholder identity")
    return parsed


@dataclass(frozen=True, slots=True)
class EmpiricalWorkstreamEvidence:
    workstream: str
    evidence_sha256: str
    provenance_sha256: str
    fixture_only: bool = False

    def __post_init__(self) -> None:
        if self.workstream not in _REQUIRED_WORKSTREAMS:
            raise EmpiricalQuantGateError("unsupported P17 empirical workstream evidence")
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha(self.evidence_sha256, field="evidence_sha256"),
        )
        object.__setattr__(
            self,
            "provenance_sha256",
            _sha(self.provenance_sha256, field="provenance_sha256"),
        )
        if self.fixture_only:
            raise EmpiricalQuantGateError("fixture-only evidence cannot certify empirical G9")

    def payload(self) -> dict[str, object]:
        return {
            "workstream": self.workstream,
            "evidence_sha256": self.evidence_sha256,
            "provenance_sha256": self.provenance_sha256,
            "fixture_only": False,
        }


@dataclass(frozen=True, slots=True)
class MetricSchema:
    category: str
    metric_id: str
    version: str
    unit: str
    comparator: str
    threshold_value: int

    def __post_init__(self) -> None:
        if self.category not in _REQUIRED_CATEGORIES:
            raise EmpiricalQuantGateError("unsupported metric category")
        if not self.metric_id.strip() or not self.version.strip():
            raise EmpiricalQuantGateError("metric_id and version must be non-empty")
        if self.unit not in _UNITS:
            raise EmpiricalQuantGateError("unsupported metric unit")
        if self.comparator not in _COMPARATORS:
            raise EmpiricalQuantGateError("unsupported metric comparator")

    def payload(self) -> dict[str, object]:
        return {
            "category": self.category,
            "metric_id": self.metric_id,
            "version": self.version,
            "unit": self.unit,
            "comparator": self.comparator,
            "threshold_value": self.threshold_value,
        }

    @property
    def schema_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class EmpiricalMeasurement:
    category: str
    metric_schema_id: str
    measured_value: int
    evidence_sha256: str
    dataset_sha256: str

    def __post_init__(self) -> None:
        if self.category not in _REQUIRED_CATEGORIES:
            raise EmpiricalQuantGateError("unsupported empirical measurement category")
        object.__setattr__(
            self,
            "metric_schema_id",
            _sha(self.metric_schema_id, field="metric_schema_id"),
        )
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha(self.evidence_sha256, field="measurement.evidence_sha256"),
        )
        object.__setattr__(
            self,
            "dataset_sha256",
            _sha(self.dataset_sha256, field="measurement.dataset_sha256"),
        )

    def payload(self) -> dict[str, object]:
        return {
            "category": self.category,
            "metric_schema_id": self.metric_schema_id,
            "measured_value": self.measured_value,
            "evidence_sha256": self.evidence_sha256,
            "dataset_sha256": self.dataset_sha256,
        }


@dataclass(frozen=True, slots=True)
class EmpiricalQuantGateCertificate:
    gate_name: str
    state: str
    certificate_id: str
    dataset_sha256: str
    threshold_policy_sha256: str
    strategy_registry_id: str
    model_registry_id: str
    workstream_evidence: tuple[EmpiricalWorkstreamEvidence, ...]
    metric_schemas: tuple[MetricSchema, ...]
    measurements: tuple[EmpiricalMeasurement, ...]
    fixture_only: bool = False
    empirical_reference: bool = True
    profitability_guarantee: bool = False
    execution_authority: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


def _passes(schema: MetricSchema, measurement: EmpiricalMeasurement) -> bool:
    if schema.comparator == "GE":
        return measurement.measured_value >= schema.threshold_value
    return measurement.measured_value <= schema.threshold_value


def certify_empirical_g9(
    *,
    dataset_sha256: str,
    threshold_policy_sha256: str,
    strategy_registry_id: str,
    model_registry_id: str,
    workstream_evidence: Iterable[EmpiricalWorkstreamEvidence],
    metric_schemas: Iterable[MetricSchema],
    measurements: Iterable[EmpiricalMeasurement],
) -> EmpiricalQuantGateCertificate:
    dataset_id = _sha(dataset_sha256, field="dataset_sha256")
    policy_id = _sha(threshold_policy_sha256, field="threshold_policy_sha256")
    strategy_id = _sha(strategy_registry_id, field="strategy_registry_id")
    model_id = _sha(model_registry_id, field="model_registry_id")
    if len({dataset_id, policy_id, strategy_id, model_id}) != 4:
        raise EmpiricalQuantGateError("top-level empirical identities must be distinct")

    evidence_by_ws: dict[str, EmpiricalWorkstreamEvidence] = {}
    evidence_hashes: set[str] = set()
    for item in workstream_evidence:
        if item.workstream in evidence_by_ws:
            raise EmpiricalQuantGateError("duplicate empirical workstream evidence")
        if item.evidence_sha256 in evidence_hashes:
            raise EmpiricalQuantGateError("duplicate empirical workstream evidence SHA-256")
        evidence_by_ws[item.workstream] = item
        evidence_hashes.add(item.evidence_sha256)
    if tuple(sorted(evidence_by_ws)) != tuple(sorted(_REQUIRED_WORKSTREAMS)):
        raise EmpiricalQuantGateError("empirical G9 requires exact P17-A..P17-H coverage")

    schemas_by_category: dict[str, MetricSchema] = {}
    for schema in metric_schemas:
        if schema.category in schemas_by_category:
            raise EmpiricalQuantGateError("duplicate empirical metric schema category")
        schemas_by_category[schema.category] = schema
    if tuple(sorted(schemas_by_category)) != tuple(sorted(_REQUIRED_CATEGORIES)):
        raise EmpiricalQuantGateError("empirical G9 requires all governed metric schemas")

    measurement_by_category: dict[str, EmpiricalMeasurement] = {}
    for measurement in measurements:
        if measurement.category in measurement_by_category:
            raise EmpiricalQuantGateError("duplicate empirical measurement category")
        schema = schemas_by_category.get(measurement.category)
        if schema is None:
            raise EmpiricalQuantGateError("measurement has no governed schema")
        if measurement.metric_schema_id != schema.schema_id:
            raise EmpiricalQuantGateError("measurement metric schema identity mismatch")
        if measurement.dataset_sha256 != dataset_id:
            raise EmpiricalQuantGateError("measurement dataset identity mismatch")
        if not _passes(schema, measurement):
            raise EmpiricalQuantGateError(
                f"empirical benchmark criterion failed: {measurement.category}"
            )
        measurement_by_category[measurement.category] = measurement
    if tuple(sorted(measurement_by_category)) != tuple(sorted(_REQUIRED_CATEGORIES)):
        raise EmpiricalQuantGateError("empirical G9 requires all benchmark measurements")

    ordered_ws = tuple(evidence_by_ws[name] for name in _REQUIRED_WORKSTREAMS)
    ordered_schemas = tuple(schemas_by_category[name] for name in _REQUIRED_CATEGORIES)
    ordered_measurements = tuple(
        measurement_by_category[name] for name in _REQUIRED_CATEGORIES
    )
    payload = {
        "schema_version": "1.0",
        "gate_name": "G9_QUANT_VALIDATED",
        "state": "PASS_EMPIRICAL_REFERENCE",
        "dataset_sha256": dataset_id,
        "threshold_policy_sha256": policy_id,
        "strategy_registry_id": strategy_id,
        "model_registry_id": model_id,
        "workstream_evidence": [item.payload() for item in ordered_ws],
        "metric_schemas": [item.payload() for item in ordered_schemas],
        "measurements": [item.payload() for item in ordered_measurements],
        "fixture_only": False,
        "empirical_reference": True,
        "profitability_guarantee": False,
        "execution_authority": False,
        "automatic_live_promotion": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    return EmpiricalQuantGateCertificate(
        gate_name="G9_QUANT_VALIDATED",
        state="PASS_EMPIRICAL_REFERENCE",
        certificate_id=hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        dataset_sha256=dataset_id,
        threshold_policy_sha256=policy_id,
        strategy_registry_id=strategy_id,
        model_registry_id=model_id,
        workstream_evidence=ordered_ws,
        metric_schemas=ordered_schemas,
        measurements=ordered_measurements,
    )
