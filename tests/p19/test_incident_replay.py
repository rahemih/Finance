from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from packages.shadow.data_replay import DataReplayEngine, DataReplayPolicy, ReplayDataEvent
from packages.shadow.incident_replay import (
    IncidentDecisionRef,
    IncidentMarker,
    IncidentReplayEngine,
    IncidentReplayError,
    IncidentReplayPolicy,
    IncidentSystemEvent,
)


ROOT = Path(__file__).resolve().parents[2]
DATA_POLICY = DataReplayPolicy.from_path(ROOT / "config/shadow/data-replay-policy.json")
INCIDENT_POLICY = IncidentReplayPolicy.from_path(ROOT / "config/shadow/incident-replay-policy.json")
SNAPSHOT_POLICY = ReplaySnapshotPolicy.from_path(
    ROOT / "config/historical-data/replay-snapshot-policy.json"
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def data_engine() -> DataReplayEngine:
    snapshot = ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=9000,
        snapshot_cutoff_ns=8000,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "btc-reference", h("dataset"), "1.0", 1000, 9000,
                h("membership"), "PUBLIC_REFERENCE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("p19d-test-v1",),
        config_sha256=h("config"),
        code_artifact_sha256=h("code"),
        rights_class="PUBLIC_REFERENCE",
        policy=SNAPSHOT_POLICY,
    )
    events = tuple(
        ReplayDataEvent.create(
            sequence=i,
            event_time_ns=i * 1000,
            available_at_ns=i * 1000 + 100,
            dataset_name="btc-reference",
            dataset_version=h("dataset"),
            entity_id="BTC-USD",
            payload={"sequence": i, "close": 100 + i},
            source_evidence_sha256=h(f"source-{i}"),
        )
        for i in range(1, 8)
    )
    return DataReplayEngine(snapshot=snapshot, events=events, policy=DATA_POLICY)


def marker() -> IncidentMarker:
    return IncidentMarker(
        "canonical-incident",
        "MANUAL_REVIEW",
        4000,
        1500,
        1500,
        h("trigger"),
    )


def decision(time_ns: int = 3001, *, match: str = "EXACT_MATCH") -> IncidentDecisionRef:
    return IncidentDecisionRef(
        decision_time_ns=time_ns,
        decision_replay_result_id=h(f"decision-result-{time_ns}"),
        decision_replay_session_id=h("decision-session"),
        shadow_record_id=h(f"shadow-record-{time_ns}"),
        match_state=match,
        source_evidence_sha256=h("p19c-evidence"),
    )


def system_event(
    sequence: int,
    *,
    available_at: int,
    state: str = "NORMAL",
) -> IncidentSystemEvent:
    return IncidentSystemEvent(
        sequence=sequence,
        event_time_ns=available_at - 50,
        available_at_ns=available_at,
        event_type="SYSTEM_STATE_CHANGE",
        system_state=state,
        source_evidence_sha256=h(f"system-source-{sequence}"),
        detail_sha256=h(f"system-detail-{sequence}"),
    )


class IncidentReplayTests(unittest.TestCase):
    def replay_engine(self) -> IncidentReplayEngine:
        return IncidentReplayEngine(data_replay=data_engine(), policy=INCIDENT_POLICY)

    def test_same_inputs_produce_identical_incident_root(self) -> None:
        left = self.replay_engine().replay(
            marker=marker(),
            decisions=(decision(),),
            system_events=(system_event(1, available_at=3200), system_event(2, available_at=4500)),
        )
        right = self.replay_engine().replay(
            marker=marker(),
            decisions=(decision(),),
            system_events=(system_event(1, available_at=3200), system_event(2, available_at=4500)),
        )
        self.assertEqual(left.replay_root_id, right.replay_root_id)

    def test_input_order_does_not_change_incident_root(self) -> None:
        first = system_event(1, available_at=3200)
        second = system_event(2, available_at=4500)
        left = self.replay_engine().replay(
            marker=marker(), decisions=(decision(),), system_events=(first, second)
        )
        right = self.replay_engine().replay(
            marker=marker(), decisions=(decision(),), system_events=(second, first)
        )
        self.assertEqual(left.replay_root_id, right.replay_root_id)

    def test_window_filters_data_by_availability(self) -> None:
        result = self.replay_engine().replay(
            marker=marker(), decisions=(decision(),), system_events=()
        )
        self.assertEqual(len(result.data_event_ids), 3)

    def test_non_exact_decision_reference_fails_closed(self) -> None:
        with self.assertRaises(IncidentReplayError):
            self.replay_engine().replay(
                marker=marker(), decisions=(decision(match="MISMATCH"),), system_events=()
            )

    def test_decision_outside_window_fails_closed(self) -> None:
        with self.assertRaises(IncidentReplayError):
            self.replay_engine().replay(
                marker=marker(), decisions=(decision(2000),), system_events=()
            )

    def test_future_system_event_fails_closed(self) -> None:
        with self.assertRaises(IncidentReplayError):
            self.replay_engine().replay(
                marker=marker(),
                decisions=(decision(),),
                system_events=(system_event(1, available_at=6000),),
            )

    def test_duplicate_system_sequence_fails_closed(self) -> None:
        with self.assertRaises(IncidentReplayError):
            self.replay_engine().replay(
                marker=marker(),
                decisions=(decision(),),
                system_events=(
                    system_event(1, available_at=3200),
                    replace(system_event(2, available_at=4500), sequence=1),
                ),
            )

    def test_unsupported_system_state_fails_closed(self) -> None:
        with self.assertRaises(IncidentReplayError):
            self.replay_engine().replay(
                marker=marker(),
                decisions=(decision(),),
                system_events=(system_event(1, available_at=3200, state="UNKNOWN"),),
            )

    def test_unsupported_incident_type_fails_closed(self) -> None:
        with self.assertRaises(IncidentReplayError):
            self.replay_engine().replay(
                marker=replace(marker(), incident_type="UNKNOWN"),
                decisions=(decision(),),
                system_events=(),
            )

    def test_result_has_zero_authority(self) -> None:
        result = self.replay_engine().replay(
            marker=marker(), decisions=(decision(),), system_events=()
        )
        self.assertFalse(result.decision_authority)
        self.assertFalse(result.fill_authority)
        self.assertFalse(result.execution_authority)
        self.assertFalse(result.order_routing_authority)
        self.assertFalse(result.broker_exchange_routing)
        self.assertFalse(result.p20_started)
        self.assertEqual(result.live_trading, "DISABLED")
        self.assertEqual(result.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
