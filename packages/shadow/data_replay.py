from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.historical_data.replay_snapshot import ReplaySnapshot, ReplaySnapshotError


class DataReplayError(ValueError):
    """P19-B deterministic data-replay invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DataReplayError(f"value is not canonical JSON: {exc}") from exc


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DataReplayError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataReplayError(f"{field} must be non-empty text")
    return value.strip()


def _sha256_text(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise DataReplayError(f"{field} must be lowercase SHA-256")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DataReplayError(f"{field} must be positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DataReplayError(f"{field} must be non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class DataReplayPolicy:
    accepted_clock_modes: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "DataReplayPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DataReplayError(f"invalid P19-B policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19B_DATA_REPLAY_POLICY",
            "task_id": "FIN-P19-WB-001",
            "mode": "DETERMINISTIC_POINT_IN_TIME_DATA_REPLAY",
            "anti_lookahead_owner": "P06_G_REPLAY_SNAPSHOT",
            "event_identity": "SHA256_CANONICAL_EVENT_PAYLOAD",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise DataReplayError(f"P19-B policy mismatch: {key}")
        modes_raw = raw.get("accepted_clock_modes")
        if not isinstance(modes_raw, list):
            raise DataReplayError("accepted_clock_modes must be a list")
        modes = tuple(
            _text(item, field="accepted_clock_mode")
            for item in cast(list[object], modes_raw)
        )
        expected_modes = (
            "EVENT_TIME",
            "RECEIVE_TIME",
            "CONTROLLED_SIMULATION_CLOCK",
        )
        if modes != expected_modes:
            raise DataReplayError("P19-B clock-mode taxonomy drift")
        required_false = (
            "duplicate_sequence_allowed",
            "duplicate_event_id_allowed",
            "future_information_allowed",
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
            raise DataReplayError("P19-B safety/authority policy drift")
        return cls(
            accepted_clock_modes=modes,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "accepted_clock_modes": list(self.accepted_clock_modes),
                    "anti_lookahead_owner": "P06_G_REPLAY_SNAPSHOT",
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ReplayDataEvent:
    sequence: int
    event_time_ns: int
    available_at_ns: int
    dataset_name: str
    dataset_version: str
    entity_id: str
    payload_json: str
    payload_sha256: str
    source_evidence_sha256: str

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        event_time_ns: int,
        available_at_ns: int,
        dataset_name: str,
        dataset_version: str,
        entity_id: str,
        payload: object,
        source_evidence_sha256: str,
    ) -> "ReplayDataEvent":
        seq = _positive_int(sequence, field="sequence")
        event_time = _non_negative_int(event_time_ns, field="event_time_ns")
        available = _non_negative_int(available_at_ns, field="available_at_ns")
        if available < event_time:
            raise DataReplayError("available_at_ns cannot precede event_time_ns")
        name = _text(dataset_name, field="dataset_name")
        version = _sha256_text(dataset_version, field="dataset_version")
        entity = _text(entity_id, field="entity_id")
        payload_bytes = _canonical_bytes(payload)
        payload_json = payload_bytes.decode("utf-8")
        return cls(
            sequence=seq,
            event_time_ns=event_time,
            available_at_ns=available,
            dataset_name=name,
            dataset_version=version,
            entity_id=entity,
            payload_json=payload_json,
            payload_sha256=hashlib.sha256(payload_bytes).hexdigest(),
            source_evidence_sha256=_sha256_text(
                source_evidence_sha256,
                field="source_evidence_sha256",
            ),
        )

    def payload_value(self) -> object:
        return json.loads(self.payload_json)

    def identity_payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "sequence": self.sequence,
            "event_time_ns": self.event_time_ns,
            "available_at_ns": self.available_at_ns,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "entity_id": self.entity_id,
            "payload_sha256": self.payload_sha256,
            "source_evidence_sha256": self.source_evidence_sha256,
        }

    @property
    def event_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.identity_payload())).hexdigest()

    def replay_payload(self) -> dict[str, object]:
        return self.identity_payload() | {
            "event_id": self.event_id,
            "payload": self.payload_value(),
        }


@dataclass(frozen=True, slots=True)
class DataReplayResult:
    snapshot_id: str
    policy_id: str
    decision_time_ns: int
    clock_mode: str
    event_ids: tuple[str, ...]
    events: tuple[ReplayDataEvent, ...]
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
            "snapshot_id": self.snapshot_id,
            "policy_id": self.policy_id,
            "decision_time_ns": self.decision_time_ns,
            "clock_mode": self.clock_mode,
            "event_ids": list(self.event_ids),
            "events": [event.replay_payload() for event in self.events],
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
    def result_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class DataReplayEngine:
    def __init__(
        self,
        *,
        snapshot: ReplaySnapshot,
        events: Sequence[ReplayDataEvent],
        policy: DataReplayPolicy,
    ) -> None:
        if snapshot.clock_mode not in policy.accepted_clock_modes:
            raise DataReplayError("snapshot clock mode is not accepted by P19-B policy")
        self._snapshot = snapshot
        self._policy = policy
        dataset_refs = {
            (item.dataset_name, item.dataset_version): item
            for item in snapshot.dataset_refs
        }
        if not dataset_refs:
            raise DataReplayError("replay snapshot has no dataset references")

        sequences: set[int] = set()
        event_ids: set[str] = set()
        validated: list[ReplayDataEvent] = []
        for event in events:
            if event.sequence in sequences:
                raise DataReplayError("duplicate replay sequence")
            if event.event_id in event_ids:
                raise DataReplayError("duplicate replay event identity")
            key = (event.dataset_name, event.dataset_version)
            dataset_ref = dataset_refs.get(key)
            if dataset_ref is None:
                raise DataReplayError("event dataset name/version is not in replay snapshot")
            if event.entity_id not in snapshot.scope_ids:
                raise DataReplayError("event entity is outside replay snapshot scope")
            if not (
                snapshot.replay_start_ns
                <= event.event_time_ns
                < snapshot.replay_end_ns
            ):
                raise DataReplayError("event time is outside replay snapshot window")
            if not (
                dataset_ref.window_start_ns
                <= event.event_time_ns
                < dataset_ref.window_end_ns
            ):
                raise DataReplayError("event time is outside dataset reference window")
            if event.available_at_ns > snapshot.snapshot_cutoff_ns:
                raise DataReplayError("event availability exceeds frozen snapshot cutoff")
            sequences.add(event.sequence)
            event_ids.add(event.event_id)
            validated.append(event)

        self._events = tuple(sorted(validated, key=self._order_key))

    def _order_key(self, event: ReplayDataEvent) -> tuple[int, int, int, str]:
        if self._snapshot.clock_mode == "EVENT_TIME":
            return (
                event.event_time_ns,
                event.available_at_ns,
                event.sequence,
                event.event_id,
            )
        return (
            event.available_at_ns,
            event.event_time_ns,
            event.sequence,
            event.event_id,
        )

    def replay_through(self, decision_time_ns: int) -> DataReplayResult:
        decision = _non_negative_int(decision_time_ns, field="decision_time_ns")
        try:
            self._snapshot.view_at(decision)
        except ReplaySnapshotError as exc:
            raise DataReplayError(f"replay decision time rejected by P06-G: {exc}") from exc
        visible = tuple(
            event
            for event in self._events
            if event.event_time_ns <= decision
            and event.available_at_ns <= decision
        )
        return DataReplayResult(
            snapshot_id=self._snapshot.snapshot_id,
            policy_id=self._policy.policy_id,
            decision_time_ns=decision,
            clock_mode=self._snapshot.clock_mode,
            event_ids=tuple(event.event_id for event in visible),
            events=visible,
            live_trading=self._policy.live_trading,
            auto_trading=self._policy.auto_trading,
        )
