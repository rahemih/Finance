from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .weighted_fusion import WeightedFusionResult


class ProbabilityCalibrationError(ValueError):
    """P14-C empirical calibration invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProbabilityCalibrationError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ProbabilityCalibrationError(f"{field} must be list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProbabilityCalibrationError(f"{field} must be non-empty text")
    return value.strip()


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProbabilityCalibrationError(f"{field} must be integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed < 0:
        raise ProbabilityCalibrationError(f"{field} must be non-negative")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed <= 0:
        raise ProbabilityCalibrationError(f"{field} must be positive")
    return parsed


def _sha256_text(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise ProbabilityCalibrationError(f"{field} must be lowercase SHA-256 hex")
    return parsed


@dataclass(frozen=True, slots=True)
class ProbabilityCalibrationPolicy:
    absolute_score_bin_edges_bps: tuple[int, ...]
    minimum_calibration_samples: int
    probability_scale_bps: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ProbabilityCalibrationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "EMPIRICAL_DIRECTIONAL_SUCCESS_CALIBRATION":
            raise ProbabilityCalibrationError("unsupported P14-C policy")
        edges = tuple(_integer(item, field="absolute_score_bin_edge_bps") for item in _object_list(raw.get("absolute_score_bin_edges_bps"), field="absolute_score_bin_edges_bps"))
        if len(edges) < 2 or edges[0] != 0 or tuple(sorted(set(edges))) != edges or edges[-1] <= 10_000:
            raise ProbabilityCalibrationError("score bin edges must be strictly increasing and cover 0..10000 bps")
        if raw.get("probability_estimator") != "RAW_EMPIRICAL_FREQUENCY":
            raise ProbabilityCalibrationError("P14-C estimator must be raw empirical frequency")
        forbidden = (
            "synthetic_prior_enabled",
            "smoothing_enabled",
            "llm_probability_authority",
            "confidence_interval_in_scope",
            "regime_similarity_uncertainty_in_scope",
            "tp_stop_probability_in_scope",
            "risk_approval_in_scope",
            "position_sizing_in_scope",
            "execution_authority_in_scope",
            "canonical_tests_network_required",
        )
        if any(raw.get(field) is not False for field in forbidden):
            raise ProbabilityCalibrationError("P14-C cannot enable priors, LLM probability, uncertainty, TP/Stop, risk or execution")
        if raw.get("training_outcome_cutoff_behavior") != "FAIL_CLOSED":
            raise ProbabilityCalibrationError("training cutoff must fail closed")
        if raw.get("prediction_cutoff_behavior") != "STRICTLY_AFTER_TRAINING_CUTOFF":
            raise ProbabilityCalibrationError("prediction cutoff must be strictly after training cutoff")
        if raw.get("context_mixing_behavior") != "FAIL_CLOSED":
            raise ProbabilityCalibrationError("calibration context mixing must fail closed")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise ProbabilityCalibrationError("P14-C cannot enable trading")
        scale = _positive_int(raw.get("probability_scale_bps"), field="probability_scale_bps")
        if scale != 10_000:
            raise ProbabilityCalibrationError("probability scale must be 10000 bps")
        return cls(
            absolute_score_bin_edges_bps=edges,
            minimum_calibration_samples=_positive_int(raw.get("minimum_calibration_samples"), field="minimum_calibration_samples"),
            probability_scale_bps=scale,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class CalibrationContext:
    subject_id: str
    strategy_id: str
    timeframe: str
    regime_label: str
    session_label: str
    outcome_definition_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _text(self.subject_id, field="subject_id"))
        object.__setattr__(self, "strategy_id", _text(self.strategy_id, field="strategy_id"))
        object.__setattr__(self, "timeframe", _text(self.timeframe, field="timeframe"))
        object.__setattr__(self, "regime_label", _text(self.regime_label, field="regime_label"))
        object.__setattr__(self, "session_label", _text(self.session_label, field="session_label"))
        object.__setattr__(self, "outcome_definition_sha256", _sha256_text(self.outcome_definition_sha256, field="outcome_definition_sha256"))

    def payload(self) -> dict[str, str]:
        return {
            "subject_id": self.subject_id,
            "strategy_id": self.strategy_id,
            "timeframe": self.timeframe,
            "regime_label": self.regime_label,
            "session_label": self.session_label,
            "outcome_definition_sha256": self.outcome_definition_sha256,
        }


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    context: CalibrationContext
    signed_score_bps: int
    direction: int
    success: bool
    decision_as_of_ns: int
    outcome_observed_ns: int
    source_dataset_version_sha256: str
    provenance_sha256: str

    def __post_init__(self) -> None:
        score = _integer(self.signed_score_bps, field="signed_score_bps")
        if score == 0 or abs(score) > 10_000:
            raise ProbabilityCalibrationError("signed_score_bps must be non-zero and within -10000..10000")
        if self.direction not in (-1, 1):
            raise ProbabilityCalibrationError("calibration direction must be -1 or 1")
        if (score > 0) != (self.direction > 0):
            raise ProbabilityCalibrationError("signed score direction mismatch")
        decision = _non_negative_int(self.decision_as_of_ns, field="decision_as_of_ns")
        observed = _non_negative_int(self.outcome_observed_ns, field="outcome_observed_ns")
        if observed < decision:
            raise ProbabilityCalibrationError("outcome cannot be observed before decision")
        object.__setattr__(self, "source_dataset_version_sha256", _sha256_text(self.source_dataset_version_sha256, field="source_dataset_version_sha256"))
        object.__setattr__(self, "provenance_sha256", _sha256_text(self.provenance_sha256, field="provenance_sha256"))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "context": self.context.payload(),
            "signed_score_bps": self.signed_score_bps,
            "direction": self.direction,
            "success": self.success,
            "decision_as_of_ns": self.decision_as_of_ns,
            "outcome_observed_ns": self.outcome_observed_ns,
            "source_dataset_version_sha256": self.source_dataset_version_sha256,
            "provenance_sha256": self.provenance_sha256,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class CalibrationCell:
    lower_abs_score_bps: int
    upper_abs_score_exclusive_bps: int
    sample_count: int
    success_count: int

    @property
    def probability_bps(self) -> int:
        if self.sample_count <= 0:
            raise ProbabilityCalibrationError("empty calibration cell has no probability")
        return (self.success_count * 10_000 + self.sample_count // 2) // self.sample_count


@dataclass(frozen=True, slots=True)
class CalibrationModel:
    context: CalibrationContext
    training_cutoff_ns: int
    calibration_dataset_version_sha256: str
    cells: tuple[CalibrationCell, ...]
    observation_ids: tuple[str, ...]
    minimum_calibration_samples: int

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "context": self.context.payload(),
            "training_cutoff_ns": self.training_cutoff_ns,
            "calibration_dataset_version_sha256": self.calibration_dataset_version_sha256,
            "minimum_calibration_samples": self.minimum_calibration_samples,
            "cells": [
                {
                    "lower_abs_score_bps": cell.lower_abs_score_bps,
                    "upper_abs_score_exclusive_bps": cell.upper_abs_score_exclusive_bps,
                    "sample_count": cell.sample_count,
                    "success_count": cell.success_count,
                }
                for cell in self.cells
            ],
            "observation_ids": list(self.observation_ids),
            "probability_estimator": "RAW_EMPIRICAL_FREQUENCY",
            "confidence_interval": None,
        }

    @property
    def model_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class CalibratedProbability:
    model_id: str
    fusion_id: str
    as_of_time_ns: int
    state: str
    probability_bps: int | None
    sample_count: int
    success_count: int
    lower_abs_score_bps: int
    upper_abs_score_exclusive_bps: int
    outcome_definition_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "model_id": self.model_id,
            "fusion_id": self.fusion_id,
            "as_of_time_ns": self.as_of_time_ns,
            "state": self.state,
            "probability_bps": self.probability_bps,
            "sample_count": self.sample_count,
            "success_count": self.success_count,
            "lower_abs_score_bps": self.lower_abs_score_bps,
            "upper_abs_score_exclusive_bps": self.upper_abs_score_exclusive_bps,
            "outcome_definition_sha256": self.outcome_definition_sha256,
            "confidence_interval": None,
            "tp_probability": None,
            "stop_probability": None,
        }

    @property
    def prediction_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def build_calibration_model(
    *,
    policy: ProbabilityCalibrationPolicy,
    context: CalibrationContext,
    training_cutoff_ns: int,
    calibration_dataset_version_sha256: str,
    observations: Sequence[CalibrationObservation],
) -> CalibrationModel:
    cutoff = _non_negative_int(training_cutoff_ns, field="training_cutoff_ns")
    dataset_version = _sha256_text(calibration_dataset_version_sha256, field="calibration_dataset_version_sha256")
    records = tuple(observations)
    if not records:
        raise ProbabilityCalibrationError("calibration observations cannot be empty")
    seen: set[str] = set()
    for item in records:
        if item.context != context:
            raise ProbabilityCalibrationError("mixed calibration contexts are forbidden")
        if item.outcome_observed_ns > cutoff:
            raise ProbabilityCalibrationError("future/unobserved outcome exceeds training cutoff")
        obs_id = item.observation_id
        if obs_id in seen:
            raise ProbabilityCalibrationError("duplicate calibration observation")
        seen.add(obs_id)

    cells: list[CalibrationCell] = []
    edges = policy.absolute_score_bin_edges_bps
    for lower, upper in zip(edges, edges[1:]):
        members = tuple(item for item in records if lower <= abs(item.signed_score_bps) < upper)
        cells.append(
            CalibrationCell(
                lower_abs_score_bps=lower,
                upper_abs_score_exclusive_bps=upper,
                sample_count=len(members),
                success_count=sum(1 for item in members if item.success),
            )
        )
    return CalibrationModel(
        context=context,
        training_cutoff_ns=cutoff,
        calibration_dataset_version_sha256=dataset_version,
        cells=tuple(cells),
        observation_ids=tuple(sorted(seen)),
        minimum_calibration_samples=policy.minimum_calibration_samples,
    )


def calibrate_probability(
    *,
    model: CalibrationModel,
    fusion: WeightedFusionResult,
    as_of_time_ns: int,
) -> CalibratedProbability:
    as_of = _non_negative_int(as_of_time_ns, field="as_of_time_ns")
    if as_of <= model.training_cutoff_ns:
        raise ProbabilityCalibrationError("prediction as-of must be strictly after training cutoff")
    if fusion.state != "FUSED" or fusion.signed_score_bps is None or fusion.direction not in (-1, 1):
        raise ProbabilityCalibrationError("only directional FUSED results may be calibrated")
    if fusion.subject_id != model.context.subject_id:
        raise ProbabilityCalibrationError("fusion subject does not match calibration context")
    if (fusion.signed_score_bps > 0) != (fusion.direction > 0):
        raise ProbabilityCalibrationError("fusion signed score direction mismatch")
    magnitude = abs(fusion.signed_score_bps)
    selected = next(
        (cell for cell in model.cells if cell.lower_abs_score_bps <= magnitude < cell.upper_abs_score_exclusive_bps),
        None,
    )
    if selected is None:
        raise ProbabilityCalibrationError("fusion score falls outside governed calibration bins")
    enough = selected.sample_count >= model.minimum_calibration_samples
    return CalibratedProbability(
        model_id=model.model_id,
        fusion_id=fusion.fusion_id,
        as_of_time_ns=as_of,
        state="CALIBRATED" if enough else "INSUFFICIENT_CALIBRATION_DATA",
        probability_bps=selected.probability_bps if enough else None,
        sample_count=selected.sample_count,
        success_count=selected.success_count,
        lower_abs_score_bps=selected.lower_abs_score_bps,
        upper_abs_score_exclusive_bps=selected.upper_abs_score_exclusive_bps,
        outcome_definition_sha256=model.context.outcome_definition_sha256,
    )
