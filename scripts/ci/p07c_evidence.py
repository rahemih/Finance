#!/usr/bin/env python3
"""Build deterministic P07-C integrity-check evidence offline."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.data_quality import (
    FreshnessRule,
    IntegrityAnalyzer,
    IntegrityBatch,
    IntegrityCheckPolicy,
    NumericObservation,
    OutlierRule,
    SequenceRule,
    SequenceSemantics,
)
from packages.historical_data import TimeSeriesRecord

POLICY = ROOT / "config/data-quality/integrity-check-policy.json"
UPSTREAM = "a" * 64


def record(
    *,
    record_id: str,
    sequence_id: str,
    event_time_ns: int,
    receive_time_ns: int,
) -> TimeSeriesRecord:
    raw = f"{sequence_id}:{event_time_ns}:{receive_time_ns}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id="CRYPTO:BTC/USD:SPOT",
        kind="TRADE",
        provider="reference-provider",
        event_time_ns=event_time_ns,
        receive_time_ns=receive_time_ns,
        sequence_id=sequence_id,
        canonical_schema_version="1.0",
        canonical_payload_json='{"price":"100"}',
        source_payload_sha256=digest,
        source_object_relative_path=f"reference/{digest}.raw",
        provenance=(("source", "p07c-evidence"),),
    )


def report_payload(report) -> dict[str, object]:
    return {
        "outcome": report.outcome.value,
        "issues": [issue.payload() for issue in report.issues],
        "opaque_sequence_streams": list(report.opaque_sequence_streams),
        "upstream_quality_evidence_sha256": report.upstream_quality_evidence_sha256,
        "fingerprint": report.fingerprint,
    }


def build(output: Path) -> None:
    policy = IntegrityCheckPolicy.from_path(POLICY)
    analyzer = IntegrityAnalyzer(policy)
    freshness = (FreshnessRule(kind="TRADE", max_event_age_ns=100, max_receive_age_ns=100),)
    sequence = (
        SequenceRule(
            canonical_id="CRYPTO:BTC/USD:SPOT",
            provider="reference-provider",
            semantics=SequenceSemantics.NUMERIC_MONOTONIC_CONTIGUOUS,
        ),
    )

    clean_records = (
        record(record_id="r1", sequence_id="1", event_time_ns=950, receive_time_ns=951),
        record(record_id="r2", sequence_id="2", event_time_ns=960, receive_time_ns=961),
    )
    clean = analyzer.analyze(
        IntegrityBatch(records=clean_records, upstream_quality_evidence_sha256=UPSTREAM),
        reference_time_ns=1000,
        freshness_rules=freshness,
        observations=(
            NumericObservation(record_id="r1", metric="price", event_time_ns=950, value=Decimal("100")),
            NumericObservation(record_id="r2", metric="price", event_time_ns=960, value=Decimal("105")),
        ),
        outlier_rules=(OutlierRule(metric="price", minimum=Decimal("0"), maximum=Decimal("1000"), max_abs_change=Decimal("10")),),
        sequence_rules=sequence,
    )

    stale = analyzer.analyze(
        IntegrityBatch(
            records=(record(record_id="stale", sequence_id="1", event_time_ns=800, receive_time_ns=810),),
            upstream_quality_evidence_sha256=UPSTREAM,
        ),
        reference_time_ns=1000,
        freshness_rules=freshness,
        sequence_rules=sequence,
    )

    outlier = analyzer.analyze(
        IntegrityBatch(
            records=(record(record_id="outlier", sequence_id="1", event_time_ns=950, receive_time_ns=951),),
            upstream_quality_evidence_sha256=UPSTREAM,
        ),
        reference_time_ns=1000,
        freshness_rules=freshness,
        observations=(
            NumericObservation(record_id="outlier", metric="price", event_time_ns=950, value=Decimal("5000")),
        ),
        outlier_rules=(OutlierRule(metric="price", maximum=Decimal("1000")),),
        sequence_rules=sequence,
    )

    sequence_gap = analyzer.analyze(
        IntegrityBatch(
            records=(
                record(record_id="s1", sequence_id="1", event_time_ns=950, receive_time_ns=951),
                record(record_id="s3", sequence_id="3", event_time_ns=960, receive_time_ns=961),
            ),
            upstream_quality_evidence_sha256=UPSTREAM,
        ),
        reference_time_ns=1000,
        freshness_rules=freshness,
        sequence_rules=sequence,
    )

    opaque_record = record(record_id="opaque", sequence_id="abc-x", event_time_ns=950, receive_time_ns=951)
    opaque = analyzer.analyze(
        IntegrityBatch(records=(opaque_record,), upstream_quality_evidence_sha256=UPSTREAM),
        reference_time_ns=1000,
        freshness_rules=freshness,
        sequence_rules=(
            SequenceRule(
                canonical_id=opaque_record.canonical_id,
                provider=opaque_record.provider,
                semantics=SequenceSemantics.OPAQUE_NO_ORDER,
            ),
        ),
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07C_INTEGRITY_EVIDENCE",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "reports": [
            report_payload(clean),
            report_payload(stale),
            report_payload(outlier),
            report_payload(sequence_gap),
            report_payload(opaque),
        ],
        "clean_pass": clean.is_valid,
        "stale_fail_closed": not stale.is_valid,
        "outlier_fail_closed": not outlier.is_valid,
        "sequence_gap_fail_closed": not sequence_gap.is_valid,
        "opaque_sequence_no_coercion_pass": opaque.is_valid,
        "adaptive_thresholds": False,
        "production_data_quality_vendor": policy.production_data_quality_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P07C_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
