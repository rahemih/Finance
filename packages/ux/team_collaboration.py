from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class TeamCollaborationError(ValueError):
    """P23-E team-collaboration invariant failure."""


EXPECTED_EVENT_TYPES = (
    "COMMENT_CREATED",
    "MENTION_ADDED",
    "ASSIGNMENT_SET",
    "ASSIGNMENT_CLEARED",
    "WORKFLOW_APPROVAL_REQUESTED",
    "WORKFLOW_APPROVAL_DECIDED",
    "WORKFLOW_APPROVAL_WITHDRAWN",
)
EXPECTED_APPROVAL_STATES = ("REQUESTED", "APPROVED", "REJECTED", "WITHDRAWN")
EXPECTED_REQUIRED_FIELDS = (
    "event_type",
    "actor_id",
    "target_kind",
    "target_id",
    "occurred_at",
    "provenance_ref",
)
EXPECTED_TARGET_KINDS = (
    "SURFACE",
    "OPPORTUNITY",
    "TRADE_RECORD",
    "PORTFOLIO_VIEW",
    "DEMO_RECORD",
    "RESEARCH_RECORD",
    "REPORT",
    "INCIDENT",
    "SETTINGS_CHANGE_REQUEST",
)
EXPECTED_SURFACES = (
    "dashboard",
    "markets",
    "opportunities",
    "trades",
    "portfolio",
    "demo",
    "research",
    "reports",
    "system",
    "settings",
    "glossary",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TeamCollaborationError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise TeamCollaborationError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TeamCollaborationError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TeamCollaborationError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class CollaborationPolicy:
    event_types: tuple[str, ...]
    approval_states: tuple[str, ...]
    required_event_fields: tuple[str, ...]
    target_kinds: tuple[str, ...]
    canonical_surfaces: tuple[str, ...]
    safety: dict[str, object]

    @classmethod
    def from_path(cls, path: Path) -> "CollaborationPolicy":
        try:
            value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TeamCollaborationError(f"invalid P23-E JSON: {exc}") from exc
        raw = _object(value, field="root")
        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23E_TEAM_COLLABORATION",
            "task_id": "FIN-P23-WE-001",
            "phase": "P23",
            "workstream": "P23-E",
            "authority": "COLLABORATION_METADATA_ONLY",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise TeamCollaborationError(f"P23-E policy mismatch: {key}")

        event_types = tuple(
            _text(item, field="event_types[]")
            for item in _list(raw.get("event_types"), field="event_types")
        )
        if event_types != EXPECTED_EVENT_TYPES:
            raise TeamCollaborationError("event type order/coverage drift")

        approval = _object(raw.get("approval"), field="approval")
        if approval.get("scope") != "TEAM_WORKFLOW_ONLY":
            raise TeamCollaborationError("approval scope drift")
        approval_states = tuple(
            _text(item, field="approval.states[]")
            for item in _list(approval.get("states"), field="approval.states")
        )
        if approval_states != EXPECTED_APPROVAL_STATES:
            raise TeamCollaborationError("approval state order/coverage drift")
        for flag in (
            "grants_owner_authorization",
            "grants_risk_approval",
            "grants_execution_approval",
            "grants_p24_production_approval",
        ):
            if approval.get(flag) is not False:
                raise TeamCollaborationError(f"forbidden workflow approval authority: {flag}")

        assignment = _object(raw.get("assignment"), field="assignment")
        for flag in (
            "grants_permissions",
            "changes_rbac",
            "changes_execution_authority",
        ):
            if assignment.get(flag) is not False:
                raise TeamCollaborationError(f"forbidden assignment authority: {flag}")

        required = tuple(
            _text(item, field="required_event_fields[]")
            for item in _list(
                raw.get("required_event_fields"), field="required_event_fields"
            )
        )
        if required != EXPECTED_REQUIRED_FIELDS:
            raise TeamCollaborationError("required event field drift")

        targets = tuple(
            _text(item, field="target_kinds[]")
            for item in _list(raw.get("target_kinds"), field="target_kinds")
        )
        if targets != EXPECTED_TARGET_KINDS:
            raise TeamCollaborationError("target kind order/coverage drift")

        surfaces = tuple(
            _text(item, field="canonical_surfaces[]")
            for item in _list(
                raw.get("canonical_surfaces"), field="canonical_surfaces"
            )
        )
        if surfaces != EXPECTED_SURFACES:
            raise TeamCollaborationError("canonical surface order/coverage drift")

        audit = _object(raw.get("audit"), field="audit")
        if audit != {
            "append_only": True,
            "deterministic_event_id": True,
            "ordered_history": True,
            "deletion_mode": "TOMBSTONE_EVENT_ONLY",
        }:
            raise TeamCollaborationError("audit policy drift")

        safety = _object(raw.get("safety"), field="safety")
        expected_safety: dict[str, object] = {
            "credential_access": False,
            "permission_mutation": False,
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "remediation_authority": False,
            "production_activation": False,
            "p24_state": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        if safety != expected_safety:
            raise TeamCollaborationError("P23-E safety boundary drift")

        return cls(
            event_types=event_types,
            approval_states=approval_states,
            required_event_fields=required,
            target_kinds=targets,
            canonical_surfaces=surfaces,
            safety=safety,
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "event_types": list(self.event_types),
            "approval_states": list(self.approval_states),
            "required_event_fields": list(self.required_event_fields),
            "target_kinds": list(self.target_kinds),
            "canonical_surfaces": list(self.canonical_surfaces),
            "safety": self.safety,
        }

    def event_id(self, event: dict[str, str]) -> str:
        if tuple(event) != self.required_event_fields:
            raise TeamCollaborationError("event fields/order must match canonical contract")
        for field in self.required_event_fields:
            _text(event.get(field), field=f"event.{field}")
        if event["event_type"] not in self.event_types:
            raise TeamCollaborationError("unknown collaboration event type")
        if event["target_kind"] not in self.target_kinds:
            raise TeamCollaborationError("unknown collaboration target kind")
        return hashlib.sha256(_canonical_bytes(event)).hexdigest()
