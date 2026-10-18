from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from packages.shadow.data_replay import DataReplayEngine
from packages.shadow.shadow_decisioning import (
    ShadowDecisionInput,
    ShadowDecisionLedger,
    ShadowDecisionPolicy,
)


class DecisionReplayError(ValueError):
    """P19-C deterministic decision-replay invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DecisionReplayError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionReplayError(f"{field} must be non-empty text")
    return value.strip()


def _sha256(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise DecisionReplayError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise DecisionReplayError(f"{field} cannot be degenerate placeholder identity")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DecisionReplayError(f"{field} must be positive integer")
    return value


@dataclass(frozen=True, slots=True)
class DecisionReplayPolicy:
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "DecisionReplayPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DecisionReplayError(f"invalid P19-C policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19C_DECISION_REPLAY_POLICY",
            "task_id": "FIN-P19-WC-001",
            "mode": "DETERMINISTIC_DECISION_REPLAY",
            "data_replay_owner": "P19_B_DATA_REPLAY",
            "decision_owner": "P19_A_SHADOW_DECISIONING",
            "visible_event_match": "EXACT_ORDERED_PREFIX",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise DecisionReplayError(f"P19-C policy mismatch: {key}")
        required_true = (
            "input_identity_match_required",
            "record_identity_match_required",
            "disposition_match_required",
            "previous_record_chain_match_required",
            "strictly_increasing_decision_time_required",
        )
        if any(raw.get(field) is not True for field in required_true):
            raise DecisionReplayError("P19-C required replay invariant disabled")
        required_false = (
            "network_required",
            "credentials_required",
            "fill_authority",
            "execution_authority",
            "order_routing_authority",
            "broker_exchange_routing",
            "p20_started",
        )
        if any(raw.get(field) is not False for field in required_false):
            raise DecisionReplayError("P19-C safety/authority policy drift")
        return cls(live_trading="DISABLED", auto_trading="DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "visible_event_match": "EXACT_ORDERED_PREFIX",
                    "input_identity_match_required": True,
                    "record_identity_match_required": True,
                    "disposition_match_required": True,
                    "previous_record_chain_match_required": True,
                    "strictly_increasing_decision_time_required": True,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class DecisionReplayCase:
    case_name: str
    decision_time_ns: int
    required_event_ids: tuple[str, ...]
    shadow_input: ShadowDecisionInput
    expected_input_id: str
    expected_record_id: str
    expected_disposition: str
    expected_previous_record_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_name", _text(self.case_name, field="case_name"))
        object.__setattr__(
            self,
            "decision_time_ns",
            _positive_int(self.decision_time_ns, field="decision_time_ns"),
        )
        if not self.required_event_ids:
            raise DecisionReplayError("required_event_ids cannot be empty")
        normalized = tuple(
            _sha256(value, field="required_event_id")
            for value in self.required_event_ids
        )
        if len(normalized) != len(set(normalized)):
            raise DecisionReplayError("required_event_ids cannot contain duplicates")
        object.__setattr__(self, "required_event_ids", normalized)
        object.__setattr__(
            self,
            "expected_input_id",
            _sha256(self.expected_input_id, field="expected_input_id"),
        )
        object.__setattr__(
            self,
            "expected_record_id",
            _sha256(self.expected_record_id, field="expected_record_id"),
        )
        object.__setattr__(
            self,
            "expected_disposition",
            _text(self.expected_disposition, field="expected_disposition"),
        )
        if self.expected_previous_record_id is not None:
            object.__setattr__(
                self,
                "expected_previous_record_id",
                _sha256(
                    self.expected_previous_record_id,
                    field="expected_previous_record_id",
                ),
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "case_name": self.case_name,
            "decision_time_ns": self.decision_time_ns,
            "required_event_ids": list(self.required_event_ids),
            "shadow_input_id": self.shadow_input.input_id,
            "expected_input_id": self.expected_input_id,
            "expected_record_id": self.expected_record_id,
            "expected_disposition": self.expected_disposition,
            "expected_previous_record_id": self.expected_previous_record_id,
        }

    @property
    def case_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DecisionReplayResult:
    case_id: str
    decision_time_ns: int
    data_replay_result_id: str
    visible_event_ids: tuple[str, ...]
    replayed_input_id: str
    replayed_record_id: str
    replayed_disposition: str
    previous_record_id: str | None
    match_state: str = "EXACT_MATCH"
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
            "case_id": self.case_id,
            "decision_time_ns": self.decision_time_ns,
            "data_replay_result_id": self.data_replay_result_id,
            "visible_event_ids": list(self.visible_event_ids),
            "replayed_input_id": self.replayed_input_id,
            "replayed_record_id": self.replayed_record_id,
            "replayed_disposition": self.replayed_disposition,
            "previous_record_id": self.previous_record_id,
            "match_state": self.match_state,
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


@dataclass(frozen=True, slots=True)
class DecisionReplaySession:
    policy_id: str
    result_ids: tuple[str, ...]
    results: tuple[DecisionReplayResult, ...]
    fill_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "policy_id": self.policy_id,
            "result_ids": list(self.result_ids),
            "results": [result.payload() for result in self.results],
            "fill_authority": self.fill_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def session_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class DecisionReplayEngine:
    def __init__(
        self,
        *,
        data_replay: DataReplayEngine,
        shadow_policy: ShadowDecisionPolicy,
        policy: DecisionReplayPolicy,
    ) -> None:
        self._data_replay = data_replay
        self._shadow_policy = shadow_policy
        self._policy = policy

    def replay(self, cases: Sequence[DecisionReplayCase]) -> DecisionReplaySession:
        if not cases:
            raise DecisionReplayError("at least one decision replay case is required")
        ledger = ShadowDecisionLedger(self._shadow_policy)
        results: list[DecisionReplayResult] = []
        previous_time: int | None = None

        for case in cases:
            if previous_time is not None and case.decision_time_ns <= previous_time:
                raise DecisionReplayError("decision replay times must be strictly increasing")
            previous_time = case.decision_time_ns

            visible = self._data_replay.replay_through(case.decision_time_ns)
            if visible.event_ids != case.required_event_ids:
                raise DecisionReplayError("visible event prefix drift")

            if case.shadow_input.input_id != case.expected_input_id:
                raise DecisionReplayError("shadow input identity drift")

            replayed = ledger.append(case.shadow_input)
            if replayed.record_id != case.expected_record_id:
                raise DecisionReplayError("shadow record identity drift")
            if replayed.disposition != case.expected_disposition:
                raise DecisionReplayError("shadow disposition drift")
            if replayed.previous_record_id != case.expected_previous_record_id:
                raise DecisionReplayError("shadow previous-record chain drift")

            results.append(
                DecisionReplayResult(
                    case_id=case.case_id,
                    decision_time_ns=case.decision_time_ns,
                    data_replay_result_id=visible.result_id,
                    visible_event_ids=visible.event_ids,
                    replayed_input_id=replayed.input_id,
                    replayed_record_id=replayed.record_id,
                    replayed_disposition=replayed.disposition,
                    previous_record_id=replayed.previous_record_id,
                    live_trading=self._policy.live_trading,
                    auto_trading=self._policy.auto_trading,
                )
            )

        return DecisionReplaySession(
            policy_id=self._policy.policy_id,
            result_ids=tuple(result.result_id for result in results),
            results=tuple(results),
            live_trading=self._policy.live_trading,
            auto_trading=self._policy.auto_trading,
        )
