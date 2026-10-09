from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast

from packages.historical_data.feature_materialization import QualityEligibility


class ProvenanceConfidenceError(ValueError):
    """Provenance/confidence policy or evidence input is invalid."""


class ControlOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ProvenanceConfidenceError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProvenanceConfidenceError(f"{field} must be a non-empty string")
    return value.strip()


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProvenanceConfidenceError(f"{field} must be a non-negative integer")
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ProvenanceConfidencePolicy:
    policy_version: str
    score_scale_bps: int
    eligibility_min_score_bps: int
    required_controls: tuple[str, ...]
    control_weights_bps: tuple[tuple[str, int], ...]
    production_data_quality_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "ProvenanceConfidencePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProvenanceConfidenceError(f"invalid provenance-confidence policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise ProvenanceConfidenceError("unsupported policy schema_version")
        if raw.get("mode") != "EXPLICIT_WEIGHTED_CONFIDENCE_FAIL_CLOSED":
            raise ProvenanceConfidenceError("unsupported provenance-confidence mode")
        if raw.get("adaptive_weights") is not False:
            raise ProvenanceConfidenceError("adaptive confidence weights are forbidden in P07-E")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise ProvenanceConfidenceError("reference provenance-confidence contract must be offline")
        if raw.get("missing_required_control_status") != "UNKNOWN":
            raise ProvenanceConfidenceError("missing required controls must yield UNKNOWN")
        if raw.get("explicit_fail_status") != "INELIGIBLE":
            raise ProvenanceConfidenceError("explicit failures must yield INELIGIBLE")
        if raw.get("complete_below_threshold_status") != "INELIGIBLE":
            raise ProvenanceConfidenceError("below-threshold complete provenance must be INELIGIBLE")
        if raw.get("complete_above_threshold_status") != "ELIGIBLE":
            raise ProvenanceConfidenceError("eligible complete provenance must yield ELIGIBLE")

        scale = _non_negative_int(raw.get("score_scale_bps"), field="score_scale_bps")
        if scale <= 0:
            raise ProvenanceConfidenceError("score_scale_bps must be positive")
        threshold = _non_negative_int(
            raw.get("eligibility_min_score_bps"),
            field="eligibility_min_score_bps",
        )
        if threshold > scale:
            raise ProvenanceConfidenceError("eligibility threshold cannot exceed score scale")

        required_raw = raw.get("required_controls")
        if not isinstance(required_raw, list) or not required_raw:
            raise ProvenanceConfidenceError("required_controls must be a non-empty list")
        required = tuple(_text(item, field="required_control") for item in cast(list[object], required_raw))
        if len(required) != len(set(required)):
            raise ProvenanceConfidenceError("required_controls must be unique")

        weights_raw = _mapping(raw.get("control_weights_bps"), field="control_weights_bps")
        weights: list[tuple[str, int]] = []
        for key, value in weights_raw.items():
            control = _text(key, field="control_weight_key")
            weight = _non_negative_int(value, field=f"control_weights_bps.{control}")
            weights.append((control, weight))
        weight_map = dict(weights)
        if set(weight_map) != set(required):
            raise ProvenanceConfidenceError("control weights must match required controls exactly")
        if sum(weight_map.values()) != scale:
            raise ProvenanceConfidenceError("control weights must sum exactly to score_scale_bps")

        vendor = _text(raw.get("production_data_quality_vendor"), field="production_data_quality_vendor")
        return cls(
            policy_version=_text(raw.get("policy_version"), field="policy_version"),
            score_scale_bps=scale,
            eligibility_min_score_bps=threshold,
            required_controls=tuple(sorted(required)),
            control_weights_bps=tuple(sorted(weight_map.items())),
            production_data_quality_vendor=vendor,
        )

    @property
    def weights(self) -> dict[str, int]:
        return dict(self.control_weights_bps)


@dataclass(frozen=True, slots=True)
class ControlEvidence:
    control_id: str
    outcome: ControlOutcome
    confidence_bps: int
    evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.control_id.strip():
            raise ProvenanceConfidenceError("control_id must be non-empty")
        if isinstance(self.confidence_bps, bool) or self.confidence_bps < 0:
            raise ProvenanceConfidenceError("confidence_bps must be a non-negative integer")
        if _SHA256.fullmatch(self.evidence_sha256) is None:
            raise ProvenanceConfidenceError("evidence_sha256 must be lowercase SHA-256")

    def payload(self) -> dict[str, object]:
        return {
            "control_id": self.control_id,
            "outcome": self.outcome.value,
            "confidence_bps": self.confidence_bps,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class ProvenanceConfidenceResult:
    policy_version: str
    status: EligibilityStatus
    aggregate_confidence_bps: int | None
    components: tuple[ControlEvidence, ...]
    missing_controls: tuple[str, ...]

    @property
    def evidence_identity(self) -> str:
        payload = {
            "schema_version": "1.0",
            "policy_version": self.policy_version,
            "status": self.status.value,
            "aggregate_confidence_bps": self.aggregate_confidence_bps,
            "components": [component.payload() for component in self.components],
            "missing_controls": list(self.missing_controls),
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    def to_feature_quality_eligibility(self) -> QualityEligibility:
        return QualityEligibility(
            status=self.status.value,
            quality_policy_version=self.policy_version,
            evidence_sha256=self.evidence_identity,
        )


class ProvenanceConfidenceEvaluator:
    def __init__(self, policy: ProvenanceConfidencePolicy) -> None:
        self._policy = policy

    def evaluate(self, components: tuple[ControlEvidence, ...]) -> ProvenanceConfidenceResult:
        if len(components) != len({component.control_id for component in components}):
            raise ProvenanceConfidenceError("control evidence must be unique by control_id")

        required = set(self._policy.required_controls)
        supplied = {component.control_id for component in components}
        unknown = supplied - required
        if unknown:
            raise ProvenanceConfidenceError(
                f"unknown control evidence: {','.join(sorted(unknown))}"
            )

        for component in components:
            if component.confidence_bps > self._policy.score_scale_bps:
                raise ProvenanceConfidenceError(
                    f"{component.control_id} confidence exceeds score scale"
                )

        missing = tuple(sorted(required - supplied))
        ordered = tuple(sorted(components, key=lambda component: component.control_id))
        if missing:
            return ProvenanceConfidenceResult(
                policy_version=self._policy.policy_version,
                status=EligibilityStatus.UNKNOWN,
                aggregate_confidence_bps=None,
                components=ordered,
                missing_controls=missing,
            )

        weights = self._policy.weights
        weighted_sum = sum(
            component.confidence_bps * weights[component.control_id]
            for component in ordered
        )
        aggregate = weighted_sum // self._policy.score_scale_bps

        if any(component.outcome is ControlOutcome.FAIL for component in ordered):
            status = EligibilityStatus.INELIGIBLE
        elif aggregate >= self._policy.eligibility_min_score_bps:
            status = EligibilityStatus.ELIGIBLE
        else:
            status = EligibilityStatus.INELIGIBLE

        return ProvenanceConfidenceResult(
            policy_version=self._policy.policy_version,
            status=status,
            aggregate_confidence_bps=aggregate,
            components=ordered,
            missing_controls=(),
        )
