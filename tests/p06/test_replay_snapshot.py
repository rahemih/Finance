from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from packages.historical_data import (
    FilesystemReplaySnapshotStore,
    ReplayDatasetRef,
    ReplayFeatureRef,
    ReplaySnapshot,
    ReplaySnapshotError,
    ReplaySnapshotIntegrityError,
    ReplaySnapshotPolicy,
    ReplayVintageRef,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/historical-data/replay-snapshot-policy.json"


def dataset(*, version: str = "a" * 64) -> ReplayDatasetRef:
    return ReplayDatasetRef(
        dataset_name="btc-usd-reference",
        dataset_version=version,
        schema_version="1.0",
        window_start_ns=0,
        window_end_ns=1000,
        membership_root_sha256="b" * 64,
        rights_class="NON_DISPLAY_INTERNAL",
    )


def feature(*, materialization: str = "c" * 64, as_of: int = 200) -> ReplayFeatureRef:
    return ReplayFeatureRef(
        definition_id="d" * 64,
        materialization_id=materialization,
        entity_id="CRYPTO:BTC-USD",
        event_time_ns=180,
        as_of_time_ns=as_of,
        quality_evidence_sha256="e" * 64,
    )


def vintage(*, vintage_id: str = "f" * 64, release: int = 150, observed: int = 160) -> ReplayVintageRef:
    return ReplayVintageRef(
        vintage_id=vintage_id,
        series_id="MACRO:CPI:REFERENCE",
        observation_time_ns=100,
        release_time_ns=release,
        observed_at_ns=observed,
    )


def snapshot(
    *,
    datasets: tuple[ReplayDatasetRef, ...] | None = None,
    features: tuple[ReplayFeatureRef, ...] | None = None,
    vintages: tuple[ReplayVintageRef, ...] | None = None,
    clock_mode: str = "CONTROLLED_SIMULATION_CLOCK",
    seed: int | None = 7,
    stochastic_version: str | None = "rng-v1",
) -> ReplaySnapshot:
    policy = ReplaySnapshotPolicy.from_path(POLICY)
    return ReplaySnapshot.build(
        replay_start_ns=100,
        replay_end_ns=500,
        snapshot_cutoff_ns=400,
        clock_mode=clock_mode,
        scope_ids=("MACRO:CPI:REFERENCE", "CRYPTO:BTC-USD"),
        dataset_refs=datasets or (dataset(),),
        feature_refs=features or (feature(),),
        vintage_refs=vintages or (vintage(),),
        quality_rule_versions=("quality-v1",),
        config_sha256="1" * 64,
        code_artifact_sha256="2" * 64,
        rights_class="NON_DISPLAY_INTERNAL",
        stochastic_seed=seed,
        stochastic_version=stochastic_version,
        policy=policy,
    )


class ReplaySnapshotPolicyTests(unittest.TestCase):
    def test_policy_is_vendor_neutral_and_has_canonical_clock_modes(self):
        policy = ReplaySnapshotPolicy.from_path(POLICY)
        self.assertEqual(policy.production_replay_storage_vendor, "NOT_SELECTED")
        self.assertEqual(
            policy.allowed_clock_modes,
            frozenset({"EVENT_TIME", "RECEIVE_TIME", "CONTROLLED_SIMULATION_CLOCK"}),
        )


class ReplaySnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ReplaySnapshotPolicy.from_path(POLICY)

    def test_snapshot_identity_is_order_independent(self):
        f1 = feature(materialization="c" * 64, as_of=200)
        f2 = feature(materialization="9" * 64, as_of=250)
        v1 = vintage(vintage_id="f" * 64, release=150, observed=160)
        v2 = vintage(vintage_id="8" * 64, release=220, observed=230)
        first = ReplaySnapshot.build(
            replay_start_ns=100,
            replay_end_ns=500,
            snapshot_cutoff_ns=400,
            clock_mode="EVENT_TIME",
            scope_ids=("CRYPTO:BTC-USD", "MACRO:CPI:REFERENCE"),
            dataset_refs=(dataset(),),
            feature_refs=(f1, f2),
            vintage_refs=(v1, v2),
            quality_rule_versions=("quality-v2", "quality-v1"),
            config_sha256="1" * 64,
            code_artifact_sha256="2" * 64,
            rights_class="NON_DISPLAY_INTERNAL",
            stochastic_seed=None,
            stochastic_version=None,
            policy=self.policy,
        )
        second = ReplaySnapshot.build(
            replay_start_ns=100,
            replay_end_ns=500,
            snapshot_cutoff_ns=400,
            clock_mode="EVENT_TIME",
            scope_ids=("MACRO:CPI:REFERENCE", "CRYPTO:BTC-USD"),
            dataset_refs=(dataset(),),
            feature_refs=(f2, f1),
            vintage_refs=(v2, v1),
            quality_rule_versions=("quality-v1", "quality-v2"),
            config_sha256="1" * 64,
            code_artifact_sha256="2" * 64,
            rights_class="NON_DISPLAY_INTERNAL",
            stochastic_seed=None,
            stochastic_version=None,
            policy=self.policy,
        )
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(first.to_bytes(), second.to_bytes())

    def test_changing_feature_lineage_changes_snapshot_id(self):
        self.assertNotEqual(
            snapshot(features=(feature(materialization="c" * 64),)).snapshot_id,
            snapshot(features=(feature(materialization="9" * 64),)).snapshot_id,
        )

    def test_view_at_filters_future_feature_and_vintage(self):
        early = feature(materialization="c" * 64, as_of=180)
        late = feature(materialization="9" * 64, as_of=300)
        initial = vintage(vintage_id="f" * 64, release=150, observed=160)
        revised = vintage(vintage_id="8" * 64, release=250, observed=260)
        value = snapshot(features=(early, late), vintages=(initial, revised))
        view = value.view_at(200)
        self.assertEqual(tuple(item.materialization_id for item in view.feature_refs), ("c" * 64,))
        self.assertEqual(tuple(item.vintage_id for item in view.vintage_refs), ("f" * 64,))
        self.assertEqual(len(view.dataset_refs), 1)

    def test_view_at_filters_dataset_by_event_window(self):
        narrow = ReplayDatasetRef(
            dataset_name="narrow",
            dataset_version="3" * 64,
            schema_version="1.0",
            window_start_ns=300,
            window_end_ns=400,
            membership_root_sha256="4" * 64,
            rights_class="NON_DISPLAY_INTERNAL",
        )
        value = snapshot(datasets=(dataset(), narrow))
        self.assertEqual(
            tuple(item.dataset_name for item in value.view_at(200).dataset_refs),
            ("btc-usd-reference",),
        )

    def test_feature_or_vintage_beyond_snapshot_cutoff_fails_closed(self):
        with self.assertRaises(ReplaySnapshotError):
            snapshot(features=(feature(as_of=401),))
        with self.assertRaises(ReplaySnapshotError):
            snapshot(vintages=(vintage(release=390, observed=401),))

    def test_invalid_clock_mode_fails_closed(self):
        with self.assertRaises(ReplaySnapshotError):
            snapshot(clock_mode="WALL_CLOCK")

    def test_stochastic_seed_and_version_are_paired(self):
        with self.assertRaises(ReplaySnapshotError):
            snapshot(seed=7, stochastic_version=None)
        with self.assertRaises(ReplaySnapshotError):
            snapshot(seed=None, stochastic_version="rng-v1")

    def test_decision_must_be_in_window_and_not_after_cutoff(self):
        value = snapshot()
        with self.assertRaises(ReplaySnapshotError):
            value.view_at(99)
        with self.assertRaises(ReplaySnapshotError):
            value.view_at(450)

    def test_round_trip_verifies_exact_snapshot_identity(self):
        value = snapshot()
        self.assertEqual(ReplaySnapshot.from_bytes(value.to_bytes(), self.policy), value)

    def test_tampered_snapshot_fails_integrity(self):
        value = snapshot()
        payload = json.loads(value.to_bytes().decode("utf-8"))
        payload["clock_mode"] = "EVENT_TIME"
        tampered = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with self.assertRaises(ReplaySnapshotIntegrityError):
            ReplaySnapshot.from_bytes(tampered, self.policy)

    def test_store_is_write_once_and_idempotent(self):
        value = snapshot()
        with tempfile.TemporaryDirectory() as temp:
            store = FilesystemReplaySnapshotStore(Path(temp), self.policy)
            first = store.save(value)
            second = store.save(value)
            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertEqual(store.load(value.snapshot_id), value)

    def test_duplicate_logical_reference_fails_closed(self):
        d = dataset()
        with self.assertRaises(ReplaySnapshotError):
            snapshot(datasets=(d, d))

    def test_core_module_has_no_replay_database_or_cloud_clients(self):
        text = (ROOT / "packages/historical_data/replay_snapshot.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "psycopg",
            "sqlalchemy",
            "clickhouse",
            "timescale",
            "boto3",
            "ray.",
            "adapters.",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
