from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .persian_explainability import PersianSignalExplanation
from .probability_uncertainty import ProbabilityUncertaintyQualification
from .tp_stop_probability import TPStopOutcomeProbability
from .weighted_fusion import WeightedFusionResult


class RedTeamChallengeError(ValueError):
    """P14-G independent challenge invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RedTeamChallengeError(f"{field} must be object")
    return cast(Mapping[str, object], value)


@dataclass(frozen=True, slots=True)
class RedTeamPolicy:
    allowed_dispositions: tuple[str, ...]
    blocked_fusion_disposition: str
    insufficient_evidence_disposition: str
    insufficient_calibration_disposition: str
    insufficient_tp_stop_disposition: str
    opposing_evidence_disposition: str
    expired_evidence_disposition: str
    tp_not_above_stop_disposition: str
    weak_or_moderate_sample_support_disposition: str

    @classmethod
    def from_path(cls, path: Path) -> "RedTeamPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "INDEPENDENT_SIGNAL_RED_TEAM":
            raise RedTeamChallengeError("unsupported P14-G policy")
        allowed_raw = raw.get("allowed_dispositions")
        if allowed_raw != ["CLEAR", "CAUTION", "REJECT"]:
            raise RedTeamChallengeError("invalid Red-Team disposition taxonomy")
        expected = {
            "blocked_fusion_disposition": "REJECT",
            "insufficient_evidence_disposition": "REJECT",
            "insufficient_calibration_disposition": "REJECT",
            "insufficient_tp_stop_disposition": "REJECT",
            "opposing_evidence_disposition": "CAUTION",
            "expired_evidence_disposition": "CAUTION",
            "tp_not_above_stop_disposition": "CAUTION",
            "weak_or_moderate_sample_support_disposition": "CAUTION",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise RedTeamChallengeError(f"{key} must be {value}")
        if raw.get("preserve_upstream_values") is not True:
            raise RedTeamChallengeError("upstream values must be preserved")
        if raw.get("probability_mutation_allowed") is not False:
            raise RedTeamChallengeError("probability mutation must remain disabled")
        if raw.get("uncertainty_mutation_allowed") is not False:
            raise RedTeamChallengeError("uncertainty mutation must remain disabled")
        if raw.get("final_signal_action_in_scope") is not False:
            raise RedTeamChallengeError("final signal action is outside P14-G")
        if raw.get("canonical_tests_network_required") is not False:
            raise RedTeamChallengeError("canonical tests must remain offline")
        return cls(
            allowed_dispositions=("CLEAR", "CAUTION", "REJECT"),
            blocked_fusion_disposition="REJECT",
            insufficient_evidence_disposition="REJECT",
            insufficient_calibration_disposition="REJECT",
            insufficient_tp_stop_disposition="REJECT",
            opposing_evidence_disposition="CAUTION",
            expired_evidence_disposition="CAUTION",
            tp_not_above_stop_disposition="CAUTION",
            weak_or_moderate_sample_support_disposition="CAUTION",
        )


@dataclass(frozen=True, slots=True)
class RedTeamFinding:
    code: str
    severity: str
    message_fa: str

    def payload(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message_fa": self.message_fa}


@dataclass(frozen=True, slots=True)
class RedTeamChallenge:
    subject_id: str
    as_of_time_ns: int
    fusion_id: str
    qualification_id: str | None
    tp_stop_prediction_id: str | None
    explanation_id: str
    disposition: str
    findings: tuple[RedTeamFinding, ...]
    empirical_probability_bps: int | None
    overall_uncertainty_bps: int | None
    tp_first_probability_bps: int | None
    stop_first_probability_bps: int | None

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "subject_id": self.subject_id,
            "as_of_time_ns": self.as_of_time_ns,
            "fusion_id": self.fusion_id,
            "qualification_id": self.qualification_id,
            "tp_stop_prediction_id": self.tp_stop_prediction_id,
            "explanation_id": self.explanation_id,
            "disposition": self.disposition,
            "findings": [item.payload() for item in self.findings],
            "empirical_probability_bps": self.empirical_probability_bps,
            "overall_uncertainty_bps": self.overall_uncertainty_bps,
            "tp_first_probability_bps": self.tp_first_probability_bps,
            "stop_first_probability_bps": self.stop_first_probability_bps,
            "probability_mutated": False,
            "uncertainty_mutated": False,
            "final_signal_action": None,
        }

    @property
    def challenge_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _max_disposition(findings: tuple[RedTeamFinding, ...]) -> str:
    if any(item.severity == "REJECT" for item in findings):
        return "REJECT"
    if any(item.severity == "CAUTION" for item in findings):
        return "CAUTION"
    return "CLEAR"


def challenge_signal(
    *,
    policy: RedTeamPolicy,
    fusion: WeightedFusionResult,
    explanation: PersianSignalExplanation,
    uncertainty: ProbabilityUncertaintyQualification | None = None,
    outcomes: TPStopOutcomeProbability | None = None,
) -> RedTeamChallenge:
    if explanation.fusion_id != fusion.fusion_id:
        raise RedTeamChallengeError("explanation fusion lineage mismatch")
    if explanation.subject_id != fusion.subject_id or explanation.as_of_time_ns != fusion.as_of_time_ns:
        raise RedTeamChallengeError("explanation context mismatch")

    findings: list[RedTeamFinding] = []

    if fusion.state == "BLOCKED":
        findings.append(RedTeamFinding("UPSTREAM_BLOCKED", policy.blocked_fusion_disposition, "منع قطعی بالادستی برقرار است."))
    elif fusion.state == "INSUFFICIENT_EVIDENCE":
        findings.append(RedTeamFinding("INSUFFICIENT_EVIDENCE", policy.insufficient_evidence_disposition, "شواهد مستقل برای ارزیابی کافی نیست."))
    elif fusion.state != "FUSED":
        raise RedTeamChallengeError("unsupported fusion state")

    if fusion.state != "FUSED":
        if uncertainty is not None or outcomes is not None:
            raise RedTeamChallengeError("blocked/insufficient fusion cannot carry downstream probability")
        ordered = tuple(sorted(findings, key=lambda item: (item.severity, item.code)))
        return RedTeamChallenge(
            subject_id=fusion.subject_id,
            as_of_time_ns=fusion.as_of_time_ns,
            fusion_id=fusion.fusion_id,
            qualification_id=None,
            tp_stop_prediction_id=None,
            explanation_id=explanation.explanation_id,
            disposition=_max_disposition(ordered),
            findings=ordered,
            empirical_probability_bps=None,
            overall_uncertainty_bps=None,
            tp_first_probability_bps=None,
            stop_first_probability_bps=None,
        )

    if uncertainty is None or outcomes is None:
        raise RedTeamChallengeError("FUSED challenge requires P14-D and P14-E outputs")
    if explanation.qualification_id != uncertainty.qualification_id:
        raise RedTeamChallengeError("explanation qualification lineage mismatch")
    if explanation.tp_stop_prediction_id != outcomes.prediction_id:
        raise RedTeamChallengeError("explanation TP/Stop lineage mismatch")
    if outcomes.upstream_qualification_id != uncertainty.qualification_id:
        raise RedTeamChallengeError("P14-E qualification lineage mismatch")
    if explanation.empirical_probability_bps != uncertainty.empirical_probability_bps:
        raise RedTeamChallengeError("explanation probability mismatch")
    if explanation.overall_uncertainty_bps != uncertainty.overall_uncertainty_bps:
        raise RedTeamChallengeError("explanation uncertainty mismatch")

    if uncertainty.state == "INSUFFICIENT_CALIBRATION_DATA":
        findings.append(RedTeamFinding("INSUFFICIENT_CALIBRATION", policy.insufficient_calibration_disposition, "کالیبراسیون تاریخی برای اتکا کافی نیست."))
    elif uncertainty.state == "QUALIFIED":
        if uncertainty.sample_support in ("WEAK", "MODERATE"):
            findings.append(RedTeamFinding("LIMITED_SAMPLE_SUPPORT", policy.weak_or_moderate_sample_support_disposition, "قدرت پشتیبانی نمونه هنوز قوی نیست."))
    else:
        raise RedTeamChallengeError("unsupported P14-D state")

    if outcomes.state == "INSUFFICIENT_UPSTREAM_CALIBRATION":
        findings.append(RedTeamFinding("TP_STOP_UPSTREAM_INSUFFICIENT", policy.insufficient_calibration_disposition, "خروجی حد سود/ضرر به‌دلیل کالیبراسیون ناکافی قابل اتکا نیست."))
    elif outcomes.state == "INSUFFICIENT_TP_STOP_DATA":
        findings.append(RedTeamFinding("TP_STOP_SAMPLE_INSUFFICIENT", policy.insufficient_tp_stop_disposition, "نمونه تاریخی حد سود/ضرر کافی نیست."))
    elif outcomes.state == "CALIBRATED_TP_STOP":
        if outcomes.tp_first_probability_bps is None or outcomes.stop_first_probability_bps is None:
            raise RedTeamChallengeError("calibrated TP/Stop state missing probabilities")
        if outcomes.tp_first_probability_bps <= outcomes.stop_first_probability_bps:
            findings.append(RedTeamFinding("TP_NOT_ABOVE_STOP", policy.tp_not_above_stop_disposition, "احتمال رسیدن اول به حد سود از حد ضرر بیشتر نیست."))
    else:
        raise RedTeamChallengeError("unsupported P14-E state")

    if fusion.opposing_groups:
        findings.append(RedTeamFinding("OPPOSING_EVIDENCE", policy.opposing_evidence_disposition, "شواهد مستقل مخالف جهت غالب وجود دارد."))
    if fusion.excluded_expired_evidence_ids:
        findings.append(RedTeamFinding("EXPIRED_EVIDENCE_EXCLUDED", policy.expired_evidence_disposition, "بخشی از شواهد به‌دلیل انقضا از ترکیب حذف شده‌اند."))

    ordered = tuple(sorted(findings, key=lambda item: (item.severity, item.code)))
    return RedTeamChallenge(
        subject_id=fusion.subject_id,
        as_of_time_ns=fusion.as_of_time_ns,
        fusion_id=fusion.fusion_id,
        qualification_id=uncertainty.qualification_id,
        tp_stop_prediction_id=outcomes.prediction_id,
        explanation_id=explanation.explanation_id,
        disposition=_max_disposition(ordered),
        findings=ordered,
        empirical_probability_bps=uncertainty.empirical_probability_bps,
        overall_uncertainty_bps=uncertainty.overall_uncertainty_bps,
        tp_first_probability_bps=outcomes.tp_first_probability_bps,
        stop_first_probability_bps=outcomes.stop_first_probability_bps,
    )
