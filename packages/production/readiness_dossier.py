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

EXPECTED_PREREQUISITES = (
    "OWNER_JURISDICTION_RESOLVED",
    "PRODUCTION_PROVIDER_SELECTED",
    "PRODUCTION_VENUE_SELECTED",
    "PRODUCTION_CREDENTIALS_READY",
    "PRODUCTION_BROKER_CERTIFIED",
    "LIVE_EXECUTION_VALIDATED",
    "PRODUCTION_READINESS_CERTIFIED",
    "UPSTREAM_GATE_FRESHNESS_FOR_LIVE",
    "PRODUCTION_SECURITY_POSTURE_VERIFIED",
    "PRODUCTION_RISK_BUDGET_DEFINED",
    "FIRST_LIVE_OWNER_APPROVAL",
    "LIVE_KILL_SWITCH_DRILL",
    "G13_OWNER_LIVE_APPROVAL",
)


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
    satisfied: bool
    marker: str


@dataclass(frozen=True, slots=True)
class ProductionReadinessDossier:
    gates: tuple[str, ...]
    prerequisites: tuple[ProductionPrerequisite, ...]
    verdict: str
    blocker_ids: tuple[str, ...]
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
            "expected_verdict": "NOT_READY_FOR_LIVE",
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
            if marker and marker not in state_text:
                raise ProductionReadinessError(
                    f"canonical blocker marker missing: {prerequisite_id}"
                )
            ids.append(prerequisite_id)
            prerequisites.append(
                ProductionPrerequisite(
                    prerequisite_id=prerequisite_id,
                    satisfied=satisfied,
                    marker=marker,
                )
            )
        if tuple(ids) != EXPECTED_PREREQUISITES:
            raise ProductionReadinessError("production prerequisite order/coverage drift")

        blocker_ids = tuple(
            item.prerequisite_id for item in prerequisites if not item.satisfied
        )
        verdict = "READY_FOR_FIRST_LIVE_GATE" if not blocker_ids else "NOT_READY_FOR_LIVE"
        if verdict != policy.get("expected_verdict"):
            raise ProductionReadinessError("readiness verdict drift")

        next_state = _object(policy.get("next"), field="next")
        expected_next: dict[str, object] = {
            "p24_b": "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES",
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
                    "satisfied": item.satisfied,
                    "marker": item.marker,
                }
                for item in self.prerequisites
            ],
            "verdict": self.verdict,
            "blocker_ids": list(self.blocker_ids),
            "safety": self.safety,
        }
