#!/usr/bin/env python3
"""Build deterministic P06-C time-series query-layer evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(record_id: str, canonical_id: str, event_time_ns: int, *, kind: str = "TRADE") -> TimeSeriesRecord:
    raw = f"{record_id}:raw".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id=record_id,
        canonical_id=canonical_id,
        kind=kind,
        provider="reference-provider",
        event_time_ns=event_time_ns,
        receive_time_ns=event_time_ns + 10_000,
        sequence_id=record_id,
        canonical_schema_version="1.0",
        canonical_payload_json=json.dumps(
            {"record_id": record_id, "value": event_time_ns},
            sort_keys=True,
            separators=(",", ":"),
        ),
        source_payload_sha256=digest,
        source_object_relative_path=f"reference-provider/2026/06/07/stream/{digest}.raw",
        provenance=(("backfill_task", "FIN-P06-WB-001"),),
    )


def build(output: Path) -> None:
    policy = TimeSeriesQueryPolicy.from_path(POLICY)
    records = (
        record("btc-d1-0", "CRYPTO:BTC-USD", DAY + 10),
        record("btc-d1-1", "CRYPTO:BTC-USD", DAY + 20, kind="QUOTE"),
        record("btc-d2-0", "CRYPTO:BTC-USD", DAY * 2 + 10),
        record("btc-d3-0", "CRYPTO:BTC-USD", DAY * 3 + 10),
        record("eur-d1-0", "FX:EUR-USD", DAY + 10),
        record("eur-d2-0", "FX:EUR-USD", DAY * 2 + 10),
        record("eur-d3-0", "FX:EUR-USD", DAY * 3 + 10),
        record("eur-d4-0", "FX:EUR-USD", DAY * 4 + 10),
    )
    index = TimeSeriesQueryIndex(records, policy)
    result = index.query(
        TimeSeriesQuery(
            start_ns=DAY,
            end_ns=DAY * 2,
            limit=10,
            canonical_ids=("CRYPTO:BTC-USD",),
        )
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06C_TIME_SERIES_QUERY_EVIDENCE",
        "policy_sha256": sha256(POLICY),
        "index_fingerprint": index.fingerprint,
        "total_records": index.total_records,
        "partition_count": index.partition_count,
        "query": {
            "window_semantics": "HALF_OPEN_START_INCLUSIVE_END_EXCLUSIVE",
            "start_ns": DAY,
            "end_ns": DAY * 2,
            "canonical_ids": ["CRYPTO:BTC-USD"],
        },
        "result_record_ids": [item.record_id for item in result.records],
        "matched_count": result.matched_count,
        "candidate_count": result.candidate_count,
        "partitions_examined": result.partitions_examined,
        "partition_pruning_proven": result.candidate_count < result.total_index_records,
        "production_query_storage_vendor": policy.production_query_storage_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P06C_EVIDENCE=PASS output={output}")
    print(f"P06C_INDEX_FINGERPRINT={index.fingerprint}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
