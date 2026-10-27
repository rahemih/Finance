from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class ProductionReadinessError(ValueError):
    """P24-A fail-closed production readiness validation failure."""


EXPECTED_GATES = (
    "G0_GOVERNANCE_READY",
    "G1_PROVIDER_BASELINE",
    "G2_ARCHITECTURE_FREEZE",
    "G3_SECURITY_BASELINE",
    "G4_REALTIME_DATA",
    "G5_TRUSTED_DATA",
    "G6_TECHNICAL_VALIDATED",
    "G7_SIGNAL_VALIDATED",
    "G8_PRETRADE_SAFE",
    "G9_QUANT_VALIDATED",
    "G10_SHADOW_VALIDATED",
    "G11_EXECUTION_VALIDATED",
    "G12_OPERATIONS_VALIDATED",
)

PRE_FIRST_LIVE_PREREQUISITES = (
    "OWNER_JURISDICTION_RESOLVED",
    "PRODUCTION_PROVIDER_SELECTED",
    "PRODUCTION_VENUE_SELECTED",
    "PRODUCTION_CREDENTIALS_READY",
    "PRODUCTION_BROKER_CERTIFIED",
    "UPSTREAM_GATE_FRESHNESS_FOR_LIVE",
    "PRODUCTION_SECURITY_POSTURE_VERIFIED",
    "PRODUCTION_RISK_BUDGET_DEFINED",
    "PRE_LIVE_KILL_SWITCH_VALIDATED",
)

FIRST_LIVE_OWNER_GATE = "FIRST_LIVE_OWNER_APPROVAL"

P24_EXIT_PREREQUISITES = (
    "LIVE_EXECUTION_VALIDATED",
    "P24_G_KILL_SWITCH_DRILLS_COMPLETE",
    "G13_OWNER_LIVE_APPROVAL",
)

EXPECTED_PREREQUISITES = (
    *PRE_FIRST_LIVE_PREREQUISITES,
    FIRST_LIVE_OWNER_GATE,
    *P24_EXIT_PREREQUISITES,
)

EXPECTED_STAGE_BY_ID = {
    **{item: "PRE_FIRST_LIVE" for item in PRE_FIRST_LIVE_PREREQUISITES},
    FIRST_LIVE_OWNER_GATE: "FIRST_LIVE_OWNER_GATE",
    **{item: "P24_EXIT" for item in P24_EXIT_PREREQUISITES},
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ProductionReadinessError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise ProductionReadinessError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ProductionReadinessError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ProductionReadinessError(f"{field} must be text")
    if not allow_empty and not value.strip():
        raise ProductionReadinessError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class ProductionPrerequisite:
    prerequisite_id: str
    stage: str
    satisfied: bool
    marker: str


@dataclass(frozen=True, slots=True)
class ProductionReadinessDossier:
    gates: tuple[str, ...]
    prerequisites: tuple[ProductionPrerequisite, ...]
    verdict: str
    blocker_ids: tuple[str, ...]
    pre_first_live_blocker_ids: tuple[str, ...]
    first_live_owner_gate_pending: bool
    p24_exit_blocker_ids: tuple[str, ...]
    p24_b_state: str
    safety: dict[str, object]

    @classmethod
    def from_root(cls, policy_path: Path, root: Path) -> "ProductionReadinessDossier":
        try:
            value: object = json.loads(policy_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProductionReadinessError(f"invalid P24-A policy JSON: {exc}") from exc
        policy = _object(value, field="root")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P24A_PRODUCTION_READINESS_DOSSIER",
            "task_id": "FIN-P24-WA-001",
            "phase": "P24",
            "workstream": "P24-A",
            "claim_scope": "READINESS_ASSESSMENT_ONLY",
            "canonical_state_path": "docs/02-current-state/CURRENT-STATE.md",
        }
        for key, expected in expected_static.items():
            if policy.get(key) != expected:
                raise ProductionReadinessError(f"P24-A policy mismatch: {key}")

        phase_auth = _object(policy.get("phase_authorization"), field="phase_authorization")
        expected_phase_auth: dict[str, object] = {
            "p24_phase_start": "GRANTED_CONSUMED",
            "first_live_activation": "NOT_GRANTED",
            "grants_g13": False,
        }
        if phase_auth != expected_phase_auth:
            raise ProductionReadinessError("phase authorization boundary drift")

        state_path = root / "docs/02-current-state/CURRENT-STATE.md"
        try:
            state_text = state_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise ProductionReadinessError(f"cannot read canonical state: {exc}") from exc

        gate_items = _list(policy.get("required_upstream_gates"), field="required_upstream_gates")
        observed_gates: list[str] = []
        for index, value in enumerate(gate_items):
            item = _object(value, field=f"required_upstream_gates[{index}]")
            gate = _text(item.get("gate"), field=f"gate[{index}].gate")
            marker = _text(item.get("marker"), field=f"gate[{index}].marker")
            observed_gates.append(gate)
            if marker not in state_text:
                raise ProductionReadinessError(f"missing canonical gate marker: {gate}")
        if tuple(observed_gates) != EXPECTED_GATES:
            raise ProductionReadinessError("upstream gate order/coverage drift")

        p23 = _object(policy.get("p23_requirement"), field="p23_requirement")
        if p23.get("required") is not True:
            raise ProductionReadinessError("P23 requirement cannot be weakened")
        p23_marker = _text(p23.get("marker"), field="p23_requirement.marker")
        if p23_marker not in state_text:
            raise ProductionReadinessError("P23 canonical closure marker missing")

        prerequisite_items = _list(
            policy.get("production_prerequisites"), field="production_prerequisites"
        )
        prerequisites: list[ProductionPrerequisite] = []
        ids: list[str] = []
        for index, value in enumerate(prerequisite_items):
            item = _object(value, field=f"production_prerequisites[{index}]")
            prerequisite_id = _text(
                item.get("id"), field=f"production_prerequisites[{index}].id"
            )
            stage = _text(
                item.get("stage"), field=f"production_prerequisites[{index}].stage"
            )
            marker = _text(
                item.get("marker"),
                field=f"production_prerequisites[{index}].marker",
                allow_empty=True,
            )
            satisfied = item.get("satisfied")
            if not isinstance(satisfied, bool):
                raise ProductionReadinessError(
                    f"production_prerequisites[{index}].satisfied must be boolean"
                )
            expected_stage = EXPECTED_STAGE_BY_ID.get(prerequisite_id)
            if expected_stage is None or stage != expected_stage:
                raise ProductionReadinessError(
                    f"production prerequisite stage drift: {prerequisite_id}"
                )
            if satisfied and not marker:
                raise ProductionReadinessError(
                    f"satisfied prerequisite requires evidence marker: {prerequisite_id}"
                )
            if marker and marker not in state_text:
                raise ProductionReadinessError(
                    f"canonical prerequisite marker missing: {prerequisite_id}"
                )
            if prerequisite_id == "G13_OWNER_LIVE_APPROVAL" and satisfied:
                raise ProductionReadinessError("G13 cannot be satisfied by P24-A")
            ids.append(prerequisite_id)
            prerequisites.append(
                ProductionPrerequisite(
                    prerequisite_id=prerequisite_id,
                    stage=stage,
                    satisfied=satisfied,
                    marker=marker,
                )
            )
        if tuple(ids) != EXPECTED_PREREQUISITES:
            raise ProductionReadinessError("production prerequisite order/coverage drift")

        blocker_ids = tuple(
            item.prerequisite_id for item in prerequisites if not item.satisfied
        )
        pre_first_live_blocker_ids = tuple(
            item.prerequisite_id
            for item in prerequisites
            if item.stage == "PRE_FIRST_LIVE" and not item.satisfied
        )
        owner_gate = next(
            item for item in prerequisites if item.prerequisite_id == FIRST_LIVE_OWNER_GATE
        )
        first_live_owner_gate_pending = not owner_gate.satisfied
        p24_exit_blocker_ids = tuple(
            item.prerequisite_id
            for item in prerequisites
            if item.stage == "P24_EXIT" and not item.satisfied
        )

        if pre_first_live_blocker_ids:
            verdict = "NOT_READY_FOR_LIVE"
            p24_b_state = "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES"
        elif first_live_owner_gate_pending:
            verdict = "READY_FOR_FIRST_LIVE_OWNER_GATE"
            p24_b_state = "FIRST_LIVE_OWNER_HUMAN_GATE_REQUIRED"
        else:
            verdict = "READY_FOR_MANUAL_LIVE"
            p24_b_state = "READY_FOR_MANUAL_LIVE"

        if verdict != policy.get("expected_verdict"):
            raise ProductionReadinessError("readiness verdict drift")

        next_state = _object(policy.get("next"), field="next")
        expected_next: dict[str, object] = {
            "p24_b": p24_b_state,
            "g13": "NOT_STARTED",
        }
        if next_state != expected_next:
            raise ProductionReadinessError("next-state boundary drift")

        safety = _object(policy.get("safety"), field="safety")
        expected_safety: dict[str, object] = {
            "credential_access": False,
            "network_mutation": False,
            "permission_mutation": False,
            "execution_authority_mutation": False,
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "remediation_authority": False,
            "production_activation": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        if safety != expected_safety:
            raise ProductionReadinessError("P24-A safety boundary drift")

        return cls(
            gates=tuple(observed_gates),
            prerequisites=tuple(prerequisites),
            verdict=verdict,
            blocker_ids=blocker_ids,
            pre_first_live_blocker_ids=pre_first_live_blocker_ids,
            first_live_owner_gate_pending=first_live_owner_gate_pending,
            p24_exit_blocker_ids=p24_exit_blocker_ids,
            p24_b_state=p24_b_state,
            safety=safety,
        )

    @property
    def dossier_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "gates": list(self.gates),
            "prerequisites": [
                {
                    "id": item.prerequisite_id,
                    "stage": item.stage,
                    "satisfied": item.satisfied,
                    "marker": item.marker,
                }
                for item in self.prerequisites
            ],
            "verdict": self.verdict,
            "blocker_ids": list(self.blocker_ids),
            "pre_first_live_blocker_ids": list(self.pre_first_live_blocker_ids),
            "first_live_owner_gate_pending": self.first_live_owner_gate_pending,
            "p24_exit_blocker_ids": list(self.p24_exit_blocker_ids),
            "p24_b_state": self.p24_b_state,
            "safety": self.safety,
        }
