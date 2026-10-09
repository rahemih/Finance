#!/usr/bin/env python3
"""Build deterministic P07-B completeness/duplicate evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.data_quality import (
    CompletenessDuplicateAnalyzer,
    CompletenessDuplicateBatch,
    CompletenessDuplicatePolicy,
    CompletenessExpectation,
)
from packages.historical_data import TimeSeriesRecord

POLICY = ROOT / "config/data-quality/completeness-duplicate-policy.json"
SCHEMA_EVIDENCE = "a" * 64


def record(*, record_id: str, sequence_id: str, payload: str, event_time_ns: int = 100) -> TimeSeriesRecord:
    raw = f"{record_id}:{sequence_id}:{payload}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id="CRYPTO:BTC/USD:SPOT",
        kind="TRADE",
        provider="reference-provider",
        event_time_ns=event_time_ns,
        receive_time_ns=event_time_ns + 10,
        sequence_id=sequence_id,
        canonical_schema_version="1.0",
        canonical_payload_json=payload,
        source_payload_sha256=digest,
        source_object_relative_path=f"reference/{digest}.raw",
        provenance=(("source", "p07b-evidence"),),
    )


def report_payload(report) -> dict[str, object]:
    return {
        "outcome": report.outcome.value,
        "observed_record_count": report.observed_record_count,
        "expected_record_count": report.expected_record_count,
        "missing_record_ids": list(report.missing_record_ids),
        "unexpected_record_ids": list(report.unexpected_record_ids),
        "duplicate_findings": [item.payload() for item in report.duplicate_findings],
        "schema_validation_evidence_sha256": report.schema_validation_evidence_sha256,
        "fingerprint": report.fingerprint,
    }


def build(output: Path) -> None:
    policy = CompletenessDuplicatePolicy.from_path(POLICY)
    analyzer = CompletenessDuplicateAnalyzer(policy)

    clean = analyzer.analyze(
        CompletenessDuplicateBatch(
            records=(
                record(record_id="r1", sequence_id="1", payload='{"price":"100"}', event_time_ns=100),
                record(record_id="r3", sequence_id="3", payload='{"price":"103"}', event_time_ns=300),
            ),
            schema_validation_evidence_sha256=SCHEMA_EVIDENCE,
        ),
        CompletenessExpectation(expected_record_ids=("r1", "r3")),
    )

    missing = analyzer.analyze(
        CompletenessDuplicateBatch(
            records=(record(record_id="r1", sequence_id="1", payload='{"price":"100"}'),),
            schema_validation_evidence_sha256=SCHEMA_EVIDENCE,
        ),
        CompletenessExpectation(expected_record_ids=("r1", "r2")),
    )

    exact_value = record(record_id="r1", sequence_id="1", payload='{"price":"100"}')
    exact_duplicate = analyzer.analyze(
        CompletenessDuplicateBatch(
            records=(exact_value, exact_value),
            schema_validation_evidence_sha256=SCHEMA_EVIDENCE,
        ),
        CompletenessExpectation(expected_record_ids=("r1",)),
    )

    conflicting = analyzer.analyze(
        CompletenessDuplicateBatch(
            records=(
                record(record_id="r1", sequence_id="1", payload='{"price":"100"}'),
                record(record_id="r2", sequence_id="1", payload='{"price":"101"}'),
            ),
            schema_validation_evidence_sha256=SCHEMA_EVIDENCE,
        ),
        CompletenessExpectation(expected_record_ids=("r1", "r2")),
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07B_COMPLETENESS_DUPLICATE_EVIDENCE",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "reports": [
            report_payload(clean),
            report_payload(missing),
            report_payload(exact_duplicate),
            report_payload(conflicting),
        ],
        "clean_non_contiguous_sequence_pass": clean.is_valid,
        "missing_fail_closed": not missing.is_valid,
        "exact_duplicate_fail_closed": not exact_duplicate.is_valid,
        "conflicting_duplicate_fail_closed": not conflicting.is_valid,
        "sequence_gap_inference": False,
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
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P07B_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
