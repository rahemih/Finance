#!/usr/bin/env python3
"""Build deterministic offline synthetic market CSV import evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.production.local_reference_import import (
    ImportContext, LocalReferenceImport, canonical, render_html,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--html", required=True)
    args = parser.parse_args()
    src = (
        b"event_time_ms,bid,ask\n"
        b"999000,1.1000,1.1002\n"
        b"999100,1.1001,1.1003\n"
        b"999300,1.1002,1.1004\n"
    )
    loader = LocalReferenceImport(ROOT / "config/production/p24-local-reference-import-policy.json")
    context = ImportContext("FX_REFERENCE_CANDIDATE", "FOREX", "EURUSD", "REFERENCE_ONLY")
    report = loader.parse(src, context, now_ms=1000000)
    if (report["source_licensed"] is not False
            or report["downstream_signal_allowed"] is not False
            or report["external_order_authority"] is not False):
        raise RuntimeError("failed synthetic rights/authority invariant")
    json_data = canonical(report) + b"\n"
    html_data = render_html(report).encode("utf-8")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("event_time_ms", "bid", "ask", "mid"))
    for value in report["samples"]:
        writer.writerow([value[k] for k in ("event_time_ms", "bid", "ask", "mid")])
    csv_data = buffer.getvalue().encode("utf-8")
    for path, content in ((args.json, json_data), (args.csv, csv_data), (args.html, html_data)):
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    print(f"P24_WS_SYNTHETIC_CSV_IMPORT=PASS samples={report['sample_count']} evidence_id={report['evidence_id']}")
    for name, content in (("json", json_data), ("csv", csv_data), ("html", html_data)):
        print(f"{name}_sha256={hashlib.sha256(content).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
