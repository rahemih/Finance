from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from packages.historical_data import (
    DatasetManifest,
    DatasetManifestError,
    DatasetManifestIntegrityError,
    DatasetManifestPolicy,
    FilesystemDatasetManifestStore,
    TimeSeriesQueryIndex,
    TimeSeriesQueryPolicy,
    TimeSeriesRecord,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_POLICY = ROOT / "config/historical-data/dataset-manifest-policy.json"
QUERY_POLICY = ROOT / "config/historical-data/query-layer-policy.json"


def record(record_id: str, event_time_ns: int, *, price: str = "100.0") -> TimeSeriesRecord:
    raw = f"{record_id}:raw".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id="CRYPTO:BTC-USD",
        kind="TRADE",
        provider="reference-provider",
        event_time_ns=event_time_ns,
        receive_time_ns=event_time_ns + 1000,
        sequence_id=record_id,
        canonical_schema_version="1.0",
        canonical_payload_json=json.dumps({"price": price}, sort_keys=True),
        source_payload_sha256=digest,
        source_object_relative_path=f"reference-provider/2026/06/07/stream/{digest}.raw",
        provenance=(("source", "test"),),
    )


def manifest(records: tuple[TimeSeriesRecord, ...], *, name: str = "btc-trades") -> DatasetManifest:
    manifest_policy = DatasetManifestPolicy.from_path(MANIFEST_POLICY)
    query_policy = TimeSeriesQueryPolicy.from_path(QUERY_POLICY)
    query_index = TimeSeriesQueryIndex(records, query_policy)
    return DatasetManifest.build(
        dataset_name=name,
        dataset_schema_version="1.0",
        window_start_ns=0,
        window_end_ns=100,
        rights_class="NON_DISPLAY_INTERNAL",
        query_index_fingerprint=query_index.fingerprint,
        records=records,
        policy=manifest_policy,
    )


class DatasetManifestPolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = DatasetManifestPolicy.from_path(MANIFEST_POLICY)
        self.assertEqual(policy.production_manifest_storage_vendor, "NOT_SELECTED")
        self.assertGreater(policy.max_members_per_manifest, 0)
        self.assertGreater(policy.max_manifest_bytes, 0)


class DatasetManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = (
            record("r0", 10),
            record("r1", 20),
            record("r2", 30),
        )
        self.policy = DatasetManifestPolicy.from_path(MANIFEST_POLICY)

    def test_version_is_order_independent(self):
        first = manifest(self.records)
        second = manifest(tuple(reversed(self.records)))
        self.assertEqual(first.dataset_version, second.dataset_version)
        self.assertEqual(first.membership_root_sha256, second.membership_root_sha256)
        self.assertEqual(first.to_bytes(), second.to_bytes())

    def test_version_changes_when_canonical_content_changes(self):
        first = manifest(self.records)
        changed = (record("r0", 10, price="101.0"), self.records[1], self.records[2])
        second = manifest(changed)
        self.assertNotEqual(first.dataset_version, second.dataset_version)
        self.assertNotEqual(first.members[0].record_digest, second.members[0].record_digest)

    def test_round_trip_verifies_exact_version(self):
        original = manifest(self.records)
        loaded = DatasetManifest.from_bytes(original.to_bytes(), self.policy)
        self.assertEqual(loaded, original)

    def test_tampered_member_fails_integrity(self):
        original = manifest(self.records)
        payload = json.loads(original.to_bytes().decode("utf-8"))
        payload["members"][0]["record_digest"] = "0" * 64
        tampered = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        with self.assertRaises(DatasetManifestIntegrityError):
            DatasetManifest.from_bytes(tampered, self.policy)

    def test_duplicate_record_ids_fail_closed(self):
        duplicate = (record("dup", 10), record("dup", 20))
        with self.assertRaises(DatasetManifestError):
            manifest(duplicate)

    def test_member_outside_window_fails_closed(self):
        records = (record("late", 100),)
        query_policy = TimeSeriesQueryPolicy.from_path(QUERY_POLICY)
        query_index = TimeSeriesQueryIndex(records, query_policy)
        with self.assertRaises(DatasetManifestError):
            DatasetManifest.build(
                dataset_name="btc-trades",
                dataset_schema_version="1.0",
                window_start_ns=0,
                window_end_ns=100,
                rights_class="NON_DISPLAY_INTERNAL",
                query_index_fingerprint=query_index.fingerprint,
                records=records,
                policy=self.policy,
            )

    def test_unsafe_dataset_name_fails_closed(self):
        with self.assertRaises(DatasetManifestError):
            manifest(self.records, name="../escape")

    def test_store_is_write_once_and_idempotent(self):
        value = manifest(self.records)
        with tempfile.TemporaryDirectory() as temp:
            store = FilesystemDatasetManifestStore(Path(temp), self.policy)
            first = store.save(value)
            second = store.save(value)
            loaded = store.load(value.dataset_name, value.dataset_version)
            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertEqual(first.relative_path, second.relative_path)
            self.assertEqual(loaded, value)

    def test_tampered_stored_manifest_fails_on_load(self):
        value = manifest(self.records)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = FilesystemDatasetManifestStore(root, self.policy)
            stored = store.save(value)
            target = root / stored.relative_path
            raw = bytearray(target.read_bytes())
            raw[-2] = ord(" ")
            target.write_bytes(bytes(raw))
            with self.assertRaises(DatasetManifestIntegrityError):
                store.load(value.dataset_name, value.dataset_version)

    def test_member_policy_bound_fails_closed(self):
        tiny = DatasetManifestPolicy(
            max_members_per_manifest=1,
            max_manifest_bytes=self.policy.max_manifest_bytes,
            production_manifest_storage_vendor="NOT_SELECTED",
        )
        query_policy = TimeSeriesQueryPolicy.from_path(QUERY_POLICY)
        query_index = TimeSeriesQueryIndex(self.records, query_policy)
        with self.assertRaises(DatasetManifestError):
            DatasetManifest.build(
                dataset_name="btc-trades",
                dataset_schema_version="1.0",
                window_start_ns=0,
                window_end_ns=100,
                rights_class="NON_DISPLAY_INTERNAL",
                query_index_fingerprint=query_index.fingerprint,
                records=self.records,
                policy=tiny,
            )

    def test_core_module_has_no_database_or_provider_client_imports(self):
        text = (ROOT / "packages/historical_data/dataset_manifest.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "psycopg",
            "sqlalchemy",
            "clickhouse",
            "timescale",
            "boto3",
            "adapters.",
            "kaiko",
            "dxfeed",
            "databento",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
