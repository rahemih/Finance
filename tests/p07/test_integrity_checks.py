from __future__ import annotations

from decimal import Decimal
import hashlib
from pathlib import Path
import unittest

from packages.data_quality import (
    FreshnessRule,
    IntegrityAnalyzer,
    IntegrityBatch,
    IntegrityCheckError,
    IntegrityCheckPolicy,
    IntegrityOutcome,
    NumericObservation,
    OutlierRule,
    SequenceRule,
    SequenceSemantics,
)
from packages.historical_data import TimeSeriesRecord

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/data-quality/integrity-check-policy.json"
UPSTREAM = "a" * 64


def record(
    *,
    record_id: str,
    sequence_id: str,
    event_time_ns: int,
    receive_time_ns: int | None = None,
    canonical_id: str = "CRYPTO:BTC/USD:SPOT",
    provider: str = "reference-provider",
    kind: str = "TRADE",
) -> TimeSeriesRecord:
    receive = event_time_ns + 5 if receive_time_ns is None else receive_time_ns
    raw = f"{canonical_id}:{provider}:{sequence_id}:{event_time_ns}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id=canonical_id,
        kind=kind,
        provider=provider,
        event_time_ns=event_time_ns,
        receive_time_ns=receive,
        sequence_id=sequence_id,
        canonical_schema_version="1.0",
        canonical_payload_json='{"price":"100"}',
        source_payload_sha256=digest,
        source_object_relative_path=f"reference/{digest}.raw",
        provenance=(("source", "p07c-test"),),
    )


def analyzer() -> IntegrityAnalyzer:
    return IntegrityAnalyzer(IntegrityCheckPolicy.from_path(POLICY))


def batch(records: tuple[TimeSeriesRecord, ...]) -> IntegrityBatch:
    return IntegrityBatch(records=records, upstream_quality_evidence_sha256=UPSTREAM)


def freshness() -> tuple[FreshnessRule, ...]:
    return (FreshnessRule(kind="TRADE", max_event_age_ns=100, max_receive_age_ns=100),)


def numeric_rule() -> tuple[SequenceRule, ...]:
    return (
        SequenceRule(
            canonical_id="CRYPTO:BTC/USD:SPOT",
            provider="reference-provider",
            semantics=SequenceSemantics.NUMERIC_MONOTONIC_CONTIGUOUS,
        ),
    )


class IntegrityPolicyTests(unittest.TestCase):
    def test_policy_is_explicit_offline_and_vendor_neutral(self):
        policy = IntegrityCheckPolicy.from_path(POLICY)
        self.assertEqual(policy.production_data_quality_vendor, "NOT_SELECTED")
        self.assertIn(SequenceSemantics.OPAQUE_NO_ORDER, policy.allowed_sequence_semantics)
        self.assertGreater(policy.max_records_per_batch, 0)


class FreshnessTests(unittest.TestCase):
    def test_fresh_records_pass(self):
        report = analyzer().analyze(
            batch((
                record(record_id="r1", sequence_id="1", event_time_ns=950),
                record(record_id="r2", sequence_id="2", event_time_ns=960),
            )),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            sequence_rules=numeric_rule(),
        )
        self.assertTrue(report.is_valid)
        self.assertEqual(report.outcome, IntegrityOutcome.VALID)

    def test_stale_event_and_receive_fail_closed(self):
        report = analyzer().analyze(
            batch((record(record_id="r1", sequence_id="1", event_time_ns=800, receive_time_ns=810),)),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            sequence_rules=numeric_rule(),
        )
        codes = {issue.code for issue in report.issues}
        self.assertEqual(report.outcome, IntegrityOutcome.INVALID_CRITICAL)
        self.assertIn("STALE_EVENT", codes)
        self.assertIn("STALE_RECEIVE", codes)

    def test_future_event_and_receive_fail_closed(self):
        report = analyzer().analyze(
            batch((record(record_id="r1", sequence_id="1", event_time_ns=1010, receive_time_ns=1020),)),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            sequence_rules=numeric_rule(),
        )
        codes = {issue.code for issue in report.issues}
        self.assertIn("FUTURE_EVENT_TIME", codes)
        self.assertIn("FUTURE_RECEIVE_TIME", codes)

    def test_missing_freshness_rule_fails_closed(self):
        report = analyzer().analyze(
            batch((record(record_id="r1", sequence_id="1", event_time_ns=950),)),
            reference_time_ns=1000,
            freshness_rules=(),
            sequence_rules=numeric_rule(),
        )
        self.assertIn("MISSING_FRESHNESS_RULE", {issue.code for issue in report.issues})


class OutlierTests(unittest.TestCase):
    def test_explicit_absolute_bounds_pass_and_fail(self):
        records = (
            record(record_id="r1", sequence_id="1", event_time_ns=950),
            record(record_id="r2", sequence_id="2", event_time_ns=960),
        )
        observations = (
            NumericObservation(record_id="r1", metric="price", event_time_ns=950, value=Decimal("100")),
            NumericObservation(record_id="r2", metric="price", event_time_ns=960, value=Decimal("250")),
        )
        report = analyzer().analyze(
            batch(records),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            observations=observations,
            outlier_rules=(OutlierRule(metric="price", minimum=Decimal("50"), maximum=Decimal("200")),),
            sequence_rules=numeric_rule(),
        )
        self.assertIn("OUTLIER_ABOVE_MAX", {issue.code for issue in report.issues})

    def test_explicit_change_bound_fails_closed(self):
        records = (
            record(record_id="r1", sequence_id="1", event_time_ns=950),
            record(record_id="r2", sequence_id="2", event_time_ns=960),
        )
        observations = (
            NumericObservation(record_id="r1", metric="price", event_time_ns=950, value=Decimal("100")),
            NumericObservation(record_id="r2", metric="price", event_time_ns=960, value=Decimal("120")),
        )
        report = analyzer().analyze(
            batch(records),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            observations=observations,
            outlier_rules=(OutlierRule(metric="price", max_abs_change=Decimal("10")),),
            sequence_rules=numeric_rule(),
        )
        self.assertIn("OUTLIER_CHANGE", {issue.code for issue in report.issues})

    def test_missing_rule_for_supplied_observation_fails_closed(self):
        value = record(record_id="r1", sequence_id="1", event_time_ns=950)
        report = analyzer().analyze(
            batch((value,)),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            observations=(
                NumericObservation(record_id="r1", metric="price", event_time_ns=950, value=Decimal("100")),
            ),
            outlier_rules=(),
            sequence_rules=numeric_rule(),
        )
        self.assertIn("MISSING_OUTLIER_RULE", {issue.code for issue in report.issues})

    def test_unknown_observation_record_fails_closed(self):
        value = record(record_id="r1", sequence_id="1", event_time_ns=950)
        report = analyzer().analyze(
            batch((value,)),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            observations=(
                NumericObservation(record_id="missing", metric="price", event_time_ns=950, value=Decimal("100")),
            ),
            outlier_rules=(OutlierRule(metric="price", minimum=Decimal("0")),),
            sequence_rules=numeric_rule(),
        )
        self.assertIn("UNKNOWN_OBSERVATION_RECORD", {issue.code for issue in report.issues})


class SequenceTests(unittest.TestCase):
    def _codes(self, records: tuple[TimeSeriesRecord, ...], rules: tuple[SequenceRule, ...] | None = None):
        report = analyzer().analyze(
            batch(records),
            reference_time_ns=1000,
            freshness_rules=freshness(),
            sequence_rules=numeric_rule() if rules is None else rules,
        )
        return report, {issue.code for issue in report.issues}

    def test_numeric_gap_fails_closed(self):
        report, codes = self._codes((
            record(record_id="r1", sequence_id="1", event_time_ns=950, receive_time_ns=951),
            record(record_id="r3", sequence_id="3", event_time_ns=960, receive_time_ns=961),
        ))
        self.assertFalse(report.is_valid)
        self.assertIn("SEQUENCE_GAP", codes)

    def test_numeric_duplicate_fails_closed(self):
        _, codes = self._codes((
            record(record_id="r1", sequence_id="1", event_time_ns=950, receive_time_ns=951),
            record(record_id="r2", sequence_id="1", event_time_ns=960, receive_time_ns=961),
        ))
        self.assertIn("SEQUENCE_DUPLICATE", codes)

    def test_numeric_out_of_order_fails_closed(self):
        _, codes = self._codes((
            record(record_id="r2", sequence_id="2", event_time_ns=950, receive_time_ns=951),
            record(record_id="r1", sequence_id="1", event_time_ns=960, receive_time_ns=961),
        ))
        self.assertIn("SEQUENCE_OUT_OF_ORDER", codes)

    def test_numeric_parse_error_fails_closed(self):
        _, codes = self._codes((
            record(record_id="r1", sequence_id="opaque-a", event_time_ns=950),
        ))
        self.assertIn("SEQUENCE_PARSE_ERROR", codes)

    def test_opaque_sequence_is_not_coerced(self):
        value = record(record_id="r1", sequence_id="opaque-a", event_time_ns=950)
        rules = (
            SequenceRule(
                canonical_id=value.canonical_id,
                provider=value.provider,
                semantics=SequenceSemantics.OPAQUE_NO_ORDER,
            ),
        )
        report, codes = self._codes((value,), rules)
        self.assertTrue(report.is_valid)
        self.assertEqual(codes, set())
        self.assertEqual(report.opaque_sequence_streams, ("CRYPTO:BTC/USD:SPOT|reference-provider",))

    def test_missing_sequence_rule_fails_closed(self):
        report, codes = self._codes(
            (record(record_id="r1", sequence_id="1", event_time_ns=950),),
            (),
        )
        self.assertFalse(report.is_valid)
        self.assertIn("MISSING_SEQUENCE_RULE", codes)


class DeterminismTests(unittest.TestCase):
    def test_input_order_does_not_change_report(self):
        records = (
            record(record_id="r1", sequence_id="1", event_time_ns=950, receive_time_ns=951),
            record(record_id="r3", sequence_id="3", event_time_ns=960, receive_time_ns=961),
        )
        kwargs = dict(
            reference_time_ns=1000,
            freshness_rules=freshness(),
            observations=(
                NumericObservation(record_id="r1", metric="price", event_time_ns=950, value=Decimal("100")),
                NumericObservation(record_id="r3", metric="price", event_time_ns=960, value=Decimal("120")),
            ),
            outlier_rules=(OutlierRule(metric="price", max_abs_change=Decimal("10")),),
            sequence_rules=numeric_rule(),
        )
        first = analyzer().analyze(batch(records), **kwargs)
        second = analyzer().analyze(batch(tuple(reversed(records))), **kwargs)
        self.assertEqual(first.issues, second.issues)
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_batch_limit_fails_closed(self):
        policy = IntegrityCheckPolicy(
            max_records_per_batch=1,
            allowed_sequence_semantics=frozenset(SequenceSemantics),
            production_data_quality_vendor="NOT_SELECTED",
        )
        value = IntegrityAnalyzer(policy)
        with self.assertRaises(IntegrityCheckError):
            value.analyze(
                batch((
                    record(record_id="r1", sequence_id="1", event_time_ns=950),
                    record(record_id="r2", sequence_id="2", event_time_ns=960),
                )),
                reference_time_ns=1000,
                freshness_rules=freshness(),
                sequence_rules=numeric_rule(),
            )

    def test_upstream_evidence_digest_is_required(self):
        with self.assertRaises(IntegrityCheckError):
            IntegrityBatch(records=(), upstream_quality_evidence_sha256="bad")


if __name__ == "__main__":
    unittest.main()
