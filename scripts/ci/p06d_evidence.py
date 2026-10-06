#!/usr/bin/env python3
"""Build deterministic P06-D dataset-manifest evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    DatasetManifest,
    DatasetManifestPolicy,
    FilesystemDatasetManifestStore,
    TimeSeriesQueryIndex,
    TimeSeriesQueryPolicy,
    TimeSeriesRecord,
)

MANIFEST_POLICY = ROOT / "config/historical-data/dataset-manifest-policy.json"
QUERY_POLICY = ROOT / "config/historical-data/query-layer-policy.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(record_id: str, event_time_ns: int, price: str) -> TimeSeriesRecord:
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
        canonical_payload_json=json.dumps({"price": price}, sort_keys=True, separators=(",", ":")),
        source_payload_sha256=digest,
        source_object_relative_path=f"reference-provider/2026/06/07/stream/{digest}.raw",
        provenance=(("backfill_task", "FIN-P06-WB-001"),),
    )


def build(output: Path) -> None:
    manifest_policy = DatasetManifestPolicy.from_path(MANIFEST_POLICY)
    query_policy = TimeSeriesQueryPolicy.from_path(QUERY_POLICY)
    records = (
        record("trade-0001", 10, "100.00"),
        record("trade-0002", 20, "100.50"),
        record("trade-0003", 30, "101.00"),
    )
    index = TimeSeriesQueryIndex(records, query_policy)
    first = DatasetManifest.build(
        dataset_name="btc-usd-trades-reference",
        dataset_schema_version="1.0",
        window_start_ns=0,
        window_end_ns=100,
        rights_class="NON_DISPLAY_INTERNAL",
        query_index_fingerprint=index.fingerprint,
        records=records,
        policy=manifest_policy,
    )
    reordered = DatasetManifest.build(
        dataset_name="btc-usd-trades-reference",
        dataset_schema_version="1.0",
        window_start_ns=0,
        window_end_ns=100,
        rights_class="NON_DISPLAY_INTERNAL",
        query_index_fingerprint=index.fingerprint,
        records=tuple(reversed(records)),
        policy=manifest_policy,
    )

    with tempfile.TemporaryDirectory() as temp:
        store = FilesystemDatasetManifestStore(Path(temp), manifest_policy)
        first_write = store.save(first)
        second_write = store.save(first)
        loaded = store.load(first.dataset_name, first.dataset_version)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06D_DATASET_MANIFEST_EVIDENCE",
        "manifest_policy_sha256": sha256(MANIFEST_POLICY),
        "query_policy_sha256": sha256(QUERY_POLICY),
        "dataset_name": first.dataset_name,
        "dataset_version": first.dataset_version,
        "membership_root_sha256": first.membership_root_sha256,
        "member_count": len(first.members),
        "member_digests": [member.member_digest for member in first.members],
        "order_independent_version": first.dataset_version == reordered.dataset_version,
        "round_trip_exact": loaded == first,
        "first_write_created": first_write.created,
        "second_write_idempotent": not second_write.created,
        "manifest_relative_path": first_write.relative_path,
        "production_manifest_storage_vendor": manifest_policy.production_manifest_storage_vendor,
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
    print(f"P06D_EVIDENCE=PASS output={output}")
    print(f"P06D_DATASET_VERSION={first.dataset_version}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
