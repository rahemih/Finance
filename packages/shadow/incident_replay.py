from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.shadow.data_replay import DataReplayEngine


class IncidentReplayError(ValueError):
    """P19-D deterministic incident-replay invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise IncidentReplayError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IncidentReplayError(f"{field} must be non-empty text")
    return value.strip()


def _sha(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise IncidentReplayError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise IncidentReplayError(f"{field} cannot be degenerate placeholder identity")
    return parsed


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise IncidentReplayError(f"{field} must be non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    parsed = _non_negative_int(value, field=field)
    if parsed == 0:
        raise IncidentReplayError(f"{field} must be positive integer")
    return parsed


@dataclass(frozen=True, slots=True)
class IncidentReplayPolicy:
    incident_types: tuple[str, ...]
    system_states: tuple[str, ...]
    max_window_ns: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "IncidentReplayPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise IncidentReplayError(f"invalid P19-D policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19D_INCIDENT_REPLAY_POLICY",
            "task_id": "FIN-P19-WD-001",
            "mode": "DETERMINISTIC_INCIDENT_REPLAY",
            "data_replay_owner": "P19_B_DATA_REPLAY",
            "decision_replay_owner": "P19_C_DECISION_REPLAY",
            "decision_match_required": "EXACT_MATCH",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise IncidentReplayError(f"P19-D policy mismatch: {key}")
        incident_raw = raw.get("supported_incident_types")
        state_raw = raw.get("supported_system_states")
        if not isinstance(incident_raw, list) or not isinstance(state_raw, list):
            raise IncidentReplayError("incident/system taxonomies must be lists")
        incident_types = tuple(str(item) for item in incident_raw)
        system_states = tuple(str(item) for item in state_raw)
        max_window = _positive_int(raw.get("max_window_ns"), field="max_window_ns")
        required_false = (
            "future_information_allowed",
            "duplicate_system_event_allowed",
            "network_required",
            "credentials_required",
            "decision_authority",
            "fill_authority",
            "execution_authority",
            "order_routing_authority",
            "broker_exchange_routing",
            "p20_started",
        )
        if any(raw.get(field) is not False for field in required_false):
            raise IncidentReplayError("P19-D safety/authority policy drift")
        return cls(
            incident_types=incident_types,
            system_states=system_states,
            max_window_ns=max_window,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "incident_types": list(self.incident_types),
                    "system_states": list(self.system_states),
                    "max_window_ns": self.max_window_ns,
                    "decision_match_required": "EXACT_MATCH",
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class IncidentMarker:
    incident_name: str
    incident_type: str
    detected_at_ns: int
    window_before_ns: int
    window_after_ns: int
    trigger_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "incident_name", _text(self.incident_name, field="incident_name"))
        object.__setattr__(self, "incident_type", _text(self.incident_type, field="incident_type"))
        object.__setattr__(self, "detected_at_ns", _positive_int(self.detected_at_ns, field="detected_at_ns"))
        object.__setattr__(self, "window_before_ns", _non_negative_int(self.window_before_ns, field="window_before_ns"))
        object.__setattr__(self, "window_after_ns", _non_negative_int(self.window_after_ns, field="window_after_ns"))
        object.__setattr__(
            self,
            "trigger_evidence_sha256",
            _sha(self.trigger_evidence_sha256, field="trigger_evidence_sha256"),
        )

    @property
    def window_start_ns(self) -> int:
        return self.detected_at_ns - self.window_before_ns

    @property
    def window_end_ns(self) -> int:
        return self.detected_at_ns + self.window_after_ns

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "incident_name": self.incident_name,
            "incident_type": self.incident_type,
            "detected_at_ns": self.detected_at_ns,
            "window_before_ns": self.window_before_ns,
            "window_after_ns": self.window_after_ns,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
            "trigger_evidence_sha256": self.trigger_evidence_sha256,
        }

    @property
    def marker_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class IncidentDecisionRef:
    decision_time_ns: int
    decision_replay_result_id: str
    decision_replay_session_id: str
    shadow_record_id: str
    match_state: str
    source_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_time_ns",
            _positive_int(self.decision_time_ns, field="decision_time_ns"),
        )
        for field in (
            "decision_replay_result_id",
            "decision_replay_session_id",
            "shadow_record_id",
            "source_evidence_sha256",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))
        object.__setattr__(self, "match_state", _text(self.match_state, field="match_state"))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "decision_time_ns": self.decision_time_ns,
            "decision_replay_result_id": self.decision_replay_result_id,
            "decision_replay_session_id": self.decision_replay_session_id,
            "shadow_record_id": self.shadow_record_id,
            "match_state": self.match_state,
            "source_evidence_sha256": self.source_evidence_sha256,
        }

    @property
    def ref_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class IncidentSystemEvent:
    sequence: int
    event_time_ns: int
    available_at_ns: int
    event_type: str
    system_state: str
    source_evidence_sha256: str
    detail_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "sequence", _positive_int(self.sequence, field="sequence"))
        object.__setattr__(self, "event_time_ns", _positive_int(self.event_time_ns, field="event_time_ns"))
        object.__setattr__(self, "available_at_ns", _positive_int(self.available_at_ns, field="available_at_ns"))
        if self.available_at_ns < self.event_time_ns:
            raise IncidentReplayError("system event availability cannot precede event time")
        object.__setattr__(self, "event_type", _text(self.event_type, field="event_type"))
        object.__setattr__(self, "system_state", _text(self.system_state, field="system_state"))
        object.__setattr__(
            self,
            "source_evidence_sha256",
            _sha(self.source_evidence_sha256, field="source_evidence_sha256"),
        )
        object.__setattr__(self, "detail_sha256", _sha(self.detail_sha256, field="detail_sha256"))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "sequence": self.sequence,
            "event_time_ns": self.event_time_ns,
            "available_at_ns": self.available_at_ns,
            "event_type": self.event_type,
            "system_state": self.system_state,
            "source_evidence_sha256": self.source_evidence_sha256,
            "detail_sha256": self.detail_sha256,
        }

    @property
    def event_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class IncidentReplayResult:
    marker_id: str
    policy_id: str
    window_start_ns: int
    window_end_ns: int
    data_replay_result_id: str
    data_event_ids: tuple[str, ...]
    decision_ref_ids: tuple[str, ...]
    system_event_ids: tuple[str, ...]
    decision_authority: bool = False
    fill_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "marker_id": self.marker_id,
            "policy_id": self.policy_id,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
            "data_replay_result_id": self.data_replay_result_id,
            "data_event_ids": list(self.data_event_ids),
            "decision_ref_ids": list(self.decision_ref_ids),
            "system_event_ids": list(self.system_event_ids),
            "decision_authority": self.decision_authority,
            "fill_authority": self.fill_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def replay_root_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class IncidentReplayEngine:
    def __init__(
        self,
        *,
        data_replay: DataReplayEngine,
        policy: IncidentReplayPolicy,
    ) -> None:
        self._data_replay = data_replay
        self._policy = policy

    def replay(
        self,
        *,
        marker: IncidentMarker,
        decisions: Sequence[IncidentDecisionRef],
        system_events: Sequence[IncidentSystemEvent],
    ) -> IncidentReplayResult:
        if marker.incident_type not in self._policy.incident_types:
            raise IncidentReplayError("unsupported incident type")
        if marker.window_start_ns < 0:
            raise IncidentReplayError("incident window cannot start before zero")
        if marker.window_end_ns <= marker.window_start_ns:
            raise IncidentReplayError("incident window must have positive width")
        if marker.window_end_ns - marker.window_start_ns > self._policy.max_window_ns:
            raise IncidentReplayError("incident replay window exceeds policy maximum")
        if not decisions:
            raise IncidentReplayError("incident replay requires at least one P19-C decision reference")

        end_state = self._data_replay.replay_through(marker.window_end_ns)
        data_events = tuple(
            event
            for event in end_state.events
            if marker.window_start_ns <= event.available_at_ns <= marker.window_end_ns
        )

        decision_ids: set[str] = set()
        validated_decisions: list[IncidentDecisionRef] = []
        for decision in decisions:
            if decision.match_state != "EXACT_MATCH":
                raise IncidentReplayError("incident decision reference is not exact-match")
            if not (
                marker.window_start_ns
                <= decision.decision_time_ns
                <= marker.window_end_ns
            ):
                raise IncidentReplayError("incident decision reference is outside replay window")
            if decision.ref_id in decision_ids:
                raise IncidentReplayError("duplicate incident decision reference")
            decision_ids.add(decision.ref_id)
            validated_decisions.append(decision)
        validated_decisions.sort(
            key=lambda item: (
                item.decision_time_ns,
                item.decision_replay_result_id,
                item.ref_id,
            )
        )

        system_sequences: set[int] = set()
        system_ids: set[str] = set()
        validated_system: list[IncidentSystemEvent] = []
        for event in system_events:
            if event.sequence in system_sequences:
                raise IncidentReplayError("duplicate incident system sequence")
            if event.event_id in system_ids:
                raise IncidentReplayError("duplicate incident system event identity")
            if event.system_state not in self._policy.system_states:
                raise IncidentReplayError("unsupported incident system state")
            if event.available_at_ns > marker.window_end_ns:
                raise IncidentReplayError("future incident system evidence is forbidden")
            if not (
                marker.window_start_ns
                <= event.available_at_ns
                <= marker.window_end_ns
            ):
                raise IncidentReplayError("incident system event is outside replay window")
            system_sequences.add(event.sequence)
            system_ids.add(event.event_id)
            validated_system.append(event)
        validated_system.sort(
            key=lambda item: (
                item.available_at_ns,
                item.event_time_ns,
                item.sequence,
                item.event_id,
            )
        )

        return IncidentReplayResult(
            marker_id=marker.marker_id,
            policy_id=self._policy.policy_id,
            window_start_ns=marker.window_start_ns,
            window_end_ns=marker.window_end_ns,
            data_replay_result_id=end_state.result_id,
            data_event_ids=tuple(event.event_id for event in data_events),
            decision_ref_ids=tuple(item.ref_id for item in validated_decisions),
            system_event_ids=tuple(item.event_id for item in validated_system),
            live_trading=self._policy.live_trading,
            auto_trading=self._policy.auto_trading,
        )
