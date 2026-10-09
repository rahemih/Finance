from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.data_quality import (
    CompletenessDuplicateAnalyzer,
    CompletenessDuplicateBatch,
    CompletenessDuplicateError,
    CompletenessDuplicateOutcome,
    CompletenessDuplicatePolicy,
    CompletenessExpectation,
    DuplicateClass,
)
from packages.historical_data import TimeSeriesRecord

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/data-quality/completeness-duplicate-policy.json"
SCHEMA_EVIDENCE = "a" * 64


def record(
    *,
    record_id: str,
    sequence_id: str,
    payload: str = '{"price":"100"}',
    event_time_ns: int = 100,
    provider: str = "reference-provider",
) -> TimeSeriesRecord:
    raw = f"{sequence_id}:{payload}:{event_time_ns}:{provider}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id="CRYPTO:BTC/USD:SPOT",
        kind="TRADE",
        provider=provider,
        event_time_ns=event_time_ns,
        receive_time_ns=event_time_ns + 10,
        sequence_id=sequence_id,
        canonical_schema_version="1.0",
        canonical_payload_json=payload,
        source_payload_sha256=digest,
        source_object_relative_path=f"reference/{digest}.raw",
        provenance=(("source", "test"),),
    )


def analyze(
    records: tuple[TimeSeriesRecord, ...],
    expected: tuple[str, ...],
):
    policy = CompletenessDuplicatePolicy.from_path(POLICY)
    analyzer = CompletenessDuplicateAnalyzer(policy)
    return analyzer.analyze(
        CompletenessDuplicateBatch(
            records=records,
            schema_validation_evidence_sha256=SCHEMA_EVIDENCE,
        ),
        CompletenessExpectation(expected_record_ids=expected),
    )


class CompletenessDuplicatePolicyTests(unittest.TestCase):
    def test_policy_is_offline_vendor_neutral_and_does_not_infer_sequence_gaps(self):
        policy = CompletenessDuplicatePolicy.from_path(POLICY)
        self.assertEqual(policy.production_data_quality_vendor, "NOT_SELECTED")
        self.assertGreater(policy.max_records_per_batch, 0)


class CompletenessTests(unittest.TestCase):
    def test_complete_unique_batch_passes(self):
        report = analyze(
            (
                record(record_id="r1", sequence_id="1", event_time_ns=100),
                record(record_id="r2", sequence_id="2", event_time_ns=200),
            ),
            ("r1", "r2"),
        )
        self.assertTrue(report.is_valid)
        self.assertEqual(report.outcome, CompletenessDuplicateOutcome.VALID)
        self.assertEqual(report.missing_record_ids, ())
        self.assertEqual(report.duplicate_findings, ())

    def test_missing_expected_record_fails_closed(self):
        report = analyze(
            (record(record_id="r1", sequence_id="1"),),
            ("r1", "r2"),
        )
        self.assertEqual(report.outcome, CompletenessDuplicateOutcome.INVALID_CRITICAL)
        self.assertEqual(report.missing_record_ids, ("r2",))

    def test_unexpected_records_are_reported_but_not_confused_with_missing(self):
        report = analyze(
            (
                record(record_id="r1", sequence_id="1"),
                record(record_id="r-extra", sequence_id="2", event_time_ns=200),
            ),
            ("r1",),
        )
        self.assertTrue(report.is_valid)
        self.assertEqual(report.unexpected_record_ids, ("r-extra",))
        self.assertEqual(report.missing_record_ids, ())

    def test_non_contiguous_sequence_ids_alone_do_not_imply_incompleteness(self):
        report = analyze(
            (
                record(record_id="r1", sequence_id="1", event_time_ns=100),
                record(record_id="r3", sequence_id="3", event_time_ns=300),
            ),
            ("r1", "r3"),
        )
        self.assertTrue(report.is_valid)

    def test_expectation_ids_must_be_unique(self):
        with self.assertRaises(CompletenessDuplicateError):
            CompletenessExpectation(expected_record_ids=("r1", "r1"))


class DuplicateTests(unittest.TestCase):
    def test_repeated_identical_record_id_is_exact_duplicate(self):
        value = record(record_id="r1", sequence_id="1")
        report = analyze((value, value), ("r1",))
        self.assertEqual(report.outcome, CompletenessDuplicateOutcome.INVALID_CRITICAL)
        self.assertEqual(len(report.duplicate_findings), 1)
        finding = report.duplicate_findings[0]
        self.assertEqual(finding.key_type, "RECORD_ID")
        self.assertEqual(finding.classification, DuplicateClass.EXACT_DUPLICATE)

    def test_reused_record_id_with_different_content_is_conflicting_duplicate(self):
        first = record(record_id="r1", sequence_id="1", payload='{"price":"100"}')
        second = record(record_id="r1", sequence_id="1", payload='{"price":"101"}')
        report = analyze((first, second), ("r1",))
        finding = report.duplicate_findings[0]
        self.assertEqual(finding.key_type, "RECORD_ID")
        self.assertEqual(finding.classification, DuplicateClass.CONFLICTING_DUPLICATE)

    def test_distinct_ids_same_logical_event_same_content_are_exact_logical_duplicates(self):
        first = record(record_id="r1", sequence_id="1", payload='{"price":"100"}')
        second = record(record_id="r2", sequence_id="1", payload='{"price":"100"}')
        report = analyze((first, second), ("r1", "r2"))
        logical = [item for item in report.duplicate_findings if item.key_type == "LOGICAL_EVENT"]
        self.assertEqual(len(logical), 1)
        self.assertEqual(logical[0].classification, DuplicateClass.EXACT_DUPLICATE)

    def test_distinct_ids_same_logical_event_different_content_are_conflicting_logical_duplicates(self):
        first = record(record_id="r1", sequence_id="1", payload='{"price":"100"}')
        second = record(record_id="r2", sequence_id="1", payload='{"price":"101"}')
        report = analyze((first, second), ("r1", "r2"))
        logical = [item for item in report.duplicate_findings if item.key_type == "LOGICAL_EVENT"]
        self.assertEqual(len(logical), 1)
        self.assertEqual(logical[0].classification, DuplicateClass.CONFLICTING_DUPLICATE)

    def test_different_sequence_ids_are_not_logical_duplicates(self):
        report = analyze(
            (
                record(record_id="r1", sequence_id="1", event_time_ns=100),
                record(record_id="r2", sequence_id="2", event_time_ns=100),
            ),
            ("r1", "r2"),
        )
        self.assertTrue(report.is_valid)

    def test_report_order_and_fingerprint_are_deterministic(self):
        records = (
            record(record_id="r2", sequence_id="1", payload='{"price":"101"}'),
            record(record_id="r1", sequence_id="1", payload='{"price":"100"}'),
        )
        first = analyze(records, ("r1", "r2"))
        second = analyze(tuple(reversed(records)), ("r2", "r1"))
        self.assertEqual(first.duplicate_findings, second.duplicate_findings)
        self.assertEqual(first.missing_record_ids, second.missing_record_ids)
        self.assertEqual(first.unexpected_record_ids, second.unexpected_record_ids)
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_batch_limit_fails_closed(self):
        policy = CompletenessDuplicatePolicy(
            max_records_per_batch=1,
            production_data_quality_vendor="NOT_SELECTED",
        )
        analyzer = CompletenessDuplicateAnalyzer(policy)
        with self.assertRaises(CompletenessDuplicateError):
            analyzer.analyze(
                CompletenessDuplicateBatch(
                    records=(
                        record(record_id="r1", sequence_id="1"),
                        record(record_id="r2", sequence_id="2"),
                    ),
                    schema_validation_evidence_sha256=SCHEMA_EVIDENCE,
                ),
                CompletenessExpectation(expected_record_ids=("r1", "r2")),
            )


if __name__ == "__main__":
    unittest.main()
