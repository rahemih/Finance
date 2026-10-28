#!/usr/bin/env python3
"""No-network reproducible *synthetic* DEMO report and privacy evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
from pathlib import Path

from packages.production.demo_telemetry_quarantine import (
    OfflineDemoTelemetry, canonical_bytes, render_html,
)

ROOT = Path(__file__).resolve().parents[2]


def sample() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "trace_id": "TRACE-0123456789abcdef",
        "source_kind": "SYNTHETIC_FIXTURE",
        "platform": "FIBO_MT5_DEMO",
        "environment": "DEMO",
        "currency_unit": "USD_CENTS",
        "observations": [
            {
                "observed_at_utc": "2026-10-01T10:00:00Z",
                "balance_minor": 10000,
                "equity_minor": 10000,
                "external_flow_minor": 0,
                "open_pnl_minor": 0,
                "quote_age_ms": 100,
                "connected": True,
                "trades_closed_count": 0,
                "rejected_orders_count": 0,
            },
            {
                "observed_at_utc": "2026-10-01T10:01:00Z",
                "balance_minor": 10000,
                "equity_minor": 9000,
                "external_flow_minor": 0,
                "open_pnl_minor": -1000,
                "quote_age_ms": 1501,
                "connected": False,
                "trades_closed_count": 0,
                "rejected_orders_count": 1,
            },
            {
                "observed_at_utc": "2026-10-01T10:02:00Z",
                "balance_minor": 10000,
                "equity_minor": 11000,
                "external_flow_minor": 0,
                "open_pnl_minor": 1000,
                "quote_age_ms": 200,
                "connected": True,
                "trades_closed_count": 1,
                "rejected_orders_count": 1,
            },
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--html", required=True)
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()
    output = OfflineDemoTelemetry(
        ROOT / "config/production/p24-demo-report-policy.json"
    ).evaluate(sample())
    if (
        output["source_kind"] != "SYNTHETIC_FIXTURE"
        or output["broker_source_attested"] is not False
        or output["broker_execution_certified"] is not False
        or output["pre_first_live_satisfied"] != 0
    ):
        raise RuntimeError("forbidden demo provenance or production promotion")
    j = canonical_bytes(output) + b"\n"
    h = render_html(output).encode("utf-8")
    writer_buffer = io.StringIO(newline="")
    writer = csv.writer(writer_buffer, lineterminator="\n")
    writer.writerow(("observed_at_utc", "equity_minor", "drawdown_bps", "quote_age_ms", "connected"))
    for item in output["observations"]:
        writer.writerow((
            item["observed_at_utc"], item["equity_minor"], item["drawdown_bps"],
            item["quote_age_ms"], item["connected"],
        ))
    c = writer_buffer.getvalue().encode("utf-8")
    for name, data in ((args.json, j), (args.html, h), (args.csv, c)):
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f"P24_WP_SYNTHETIC_DEMO_REPORT=PASS samples={output['number_of_samples']} "
          f"report_id={output['report_id']}")
    print(
        f"json_sha256={hashlib.sha256(j).hexdigest()} "
        f"html_sha256={hashlib.sha256(h).hexdigest()} "
        f"csv_sha256={hashlib.sha256(c).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
