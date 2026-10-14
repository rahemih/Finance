from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.timing_opportunity.expiry_no_chase import ExpiryNoChaseAssessment
from packages.timing_opportunity.no_trade import NoTradeDecision
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate

from .persian_explainability import PersianSignalExplanation
from .probability_uncertainty import ProbabilityUncertaintyQualification
from .red_team_challenge import RedTeamChallenge
from .signal_output_contract import (
    AnalyticalSignalOutput,
    CandidatePriceGeometry,
    SignalOutputPolicy,
    build_signal_output,
)
from .tp_stop_probability import BarrierPlanContext, TPStopOutcomeProbability
from .weighted_fusion import WeightedFusionResult


class SignalValidationError(ValueError):
    """P14-I integrated signal-validation invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SignalValidationError(f"{field} must be object")
    return cast(Mapping[str, object], value)


@dataclass(frozen=True, slots=True)
class SignalValidationPolicy:
    gate_name: str
    required_action_coverage: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "SignalValidationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_SIGNAL_VALIDATION_GATE":
            raise SignalValidationError("unsupported P14-I policy")
        if raw.get("gate_name") != "G7_SIGNAL_VALIDATED":
            raise SignalValidationError("unexpected P14-I gate name")
        coverage = raw.get("required_action_coverage")
        if coverage != ["LONG", "SHORT", "WAIT", "NO_TRADE"]:
            raise SignalValidationError("required P14-I action coverage mismatch")
        required_true = (
            "exact_signal_id_match_required",
            "exact_payload_match_required",
            "directional_geometry_required",
            "non_directional_geometry_forbidden",
            "risk_authority_forbidden",
            "position_sizing_forbidden",
            "leverage_forbidden",
            "execution_authority_forbidden",
        )
        if any(raw.get(field) is not True for field in required_true):
            raise SignalValidationError("P14-I fail-closed requirements must remain enabled")
        if raw.get("duplicate_action_certificate_behavior") != "FAIL_CLOSED":
            raise SignalValidationError("duplicate action certificates must fail closed")
        if raw.get("missing_action_coverage_behavior") != "FAIL_CLOSED":
            raise SignalValidationError("missing action coverage must fail closed")
        if raw.get("canonical_tests_network_required") is not False:
            raise SignalValidationError("canonical P14-I tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise SignalValidationError("P14-I cannot enable trading")
        return cls(
            gate_name="G7_SIGNAL_VALIDATED",
            required_action_coverage=("LONG", "SHORT", "WAIT", "NO_TRADE"),
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class SignalValidationCertificate:
    signal_id: str
    action: str
    replay_signal_id: str
    validation_state: str
    checks: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "signal_id": self.signal_id,
            "action": self.action,
            "replay_signal_id": self.replay_signal_id,
            "validation_state": self.validation_state,
            "checks": list(self.checks),
        }

    @property
    def certificate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class SignalValidationGate:
    gate_name: str
    state: str
    action_coverage: tuple[str, ...]
    certificate_ids: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "gate_name": self.gate_name,
            "state": self.state,
            "action_coverage": list(self.action_coverage),
            "certificate_ids": list(self.certificate_ids),
            "p15_started": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }

    @property
    def gate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _validate_output_shape(signal: AnalyticalSignalOutput) -> tuple[str, ...]:
    payload = signal.payload()
    checks: list[str] = []
    if signal.action in ("LONG", "SHORT"):
        directional_fields = (
            signal.entry_low_scaled,
            signal.entry_high_scaled,
            signal.invalidation_price_scaled,
            signal.candidate_stop_scaled,
            signal.candidate_target_scaled,
            signal.price_scale,
            signal.geometry_version_sha256,
        )
        if any(value is None for value in directional_fields):
            raise SignalValidationError("directional signal is missing price geometry")
        checks.append("DIRECTIONAL_GEOMETRY_PRESENT")
    elif signal.action in ("WAIT", "NO_TRADE"):
        directional_fields = (
            signal.entry_low_scaled,
            signal.entry_high_scaled,
            signal.invalidation_price_scaled,
            signal.candidate_stop_scaled,
            signal.candidate_target_scaled,
            signal.price_scale,
            signal.geometry_version_sha256,
        )
        if any(value is not None for value in directional_fields):
            raise SignalValidationError("non-directional signal must not carry price geometry")
        checks.append("NON_DIRECTIONAL_GEOMETRY_ABSENT")
    else:
        raise SignalValidationError("unsupported analytical signal action")

    for key in ("risk_approval", "position_size", "leverage", "execution_command"):
        if payload.get(key) is not None:
            raise SignalValidationError(f"{key} must remain absent in P14")
    checks.append("DOWNSTREAM_AUTHORITY_ABSENT")
    return tuple(checks)


def validate_signal_output(
    *,
    validation_policy: SignalValidationPolicy,
    signal_policy: SignalOutputPolicy,
    expected: AnalyticalSignalOutput,
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
) -> SignalValidationCertificate:
    if validation_policy.live_trading != "DISABLED" or validation_policy.auto_trading != "DISABLED":
        raise SignalValidationError("P14-I cannot enable trading")
    shape_checks = _validate_output_shape(expected)
    replayed = build_signal_output(
        policy=signal_policy,
        candidate=candidate,
        no_trade=no_trade,
        expiry=expiry,
        fusion=fusion,
        uncertainty=uncertainty,
        barrier=barrier,
        outcomes=outcomes,
        explanation=explanation,
        challenge=challenge,
        geometry=geometry,
    )
    if replayed.signal_id != expected.signal_id:
        raise SignalValidationError("signal replay identity mismatch")
    if replayed.payload() != expected.payload():
        raise SignalValidationError("signal replay payload mismatch")
    checks = tuple(sorted(shape_checks + ("EXACT_SIGNAL_ID_MATCH", "EXACT_PAYLOAD_MATCH", "UPSTREAM_REPLAY_MATCH")))
    return SignalValidationCertificate(
        signal_id=expected.signal_id,
        action=expected.action,
        replay_signal_id=replayed.signal_id,
        validation_state="VALIDATED",
        checks=checks,
    )


def certify_g7_signal_gate(
    *,
    policy: SignalValidationPolicy,
    certificates: Sequence[SignalValidationCertificate],
) -> SignalValidationGate:
    records = tuple(certificates)
    if len(records) != len(policy.required_action_coverage):
        raise SignalValidationError("G7 requires exactly one certificate per required action")
    action_to_cert: dict[str, SignalValidationCertificate] = {}
    for certificate in records:
        if certificate.validation_state != "VALIDATED":
            raise SignalValidationError("G7 cannot accept non-validated certificate")
        if certificate.action not in policy.required_action_coverage:
            raise SignalValidationError("G7 received unsupported action certificate")
        if certificate.action in action_to_cert:
            raise SignalValidationError("duplicate action certificate")
        action_to_cert[certificate.action] = certificate
    if tuple(action for action in policy.required_action_coverage if action not in action_to_cert):
        raise SignalValidationError("G7 action coverage is incomplete")
    ordered = tuple(action_to_cert[action] for action in policy.required_action_coverage)
    return SignalValidationGate(
        gate_name=policy.gate_name,
        state="PASS",
        action_coverage=policy.required_action_coverage,
        certificate_ids=tuple(certificate.certificate_id for certificate in ordered),
    )
