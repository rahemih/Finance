from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from packages.shadow.data_replay import (
    DataReplayEngine,
    DataReplayError,
    DataReplayPolicy,
    ReplayDataEvent,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = DataReplayPolicy.from_path(ROOT / "config/shadow/data-replay-policy.json")
SNAPSHOT_POLICY = ReplaySnapshotPolicy.from_path(
    ROOT / "config/historical-data/replay-snapshot-policy.json"
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def snapshot(clock_mode: str = "CONTROLLED_SIMULATION_CLOCK") -> ReplaySnapshot:
    return ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=6000,
        snapshot_cutoff_ns=5000,
        clock_mode=clock_mode,
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "btc-reference",
                h("dataset"),
                "1.0",
                1000,
                6000,
                h("membership"),
                "PUBLIC_REFERENCE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("p19b-test-v1",),
        config_sha256=h("config"),
        code_artifact_sha256=h("code"),
        rights_class="PUBLIC_REFERENCE",
        policy=SNAPSHOT_POLICY,
    )


def event(
    sequence: int,
    *,
    event_time: int | None = None,
    available_at: int | None = None,
    version: str | None = None,
    entity: str = "BTC-USD",
) -> ReplayDataEvent:
    t = sequence * 1000 if event_time is None else event_time
    a = t if available_at is None else available_at
    return ReplayDataEvent.create(
        sequence=sequence,
        event_time_ns=t,
        available_at_ns=a,
        dataset_name="btc-reference",
        dataset_version=h("dataset") if version is None else version,
        entity_id=entity,
        payload={"sequence": sequence, "close": 100 + sequence},
        source_evidence_sha256=h(f"row-{sequence}"),
    )


class DataReplayTests(unittest.TestCase):
    def test_same_snapshot_and_events_produce_identical_result(self) -> None:
        left = DataReplayEngine(
            snapshot=snapshot(),
            events=(event(1), event(2), event(3)),
            policy=POLICY,
        ).replay_through(4000)
        right = DataReplayEngine(
            snapshot=snapshot(),
            events=(event(1), event(2), event(3)),
            policy=POLICY,
        ).replay_through(4000)
        self.assertEqual(left.result_id, right.result_id)
        self.assertEqual(left.event_ids, right.event_ids)

    def test_input_order_does_not_change_replay(self) -> None:
        ordered = (event(1), event(2), event(3), event(4))
        reversed_events = tuple(reversed(ordered))
        left = DataReplayEngine(snapshot=snapshot(), events=ordered, policy=POLICY)
        right = DataReplayEngine(
            snapshot=snapshot(),
            events=reversed_events,
            policy=POLICY,
        )
        self.assertEqual(
            left.replay_through(5000).result_id,
            right.replay_through(5000).result_id,
        )

    def test_future_available_event_is_withheld(self) -> None:
        delayed = event(2, event_time=2000, available_at=4000)
        engine = DataReplayEngine(
            snapshot=snapshot(),
            events=(event(1), delayed),
            policy=POLICY,
        )
        early = engine.replay_through(3000)
        late = engine.replay_through(4000)
        self.assertEqual(len(early.events), 1)
        self.assertEqual(len(late.events), 2)

    def test_unknown_dataset_version_fails_closed(self) -> None:
        with self.assertRaises(DataReplayError):
            DataReplayEngine(
                snapshot=snapshot(),
                events=(event(1, version=h("wrong")),),
                policy=POLICY,
            )

    def test_outside_snapshot_window_fails_closed(self) -> None:
        with self.assertRaises(DataReplayError):
            DataReplayEngine(
                snapshot=snapshot(),
                events=(event(7, event_time=7000),),
                policy=POLICY,
            )

    def test_duplicate_sequence_fails_closed(self) -> None:
        duplicate = ReplayDataEvent.create(
            sequence=1,
            event_time_ns=2000,
            available_at_ns=2000,
            dataset_name="btc-reference",
            dataset_version=h("dataset"),
            entity_id="BTC-USD",
            payload={"different": True},
            source_evidence_sha256=h("other-row"),
        )
        with self.assertRaises(DataReplayError):
            DataReplayEngine(
                snapshot=snapshot(),
                events=(event(1), duplicate),
                policy=POLICY,
            )

    def test_entity_outside_scope_fails_closed(self) -> None:
        with self.assertRaises(DataReplayError):
            DataReplayEngine(
                snapshot=snapshot(),
                events=(event(1, entity="ETH-USD"),),
                policy=POLICY,
            )

    def test_event_time_clock_orders_by_event_time(self) -> None:
        first_received = event(1, event_time=2000, available_at=2100)
        second_received = event(2, event_time=1500, available_at=2200)
        result = DataReplayEngine(
            snapshot=snapshot("EVENT_TIME"),
            events=(first_received, second_received),
            policy=POLICY,
        ).replay_through(3000)
        self.assertEqual(result.events[0].event_time_ns, 1500)
        self.assertEqual(result.events[1].event_time_ns, 2000)

    def test_receive_clock_orders_by_availability(self) -> None:
        late_event = event(1, event_time=1000, available_at=3000)
        early_receive = event(2, event_time=2000, available_at=2500)
        result = DataReplayEngine(
            snapshot=snapshot("RECEIVE_TIME"),
            events=(late_event, early_receive),
            policy=POLICY,
        ).replay_through(4000)
        self.assertEqual(result.events[0].available_at_ns, 2500)
        self.assertEqual(result.events[1].available_at_ns, 3000)

    def test_result_has_zero_downstream_authority(self) -> None:
        result = DataReplayEngine(
            snapshot=snapshot(),
            events=(event(1),),
            policy=POLICY,
        ).replay_through(2000)
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
