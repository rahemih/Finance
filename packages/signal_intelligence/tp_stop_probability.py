from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .probability_uncertainty import ProbabilityUncertaintyQualification


class TPStopProbabilityError(ValueError):
    """P14-E TP/Stop empirical probability invariant failure."""


_OUTCOMES = ("TP_FIRST", "STOP_FIRST", "NEITHER")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TPStopProbabilityError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TPStopProbabilityError(f"{field} must be list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TPStopProbabilityError(f"{field} must be non-empty text")
    return value.strip()


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TPStopProbabilityError(f"{field} must be integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed < 0:
        raise TPStopProbabilityError(f"{field} must be non-negative")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed <= 0:
        raise TPStopProbabilityError(f"{field} must be positive")
    return parsed


def _sha256_text(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise TPStopProbabilityError(f"{field} must be lowercase SHA-256 hex")
    return parsed


@dataclass(frozen=True, slots=True)
class TPStopProbabilityPolicy:
    allowed_outcomes: tuple[str, ...]
    minimum_outcome_samples: int
    probability_scale_bps: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "TPStopProbabilityPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "EMPIRICAL_TP_STOP_OUTCOME_PROBABILITIES":
            raise TPStopProbabilityError("unsupported P14-E policy")
        outcomes = tuple(_text(item, field="allowed_outcome") for item in _object_list(raw.get("allowed_outcomes"), field="allowed_outcomes"))
        if outcomes != _OUTCOMES:
            raise TPStopProbabilityError("P14-E outcome taxonomy must be TP_FIRST/STOP_FIRST/NEITHER")
        if raw.get("probability_estimator") != "RAW_EMPIRICAL_FREQUENCY":
            raise TPStopProbabilityError("P14-E estimator must be raw empirical frequency")
        if raw.get("ambiguous_path_behavior") != "REJECT":
            raise TPStopProbabilityError("ambiguous price paths must be rejected")
        if raw.get("training_outcome_cutoff_behavior") != "FAIL_CLOSED":
            raise TPStopProbabilityError("training cutoff must fail closed")
        if raw.get("prediction_cutoff_behavior") != "STRICTLY_AFTER_TRAINING_CUTOFF":
            raise TPStopProbabilityError("prediction cutoff must be strictly after training cutoff")
        if raw.get("context_mixing_behavior") != "FAIL_CLOSED":
            raise TPStopProbabilityError("barrier-plan context mixing must fail closed")
        if raw.get("general_probability_relationship") != "SEPARATE_CONTEXT_NOT_EQUALITY_CONSTRAINT":
            raise TPStopProbabilityError("general and TP probabilities must remain separate")
        forbidden = (
            "synthetic_prior_enabled",
            "smoothing_enabled",
            "llm_probability_authority",
            "risk_approval_in_scope",
            "position_sizing_in_scope",
            "execution_authority_in_scope",
            "position_management_in_scope",
            "canonical_tests_network_required",
        )
        if any(raw.get(field) is not False for field in forbidden):
            raise TPStopProbabilityError("P14-E cannot enable priors/LLM/risk/execution/network authority")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise TPStopProbabilityError("P14-E cannot enable trading")
        scale = _positive_int(raw.get("probability_scale_bps"), field="probability_scale_bps")
        if scale != 10_000:
            raise TPStopProbabilityError("probability scale must be 10000 bps")
        return cls(
            allowed_outcomes=outcomes,
            minimum_outcome_samples=_positive_int(raw.get("minimum_outcome_samples"), field="minimum_outcome_samples"),
            probability_scale_bps=scale,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class BarrierPlanContext:
    subject_id: str
    strategy_id: str
    timeframe: str
    regime_label: str
    session_label: str
    direction: int
    target_distance_bps: int
    stop_distance_bps: int
    evaluation_horizon_steps: int
    outcome_definition_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _text(self.subject_id, field="subject_id"))
        object.__setattr__(self, "strategy_id", _text(self.strategy_id, field="strategy_id"))
        object.__setattr__(self, "timeframe", _text(self.timeframe, field="timeframe"))
        object.__setattr__(self, "regime_label", _text(self.regime_label, field="regime_label"))
        object.__setattr__(self, "session_label", _text(self.session_label, field="session_label"))
        if self.direction not in (-1, 1):
            raise TPStopProbabilityError("direction must be -1 or 1")
        object.__setattr__(self, "target_distance_bps", _positive_int(self.target_distance_bps, field="target_distance_bps"))
        object.__setattr__(self, "stop_distance_bps", _positive_int(self.stop_distance_bps, field="stop_distance_bps"))
        object.__setattr__(self, "evaluation_horizon_steps", _positive_int(self.evaluation_horizon_steps, field="evaluation_horizon_steps"))
        object.__setattr__(self, "outcome_definition_sha256", _sha256_text(self.outcome_definition_sha256, field="outcome_definition_sha256"))

    def payload(self) -> dict[str, object]:
        return {
            "subject_id": self.subject_id,
            "strategy_id": self.strategy_id,
            "timeframe": self.timeframe,
            "regime_label": self.regime_label,
            "session_label": self.session_label,
            "direction": self.direction,
            "target_distance_bps": self.target_distance_bps,
            "stop_distance_bps": self.stop_distance_bps,
            "evaluation_horizon_steps": self.evaluation_horizon_steps,
            "outcome_definition_sha256": self.outcome_definition_sha256,
        }


@dataclass(frozen=True, slots=True)
class TPStopObservation:
    context: BarrierPlanContext
    outcome: str
    decision_as_of_ns: int
    outcome_observed_ns: int
    source_dataset_version_sha256: str
    provenance_sha256: str

    def __post_init__(self) -> None:
        normalized = _text(self.outcome, field="outcome").upper()
        if normalized not in _OUTCOMES:
            raise TPStopProbabilityError("unresolved/ambiguous TP-stop outcome is forbidden")
        object.__setattr__(self, "outcome", normalized)
        decision = _non_negative_int(self.decision_as_of_ns, field="decision_as_of_ns")
        observed = _non_negative_int(self.outcome_observed_ns, field="outcome_observed_ns")
        if observed < decision:
            raise TPStopProbabilityError("outcome cannot be observed before decision")
        object.__setattr__(self, "source_dataset_version_sha256", _sha256_text(self.source_dataset_version_sha256, field="source_dataset_version_sha256"))
        object.__setattr__(self, "provenance_sha256", _sha256_text(self.provenance_sha256, field="provenance_sha256"))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "context": self.context.payload(),
            "outcome": self.outcome,
            "decision_as_of_ns": self.decision_as_of_ns,
            "outcome_observed_ns": self.outcome_observed_ns,
            "source_dataset_version_sha256": self.source_dataset_version_sha256,
            "provenance_sha256": self.provenance_sha256,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class TPStopProbabilityModel:
    context: BarrierPlanContext
    training_cutoff_ns: int
    outcome_dataset_version_sha256: str
    sample_count: int
    tp_first_count: int
    stop_first_count: int
    neither_count: int
    observation_ids: tuple[str, ...]
    minimum_outcome_samples: int

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "context": self.context.payload(),
            "training_cutoff_ns": self.training_cutoff_ns,
            "outcome_dataset_version_sha256": self.outcome_dataset_version_sha256,
            "sample_count": self.sample_count,
            "tp_first_count": self.tp_first_count,
            "stop_first_count": self.stop_first_count,
            "neither_count": self.neither_count,
            "observation_ids": list(self.observation_ids),
            "minimum_outcome_samples": self.minimum_outcome_samples,
            "probability_estimator": "RAW_EMPIRICAL_FREQUENCY",
        }

    @property
    def model_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class TPStopOutcomeProbability:
    model_id: str
    upstream_qualification_id: str
    as_of_time_ns: int
    state: str
    tp_first_probability_bps: int | None
    stop_first_probability_bps: int | None
    neither_probability_bps: int | None
    sample_count: int
    tp_first_count: int
    stop_first_count: int
    neither_count: int
    general_empirical_probability_bps: int | None
    general_overall_uncertainty_bps: int
    outcome_definition_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "model_id": self.model_id,
            "upstream_qualification_id": self.upstream_qualification_id,
            "as_of_time_ns": self.as_of_time_ns,
            "state": self.state,
            "tp_first_probability_bps": self.tp_first_probability_bps,
            "stop_first_probability_bps": self.stop_first_probability_bps,
            "neither_probability_bps": self.neither_probability_bps,
            "sample_count": self.sample_count,
            "tp_first_count": self.tp_first_count,
            "stop_first_count": self.stop_first_count,
            "neither_count": self.neither_count,
            "general_empirical_probability_bps": self.general_empirical_probability_bps,
            "general_overall_uncertainty_bps": self.general_overall_uncertainty_bps,
            "general_probability_equals_tp_probability": False,
            "outcome_definition_sha256": self.outcome_definition_sha256,
            "risk_approval": None,
            "position_size": None,
            "execution_command": None,
        }

    @property
    def prediction_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def build_tp_stop_model(
    *,
    policy: TPStopProbabilityPolicy,
    context: BarrierPlanContext,
    training_cutoff_ns: int,
    outcome_dataset_version_sha256: str,
    observations: Sequence[TPStopObservation],
) -> TPStopProbabilityModel:
    cutoff = _non_negative_int(training_cutoff_ns, field="training_cutoff_ns")
    dataset = _sha256_text(outcome_dataset_version_sha256, field="outcome_dataset_version_sha256")
    records = tuple(observations)
    if not records:
        raise TPStopProbabilityError("TP/Stop observations cannot be empty")
    seen: set[str] = set()
    counts = {outcome: 0 for outcome in _OUTCOMES}
    for item in records:
        if item.context != context:
            raise TPStopProbabilityError("mixed barrier-plan contexts are forbidden")
        if item.outcome not in policy.allowed_outcomes:
            raise TPStopProbabilityError("unapproved outcome label")
        if item.outcome_observed_ns > cutoff:
            raise TPStopProbabilityError("future/unobserved outcome exceeds training cutoff")
        observation_id = item.observation_id
        if observation_id in seen:
            raise TPStopProbabilityError("duplicate TP/Stop observation")
        seen.add(observation_id)
        counts[item.outcome] += 1
    return TPStopProbabilityModel(
        context=context,
        training_cutoff_ns=cutoff,
        outcome_dataset_version_sha256=dataset,
        sample_count=len(records),
        tp_first_count=counts["TP_FIRST"],
        stop_first_count=counts["STOP_FIRST"],
        neither_count=counts["NEITHER"],
        observation_ids=tuple(sorted(seen)),
        minimum_outcome_samples=policy.minimum_outcome_samples,
    )


def _distribution_bps(model: TPStopProbabilityModel) -> tuple[int, int, int]:
    counts = (model.tp_first_count, model.stop_first_count, model.neither_count)
    total = model.sample_count
    if total <= 0 or sum(counts) != total:
        raise TPStopProbabilityError("invalid TP/Stop model counts")
    base = [count * 10_000 // total for count in counts]
    remainders = [count * 10_000 % total for count in counts]
    units = 10_000 - sum(base)
    order = sorted(range(3), key=lambda index: (-remainders[index], index))
    for index in order[:units]:
        base[index] += 1
    return base[0], base[1], base[2]


def estimate_tp_stop_probabilities(
    *,
    model: TPStopProbabilityModel,
    qualification: ProbabilityUncertaintyQualification,
    as_of_time_ns: int,
) -> TPStopOutcomeProbability:
    as_of = _non_negative_int(as_of_time_ns, field="as_of_time_ns")
    if as_of <= model.training_cutoff_ns:
        raise TPStopProbabilityError("prediction as-of must be strictly after training cutoff")
    if qualification.state == "INSUFFICIENT_CALIBRATION_DATA":
        return TPStopOutcomeProbability(
            model_id=model.model_id,
            upstream_qualification_id=qualification.qualification_id,
            as_of_time_ns=as_of,
            state="INSUFFICIENT_UPSTREAM_CALIBRATION",
            tp_first_probability_bps=None,
            stop_first_probability_bps=None,
            neither_probability_bps=None,
            sample_count=model.sample_count,
            tp_first_count=model.tp_first_count,
            stop_first_count=model.stop_first_count,
            neither_count=model.neither_count,
            general_empirical_probability_bps=None,
            general_overall_uncertainty_bps=qualification.overall_uncertainty_bps,
            outcome_definition_sha256=model.context.outcome_definition_sha256,
        )
    if qualification.state != "QUALIFIED" or qualification.empirical_probability_bps is None:
        raise TPStopProbabilityError("P14-E requires QUALIFIED or explicit insufficient P14-D state")
    if model.sample_count < model.minimum_outcome_samples:
        return TPStopOutcomeProbability(
            model_id=model.model_id,
            upstream_qualification_id=qualification.qualification_id,
            as_of_time_ns=as_of,
            state="INSUFFICIENT_TP_STOP_DATA",
            tp_first_probability_bps=None,
            stop_first_probability_bps=None,
            neither_probability_bps=None,
            sample_count=model.sample_count,
            tp_first_count=model.tp_first_count,
            stop_first_count=model.stop_first_count,
            neither_count=model.neither_count,
            general_empirical_probability_bps=qualification.empirical_probability_bps,
            general_overall_uncertainty_bps=qualification.overall_uncertainty_bps,
            outcome_definition_sha256=model.context.outcome_definition_sha256,
        )
    tp, stop, neither = _distribution_bps(model)
    return TPStopOutcomeProbability(
        model_id=model.model_id,
        upstream_qualification_id=qualification.qualification_id,
        as_of_time_ns=as_of,
        state="CALIBRATED_TP_STOP",
        tp_first_probability_bps=tp,
        stop_first_probability_bps=stop,
        neither_probability_bps=neither,
        sample_count=model.sample_count,
        tp_first_count=model.tp_first_count,
        stop_first_count=model.stop_first_count,
        neither_count=model.neither_count,
        general_empirical_probability_bps=qualification.empirical_probability_bps,
        general_overall_uncertainty_bps=qualification.overall_uncertainty_bps,
        outcome_definition_sha256=model.context.outcome_definition_sha256,
    )
