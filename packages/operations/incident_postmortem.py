from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast


IncidentSeverity = Literal["SEV1", "SEV2", "SEV3", "SEV4"]
IncidentState = Literal["OPEN", "CONTAINED", "RECOVERED", "CLOSED"]
ActionPriority = Literal["P0", "P1", "P2", "P3"]


class IncidentPostmortemError(ValueError):
    """P22-H deterministic incident/postmortem invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: str, *, field: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise IncidentPostmortemError(f"{field} must be non-empty text of at most {max_length} characters")
    return normalized


def _code(value: str, *, field: str, max_length: int = 96) -> str:
    normalized = _text(value, field=field, max_length=max_length).upper()
    if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-." for ch in normalized):
        raise IncidentPostmortemError(f"{field} contains unsupported characters")
    return normalized


def _hex_id(value: str, *, field: str, length: int) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise IncidentPostmortemError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _epoch_ns(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise IncidentPostmortemError(f"{field} must be a non-negative integer epoch-ns value")
    return value


def _evidence_refs(values: tuple[str, ...], *, max_count: int = 32) -> tuple[str, ...]:
    if not values or len(values) > max_count:
        raise IncidentPostmortemError("evidence refs must be non-empty and bounded")
    normalized = tuple(sorted(_hex_id(v, field="evidence_ref", length=64) for v in values))
    if len(set(normalized)) != len(normalized):
        raise IncidentPostmortemError("duplicate evidence refs are forbidden")
    return normalized


@dataclass(frozen=True, slots=True)
class IncidentPostmortemPolicy:
    incident_severities: tuple[IncidentSeverity, ...]
    incident_states: tuple[IncidentState, ...]
    corrective_action_priorities: tuple[ActionPriority, ...]
    max_timeline_events: int
    max_contributing_factors: int
    max_corrective_actions: int
    evidence_ref_hex_length: int
    correlation_id_hex_length: int

    @classmethod
    def from_path(cls, path: Path) -> "IncidentPostmortemPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise IncidentPostmortemError(f"invalid P22-H policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise IncidentPostmortemError("P22-H policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22H_INCIDENT_POSTMORTEM_POLICY",
            "task_id": "FIN-P22-WH-001",
            "mode": "DETERMINISTIC_REFERENCE_INCIDENT_POSTMORTEM",
            "incident_severities": ["SEV1", "SEV2", "SEV3", "SEV4"],
            "incident_states": ["OPEN", "CONTAINED", "RECOVERED", "CLOSED"],
            "corrective_action_priorities": ["P0", "P1", "P2", "P3"],
            "max_timeline_events": 64,
            "max_contributing_factors": 16,
            "max_corrective_actions": 32,
            "evidence_ref_hex_length": 64,
            "correlation_id_hex_length": 32,
            "person_name_fields_allowed": False,
            "pii_fields_allowed": False,
            "corrective_action_execution_authority": False,
            "automatic_remediation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "runtime_state_mutation": False,
            "external_order_authority": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise IncidentPostmortemError(f"P22-H policy mismatch: {key}")
        return cls(
            incident_severities=("SEV1", "SEV2", "SEV3", "SEV4"),
            incident_states=("OPEN", "CONTAINED", "RECOVERED", "CLOSED"),
            corrective_action_priorities=("P0", "P1", "P2", "P3"),
            max_timeline_events=64,
            max_contributing_factors=16,
            max_corrective_actions=32,
            evidence_ref_hex_length=64,
            correlation_id_hex_length=32,
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "incident_severities": self.incident_severities,
            "incident_states": self.incident_states,
            "corrective_action_priorities": self.corrective_action_priorities,
            "max_timeline_events": self.max_timeline_events,
            "max_contributing_factors": self.max_contributing_factors,
            "max_corrective_actions": self.max_corrective_actions,
            "evidence_ref_hex_length": self.evidence_ref_hex_length,
            "correlation_id_hex_length": self.correlation_id_hex_length,
            "person_name_fields_allowed": False,
            "pii_fields_allowed": False,
            "corrective_action_execution_authority": False,
            "automatic_remediation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "runtime_state_mutation": False,
            "external_order_authority": False,
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class IncidentEvent:
    event_id: str
    event_code: str
    occurred_at_ns: int
    summary: str
    evidence_refs: tuple[str, ...]
    correlation_id: str

    def payload(self) -> dict[str, object]:
        return {
            "event_code": self.event_code,
            "occurred_at_ns": self.occurred_at_ns,
            "summary": self.summary,
            "evidence_refs": list(self.evidence_refs),
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True, slots=True)
class IncidentRecord:
    incident_id: str
    policy_id: str
    severity: IncidentSeverity
    state: IncidentState
    opened_at_ns: int
    contained_at_ns: int | None
    recovered_at_ns: int | None
    closed_at_ns: int | None
    impact_scopes: tuple[str, ...]
    timeline: tuple[IncidentEvent, ...]
    correlation_id: str

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "severity": self.severity,
            "state": self.state,
            "opened_at_ns": self.opened_at_ns,
            "contained_at_ns": self.contained_at_ns,
            "recovered_at_ns": self.recovered_at_ns,
            "closed_at_ns": self.closed_at_ns,
            "impact_scopes": list(self.impact_scopes),
            "timeline": [{"event_id": event.event_id, **event.payload()} for event in self.timeline],
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True, slots=True)
class CorrectiveAction:
    action_id: str
    action_code: str
    owner_role: str
    priority: ActionPriority
    verification_required: bool
    evidence_refs: tuple[str, ...]
    execution_authority: bool
    automatic_remediation: bool

    def payload(self) -> dict[str, object]:
        return {
            "action_code": self.action_code,
            "owner_role": self.owner_role,
            "priority": self.priority,
            "verification_required": self.verification_required,
            "evidence_refs": list(self.evidence_refs),
            "execution_authority": self.execution_authority,
            "automatic_remediation": self.automatic_remediation,
        }


@dataclass(frozen=True, slots=True)
class PostmortemRecord:
    postmortem_id: str
    policy_id: str
    incident_id: str
    root_cause_code: str
    root_cause_summary: str
    contributing_factors: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    corrective_actions: tuple[CorrectiveAction, ...]
    created_at_ns: int
    complete: bool
    execution_authority: bool
    runtime_state_mutation: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "incident_id": self.incident_id,
            "root_cause_code": self.root_cause_code,
            "root_cause_summary": self.root_cause_summary,
            "contributing_factors": list(self.contributing_factors),
            "evidence_refs": list(self.evidence_refs),
            "corrective_actions": [{"action_id": action.action_id, **action.payload()} for action in self.corrective_actions],
            "created_at_ns": self.created_at_ns,
            "complete": self.complete,
            "execution_authority": self.execution_authority,
            "runtime_state_mutation": self.runtime_state_mutation,
        }


def build_incident_event(
    policy: IncidentPostmortemPolicy,
    *,
    event_code: str,
    occurred_at_ns: int,
    summary: str,
    evidence_refs: tuple[str, ...],
    correlation_id: str,
) -> IncidentEvent:
    code = _code(event_code, field="event_code")
    occurred = _epoch_ns(occurred_at_ns, field="occurred_at_ns")
    summary_text = _text(summary, field="summary", max_length=512)
    refs = _evidence_refs(evidence_refs)
    correlation = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)
    payload: dict[str, object] = {
        "event_code": code,
        "occurred_at_ns": occurred,
        "summary": summary_text,
        "evidence_refs": list(refs),
        "correlation_id": correlation,
    }
    event_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return IncidentEvent(event_id, code, occurred, summary_text, refs, correlation)


def build_incident_record(
    policy: IncidentPostmortemPolicy,
    *,
    severity: IncidentSeverity,
    state: IncidentState,
    opened_at_ns: int,
    contained_at_ns: int | None,
    recovered_at_ns: int | None,
    closed_at_ns: int | None,
    impact_scopes: tuple[str, ...],
    timeline: tuple[IncidentEvent, ...],
    correlation_id: str,
) -> IncidentRecord:
    if severity not in policy.incident_severities:
        raise IncidentPostmortemError("unsupported incident severity")
    if state not in policy.incident_states:
        raise IncidentPostmortemError("unsupported incident state")
    opened = _epoch_ns(opened_at_ns, field="opened_at_ns")
    contained = None if contained_at_ns is None else _epoch_ns(contained_at_ns, field="contained_at_ns")
    recovered = None if recovered_at_ns is None else _epoch_ns(recovered_at_ns, field="recovered_at_ns")
    closed = None if closed_at_ns is None else _epoch_ns(closed_at_ns, field="closed_at_ns")
    if contained is not None and contained < opened:
        raise IncidentPostmortemError("contained_at_ns precedes opened_at_ns")
    if recovered is not None and recovered < (contained if contained is not None else opened):
        raise IncidentPostmortemError("recovered_at_ns precedes prior lifecycle timestamp")
    if closed is not None and recovered is None:
        raise IncidentPostmortemError("closed incident requires recovered_at_ns")
    if closed is not None and closed < recovered:
        raise IncidentPostmortemError("closed_at_ns precedes recovered_at_ns")
    if state == "OPEN" and any(v is not None for v in (contained, recovered, closed)):
        raise IncidentPostmortemError("OPEN incident cannot carry later lifecycle timestamps")
    if state == "CONTAINED" and (contained is None or recovered is not None or closed is not None):
        raise IncidentPostmortemError("CONTAINED incident requires only contained_at_ns")
    if state == "RECOVERED" and (recovered is None or closed is not None):
        raise IncidentPostmortemError("RECOVERED incident requires recovered_at_ns and no closed_at_ns")
    if state == "CLOSED" and (recovered is None or closed is None):
        raise IncidentPostmortemError("CLOSED incident requires recovery and closure timestamps")
    if not impact_scopes or len(impact_scopes) > 16:
        raise IncidentPostmortemError("impact scopes must be non-empty and bounded")
    scopes = tuple(sorted(_code(v, field="impact_scope") for v in impact_scopes))
    if len(set(scopes)) != len(scopes):
        raise IncidentPostmortemError("duplicate impact scopes are forbidden")
    if not timeline or len(timeline) > policy.max_timeline_events:
        raise IncidentPostmortemError("incident timeline must be non-empty and bounded")
    event_ids = [event.event_id for event in timeline]
    if len(set(event_ids)) != len(event_ids):
        raise IncidentPostmortemError("duplicate timeline events are forbidden")
    timestamps = [event.occurred_at_ns for event in timeline]
    if timestamps != sorted(timestamps):
        raise IncidentPostmortemError("incident timeline must be ordered")
    if timestamps[0] < opened:
        raise IncidentPostmortemError("timeline event precedes incident open time")
    correlation = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)
    if any(event.correlation_id != correlation for event in timeline):
        raise IncidentPostmortemError("timeline correlation lineage mismatch")
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "severity": severity,
        "state": state,
        "opened_at_ns": opened,
        "contained_at_ns": contained,
        "recovered_at_ns": recovered,
        "closed_at_ns": closed,
        "impact_scopes": list(scopes),
        "timeline": [{"event_id": event.event_id, **event.payload()} for event in timeline],
        "correlation_id": correlation,
    }
    incident_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return IncidentRecord(
        incident_id,
        policy.policy_id,
        severity,
        state,
        opened,
        contained,
        recovered,
        closed,
        scopes,
        timeline,
        correlation,
    )


def build_corrective_action(
    policy: IncidentPostmortemPolicy,
    *,
    action_code: str,
    owner_role: str,
    priority: ActionPriority,
    verification_required: bool,
    evidence_refs: tuple[str, ...],
) -> CorrectiveAction:
    code = _code(action_code, field="action_code")
    role = _code(owner_role, field="owner_role")
    if priority not in policy.corrective_action_priorities:
        raise IncidentPostmortemError("unsupported corrective-action priority")
    if not verification_required:
        raise IncidentPostmortemError("corrective action must require verification")
    refs = _evidence_refs(evidence_refs)
    payload: dict[str, object] = {
        "action_code": code,
        "owner_role": role,
        "priority": priority,
        "verification_required": True,
        "evidence_refs": list(refs),
        "execution_authority": False,
        "automatic_remediation": False,
    }
    action_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return CorrectiveAction(action_id, code, role, priority, True, refs, False, False)


def build_postmortem(
    policy: IncidentPostmortemPolicy,
    *,
    incident: IncidentRecord,
    root_cause_code: str,
    root_cause_summary: str,
    contributing_factors: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    corrective_actions: tuple[CorrectiveAction, ...],
    created_at_ns: int,
) -> PostmortemRecord:
    if incident.state not in ("RECOVERED", "CLOSED"):
        raise IncidentPostmortemError("postmortem requires a recovered or closed incident")
    root_code = _code(root_cause_code, field="root_cause_code")
    root_summary = _text(root_cause_summary, field="root_cause_summary", max_length=1024)
    if len(contributing_factors) > policy.max_contributing_factors:
        raise IncidentPostmortemError("too many contributing factors")
    factors = tuple(sorted(_code(v, field="contributing_factor") for v in contributing_factors))
    if len(set(factors)) != len(factors):
        raise IncidentPostmortemError("duplicate contributing factors are forbidden")
    refs = _evidence_refs(evidence_refs)
    if not corrective_actions or len(corrective_actions) > policy.max_corrective_actions:
        raise IncidentPostmortemError("corrective actions must be non-empty and bounded")
    action_ids = [action.action_id for action in corrective_actions]
    if len(set(action_ids)) != len(action_ids):
        raise IncidentPostmortemError("duplicate corrective actions are forbidden")
    if any(action.execution_authority or action.automatic_remediation for action in corrective_actions):
        raise IncidentPostmortemError("corrective action unexpectedly carries execution authority")
    created = _epoch_ns(created_at_ns, field="created_at_ns")
    recovery_time = incident.recovered_at_ns
    if recovery_time is None or created < recovery_time:
        raise IncidentPostmortemError("postmortem cannot predate incident recovery")
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "incident_id": incident.incident_id,
        "root_cause_code": root_code,
        "root_cause_summary": root_summary,
        "contributing_factors": list(factors),
        "evidence_refs": list(refs),
        "corrective_actions": [{"action_id": action.action_id, **action.payload()} for action in corrective_actions],
        "created_at_ns": created,
        "complete": True,
        "execution_authority": False,
        "runtime_state_mutation": False,
    }
    postmortem_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return PostmortemRecord(
        postmortem_id,
        policy.policy_id,
        incident.incident_id,
        root_code,
        root_summary,
        factors,
        refs,
        corrective_actions,
        created,
        True,
        False,
        False,
    )
