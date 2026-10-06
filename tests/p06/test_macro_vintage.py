from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.historical_data import (
    MacroVintage,
    MacroVintageError,
    MacroVintagePolicy,
    MacroVintageStore,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/historical-data/macro-vintage-policy.json"
DATASET_VERSION = "a" * 64


def vintage(
    *,
    observation: int = 10,
    release: int,
    observed: int,
    revision: int,
    value: str,
    series: str = "MACRO:CPI:ALL",
    source_digest_seed: str | None = None,
) -> MacroVintage:
    seed = source_digest_seed or f"{series}:{observation}:{revision}:{value}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return MacroVintage(
        series_id=series,
        observation_time_ns=observation,
        release_time_ns=release,
        observed_at_ns=observed,
        revision_number=revision,
        value_text=value,
        unit="INDEX",
        source="reference-macro-provider",
        source_dataset_version=DATASET_VERSION,
        source_payload_sha256=digest,
        source_object_relative_path=f"reference-provider/2026/06/07/macro/{digest}.raw",
        source_revision_id=f"rev-{revision}",
    )


class MacroVintagePolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = MacroVintagePolicy.from_path(POLICY)
        self.assertEqual(policy.production_macro_storage_vendor, "NOT_SELECTED")
        self.assertGreater(policy.max_vintages_per_store, 0)


class MacroVintageStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = MacroVintagePolicy.from_path(POLICY)
        self.initial = vintage(release=100, observed=105, revision=0, value="100.0")
        self.revised = vintage(release=200, observed=205, revision=1, value="100.4")
        self.store = MacroVintageStore((self.revised, self.initial), self.policy)

    def test_before_initial_release_returns_none(self):
        self.assertIsNone(
            self.store.resolve(series_id=self.initial.series_id, observation_time_ns=10, decision_time_ns=99)
        )

    def test_initial_is_visible_before_revision(self):
        resolved = self.store.resolve(
            series_id=self.initial.series_id,
            observation_time_ns=10,
            decision_time_ns=150,
        )
        self.assertEqual(resolved, self.initial)

    def test_released_but_not_observed_revision_does_not_leak(self):
        resolved = self.store.resolve(
            series_id=self.initial.series_id,
            observation_time_ns=10,
            decision_time_ns=202,
        )
        self.assertEqual(resolved, self.initial)

    def test_revision_is_visible_after_observed_at(self):
        resolved = self.store.resolve(
            series_id=self.initial.series_id,
            observation_time_ns=10,
            decision_time_ns=205,
        )
        self.assertEqual(resolved, self.revised)

    def test_snapshot_resolves_each_observation_as_of_decision(self):
        older = vintage(observation=5, release=50, observed=51, revision=0, value="98.0")
        older_revision = vintage(observation=5, release=250, observed=251, revision=1, value="98.2")
        store = MacroVintageStore(
            (self.revised, older_revision, self.initial, older),
            self.policy,
        )
        snapshot = store.snapshot_as_of(series_id=self.initial.series_id, decision_time_ns=210)
        self.assertEqual(
            tuple((item.observation_time_ns, item.value_text) for item in snapshot.vintages),
            ((5, "98.0"), (10, "100.4")),
        )

    def test_latest_projection_is_explicitly_distinct_from_as_of(self):
        latest = self.store.latest_projection(series_id=self.initial.series_id)
        as_of = self.store.snapshot_as_of(series_id=self.initial.series_id, decision_time_ns=150)
        self.assertEqual(latest[0], self.revised)
        self.assertEqual(as_of.vintages[0], self.initial)

    def test_revision_numbers_must_start_zero_and_be_contiguous(self):
        with self.assertRaises(MacroVintageError):
            MacroVintageStore(
                (vintage(release=200, observed=205, revision=1, value="100.4"),),
                self.policy,
            )
        with self.assertRaises(MacroVintageError):
            MacroVintageStore(
                (
                    self.initial,
                    vintage(release=300, observed=305, revision=2, value="100.5"),
                ),
                self.policy,
            )

    def test_revision_times_cannot_move_backward(self):
        with self.assertRaises(MacroVintageError):
            MacroVintageStore(
                (
                    self.initial,
                    vintage(release=90, observed=110, revision=1, value="100.4"),
                ),
                self.policy,
            )
        with self.assertRaises(MacroVintageError):
            MacroVintageStore(
                (
                    self.initial,
                    vintage(release=110, observed=104, revision=1, value="100.4"),
                ),
                self.policy,
            )

    def test_observed_at_cannot_precede_release(self):
        with self.assertRaises(MacroVintageError):
            vintage(release=110, observed=109, revision=0, value="1.0")

    def test_duplicate_revision_identity_fails_closed(self):
        with self.assertRaises(MacroVintageError):
            MacroVintageStore((self.initial, self.initial), self.policy)

    def test_fingerprint_is_input_order_independent_and_content_sensitive(self):
        first = MacroVintageStore((self.initial, self.revised), self.policy)
        second = MacroVintageStore((self.revised, self.initial), self.policy)
        self.assertEqual(first.fingerprint, second.fingerprint)
        changed = vintage(release=200, observed=205, revision=1, value="100.5")
        self.assertNotEqual(
            first.fingerprint,
            MacroVintageStore((self.initial, changed), self.policy).fingerprint,
        )

    def test_invalid_dataset_version_and_unsafe_path_fail_closed(self):
        digest = hashlib.sha256(b"x").hexdigest()
        with self.assertRaises(MacroVintageError):
            MacroVintage(
                series_id="MACRO:CPI",
                observation_time_ns=1,
                release_time_ns=2,
                observed_at_ns=3,
                revision_number=0,
                value_text="1.0",
                unit="INDEX",
                source="source",
                source_dataset_version="bad",
                source_payload_sha256=digest,
                source_object_relative_path="safe/x.raw",
            )
        with self.assertRaises(MacroVintageError):
            MacroVintage(
                series_id="MACRO:CPI",
                observation_time_ns=1,
                release_time_ns=2,
                observed_at_ns=3,
                revision_number=0,
                value_text="1.0",
                unit="INDEX",
                source="source",
                source_dataset_version=DATASET_VERSION,
                source_payload_sha256=digest,
                source_object_relative_path="../escape.raw",
            )

    def test_policy_bound_fails_closed(self):
        tiny = MacroVintagePolicy(
            max_vintages_per_store=1,
            production_macro_storage_vendor="NOT_SELECTED",
        )
        with self.assertRaises(MacroVintageError):
            MacroVintageStore((self.initial, self.revised), tiny)

    def test_core_module_has_no_provider_database_or_cloud_clients(self):
        text = (ROOT / "packages/historical_data/macro_vintage.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "psycopg",
            "sqlalchemy",
            "clickhouse",
            "timescale",
            "boto3",
            "adapters.",
            "fredapi",
            "ecbdata",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
