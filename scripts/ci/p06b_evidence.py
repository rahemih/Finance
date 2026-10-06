#!/usr/bin/env python3
"""Build deterministic P06-B historical-backfill evidence offline."""

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
    BackfillPage,
    BackfillPolicy,
    BackfillRequest,
    FilesystemRawArchive,
    HistoricalBackfillRunner,
    RawArchivePolicy,
    RawArchiveRightsError,
    RightsState,
)

RAW_POLICY = ROOT / "config/historical-data/raw-archive-policy.json"
BACKFILL_POLICY = ROOT / "config/historical-data/backfill-policy.json"
PAGES = (
    BackfillPage(
        ordinal=0,
        payload=b'{"kind":"trade","page":0,"price":"123.45"}\n',
        captured_at_ns=1_780_819_201_000_000_000,
        source_event_id="historical-page-0000",
        source_timestamp="2026-06-07T00:00:01Z",
    ),
    BackfillPage(
        ordinal=1,
        payload=b'{"kind":"trade","page":1,"price":"123.55"}\n',
        captured_at_ns=1_780_819_202_000_000_000,
        source_event_id="historical-page-0001",
        source_timestamp="2026-06-07T00:00:02Z",
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    request = BackfillRequest(
        provider="reference-provider",
        source_stream="venue:spot:asset-usd:trades:historical",
        window_start_ns=1_780_819_200_000_000_000,
        window_end_ns=1_780_905_600_000_000_000,
        rights_state=RightsState.RETENTION_ALLOWED,
        retention_class="MARKET_DATA_RAW",
        media_type="application/json",
    )
    backfill_policy = BackfillPolicy.from_path(BACKFILL_POLICY)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        runner = HistoricalBackfillRunner(
            FilesystemRawArchive(root, RawArchivePolicy.from_path(RAW_POLICY)),
            backfill_policy,
        )
        first = runner.run(request, PAGES)
        second = runner.run(request, PAGES)
        exact = [
            (root / archived.object_relative_path).read_bytes() == source.payload
            for source, archived in zip(PAGES, first.pages, strict=True)
        ]
        forbidden_fail_closed = False
        try:
            runner.run(
                BackfillRequest(
                    provider=request.provider,
                    source_stream=request.source_stream,
                    window_start_ns=request.window_start_ns,
                    window_end_ns=request.window_end_ns,
                    rights_state=RightsState.RETENTION_FORBIDDEN,
                    retention_class=request.retention_class,
                    media_type=request.media_type,
                ),
                PAGES,
            )
        except RawArchiveRightsError:
            forbidden_fail_closed = True

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06B_HISTORICAL_BACKFILL_EVIDENCE",
        "raw_policy_sha256": sha256(RAW_POLICY),
        "backfill_policy_sha256": sha256(BACKFILL_POLICY),
        "request_fingerprint": first.request_fingerprint,
        "page_count": first.page_count,
        "total_bytes": first.total_bytes,
        "page_sha256": [page.payload_sha256 for page in first.pages],
        "exact_raw_bytes": exact,
        "first_created_pages": first.created_pages,
        "second_created_pages": second.created_pages,
        "second_idempotent_pages": second.idempotent_pages,
        "forbidden_rights_fail_closed": forbidden_fail_closed,
        "production_historical_provider_entitlement": backfill_policy.production_historical_provider_entitlement,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "production_storage_vendor": backfill_policy.production_storage_vendor,
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
    print(f"P06B_EVIDENCE=PASS output={output}")
    print(f"P06B_REQUEST_FINGERPRINT={first.request_fingerprint}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
