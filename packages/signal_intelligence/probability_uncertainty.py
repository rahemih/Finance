from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .probability_calibration import CalibratedProbability


class ProbabilityUncertaintyError(ValueError):
    """P14-D probability uncertainty invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProbabilityUncertaintyError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ProbabilityUncertaintyError(f"{field} must be list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProbabilityUncertaintyError(f"{field} must be non-empty text")
    return value.strip()


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProbabilityUncertaintyError(f"{field} must be integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed < 0:
        raise ProbabilityUncertaintyError(f"{field} must be non-negative")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed <= 0:
        raise ProbabilityUncertaintyError(f"{field} must be positive")
    return parsed


def _bps(value: object, *, field: str) -> int:
    parsed = _non_negative_int(value, field=field)
    if parsed > 10_000:
        raise ProbabilityUncertaintyError(f"{field} must be within 0..10000")
    return parsed


def _sha256_text(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise ProbabilityUncertaintyError(f"{field} must be lowercase SHA-256 hex")
    return parsed


@dataclass(frozen=True, slots=True)
class ProbabilityUncertaintyPolicy:
    confidence_level_bps: int
    z_score_milli: int
    sample_support_moderate_min: int
    sample_support_strong_min: int
    allowed_regime_similarity_sources: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ProbabilityUncertaintyPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "PROBABILITY_UNCERTAINTY_QUALIFICATION":
            raise ProbabilityUncertaintyError("unsupported P14-D policy")
        if raw.get("confidence_interval_method") != "WILSON_SCORE":
            raise ProbabilityUncertaintyError("P14-D confidence interval must use Wilson score")
        confidence_level = _bps(raw.get("confidence_level_bps"), field="confidence_level_bps")
        if confidence_level != 9500:
            raise ProbabilityUncertaintyError("canonical confidence level must be 95%")
        z_milli = _positive_int(raw.get("z_score_milli"), field="z_score_milli")
        if z_milli != 1960:
            raise ProbabilityUncertaintyError("canonical 95% z-score must be 1.960")
        moderate = _positive_int(raw.get("sample_support_moderate_min"), field="sample_support_moderate_min")
        strong = _positive_int(raw.get("sample_support_strong_min"), field="sample_support_strong_min")
        if moderate >= strong:
            raise ProbabilityUncertaintyError("sample support thresholds must be increasing")
        sources = tuple(_text(item, field="regime_similarity_source") for item in _object_list(raw.get("allowed_regime_similarity_sources"), field="allowed_regime_similarity_sources"))
        if sources != ("P12_HISTORICAL_ANALOG", "P08_REGIME"):
            raise ProbabilityUncertaintyError("unexpected regime similarity source registry")
        if (_integer(raw.get("similarity_scale_min_bps"), field="similarity_scale_min_bps"), _integer(raw.get("similarity_scale_max_bps"), field="similarity_scale_max_bps")) != (0, 10_000):
            raise ProbabilityUncertaintyError("regime similarity scale must be 0..10000")
        if (_integer(raw.get("uncertainty_scale_min_bps"), field="uncertainty_scale_min_bps"), _integer(raw.get("uncertainty_scale_max_bps"), field="uncertainty_scale_max_bps")) != (0, 10_000):
            raise ProbabilityUncertaintyError("uncertainty scale must be 0..10000")
        if raw.get("overall_uncertainty_method") != "MAX_COMPONENT":
            raise ProbabilityUncertaintyError("overall uncertainty must use conservative max component")
        forbidden_true = (
            "probability_mutation_allowed",
            "regime_similarity_is_probability",
            "llm_probability_authority",
            "llm_uncertainty_authority",
            "tp_stop_probability_in_scope",
            "risk_approval_in_scope",
            "position_sizing_in_scope",
            "execution_authority_in_scope",
            "canonical_tests_network_required",
        )
        if any(raw.get(field) is not False for field in forbidden_true):
            raise ProbabilityUncertaintyError("P14-D cannot enable probability mutation/LLM/TP-stop/risk/execution/network authority")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise ProbabilityUncertaintyError("P14-D cannot enable trading")
        return cls(
            confidence_level_bps=confidence_level,
            z_score_milli=z_milli,
            sample_support_moderate_min=moderate,
            sample_support_strong_min=strong,
            allowed_regime_similarity_sources=sources,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class RegimeSimilarityEvidence:
    prediction_id: str
    source_kind: str
    as_of_time_ns: int
    similarity_bps: int
    uncertainty_bps: int
    source_record_id: str
    provenance_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "prediction_id", _sha256_text(self.prediction_id, field="prediction_id"))
        object.__setattr__(self, "source_kind", _text(self.source_kind, field="source_kind").upper())
        object.__setattr__(self, "as_of_time_ns", _non_negative_int(self.as_of_time_ns, field="as_of_time_ns"))
        object.__setattr__(self, "similarity_bps", _bps(self.similarity_bps, field="similarity_bps"))
        object.__setattr__(self, "uncertainty_bps", _bps(self.uncertainty_bps, field="uncertainty_bps"))
        object.__setattr__(self, "source_record_id", _text(self.source_record_id, field="source_record_id"))
        object.__setattr__(self, "provenance_sha256", _sha256_text(self.provenance_sha256, field="provenance_sha256"))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "prediction_id": self.prediction_id,
            "source_kind": self.source_kind,
            "as_of_time_ns": self.as_of_time_ns,
            "similarity_bps": self.similarity_bps,
            "uncertainty_bps": self.uncertainty_bps,
            "source_record_id": self.source_record_id,
            "provenance_sha256": self.provenance_sha256,
            "similarity_is_probability": False,
        }

    @property
    def evidence_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ProbabilityUncertaintyQualification:
    prediction_id: str
    empirical_probability_bps: int | None
    sample_count: int
    success_count: int
    state: str
    sample_support: str
    confidence_level_bps: int
    confidence_interval_lower_bps: int | None
    confidence_interval_upper_bps: int | None
    interval_half_width_bps: int | None
    regime_similarity_bps: int
    regime_dissimilarity_bps: int
    regime_uncertainty_bps: int
    overall_uncertainty_bps: int
    dominant_uncertainty_sources: tuple[str, ...]
    regime_evidence_id: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "prediction_id": self.prediction_id,
            "empirical_probability_bps": self.empirical_probability_bps,
            "sample_count": self.sample_count,
            "success_count": self.success_count,
            "state": self.state,
            "sample_support": self.sample_support,
            "confidence_level_bps": self.confidence_level_bps,
            "confidence_interval_lower_bps": self.confidence_interval_lower_bps,
            "confidence_interval_upper_bps": self.confidence_interval_upper_bps,
            "interval_half_width_bps": self.interval_half_width_bps,
            "regime_similarity_bps": self.regime_similarity_bps,
            "regime_similarity_is_probability": False,
            "regime_dissimilarity_bps": self.regime_dissimilarity_bps,
            "regime_uncertainty_bps": self.regime_uncertainty_bps,
            "overall_uncertainty_bps": self.overall_uncertainty_bps,
            "dominant_uncertainty_sources": list(self.dominant_uncertainty_sources),
            "regime_evidence_id": self.regime_evidence_id,
            "probability_mutated": False,
            "tp_probability": None,
            "stop_probability": None,
        }

    @property
    def qualification_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _rounded_probability_bps(success_count: int, sample_count: int) -> int:
    return (success_count * 10_000 + sample_count // 2) // sample_count


def _wilson_interval_bps(*, success_count: int, sample_count: int, z_score_milli: int) -> tuple[int, int]:
    success = _non_negative_int(success_count, field="success_count")
    sample = _positive_int(sample_count, field="sample_count")
    if success > sample:
        raise ProbabilityUncertaintyError("success_count cannot exceed sample_count")
    with localcontext() as ctx:
        ctx.prec = 50
        n = Decimal(sample)
        p = Decimal(success) / n
        z = Decimal(z_score_milli) / Decimal(1000)
        z2 = z * z
        denominator = Decimal(1) + z2 / n
        center = (p + z2 / (Decimal(2) * n)) / denominator
        variance = p * (Decimal(1) - p) / n + z2 / (Decimal(4) * n * n)
        margin = z * variance.sqrt() / denominator
        lower = max(Decimal(0), center - margin)
        upper = min(Decimal(1), center + margin)
        lower_bps = int((lower * Decimal(10_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        upper_bps = int((upper * Decimal(10_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return lower_bps, upper_bps


def _sample_support(policy: ProbabilityUncertaintyPolicy, sample_count: int) -> str:
    if sample_count >= policy.sample_support_strong_min:
        return "STRONG"
    if sample_count >= policy.sample_support_moderate_min:
        return "MODERATE"
    return "MINIMUM"


def qualify_probability_uncertainty(
    *,
    policy: ProbabilityUncertaintyPolicy,
    calibrated: CalibratedProbability,
    regime: RegimeSimilarityEvidence,
) -> ProbabilityUncertaintyQualification:
    prediction_id = calibrated.prediction_id
    if regime.prediction_id != prediction_id:
        raise ProbabilityUncertaintyError("regime evidence prediction_id mismatch")
    if regime.source_kind not in policy.allowed_regime_similarity_sources:
        raise ProbabilityUncertaintyError("unapproved regime similarity source")
    if regime.as_of_time_ns != calibrated.as_of_time_ns:
        raise ProbabilityUncertaintyError("regime evidence as-of must equal calibrated prediction as-of")
    sample_count = _non_negative_int(calibrated.sample_count, field="sample_count")
    success_count = _non_negative_int(calibrated.success_count, field="success_count")
    if success_count > sample_count:
        raise ProbabilityUncertaintyError("success_count cannot exceed sample_count")

    regime_dissimilarity = 10_000 - regime.similarity_bps

    if calibrated.state == "INSUFFICIENT_CALIBRATION_DATA":
        if calibrated.probability_bps is not None:
            raise ProbabilityUncertaintyError("insufficient calibration data cannot expose probability")
        return ProbabilityUncertaintyQualification(
            prediction_id=prediction_id,
            empirical_probability_bps=None,
            sample_count=sample_count,
            success_count=success_count,
            state="INSUFFICIENT_CALIBRATION_DATA",
            sample_support="INSUFFICIENT",
            confidence_level_bps=policy.confidence_level_bps,
            confidence_interval_lower_bps=None,
            confidence_interval_upper_bps=None,
            interval_half_width_bps=None,
            regime_similarity_bps=regime.similarity_bps,
            regime_dissimilarity_bps=regime_dissimilarity,
            regime_uncertainty_bps=regime.uncertainty_bps,
            overall_uncertainty_bps=10_000,
            dominant_uncertainty_sources=("INSUFFICIENT_CALIBRATION_DATA",),
            regime_evidence_id=regime.evidence_id,
        )

    if calibrated.state != "CALIBRATED" or calibrated.probability_bps is None:
        raise ProbabilityUncertaintyError("P14-D requires CALIBRATED or explicit insufficient P14-C state")
    if sample_count <= 0:
        raise ProbabilityUncertaintyError("CALIBRATED result requires positive sample_count")
    empirical = _bps(calibrated.probability_bps, field="probability_bps")
    if empirical != _rounded_probability_bps(success_count, sample_count):
        raise ProbabilityUncertaintyError("P14-C probability does not match raw empirical frequency")

    lower, upper = _wilson_interval_bps(
        success_count=success_count,
        sample_count=sample_count,
        z_score_milli=policy.z_score_milli,
    )
    if not lower <= empirical <= upper:
        raise ProbabilityUncertaintyError("Wilson interval must contain empirical probability")
    half_width = (upper - lower + 1) // 2
    components = {
        "STATISTICAL_INTERVAL": half_width,
        "REGIME_DISSIMILARITY": regime_dissimilarity,
        "REGIME_EVIDENCE_UNCERTAINTY": regime.uncertainty_bps,
    }
    overall = max(components.values())
    dominant = tuple(sorted(name for name, value in components.items() if value == overall))

    return ProbabilityUncertaintyQualification(
        prediction_id=prediction_id,
        empirical_probability_bps=empirical,
        sample_count=sample_count,
        success_count=success_count,
        state="QUALIFIED",
        sample_support=_sample_support(policy, sample_count),
        confidence_level_bps=policy.confidence_level_bps,
        confidence_interval_lower_bps=lower,
        confidence_interval_upper_bps=upper,
        interval_half_width_bps=half_width,
        regime_similarity_bps=regime.similarity_bps,
        regime_dissimilarity_bps=regime_dissimilarity,
        regime_uncertainty_bps=regime.uncertainty_bps,
        overall_uncertainty_bps=overall,
        dominant_uncertainty_sources=dominant,
        regime_evidence_id=regime.evidence_id,
    )
