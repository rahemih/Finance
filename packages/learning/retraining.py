from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Mapping, Protocol


class ControlledRetrainingError(ValueError):
    """P18-E deterministic controlled-retraining invariant failure."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe(value: str, *, field: str) -> str:
    parsed=value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise ControlledRetrainingError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed=value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise ControlledRetrainingError(f"{field} must be lowercase SHA-256")
    return parsed


def _num(value: str, *, field: str) -> str:
    try:
        parsed=Decimal(value)
    except InvalidOperation as exc:
        raise ControlledRetrainingError(f"{field} must be decimal") from exc
    if not parsed.is_finite():
        raise ControlledRetrainingError(f"{field} must be finite")
    if parsed == 0:
        return "0"
    text=format(parsed.normalize(),"f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _numeric_map(values: Mapping[str,str], *, field: str) -> tuple[tuple[str,str],...]:
    return tuple((_safe(k,field=f"{field}.key"),_num(v,field=f"{field}.{k}")) for k,v in sorted(values.items()))


@dataclass(frozen=True, slots=True)
class RetrainingRequest:
    dataset_id: str
    experiment_id: str
    base_model_id: str
    code_sha256: str
    trainer_id: str
    trainer_version: str
    seed: int
    parameters: tuple[tuple[str,str],...]

    @classmethod
    def create(cls, *, dataset_id:str, experiment_id:str, base_model_id:str, code_sha256:str,
               trainer_id:str, trainer_version:str, seed:int, parameters:Mapping[str,str]) -> "RetrainingRequest":
        if seed < 0:
            raise ControlledRetrainingError("seed must be non-negative")
        return cls(
            dataset_id=_sha(dataset_id,field="dataset_id"),
            experiment_id=_sha(experiment_id,field="experiment_id"),
            base_model_id=_sha(base_model_id,field="base_model_id"),
            code_sha256=_sha(code_sha256,field="code_sha256"),
            trainer_id=_safe(trainer_id,field="trainer_id"),
            trainer_version=_safe(trainer_version,field="trainer_version"),
            seed=seed,
            parameters=_numeric_map(parameters,field="parameters"),
        )

    def payload(self) -> dict[str,object]:
        return {
            "schema_version":"1.0","dataset_id":self.dataset_id,"experiment_id":self.experiment_id,
            "base_model_id":self.base_model_id,"code_sha256":self.code_sha256,
            "trainer_id":self.trainer_id,"trainer_version":self.trainer_version,"seed":self.seed,
            "parameters":[list(x) for x in self.parameters],
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class TrainerOutput:
    request_id: str
    candidate_model_id: str
    model_artifact_sha256: str
    metrics: tuple[tuple[str,str],...]

    @classmethod
    def create(cls, *, request_id:str, candidate_model_id:str, model_artifact_sha256:str,
               metrics:Mapping[str,str]) -> "TrainerOutput":
        return cls(
            request_id=_sha(request_id,field="request_id"),
            candidate_model_id=_sha(candidate_model_id,field="candidate_model_id"),
            model_artifact_sha256=_sha(model_artifact_sha256,field="model_artifact_sha256"),
            metrics=_numeric_map(metrics,field="metrics"),
        )


class OfflineTrainer(Protocol):
    def train(self, request: RetrainingRequest) -> TrainerOutput: ...
    def checkpoint_sha256(self) -> str: ...


@dataclass(frozen=True, slots=True)
class RetrainingResult:
    request_id: str
    candidate_model_id: str
    model_artifact_sha256: str
    metrics: tuple[tuple[str,str],...]
    trainer_checkpoint_sha256: str
    candidate_only: bool = True
    champion_selection_authority: bool = False
    promotion_authority: bool = False
    automatic_live_promotion: bool = False
    broker_exchange_routing: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str,object]:
        return {
            "schema_version":"1.0","request_id":self.request_id,
            "candidate_model_id":self.candidate_model_id,"model_artifact_sha256":self.model_artifact_sha256,
            "metrics":[list(x) for x in self.metrics],"trainer_checkpoint_sha256":self.trainer_checkpoint_sha256,
            "candidate_only":self.candidate_only,"champion_selection_authority":self.champion_selection_authority,
            "promotion_authority":self.promotion_authority,"automatic_live_promotion":self.automatic_live_promotion,
            "broker_exchange_routing":self.broker_exchange_routing,"live_trading":self.live_trading,"auto_trading":self.auto_trading,
        }

    @property
    def result_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class ControlledRetrainingEngine:
    def __init__(self, trainer: OfflineTrainer) -> None:
        self._trainer=trainer
        self._seen_candidates:set[str]=set()

    def run(self, request: RetrainingRequest) -> RetrainingResult:
        checkpoint=_sha(self._trainer.checkpoint_sha256(),field="trainer_checkpoint_sha256")
        output=self._trainer.train(request)
        if output.request_id != request.request_id:
            raise ControlledRetrainingError("trainer output request lineage mismatch")
        if output.candidate_model_id in self._seen_candidates:
            raise ControlledRetrainingError("duplicate candidate model identity")
        result=RetrainingResult(
            request_id=request.request_id,
            candidate_model_id=output.candidate_model_id,
            model_artifact_sha256=output.model_artifact_sha256,
            metrics=output.metrics,
            trainer_checkpoint_sha256=checkpoint,
        )
        self._seen_candidates.add(output.candidate_model_id)
        return result
