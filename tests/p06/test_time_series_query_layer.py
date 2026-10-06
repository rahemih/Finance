from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.historical_data import (
    TimeSeriesQuery,
    TimeSeriesQueryError,
    TimeSeriesQueryIndex,
    TimeSeriesQueryPolicy,
    TimeSeriesRecord,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/historical-data/query-layer-policy.json"
DAY = 86_400_000_000_000


def record(
    record_id: str,
    canonical_id: str,
    event_time_ns: int,
    *,
    kind: str = "TRADE",
    provider: str = "reference-provider",
    sequence_id: str | None = None,
    payload_json: str = '{"price":"100.0"}',
) -> TimeSeriesRecord:
    payload = f"{record_id}-raw".encode("utf-8")
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id=canonical_id,
        kind=kind,
        provider=provider,
        event_time_ns=event_time_ns,
        receive_time_ns=event_time_ns + 1_000,
        sequence_id=sequence_id or record_id,
        canonical_schema_version="1.0",
        canonical_payload_json=payload_json,
        source_payload_sha256=hashlib.sha256(payload).hexdigest(),
        source_object_relative_path=f"reference-provider/2026/06/07/stream/{hashlib.sha256(payload).hexdigest()}.raw",
        provenance=(("source", "test"),),
    )


class TimeSeriesQueryPolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = TimeSeriesQueryPolicy.from_path(POLICY)
        self.assertEqual(policy.partition_span_ns, DAY)
        self.assertEqual(policy.production_query_storage_vendor, "NOT_SELECTED")
        self.assertGreaterEqual(policy.minimum_synthetic_queries_per_second, 1)


class TimeSeriesQueryIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = TimeSeriesQueryPolicy.from_path(POLICY)
        self.records = (
            record("a0", "CRYPTO:BTC-USD", DAY + 10),
            record("a1", "CRYPTO:BTC-USD", DAY + 20, kind="QUOTE"),
            record("a2", "CRYPTO:BTC-USD", DAY * 2 + 10, provider="backup-provider"),
            record("b0", "FX:EUR-USD", DAY + 10),
            record("b1", "FX:EUR-USD", DAY * 3 + 10),
        )
        self.index = TimeSeriesQueryIndex(self.records, self.policy)

    def test_half_open_window_excludes_end_boundary(self):
        result = self.index.query(
            TimeSeriesQuery(
                start_ns=DAY,
                end_ns=DAY + 20,
                limit=10,
                canonical_ids=("CRYPTO:BTC-USD",),
            )
        )
        self.assertEqual(tuple(item.record_id for item in result.records), ("a0",))
        self.assertEqual(result.matched_count, 1)

    def test_partition_pruning_reduces_candidates(self):
        result = self.index.query(
            TimeSeriesQuery(
                start_ns=DAY,
                end_ns=DAY * 2,
                limit=10,
                canonical_ids=("CRYPTO:BTC-USD",),
            )
        )
        self.assertEqual(result.partitions_examined, 1)
        self.assertEqual(result.candidate_count, 2)
        self.assertLess(result.candidate_count, result.total_index_records)

    def test_provider_and_kind_filters_are_applied(self):
        result = self.index.query(
            TimeSeriesQuery(
                start_ns=0,
                end_ns=DAY * 4,
                limit=10,
                canonical_ids=("CRYPTO:BTC-USD",),
                providers=("reference-provider",),
                kinds=("QUOTE",),
            )
        )
        self.assertEqual(tuple(item.record_id for item in result.records), ("a1",))

    def test_stable_tiebreak_order_is_deterministic(self):
        records = (
            record("z", "CRYPTO:BTC-USD", DAY, sequence_id="2"),
            record("a", "CRYPTO:BTC-USD", DAY, sequence_id="1"),
            record("b", "CRYPTO:BTC-USD", DAY, sequence_id="1"),
        )
        index = TimeSeriesQueryIndex(records, self.policy)
        result = index.query(TimeSeriesQuery(start_ns=DAY, end_ns=DAY + 1, limit=10))
        self.assertEqual(tuple(item.record_id for item in result.records), ("a", "b", "z"))

    def test_limit_reports_truncation_and_full_match_count(self):
        result = self.index.query(TimeSeriesQuery(start_ns=0, end_ns=DAY * 4, limit=2))
        self.assertTrue(result.truncated)
        self.assertEqual(result.matched_count, 5)
        self.assertEqual(len(result.records), 2)

    def test_duplicate_record_ids_fail_closed(self):
        duplicate = (record("dup", "A", 1), record("dup", "B", 2))
        with self.assertRaises(TimeSeriesQueryError):
            TimeSeriesQueryIndex(duplicate, self.policy)

    def test_unsafe_archive_reference_fails_closed(self):
        payload = b"bad"
        with self.assertRaises(TimeSeriesQueryError):
            TimeSeriesRecord(
                record_id="bad",
                canonical_id="CRYPTO:BTC-USD",
                kind="TRADE",
                provider="reference-provider",
                event_time_ns=1,
                receive_time_ns=2,
                sequence_id="1",
                canonical_schema_version="1.0",
                canonical_payload_json="{}",
                source_payload_sha256=hashlib.sha256(payload).hexdigest(),
                source_object_relative_path="../escape.raw",
            )

    def test_query_policy_bounds_fail_closed(self):
        with self.assertRaises(TimeSeriesQueryError):
            self.index.query(TimeSeriesQuery(start_ns=0, end_ns=DAY, limit=self.policy.max_query_limit + 1))
        with self.assertRaises(TimeSeriesQueryError):
            self.index.query(
                TimeSeriesQuery(
                    start_ns=0,
                    end_ns=DAY * (self.policy.max_partitions_per_query + 1),
                    limit=1,
                )
            )

    def test_fingerprint_is_deterministic_and_content_sensitive(self):
        first = TimeSeriesQueryIndex(self.records, self.policy)
        second = TimeSeriesQueryIndex(tuple(reversed(self.records)), self.policy)
        self.assertEqual(first.fingerprint, second.fingerprint)
        changed = list(self.records)
        changed[0] = record(
            "a0",
            "CRYPTO:BTC-USD",
            DAY + 10,
            payload_json='{"price":"101.0"}',
        )
        self.assertNotEqual(first.fingerprint, TimeSeriesQueryIndex(changed, self.policy).fingerprint)

    def test_core_module_has_no_database_or_provider_client_imports(self):
        text = (ROOT / "packages/historical_data/query_layer.py").read_text(encoding="utf-8").lower()
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
