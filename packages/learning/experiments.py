from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping, Sequence


class ExperimentTrackingError(ValueError):
    """P18-D deterministic experiment tracking invariant failure."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _safe_id(value: str, *, field: str) -> str:
    parsed = value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise ExperimentTrackingError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise ExperimentTrackingError(f"{field} must be lowercase SHA-256")
    return parsed


def _number(value: str, *, field: str) -> str:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ExperimentTrackingError(f"{field} must be decimal") from exc
    if not parsed.is_finite():
        raise ExperimentTrackingError(f"{field} must be finite")
    if parsed == 0:
        return "0"
    text = format(parsed.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _canonical_numeric_map(values: Mapping[str, str], *, field: str) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for key, value in sorted(values.items()):
        out.append((_safe_id(key, field=f"{field}.key"), _number(value, field=f"{field}.{key}")))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_name: str
    hypothesis_id: str
    dataset_id: str
    code_sha256: str
    strategy_id: str
    strategy_version: str
    model_id: str
    model_version: str
    parameters: tuple[tuple[str, str], ...]

    @classmethod
    def create(
        cls,
        *,
        experiment_name: str,
        hypothesis_id: str,
        dataset_id: str,
        code_sha256: str,
        strategy_id: str,
        strategy_version: str,
        model_id: str,
        model_version: str,
        parameters: Mapping[str, str],
    ) -> "ExperimentSpec":
        return cls(
            experiment_name=_safe_id(experiment_name, field="experiment_name"),
            hypothesis_id=_safe_id(hypothesis_id, field="hypothesis_id"),
            dataset_id=_sha(dataset_id, field="dataset_id"),
            code_sha256=_sha(code_sha256, field="code_sha256"),
            strategy_id=_safe_id(strategy_id, field="strategy_id"),
            strategy_version=_safe_id(strategy_version, field="strategy_version"),
            model_id=_safe_id(model_id, field="model_id"),
            model_version=_safe_id(model_version, field="model_version"),
            parameters=_canonical_numeric_map(parameters, field="parameters"),
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "experiment_name": self.experiment_name,
            "hypothesis_id": self.hypothesis_id,
            "dataset_id": self.dataset_id,
            "code_sha256": self.code_sha256,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "parameters": [list(item) for item in self.parameters],
        }

    @property
    def experiment_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ExperimentRun:
    run_name: str
    experiment_id: str
    started_at_ns: int
    completed_at_ns: int
    metrics: tuple[tuple[str, str], ...]
    artifact_sha256: str

    @classmethod
    def create(
        cls,
        *,
        run_name: str,
        experiment_id: str,
        started_at_ns: int,
        completed_at_ns: int,
        metrics: Mapping[str, str],
        artifact_sha256: str,
    ) -> "ExperimentRun":
        if started_at_ns < 0 or completed_at_ns < started_at_ns:
            raise ExperimentTrackingError("invalid experiment run time range")
        return cls(
            run_name=_safe_id(run_name, field="run_name"),
            experiment_id=_sha(experiment_id, field="experiment_id"),
            started_at_ns=started_at_ns,
            completed_at_ns=completed_at_ns,
            metrics=_canonical_numeric_map(metrics, field="metrics"),
            artifact_sha256=_sha(artifact_sha256, field="artifact_sha256"),
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0",
            "run_name":self.run_name,
            "experiment_id":self.experiment_id,
            "started_at_ns":self.started_at_ns,
            "completed_at_ns":self.completed_at_ns,
            "metrics":[list(item) for item in self.metrics],
            "artifact_sha256":self.artifact_sha256,
        }

    @property
    def run_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ExperimentRegistrySnapshot:
    experiment_ids: tuple[str, ...]
    run_ids: tuple[str, ...]
    training_execution_authority: bool = False
    retraining_authority: bool = False
    promotion_authority: bool = False
    broker_exchange_routing: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @property
    def snapshot_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "schema_version":"1.0",
            "experiment_ids":list(self.experiment_ids),
            "run_ids":list(self.run_ids),
            "training_execution_authority":self.training_execution_authority,
            "retraining_authority":self.retraining_authority,
            "promotion_authority":self.promotion_authority,
            "broker_exchange_routing":self.broker_exchange_routing,
            "automatic_live_promotion":self.automatic_live_promotion,
            "live_trading":self.live_trading,
            "auto_trading":self.auto_trading,
        })).hexdigest()


class ExperimentRegistry:
    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentSpec] = {}
        self._experiment_names: dict[str, str] = {}
        self._runs: dict[str, ExperimentRun] = {}
        self._run_names: dict[str, str] = {}

    def register_experiment(self, spec: ExperimentSpec) -> str:
        existing = self._experiment_names.get(spec.experiment_name)
        if existing is not None:
            raise ExperimentTrackingError("duplicate or conflicting experiment name")
        if spec.experiment_id in self._experiments:
            raise ExperimentTrackingError("duplicate experiment identity")
        self._experiments[spec.experiment_id] = spec
        self._experiment_names[spec.experiment_name] = spec.experiment_id
        return spec.experiment_id

    def register_run(self, run: ExperimentRun) -> str:
        if run.experiment_id not in self._experiments:
            raise ExperimentTrackingError("run references unknown experiment")
        if run.run_name in self._run_names:
            raise ExperimentTrackingError("duplicate or conflicting run name")
        if run.run_id in self._runs:
            raise ExperimentTrackingError("duplicate run identity")
        self._runs[run.run_id] = run
        self._run_names[run.run_name] = run.run_id
        return run.run_id

    def snapshot(self) -> ExperimentRegistrySnapshot:
        return ExperimentRegistrySnapshot(
            experiment_ids=tuple(sorted(self._experiments)),
            run_ids=tuple(sorted(self._runs)),
        )
