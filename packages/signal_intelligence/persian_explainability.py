from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .probability_uncertainty import ProbabilityUncertaintyQualification
from .tp_stop_probability import TPStopOutcomeProbability
from .weighted_fusion import WeightedFusionResult


class PersianExplainabilityError(ValueError):
    """P14-F deterministic Persian explainability invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PersianExplainabilityError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersianExplainabilityError(f"{field} must be non-empty text")
    return value.strip()


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PersianExplainabilityError(f"{field} must be integer")
    return value


def _bps(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed < 0 or parsed > 10_000:
        raise PersianExplainabilityError(f"{field} must be within 0..10000")
    return parsed


def _percent_fa(bps: int) -> str:
    value = _bps(bps, field="percentage_bps")
    return f"{value // 100}.{value % 100:02d}٪"


@dataclass(frozen=True, slots=True)
class PersianExplainabilityPolicy:
    language: str
    percentage_decimals: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "PersianExplainabilityPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_PERSIAN_SIGNAL_EXPLAINABILITY":
            raise PersianExplainabilityError("unsupported P14-F policy")
        if raw.get("language") != "fa-IR" or raw.get("rendering") != "GOVERNED_TEMPLATE_ONLY":
            raise PersianExplainabilityError("P14-F must use governed Persian templates")
        if raw.get("preserve_exact_upstream_values") is not True:
            raise PersianExplainabilityError("upstream values must remain exact")
        if raw.get("hard_veto_non_bypassable") is not True:
            raise PersianExplainabilityError("hard veto must remain non-bypassable")
        if raw.get("blocked_probability_behavior") != "ABSENT" or raw.get("insufficient_probability_behavior") != "ABSENT":
            raise PersianExplainabilityError("blocked/insufficient states cannot expose invented probability")
        forbidden = (
            "llm_freeform_numeric_authority",
            "probability_mutation_allowed",
            "uncertainty_mutation_allowed",
            "final_signal_action_in_scope",
            "risk_approval_in_scope",
            "position_sizing_in_scope",
            "execution_authority_in_scope",
            "canonical_tests_network_required",
        )
        if any(raw.get(field) is not False for field in forbidden):
            raise PersianExplainabilityError("P14-F cannot enable numeric/action/risk/execution authority")
        decimals = _integer(raw.get("percentage_decimals"), field="percentage_decimals")
        if decimals != 2:
            raise PersianExplainabilityError("canonical percentage precision must be two decimals")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise PersianExplainabilityError("P14-F cannot enable trading")
        return cls(language="fa-IR", percentage_decimals=decimals, live_trading="DISABLED", auto_trading="DISABLED")


@dataclass(frozen=True, slots=True)
class PersianSignalExplanation:
    subject_id: str
    as_of_time_ns: int
    fusion_id: str
    fusion_state: str
    fusion_direction: int
    qualification_id: str | None
    tp_stop_prediction_id: str | None
    summary_fa: str
    supporting_factors_fa: tuple[str, ...]
    opposing_factors_fa: tuple[str, ...]
    neutral_factors_fa: tuple[str, ...]
    veto_factors_fa: tuple[str, ...]
    probability_fa: str | None
    uncertainty_fa: str | None
    tp_stop_fa: str | None
    evidence_quality_fa: str
    empirical_probability_bps: int | None
    overall_uncertainty_bps: int | None
    tp_first_probability_bps: int | None
    stop_first_probability_bps: int | None
    neither_probability_bps: int | None

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "language": "fa-IR",
            "subject_id": self.subject_id,
            "as_of_time_ns": self.as_of_time_ns,
            "fusion_id": self.fusion_id,
            "fusion_state": self.fusion_state,
            "fusion_direction": self.fusion_direction,
            "qualification_id": self.qualification_id,
            "tp_stop_prediction_id": self.tp_stop_prediction_id,
            "summary_fa": self.summary_fa,
            "supporting_factors_fa": list(self.supporting_factors_fa),
            "opposing_factors_fa": list(self.opposing_factors_fa),
            "neutral_factors_fa": list(self.neutral_factors_fa),
            "veto_factors_fa": list(self.veto_factors_fa),
            "probability_fa": self.probability_fa,
            "uncertainty_fa": self.uncertainty_fa,
            "tp_stop_fa": self.tp_stop_fa,
            "evidence_quality_fa": self.evidence_quality_fa,
            "empirical_probability_bps": self.empirical_probability_bps,
            "overall_uncertainty_bps": self.overall_uncertainty_bps,
            "tp_first_probability_bps": self.tp_first_probability_bps,
            "stop_first_probability_bps": self.stop_first_probability_bps,
            "neither_probability_bps": self.neither_probability_bps,
            "probability_mutated": False,
            "uncertainty_mutated": False,
            "final_signal_action": None,
            "risk_approval": None,
            "position_size": None,
            "execution_command": None,
        }

    @property
    def explanation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _group_lines(prefix: str, groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{prefix}: {group}" for group in sorted(groups))


def explain_signal_fa(
    *,
    policy: PersianExplainabilityPolicy,
    fusion: WeightedFusionResult,
    uncertainty: ProbabilityUncertaintyQualification | None = None,
    outcomes: TPStopOutcomeProbability | None = None,
) -> PersianSignalExplanation:
    if policy.language != "fa-IR" or policy.percentage_decimals != 2:
        raise PersianExplainabilityError("invalid Persian explainability policy instance")
    if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
        raise PersianExplainabilityError("P14-F cannot enable trading")
    subject = _text(fusion.subject_id, field="subject_id")
    if fusion.as_of_time_ns < 0:
        raise PersianExplainabilityError("as_of_time_ns must be non-negative")
    if fusion.state not in ("BLOCKED", "INSUFFICIENT_EVIDENCE", "FUSED"):
        raise PersianExplainabilityError("unsupported fusion state")

    supporting = _group_lines("عامل تأییدکننده", fusion.supporting_groups)
    opposing = _group_lines("عامل مخالف", fusion.opposing_groups)
    neutral = _group_lines("عامل خنثی", fusion.neutral_groups)
    veto = _group_lines("دلیل منع", fusion.veto_codes)
    evidence_quality = (
        f"شواهد منقضی کنارگذاشته‌شده: {len(fusion.excluded_expired_evidence_ids)}؛ "
        f"شواهد هم‌بسته کنارگذاشته‌شده: {len(fusion.excluded_correlated_evidence_ids)}؛ "
        f"خانواده‌های منبع: {len(fusion.source_families)}."
    )

    if fusion.state == "BLOCKED":
        if uncertainty is not None or outcomes is not None:
            raise PersianExplainabilityError("BLOCKED state cannot carry downstream probabilities")
        if not fusion.veto_codes:
            raise PersianExplainabilityError("BLOCKED state requires veto codes")
        return PersianSignalExplanation(
            subject_id=subject,
            as_of_time_ns=fusion.as_of_time_ns,
            fusion_id=fusion.fusion_id,
            fusion_state=fusion.state,
            fusion_direction=fusion.direction,
            qualification_id=None,
            tp_stop_prediction_id=None,
            summary_fa="ترکیب شواهد به‌دلیل وجود منع قطعی مسدود است.",
            supporting_factors_fa=supporting,
            opposing_factors_fa=opposing,
            neutral_factors_fa=neutral,
            veto_factors_fa=veto,
            probability_fa=None,
            uncertainty_fa=None,
            tp_stop_fa=None,
            evidence_quality_fa=evidence_quality,
            empirical_probability_bps=None,
            overall_uncertainty_bps=None,
            tp_first_probability_bps=None,
            stop_first_probability_bps=None,
            neither_probability_bps=None,
        )

    if fusion.state == "INSUFFICIENT_EVIDENCE":
        if uncertainty is not None or outcomes is not None:
            raise PersianExplainabilityError("insufficient evidence cannot carry downstream probabilities")
        return PersianSignalExplanation(
            subject_id=subject,
            as_of_time_ns=fusion.as_of_time_ns,
            fusion_id=fusion.fusion_id,
            fusion_state=fusion.state,
            fusion_direction=fusion.direction,
            qualification_id=None,
            tp_stop_prediction_id=None,
            summary_fa="شواهد مستقل برای نتیجه‌گیری کافی نیست.",
            supporting_factors_fa=supporting,
            opposing_factors_fa=opposing,
            neutral_factors_fa=neutral,
            veto_factors_fa=veto,
            probability_fa=None,
            uncertainty_fa=None,
            tp_stop_fa=None,
            evidence_quality_fa=evidence_quality,
            empirical_probability_bps=None,
            overall_uncertainty_bps=None,
            tp_first_probability_bps=None,
            stop_first_probability_bps=None,
            neither_probability_bps=None,
        )

    if fusion.direction not in (-1, 1) or fusion.signed_score_bps is None:
        raise PersianExplainabilityError("FUSED explanation requires directional score")
    if uncertainty is None or outcomes is None:
        raise PersianExplainabilityError("FUSED explanation requires P14-D and P14-E outputs")
    if outcomes.upstream_qualification_id != uncertainty.qualification_id:
        raise PersianExplainabilityError("P14-E qualification lineage mismatch")
    if outcomes.general_empirical_probability_bps != uncertainty.empirical_probability_bps:
        raise PersianExplainabilityError("general empirical probability mismatch")
    if outcomes.general_overall_uncertainty_bps != uncertainty.overall_uncertainty_bps:
        raise PersianExplainabilityError("overall uncertainty mismatch")

    direction_fa = "صعودی" if fusion.direction > 0 else "نزولی"
    summary = f"ترکیب شواهد مستقل جهت {direction_fa} دارد؛ این توضیح به‌تنهایی دستور معامله نیست."

    probability_fa: str | None = None
    uncertainty_fa: str | None = None
    if uncertainty.state == "QUALIFIED":
        if uncertainty.empirical_probability_bps is None:
            raise PersianExplainabilityError("QUALIFIED uncertainty requires empirical probability")
        probability_fa = (
            f"احتمال تجربی موفقیت جهت: {_percent_fa(uncertainty.empirical_probability_bps)} "
            f"بر پایه {uncertainty.sample_count} نمونه."
        )
        if uncertainty.confidence_interval_lower_bps is None or uncertainty.confidence_interval_upper_bps is None:
            raise PersianExplainabilityError("QUALIFIED uncertainty requires confidence interval")
        uncertainty_fa = (
            f"بازه اطمینان {_percent_fa(uncertainty.confidence_level_bps)}: "
            f"{_percent_fa(uncertainty.confidence_interval_lower_bps)} تا "
            f"{_percent_fa(uncertainty.confidence_interval_upper_bps)}؛ "
            f"عدم‌قطعیت کل: {_percent_fa(uncertainty.overall_uncertainty_bps)}."
        )
    elif uncertainty.state == "INSUFFICIENT_CALIBRATION_DATA":
        if uncertainty.empirical_probability_bps is not None:
            raise PersianExplainabilityError("insufficient calibration cannot expose empirical probability")
        probability_fa = "داده کالیبراسیون برای گزارش احتمال تجربی کافی نیست."
        uncertainty_fa = "عدم‌قطعیت به‌دلیل داده کالیبراسیون ناکافی در سطح حداکثری نگه داشته شده است."
    else:
        raise PersianExplainabilityError("unsupported uncertainty state")

    tp_stop_fa: str | None
    if outcomes.state == "CALIBRATED_TP_STOP":
        if outcomes.tp_first_probability_bps is None or outcomes.stop_first_probability_bps is None or outcomes.neither_probability_bps is None:
            raise PersianExplainabilityError("calibrated TP/Stop state requires all outcome probabilities")
        tp_stop_fa = (
            f"در تعریف فعلی حد سود/حد ضرر: رسیدن اول به حد سود {_percent_fa(outcomes.tp_first_probability_bps)}، "
            f"رسیدن اول به حد ضرر {_percent_fa(outcomes.stop_first_probability_bps)}، "
            f"و هیچ‌کدام در افق ارزیابی {_percent_fa(outcomes.neither_probability_bps)}."
        )
    elif outcomes.state == "INSUFFICIENT_TP_STOP_DATA":
        tp_stop_fa = "داده تاریخی برای گزارش احتمال حد سود/حد ضرر کافی نیست."
    elif outcomes.state == "INSUFFICIENT_UPSTREAM_CALIBRATION":
        tp_stop_fa = "به‌دلیل ناکافی بودن کالیبراسیون بالادستی، احتمال حد سود/حد ضرر گزارش نمی‌شود."
    else:
        raise PersianExplainabilityError("unsupported TP/Stop state")

    return PersianSignalExplanation(
        subject_id=subject,
        as_of_time_ns=fusion.as_of_time_ns,
        fusion_id=fusion.fusion_id,
        fusion_state=fusion.state,
        fusion_direction=fusion.direction,
        qualification_id=uncertainty.qualification_id,
        tp_stop_prediction_id=outcomes.prediction_id,
        summary_fa=summary,
        supporting_factors_fa=supporting,
        opposing_factors_fa=opposing,
        neutral_factors_fa=neutral,
        veto_factors_fa=veto,
        probability_fa=probability_fa,
        uncertainty_fa=uncertainty_fa,
        tp_stop_fa=tp_stop_fa,
        evidence_quality_fa=evidence_quality,
        empirical_probability_bps=uncertainty.empirical_probability_bps,
        overall_uncertainty_bps=uncertainty.overall_uncertainty_bps,
        tp_first_probability_bps=outcomes.tp_first_probability_bps,
        stop_first_probability_bps=outcomes.stop_first_probability_bps,
        neither_probability_bps=outcomes.neither_probability_bps,
    )
