from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping, Protocol


class ControlledRetrainingError(ValueError):
    """P18-E governed retraining invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe_id(value: str, *, field: str) -> str:
    parsed = value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise ControlledRetrainingError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise ControlledRetrainingError(f"{field} must be lowercase SHA-256")
    return parsed


def _decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ControlledRetrainingError(f"{field} must be decimal") from exc
    if not parsed.is_finite():
        raise ControlledRetrainingError(f"{field} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _numeric_map(values: Mapping[str, str], *, field: str) -> tuple[tuple[str, str], ...]:
    return tuple(
        (_safe_id(key, field=f"{field}.key"), _decimal_text(_decimal(value, field=f"{field}.{key}")))
        for key, value in sorted(values.items())
    )


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    max_cpu_seconds: int
    max_memory_mb: int
    max_output_bytes: int

    def __post_init__(self) -> None:
        if min(self.max_cpu_seconds, self.max_memory_mb, self.max_output_bytes) <= 0:
            raise ControlledRetrainingError("resource budget values must be positive")

    def payload(self) -> dict[str, int]:
        return {
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_output_bytes": self.max_output_bytes,
        }


@dataclass(frozen=True, slots=True)
class RetrainingRequest:
    request_name: str
    dataset_id: str
    experiment_id: str
    experiment_run_id: str
    base_model_id: str
    base_model_version: str
    strategy_id: str
    strategy_version: str
    code_sha256: str
    seed: int
    budget: ResourceBudget
    minimum_metrics: tuple[tuple[str, str], ...]

    @classmethod
    def create(
        cls,
        *,
        request_name: str,
        dataset_id: str,
        experiment_id: str,
        experiment_run_id: str,
        base_model_id: str,
        base_model_version: str,
        strategy_id: str,
        strategy_version: str,
        code_sha256: str,
        seed: int,
        budget: ResourceBudget,
        minimum_metrics: Mapping[str, str],
    ) -> "RetrainingRequest":
        if seed < 0:
            raise ControlledRetrainingError("seed must be non-negative")
        return cls(
            request_name=_safe_id(request_name, field="request_name"),
            dataset_id=_sha(dataset_id, field="dataset_id"),
            experiment_id=_sha(experiment_id, field="experiment_id"),
            experiment_run_id=_sha(experiment_run_id, field="experiment_run_id"),
            base_model_id=_safe_id(base_model_id, field="base_model_id"),
            base_model_version=_safe_id(base_model_version, field="base_model_version"),
            strategy_id=_safe_id(strategy_id, field="strategy_id"),
            strategy_version=_safe_id(strategy_version, field="strategy_version"),
            code_sha256=_sha(code_sha256, field="code_sha256"),
            seed=seed,
            budget=budget,
            minimum_metrics=_numeric_map(minimum_metrics, field="minimum_metrics"),
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0",
            "request_name":self.request_name,
            "dataset_id":self.dataset_id,
            "experiment_id":self.experiment_id,
            "experiment_run_id":self.experiment_run_id,
            "base_model_id":self.base_model_id,
            "base_model_version":self.base_model_version,
            "strategy_id":self.strategy_id,
            "strategy_version":self.strategy_version,
            "code_sha256":self.code_sha256,
            "seed":self.seed,
            "budget":self.budget.payload(),
            "minimum_metrics":[list(item) for item in self.minimum_metrics],
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class TrainerResult:
    candidate_model_id: str
    artifact_sha256: str
    metrics: tuple[tuple[str, str], ...]
    cpu_seconds: int
    peak_memory_mb: int
    output_bytes: int

    @classmethod
    def create(
        cls,
        *,
        candidate_model_id: str,
        artifact_sha256: str,
        metrics: Mapping[str, str],
        cpu_seconds: int,
        peak_memory_mb: int,
        output_bytes: int,
    ) -> "TrainerResult":
        if min(cpu_seconds, peak_memory_mb, output_bytes) < 0:
            raise ControlledRetrainingError("trainer resource usage must be non-negative")
        return cls(
            candidate_model_id=_safe_id(candidate_model_id, field="candidate_model_id"),
            artifact_sha256=_sha(artifact_sha256, field="artifact_sha256"),
            metrics=_numeric_map(metrics, field="metrics"),
            cpu_seconds=cpu_seconds,
            peak_memory_mb=peak_memory_mb,
            output_bytes=output_bytes,
        )


class OfflineTrainer(Protocol):
    def train(self, request: RetrainingRequest) -> TrainerResult:
        ...


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    request_id: str
    candidate_model_id: str
    artifact_sha256: str
    metrics: tuple[tuple[str, str], ...]
    validation_status: str
    validation_failures: tuple[str, ...]
    candidate_only: bool = True
    promotion_authority: bool = False
    broker_exchange_routing: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @property
    def candidate_record_id(self) -> str:
        payload = {
            "schema_version":"1.0",
            "request_id":self.request_id,
            "candidate_model_id":self.candidate_model_id,
            "artifact_sha256":self.artifact_sha256,
            "metrics":[list(item) for item in self.metrics],
            "validation_status":self.validation_status,
            "validation_failures":list(self.validation_failures),
            "candidate_only":self.candidate_only,
            "promotion_authority":self.promotion_authority,
            "broker_exchange_routing":self.broker_exchange_routing,
            "automatic_live_promotion":self.automatic_live_promotion,
            "live_trading":self.live_trading,
            "auto_trading":self.auto_trading,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class ControlledRetrainer:
    def __init__(self) -> None:
        self._request_names: set[str] = set()
        self._request_ids: set[str] = set()

    def run(self, request: RetrainingRequest, trainer: OfflineTrainer) -> CandidateRecord:
        if request.request_name in self._request_names or request.request_id in self._request_ids:
            raise ControlledRetrainingError("duplicate or conflicting retraining request")
        result = trainer.train(request)
        if result.cpu_seconds > request.budget.max_cpu_seconds:
            raise ControlledRetrainingError("trainer exceeded CPU budget")
        if result.peak_memory_mb > request.budget.max_memory_mb:
            raise ControlledRetrainingError("trainer exceeded memory budget")
        if result.output_bytes > request.budget.max_output_bytes:
            raise ControlledRetrainingError("trainer exceeded output budget")

        metric_map = dict(result.metrics)
        failures: list[str] = []
        for name, minimum in request.minimum_metrics:
            actual = metric_map.get(name)
            if actual is None:
                failures.append(f"MISSING_METRIC:{name}")
                continue
            if _decimal(actual, field=f"metric.{name}") < _decimal(minimum, field=f"minimum.{name}"):
                failures.append(f"BELOW_MINIMUM:{name}")

        self._request_names.add(request.request_name)
        self._request_ids.add(request.request_id)
        return CandidateRecord(
            request_id=request.request_id,
            candidate_model_id=result.candidate_model_id,
            artifact_sha256=result.artifact_sha256,
            metrics=result.metrics,
            validation_status="PASS" if not failures else "FAIL",
            validation_failures=tuple(failures),
        )
