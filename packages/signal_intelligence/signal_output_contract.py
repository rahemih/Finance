from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate

from .persian_explainability import PersianSignalExplanation
from .probability_uncertainty import ProbabilityUncertaintyQualification
from .red_team_challenge import RedTeamChallenge
from .tp_stop_probability import BarrierPlanContext, TPStopOutcomeProbability
from .weighted_fusion import WeightedFusionResult


class SignalOutputContractError(ValueError):
    """P14-H analytical signal-output invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SignalOutputContractError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SignalOutputContractError(f"{field} must be positive integer")
    return value


def _sha256_text(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise SignalOutputContractError(f"{field} must be SHA-256 text")
    parsed = value.strip().lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise SignalOutputContractError(f"{field} must be lowercase SHA-256")
    return parsed


@dataclass(frozen=True, slots=True)
class SignalOutputPolicy:
    actions: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "SignalOutputPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_ANALYTICAL_SIGNAL_OUTPUT":
            raise SignalOutputContractError("unsupported P14-H policy")
        if raw.get("actions") != ["LONG", "SHORT", "WAIT", "NO_TRADE"]:
            raise SignalOutputContractError("invalid signal action taxonomy")
        expected = {
            "timing_active_state": "ACTIVE",
            "timing_block_state": "BLOCKED_BY_NO_TRADE",
            "no_trade_decision": "NO_TRADE",
            "eligible_decision": "TIMING_ELIGIBLE",
            "challenge_directional_requirement": "CLEAR",
            "challenge_wait_disposition": "CAUTION",
            "challenge_block_disposition": "REJECT",
            "insufficient_state_action": "WAIT",
            "price_representation": "SCALED_POSITIVE_INTEGER",
            "price_rounding": "NEAREST_HALF_UP_BPS",
        }
        if any(raw.get(k) != v for k, v in expected.items()):
            raise SignalOutputContractError("P14-H policy semantics mismatch")
        if raw.get("timing_wait_states") != ["EXPIRED", "NO_CHASE"]:
            raise SignalOutputContractError("timing wait states mismatch")
        if raw.get("directional_geometry_required") is not True or raw.get("non_directional_geometry_forbidden") is not True:
            raise SignalOutputContractError("geometry boundary mismatch")
        if raw.get("preserve_upstream_values") is not True or raw.get("probability_mutation_allowed") is not False:
            raise SignalOutputContractError("upstream value preservation required")
        forbidden = ("risk_approval_in_scope", "position_sizing_in_scope", "leverage_in_scope", "execution_authority_in_scope", "canonical_tests_network_required")
        if any(raw.get(field) is not False for field in forbidden):
            raise SignalOutputContractError("P14-H cannot enable downstream authority")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise SignalOutputContractError("P14-H cannot enable trading")
        return cls(actions=("LONG", "SHORT", "WAIT", "NO_TRADE"), live_trading="DISABLED", auto_trading="DISABLED")


@dataclass(frozen=True, slots=True)
class CandidatePriceGeometry:
    price_scale: int
    reference_price_scaled: int
    entry_low_scaled: int
    entry_high_scaled: int
    entry_anchor_scaled: int
    invalidation_price_scaled: int
    geometry_version_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "price_scale", _positive_int(self.price_scale, field="price_scale"))
        for field in ("reference_price_scaled", "entry_low_scaled", "entry_high_scaled", "entry_anchor_scaled", "invalidation_price_scaled"):
            object.__setattr__(self, field, _positive_int(getattr(self, field), field=field))
        if self.entry_low_scaled > self.entry_high_scaled:
            raise SignalOutputContractError("entry zone low cannot exceed high")
        if not self.entry_low_scaled <= self.entry_anchor_scaled <= self.entry_high_scaled:
            raise SignalOutputContractError("entry anchor must be inside entry zone")
        object.__setattr__(self, "geometry_version_sha256", _sha256_text(self.geometry_version_sha256, field="geometry_version_sha256"))

    def payload(self) -> dict[str, object]:
        return {
            "price_scale": self.price_scale,
            "reference_price_scaled": self.reference_price_scaled,
            "entry_low_scaled": self.entry_low_scaled,
            "entry_high_scaled": self.entry_high_scaled,
            "entry_anchor_scaled": self.entry_anchor_scaled,
            "invalidation_price_scaled": self.invalidation_price_scaled,
            "geometry_version_sha256": self.geometry_version_sha256,
        }


@dataclass(frozen=True, slots=True)
class AnalyticalSignalOutput:
    candidate_id: str
    asset_id: str
    strategy_id: str
    timeframe: str
    regime_label: str
    as_of_time_ns: int
    action: str
    action_reason_codes: tuple[str, ...]
    fusion_id: str
    qualification_id: str | None
    tp_stop_prediction_id: str | None
    explanation_id: str
    challenge_id: str
    empirical_probability_bps: int | None
    overall_uncertainty_bps: int | None
    tp_first_probability_bps: int | None
    stop_first_probability_bps: int | None
    neither_probability_bps: int | None
    entry_low_scaled: int | None
    entry_high_scaled: int | None
    invalidation_price_scaled: int | None
    candidate_stop_scaled: int | None
    candidate_target_scaled: int | None
    price_scale: int | None
    geometry_version_sha256: str | None
    evidence_freshness_exclusions: tuple[str, ...]
    reasons_for: tuple[str, ...]
    reasons_against: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "candidate_id": self.candidate_id,
            "asset_id": self.asset_id,
            "strategy_id": self.strategy_id,
            "timeframe": self.timeframe,
            "regime_label": self.regime_label,
            "as_of_time_ns": self.as_of_time_ns,
            "action": self.action,
            "action_reason_codes": list(self.action_reason_codes),
            "fusion_id": self.fusion_id,
            "qualification_id": self.qualification_id,
            "tp_stop_prediction_id": self.tp_stop_prediction_id,
            "explanation_id": self.explanation_id,
            "challenge_id": self.challenge_id,
            "empirical_probability_bps": self.empirical_probability_bps,
            "overall_uncertainty_bps": self.overall_uncertainty_bps,
            "tp_first_probability_bps": self.tp_first_probability_bps,
            "stop_first_probability_bps": self.stop_first_probability_bps,
            "neither_probability_bps": self.neither_probability_bps,
            "entry_low_scaled": self.entry_low_scaled,
            "entry_high_scaled": self.entry_high_scaled,
            "invalidation_price_scaled": self.invalidation_price_scaled,
            "candidate_stop_scaled": self.candidate_stop_scaled,
            "candidate_target_scaled": self.candidate_target_scaled,
            "price_scale": self.price_scale,
            "geometry_version_sha256": self.geometry_version_sha256,
            "evidence_freshness_exclusions": list(self.evidence_freshness_exclusions),
            "reasons_for": list(self.reasons_for),
            "reasons_against": list(self.reasons_against),
            "risk_approval": None,
            "position_size": None,
            "leverage": None,
            "execution_command": None,
        }

    @property
    def signal_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _price_delta(anchor: int, distance_bps: int) -> int:
    return (anchor * distance_bps + 5_000) // 10_000


def _directional_prices(
    *, geometry: CandidatePriceGeometry, barrier: BarrierPlanContext, direction: int
) -> tuple[int, int]:
    target_delta = _price_delta(geometry.entry_anchor_scaled, barrier.target_distance_bps)
    stop_delta = _price_delta(geometry.entry_anchor_scaled, barrier.stop_distance_bps)
    if target_delta <= 0 or stop_delta <= 0:
        raise SignalOutputContractError("TP/Stop distance rounds to zero")
    if direction == 1:
        target = geometry.entry_anchor_scaled + target_delta
        stop = geometry.entry_anchor_scaled - stop_delta
        if stop <= 0 or geometry.invalidation_price_scaled >= geometry.entry_low_scaled:
            raise SignalOutputContractError("LONG geometry is directionally incoherent")
        if target <= geometry.entry_high_scaled:
            raise SignalOutputContractError("LONG target must be above entry zone")
    elif direction == -1:
        target = geometry.entry_anchor_scaled - target_delta
        stop = geometry.entry_anchor_scaled + stop_delta
        if target <= 0 or geometry.invalidation_price_scaled <= geometry.entry_high_scaled:
            raise SignalOutputContractError("SHORT geometry is directionally incoherent")
        if target >= geometry.entry_low_scaled:
            raise SignalOutputContractError("SHORT target must be below entry zone")
    else:
        raise SignalOutputContractError("directional signal requires -1 or +1")
    return stop, target


def build_signal_output(
    *,
    policy: SignalOutputPolicy,
    candidate: OpportunityCandidate,
    no_trade: NoTradeDecision,
    expiry: ExpiryNoChaseAssessment,
    fusion: WeightedFusionResult,
    uncertainty: ProbabilityUncertaintyQualification | None,
    barrier: BarrierPlanContext | None,
    outcomes: TPStopOutcomeProbability | None,
    explanation: PersianSignalExplanation,
    challenge: RedTeamChallenge,
    geometry: CandidatePriceGeometry | None,
) -> AnalyticalSignalOutput:
    if candidate.candidate_id != no_trade.candidate_id or candidate.candidate_id != expiry.candidate_id:
        raise SignalOutputContractError("P13 candidate identity mismatch")
    if candidate.asset_id != fusion.subject_id or candidate.asset_id != explanation.subject_id or candidate.asset_id != challenge.subject_id:
        raise SignalOutputContractError("asset/subject mismatch")
    if explanation.fusion_id != fusion.fusion_id or challenge.fusion_id != fusion.fusion_id:
        raise SignalOutputContractError("fusion lineage mismatch")
    if challenge.explanation_id != explanation.explanation_id:
        raise SignalOutputContractError("explanation/challenge lineage mismatch")

    if no_trade.decision not in ("NO_TRADE", "TIMING_ELIGIBLE"):
        raise SignalOutputContractError("unsupported P13 no-trade decision")
    if expiry.state not in ("ACTIVE", "BLOCKED_BY_NO_TRADE", "EXPIRED", "NO_CHASE"):
        raise SignalOutputContractError("unsupported P13 expiry/no-chase state")

    hard_block = (
        no_trade.decision == "NO_TRADE"
        or expiry.state == "BLOCKED_BY_NO_TRADE"
        or fusion.state == "BLOCKED"
        or challenge.disposition == "REJECT"
    )
    timing_wait = expiry.state in ("EXPIRED", "NO_CHASE") or not candidate.eligible
    insufficient = fusion.state != "FUSED"

    qualification_id: str | None = None
    tp_stop_prediction_id: str | None = None
    empirical_probability: int | None = None
    overall_uncertainty: int | None = None
    tp_probability: int | None = None
    stop_probability: int | None = None
    neither_probability: int | None = None

    if fusion.state == "FUSED":
        if uncertainty is None or barrier is None or outcomes is None:
            raise SignalOutputContractError("FUSED signal requires P14-D/P14-E context")
        if barrier.subject_id != candidate.asset_id or barrier.strategy_id != candidate.strategy_id or barrier.timeframe != candidate.timeframe or barrier.regime_label != candidate.regime_label:
            raise SignalOutputContractError("P14-E barrier context mismatch")
        if barrier.session_label not in candidate.session_labels:
            raise SignalOutputContractError("P14-E session is outside candidate session labels")
        if barrier.direction != fusion.direction:
            raise SignalOutputContractError("fusion/barrier direction mismatch")
        if outcomes.upstream_qualification_id != uncertainty.qualification_id:
            raise SignalOutputContractError("P14-D/P14-E lineage mismatch")
        if explanation.qualification_id != uncertainty.qualification_id or challenge.qualification_id != uncertainty.qualification_id:
            raise SignalOutputContractError("qualification lineage mismatch")
        if explanation.tp_stop_prediction_id != outcomes.prediction_id or challenge.tp_stop_prediction_id != outcomes.prediction_id:
            raise SignalOutputContractError("TP/Stop lineage mismatch")
        qualification_id = uncertainty.qualification_id
        tp_stop_prediction_id = outcomes.prediction_id
        empirical_probability = uncertainty.empirical_probability_bps
        overall_uncertainty = uncertainty.overall_uncertainty_bps
        tp_probability = outcomes.tp_first_probability_bps
        stop_probability = outcomes.stop_first_probability_bps
        neither_probability = outcomes.neither_probability_bps
        insufficient = uncertainty.state != "QUALIFIED" or outcomes.state != "CALIBRATED_TP_STOP"

    if hard_block:
        action = "NO_TRADE"
        reason_set: set[str] = set(no_trade.reason_codes)
        reason_set.update(item.code for item in challenge.findings if item.severity == "REJECT")
        reasons = tuple(sorted(reason_set))
    elif timing_wait or challenge.disposition == "CAUTION" or insufficient:
        action = "WAIT"
        reason_set = set()
        if expiry.state != "ACTIVE":
            reason_set.add(expiry.state)
        reason_set.update(item.code for item in challenge.findings)
        if not candidate.eligible:
            reason_set.add("CANDIDATE_NOT_ELIGIBLE")
        if insufficient:
            reason_set.add("INSUFFICIENT_ANALYTICAL_STATE")
        reasons = tuple(sorted(reason_set))
    else:
        if no_trade.decision != "TIMING_ELIGIBLE" or expiry.state != "ACTIVE" or challenge.disposition != "CLEAR":
            raise SignalOutputContractError("directional signal prerequisites are not canonical")
        if fusion.direction == 1:
            action = "LONG"
        elif fusion.direction == -1:
            action = "SHORT"
        else:
            raise SignalOutputContractError("FUSED directional signal requires non-zero direction")
        reasons = ("ANALYTICAL_CHAIN_CLEAR",)

    if action in ("LONG", "SHORT"):
        if geometry is None or barrier is None:
            raise SignalOutputContractError("directional output requires explicit price geometry")
        stop, target = _directional_prices(geometry=geometry, barrier=barrier, direction=fusion.direction)
        entry_low = geometry.entry_low_scaled
        entry_high = geometry.entry_high_scaled
        invalidation = geometry.invalidation_price_scaled
        price_scale = geometry.price_scale
        geometry_version = geometry.geometry_version_sha256
    else:
        if geometry is not None:
            raise SignalOutputContractError("WAIT/NO_TRADE cannot carry directional price geometry")
        stop = target = entry_low = entry_high = invalidation = price_scale = None
        geometry_version = None

    reasons_for = tuple(sorted(explanation.supporting_factors_fa))
    reasons_against = tuple(sorted(explanation.opposing_factors_fa + explanation.veto_factors_fa + tuple(item.message_fa for item in challenge.findings)))
    freshness = tuple(sorted(fusion.excluded_expired_evidence_ids))

    return AnalyticalSignalOutput(
        candidate_id=candidate.candidate_id,
        asset_id=candidate.asset_id,
        strategy_id=candidate.strategy_id,
        timeframe=candidate.timeframe,
        regime_label=candidate.regime_label,
        as_of_time_ns=expiry.as_of_ns,
        action=action,
        action_reason_codes=reasons,
        fusion_id=fusion.fusion_id,
        qualification_id=qualification_id,
        tp_stop_prediction_id=tp_stop_prediction_id,
        explanation_id=explanation.explanation_id,
        challenge_id=challenge.challenge_id,
        empirical_probability_bps=empirical_probability,
        overall_uncertainty_bps=overall_uncertainty,
        tp_first_probability_bps=tp_probability,
        stop_first_probability_bps=stop_probability,
        neither_probability_bps=neither_probability,
        entry_low_scaled=entry_low,
        entry_high_scaled=entry_high,
        invalidation_price_scaled=invalidation,
        candidate_stop_scaled=stop,
        candidate_target_scaled=target,
        price_scale=price_scale,
        geometry_version_sha256=geometry_version,
        evidence_freshness_exclusions=freshness,
        reasons_for=reasons_for,
        reasons_against=reasons_against,
    )
