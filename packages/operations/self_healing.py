from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast

from .diagnostics import DiagnosticReport
from .system_state import SystemState


HealingDecisionStatus = Literal["ELIGIBLE_REFERENCE_PLAN", "BLOCKED"]


class SelfHealingError(ValueError):
    """P22-D constrained self-healing invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class HealingRule:
    action: str
    rollback_action: str
    max_attempts: int
    cooldown_required: bool
    post_action_validation_required: bool


@dataclass(frozen=True, slots=True)
class SelfHealingPolicy:
    eligible_system_states: tuple[SystemState, ...]
    allowed_diagnostic_status: tuple[str, ...]
    allowed_severity: tuple[str, ...]
    preapproved_actions: Mapping[str, HealingRule]

    @classmethod
    def from_path(cls, path: Path) -> "SelfHealingPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SelfHealingError(f"invalid P22-D policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise SelfHealingError("P22-D policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22D_CONSTRAINED_SELF_HEALING_POLICY",
            "task_id": "FIN-P22-WD-001",
            "mode": "DETERMINISTIC_REFERENCE_CONSTRAINED_SELF_HEALING",
            "eligible_system_states": ["NORMAL", "DEGRADED"],
            "allowed_diagnostic_status": ["MATCHED_RULE"],
            "allowed_severity": ["WARNING"],
            "blocked_if_operator_review_required": True,
            "preapproved_actions": {
                "DATA_FRESHNESS_DEGRADATION": {
                    "action": "RESTART_STATELESS_OBSERVER",
                    "rollback_action": "STOP_REPLACEMENT_OBSERVER",
                    "max_attempts": 1,
                    "cooldown_required": True,
                    "post_action_validation_required": True,
                }
            },
            "execution_mode": "REFERENCE_PLAN_ONLY",
            "execution_authority": False,
            "external_side_effects": False,
            "automatic_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise SelfHealingError(f"P22-D policy mismatch: {key}")

        rules: dict[str, HealingRule] = {
            "DATA_FRESHNESS_DEGRADATION": HealingRule(
                action="RESTART_STATELESS_OBSERVER",
                rollback_action="STOP_REPLACEMENT_OBSERVER",
                max_attempts=1,
                cooldown_required=True,
                post_action_validation_required=True,
            )
        }
        return cls(
            eligible_system_states=("NORMAL", "DEGRADED"),
            allowed_diagnostic_status=("MATCHED_RULE",),
            allowed_severity=("WARNING",),
            preapproved_actions=rules,
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "eligible_system_states": self.eligible_system_states,
            "allowed_diagnostic_status": self.allowed_diagnostic_status,
            "allowed_severity": self.allowed_severity,
            "blocked_if_operator_review_required": True,
            "preapproved_actions": {
                key: {
                    "action": rule.action,
                    "rollback_action": rule.rollback_action,
                    "max_attempts": rule.max_attempts,
                    "cooldown_required": rule.cooldown_required,
                    "post_action_validation_required": rule.post_action_validation_required,
                }
                for key, rule in sorted(self.preapproved_actions.items())
            },
            "execution_mode": "REFERENCE_PLAN_ONLY",
            "execution_authority": False,
            "external_side_effects": False,
            "automatic_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class HealingDecision:
    decision_id: str
    policy_id: str
    diagnostic_report_id: str
    system_state: SystemState
    status: HealingDecisionStatus
    reason_code: str
    action: str | None
    rollback_action: str | None
    attempt_number: int
    cooldown_elapsed: bool
    post_action_validation_required: bool
    execution_authority: bool
    external_side_effects: bool
    automatic_state_mutation: bool
    automatic_risk_policy_relaxation: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "diagnostic_report_id": self.diagnostic_report_id,
            "system_state": self.system_state,
            "status": self.status,
            "reason_code": self.reason_code,
            "action": self.action,
            "rollback_action": self.rollback_action,
            "attempt_number": self.attempt_number,
            "cooldown_elapsed": self.cooldown_elapsed,
            "post_action_validation_required": self.post_action_validation_required,
            "execution_authority": self.execution_authority,
            "external_side_effects": self.external_side_effects,
            "automatic_state_mutation": self.automatic_state_mutation,
            "automatic_risk_policy_relaxation": self.automatic_risk_policy_relaxation,
        }


def _decision(
    policy: SelfHealingPolicy,
    report: DiagnosticReport,
    *,
    status: HealingDecisionStatus,
    reason_code: str,
    action: str | None,
    rollback_action: str | None,
    attempt_number: int,
    cooldown_elapsed: bool,
    post_action_validation_required: bool,
) -> HealingDecision:
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "diagnostic_report_id": report.report_id,
        "system_state": report.system_state,
        "status": status,
        "reason_code": reason_code,
        "action": action,
        "rollback_action": rollback_action,
        "attempt_number": attempt_number,
        "cooldown_elapsed": cooldown_elapsed,
        "post_action_validation_required": post_action_validation_required,
        "execution_authority": False,
        "external_side_effects": False,
        "automatic_state_mutation": False,
        "automatic_risk_policy_relaxation": False,
    }
    decision_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return HealingDecision(
        decision_id=decision_id,
        policy_id=policy.policy_id,
        diagnostic_report_id=report.report_id,
        system_state=report.system_state,
        status=status,
        reason_code=reason_code,
        action=action,
        rollback_action=rollback_action,
        attempt_number=attempt_number,
        cooldown_elapsed=cooldown_elapsed,
        post_action_validation_required=post_action_validation_required,
        execution_authority=False,
        external_side_effects=False,
        automatic_state_mutation=False,
        automatic_risk_policy_relaxation=False,
    )


def plan_self_healing(
    policy: SelfHealingPolicy,
    *,
    report: DiagnosticReport,
    attempt_number: int,
    cooldown_elapsed: bool,
) -> HealingDecision:
    if isinstance(attempt_number, bool) or attempt_number < 1:
        raise SelfHealingError("attempt_number must be a positive integer")
    if report.remediation_authority:
        raise SelfHealingError("P22-C diagnostic reports must not carry remediation authority")

    rule = policy.preapproved_actions.get(report.hypothesis_code)

    if report.status not in policy.allowed_diagnostic_status:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="DIAGNOSTIC_STATUS_NOT_ELIGIBLE",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )
    if report.operator_review_required:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="OPERATOR_REVIEW_REQUIRED",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )
    if report.system_state not in policy.eligible_system_states:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="SYSTEM_STATE_NOT_ELIGIBLE",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )
    if report.severity not in policy.allowed_severity:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="SEVERITY_NOT_ELIGIBLE",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )
    if rule is None:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="NO_PREAPPROVED_ACTION",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )
    if attempt_number > rule.max_attempts:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="ATTEMPT_BUDGET_EXHAUSTED",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )
    if rule.cooldown_required and not cooldown_elapsed:
        return _decision(
            policy,
            report,
            status="BLOCKED",
            reason_code="COOLDOWN_NOT_ELAPSED",
            action=None,
            rollback_action=None,
            attempt_number=attempt_number,
            cooldown_elapsed=cooldown_elapsed,
            post_action_validation_required=False,
        )

    return _decision(
        policy,
        report,
        status="ELIGIBLE_REFERENCE_PLAN",
        reason_code="PREAPPROVED_RECOVERABLE_ACTION",
        action=rule.action,
        rollback_action=rule.rollback_action,
        attempt_number=attempt_number,
        cooldown_elapsed=cooldown_elapsed,
        post_action_validation_required=rule.post_action_validation_required,
    )
