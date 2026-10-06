#!/usr/bin/env python3
"""Measure the vendor-neutral P06-C reference query index on synthetic data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    TimeSeriesQuery,
    TimeSeriesQueryIndex,
    TimeSeriesQueryPolicy,
    TimeSeriesRecord,
)

POLICY = ROOT / "config/historical-data/query-layer-policy.json"
DAY = 86_400_000_000_000


def record(index: int) -> TimeSeriesRecord:
    canonical_id = f"CRYPTO:ASSET-{index % 20:02d}"
    day = index // 2000
    event_time_ns = day * DAY + (index % 2000) * 1_000_000
    raw = f"synthetic-{index}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=f"record-{index:05d}",
        canonical_id=canonical_id,
        kind="TRADE",
        provider="reference-provider",
        event_time_ns=event_time_ns,
        receive_time_ns=event_time_ns + 1_000,
        sequence_id=f"{index:05d}",
        canonical_schema_version="1.0",
        canonical_payload_json=f'{{"i":{index}}}',
        source_payload_sha256=digest,
        source_object_relative_path=f"reference-provider/2026/06/07/stream/{digest}.raw",
    )


def build(output: Path) -> None:
    policy = TimeSeriesQueryPolicy.from_path(POLICY)
    records = tuple(record(index) for index in range(20_000))
    started = time.perf_counter()
    query_index = TimeSeriesQueryIndex(records, policy)
    build_seconds = time.perf_counter() - started

    queries = 400
    candidate_total = 0
    started = time.perf_counter()
    for query_number in range(queries):
        day = query_number % 10
        asset = query_number % 20
        result = query_index.query(
            TimeSeriesQuery(
                start_ns=day * DAY,
                end_ns=(day + 1) * DAY,
                limit=500,
                canonical_ids=(f"CRYPTO:ASSET-{asset:02d}",),
            )
        )
        candidate_total += result.candidate_count
    query_seconds = time.perf_counter() - started
    queries_per_second = queries / max(query_seconds, 1e-9)
    minimum = policy.minimum_synthetic_queries_per_second
    if queries_per_second < minimum:
        raise RuntimeError(
            f"P06C synthetic query throughput below policy: {queries_per_second:.2f} < {minimum}"
        )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06C_SYNTHETIC_PERFORMANCE",
        "records": len(records),
        "partitions": query_index.partition_count,
        "queries": queries,
        "build_seconds": round(build_seconds, 6),
        "query_seconds": round(query_seconds, 6),
        "queries_per_second": round(queries_per_second, 2),
        "minimum_queries_per_second": minimum,
        "average_candidates_per_query": candidate_total / queries,
        "status": "PASS",
        "environment": "CI_SYNTHETIC_REFERENCE_NOT_PRODUCTION_CAPACITY"
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "P06C_PERFORMANCE=PASS "
        f"records={len(records)} queries={queries} qps={queries_per_second:.2f} minimum={minimum}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
