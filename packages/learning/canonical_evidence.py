from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIRECTIONS = {"HIGHER_BETTER", "LOWER_BETTER"}
_UNITS = {"BPS", "PPM", "RATIO", "COUNT", "USD", "DECIMAL"}


class CanonicalLearningEvidenceError(ValueError):
    """Authoritative P18 canonical evidence invariant failure."""


def _bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise CanonicalLearningEvidenceError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise CanonicalLearningEvidenceError(f"{field} is a degenerate placeholder identity")
    return parsed


def _decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise CanonicalLearningEvidenceError(f"{field} must be decimal") from exc
    if not parsed.is_finite():
        raise CanonicalLearningEvidenceError(f"{field} must be finite")
    return parsed


@dataclass(frozen=True, slots=True)
class CanonicalArtifact:
    artifact_id: str
    kind: str
    state: str
    provenance_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _sha(self.artifact_id, field="artifact_id"))
        object.__setattr__(
            self,
            "provenance_sha256",
            _sha(self.provenance_sha256, field="provenance_sha256"),
        )
        if not self.kind.strip() or not self.state.strip():
            raise CanonicalLearningEvidenceError("artifact kind/state must be non-empty")


class CanonicalEvidenceStore:
    def __init__(self) -> None:
        self._records: dict[str, CanonicalArtifact] = {}

    def add(self, record: CanonicalArtifact) -> None:
        prior = self._records.get(record.artifact_id)
        if prior is not None and prior != record:
            raise CanonicalLearningEvidenceError("canonical artifact identity conflict")
        self._records[record.artifact_id] = record

    def require(
        self,
        artifact_id: str,
        *,
        kind: str,
        allowed_states: set[str],
    ) -> CanonicalArtifact:
        parsed = _sha(artifact_id, field="required_artifact_id")
        record = self._records.get(parsed)
        if record is None:
            raise CanonicalLearningEvidenceError("canonical artifact not found")
        if record.kind != kind:
            raise CanonicalLearningEvidenceError(
                f"canonical artifact kind mismatch: expected {kind}, got {record.kind}"
            )
        if record.state not in allowed_states:
            raise CanonicalLearningEvidenceError(
                f"canonical artifact state not allowed: {record.state}"
            )
        return record


@dataclass(frozen=True, slots=True)
class CanonicalDemoLineage:
    strategy_record_id: str
    model_record_id: str
    signal_decision_id: str
    risk_decision_id: str
    firewall_decision_id: str

    def __post_init__(self) -> None:
        for field in (
            "strategy_record_id",
            "model_record_id",
            "signal_decision_id",
            "risk_decision_id",
            "firewall_decision_id",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))

    @property
    def lineage_id(self) -> str:
        return hashlib.sha256(
            _bytes(
                {
                    "strategy_record_id": self.strategy_record_id,
                    "model_record_id": self.model_record_id,
                    "signal_decision_id": self.signal_decision_id,
                    "risk_decision_id": self.risk_decision_id,
                    "firewall_decision_id": self.firewall_decision_id,
                }
            )
        ).hexdigest()


def verify_demo_lineage(
    store: CanonicalEvidenceStore,
    lineage: CanonicalDemoLineage,
) -> str:
    store.require(
        lineage.strategy_record_id,
        kind="STRATEGY_RECORD",
        allowed_states={"VALIDATED"},
    )
    store.require(
        lineage.model_record_id,
        kind="MODEL_RECORD",
        allowed_states={"VALIDATED"},
    )
    store.require(
        lineage.signal_decision_id,
        kind="SIGNAL_DECISION",
        allowed_states={"PASS"},
    )
    store.require(
        lineage.risk_decision_id,
        kind="RISK_DECISION",
        allowed_states={"PASS"},
    )
    store.require(
        lineage.firewall_decision_id,
        kind="FIREWALL_DECISION",
        allowed_states={"PASS"},
    )
    return lineage.lineage_id


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    version: str
    unit: str
    direction: str

    def __post_init__(self) -> None:
        if not self.metric_id.strip() or not self.version.strip():
            raise CanonicalLearningEvidenceError("metric id/version must be non-empty")
        if self.unit not in _UNITS:
            raise CanonicalLearningEvidenceError("unsupported metric unit")
        if self.direction not in _DIRECTIONS:
            raise CanonicalLearningEvidenceError("unsupported metric direction")

    def payload(self) -> dict[str, str]:
        return {
            "metric_id": self.metric_id,
            "version": self.version,
            "unit": self.unit,
            "direction": self.direction,
        }


@dataclass(frozen=True, slots=True)
class MetricPolicy:
    definitions: tuple[MetricDefinition, ...]
    primary_metric: str

    def __post_init__(self) -> None:
        if not self.definitions:
            raise CanonicalLearningEvidenceError("metric policy requires definitions")
        ids = [item.metric_id for item in self.definitions]
        if len(ids) != len(set(ids)):
            raise CanonicalLearningEvidenceError("duplicate metric definition")
        if self.primary_metric not in ids:
            raise CanonicalLearningEvidenceError("primary metric is not defined")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _bytes(
                {
                    "definitions": [
                        item.payload()
                        for item in sorted(
                            self.definitions,
                            key=lambda item: item.metric_id,
                        )
                    ],
                    "primary_metric": self.primary_metric,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class CanonicalEvaluation:
    model_record_id: str
    dataset_id: str
    metric_policy_id: str
    metrics: tuple[tuple[str, str], ...]
    evidence_sha256: str

    @classmethod
    def create(
        cls,
        *,
        model_record_id: str,
        dataset_id: str,
        metric_policy: MetricPolicy,
        metrics: Mapping[str, str],
        evidence_sha256: str,
    ) -> "CanonicalEvaluation":
        expected = {item.metric_id for item in metric_policy.definitions}
        actual = set(metrics)
        if actual != expected:
            raise CanonicalLearningEvidenceError("evaluation metric set does not match policy")
        normalized: list[tuple[str, str]] = []
        for key, value in sorted(metrics.items()):
            parsed = _decimal(value, field=f"metrics.{key}")
            text = "0" if parsed == 0 else format(parsed.normalize(), "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            normalized.append((key, text))
        return cls(
            model_record_id=_sha(model_record_id, field="model_record_id"),
            dataset_id=_sha(dataset_id, field="dataset_id"),
            metric_policy_id=metric_policy.policy_id,
            metrics=tuple(normalized),
            evidence_sha256=_sha(evidence_sha256, field="evidence_sha256"),
        )

    @property
    def evaluation_id(self) -> str:
        return hashlib.sha256(
            _bytes(
                {
                    "model_record_id": self.model_record_id,
                    "dataset_id": self.dataset_id,
                    "metric_policy_id": self.metric_policy_id,
                    "metrics": [list(item) for item in self.metrics],
                    "evidence_sha256": self.evidence_sha256,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class RetrainingResourceBudget:
    max_cpu_seconds: int
    max_memory_mb: int
    max_wall_seconds: int
    max_attempts: int

    def __post_init__(self) -> None:
        if min(
            self.max_cpu_seconds,
            self.max_memory_mb,
            self.max_wall_seconds,
            self.max_attempts,
        ) <= 0:
            raise CanonicalLearningEvidenceError("retraining budget values must be positive")

    @property
    def budget_id(self) -> str:
        return hashlib.sha256(
            _bytes(
                {
                    "max_cpu_seconds": self.max_cpu_seconds,
                    "max_memory_mb": self.max_memory_mb,
                    "max_wall_seconds": self.max_wall_seconds,
                    "max_attempts": self.max_attempts,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class RetrainingResourceUsage:
    cpu_seconds: int
    peak_memory_mb: int
    wall_seconds: int
    attempts: int


def enforce_retraining_budget(
    usage: RetrainingResourceUsage,
    budget: RetrainingResourceBudget,
) -> str:
    values = (
        usage.cpu_seconds,
        usage.peak_memory_mb,
        usage.wall_seconds,
        usage.attempts,
    )
    if min(values) < 0:
        raise CanonicalLearningEvidenceError("resource usage cannot be negative")
    if usage.cpu_seconds > budget.max_cpu_seconds:
        raise CanonicalLearningEvidenceError("retraining CPU budget exceeded")
    if usage.peak_memory_mb > budget.max_memory_mb:
        raise CanonicalLearningEvidenceError("retraining memory budget exceeded")
    if usage.wall_seconds > budget.max_wall_seconds:
        raise CanonicalLearningEvidenceError("retraining wall-time budget exceeded")
    if usage.attempts > budget.max_attempts:
        raise CanonicalLearningEvidenceError("retraining attempt budget exceeded")
    return hashlib.sha256(
        _bytes(
            {
                "budget_id": budget.budget_id,
                "usage": {
                    "cpu_seconds": usage.cpu_seconds,
                    "peak_memory_mb": usage.peak_memory_mb,
                    "wall_seconds": usage.wall_seconds,
                    "attempts": usage.attempts,
                },
            }
        )
    ).hexdigest()


def verify_retraining_lineage(
    store: CanonicalEvidenceStore,
    *,
    dataset_id: str,
    experiment_id: str,
    base_model_id: str,
) -> str:
    store.require(dataset_id, kind="DATASET", allowed_states={"READY"})
    store.require(experiment_id, kind="EXPERIMENT", allowed_states={"PASS"})
    store.require(base_model_id, kind="MODEL_RECORD", allowed_states={"VALIDATED"})
    return hashlib.sha256(
        _bytes(
            {
                "dataset_id": dataset_id,
                "experiment_id": experiment_id,
                "base_model_id": base_model_id,
            }
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CanonicalPromotionRequest:
    request_name: str
    target: str
    candidate_validation_id: str
    comparison_id: str
    drift_id: str
    risk_review_id: str
    audit_bundle_id: str

    def __post_init__(self) -> None:
        if not self.request_name.strip():
            raise CanonicalLearningEvidenceError("request_name must be non-empty")
        if self.target not in {"DEMO_CHAMPION", "LIVE"}:
            raise CanonicalLearningEvidenceError("unsupported promotion target")
        for field in (
            "candidate_validation_id",
            "comparison_id",
            "drift_id",
            "risk_review_id",
            "audit_bundle_id",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))

    @property
    def request_id(self) -> str:
        return hashlib.sha256(
            _bytes(
                {
                    "request_name": self.request_name,
                    "target": self.target,
                    "candidate_validation_id": self.candidate_validation_id,
                    "comparison_id": self.comparison_id,
                    "drift_id": self.drift_id,
                    "risk_review_id": self.risk_review_id,
                    "audit_bundle_id": self.audit_bundle_id,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class CanonicalPromotionDecision:
    request_id: str
    status: str
    registry_mutation: bool = False
    promotion_execution_authority: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @property
    def decision_id(self) -> str:
        return hashlib.sha256(
            _bytes(
                {
                    "request_id": self.request_id,
                    "status": self.status,
                    "registry_mutation": self.registry_mutation,
                    "promotion_execution_authority": self.promotion_execution_authority,
                    "automatic_live_promotion": self.automatic_live_promotion,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


def evaluate_canonical_promotion(
    store: CanonicalEvidenceStore,
    request: CanonicalPromotionRequest,
) -> CanonicalPromotionDecision:
    if request.target == "LIVE":
        return CanonicalPromotionDecision(
            request_id=request.request_id,
            status="OWNER_LIVE_GATE_REQUIRED",
        )

    store.require(
        request.candidate_validation_id,
        kind="CANDIDATE_VALIDATION",
        allowed_states={"PASS"},
    )
    store.require(
        request.comparison_id,
        kind="CHALLENGER_COMPARISON",
        allowed_states={"RECOMMENDED"},
    )
    store.require(
        request.drift_id,
        kind="DRIFT_ASSESSMENT",
        allowed_states={"NORMAL", "WARN"},
    )
    store.require(
        request.risk_review_id,
        kind="RISK_REVIEW",
        allowed_states={"PASS"},
    )
    store.require(
        request.audit_bundle_id,
        kind="AUDIT_BUNDLE",
        allowed_states={"COMPLETE"},
    )
    return CanonicalPromotionDecision(
        request_id=request.request_id,
        status="APPROVE_DEMO_CHAMPION_RECORD",
    )
