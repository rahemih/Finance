#!/usr/bin/env python3
"""Reproducible synthetic, no-network P24-WQ source comparison evidence."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.production.multisource_reference_lab import (
    MultiSourceReferenceLab, ROLES, SyntheticQuote, canonical, digest, render_html,
)


def fixture() -> tuple[SyntheticQuote, ...]:
    values = {
        "DUKASCOPY_SIM": ("1.10000", "0.00010"),
        "FX_INDEPENDENT_SIM": ("1.10005", "0.00010"),
        "FIBO_SIM": ("1.10015", "0.00010"),
        "BINANCE_ARCHIVE_SIM": ("70000", "1"),
        "CRYPTO_INDEPENDENT_SIM": ("70002", "1"),
        "USDTIRT_SIM": ("60000", "1"),
        "TABDEAL_SPOT_SIM": ("4200150000", "1000"),
    }
    result = []
    for name, (market, pair, root, role) in ROLES.items():
        mid, spread = (Decimal(x) for x in values[name])
        result.append(SyntheticQuote(
            provider=name, market=market, pair=pair, root=root, role=role,
            bid=mid - spread / 2, ask=mid + spread / 2,
            event_time_ms=999900, observed_time_ms=999940,
            lineage_sha256=digest({"SYNTHETIC_SOURCE": name}),
        ))
    return tuple(result)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--html", required=True)
    args = ap.parse_args()
    lab = MultiSourceReferenceLab(
        ROOT / "config/production/p24-multisource-reference-policy.json",
        ROOT / "config/data-quality/cross-provider-policy.json",
    )
    report = lab.evaluate(fixture(), 1_000_000)
    if (report["outcome"] != "SYNTHETIC_CONSISTENCY_ONLY"
            or report["real_source_quotes_observed"] != 0
            or report["order_authority"] is not False):
        raise ValueError("synthetic report is not admissible")
    raw_json = canonical(report) + b"\n"
    raw_html = render_html(report).encode("utf-8")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("pair", "reference_mid", "destination_mid", "drift_bps", "outcome"))
    for item in report["comparison"]:
        writer.writerow(tuple(item[key] for key in ("pair", "reference_mid", "destination_mid", "drift_bps", "outcome")))
    raw_csv = buffer.getvalue().encode("utf-8")
    for path, value in ((args.json, raw_json), (args.csv, raw_csv), (args.html, raw_html)):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
    print("P24_WQ_SYNTHETIC_REFERENCE=PASS sources=7 comparisons=2")
    print("evidence_id=" + str(report["evidence_id"]))
    for name, content in (("json", raw_json), ("csv", raw_csv), ("html", raw_html)):
        print(name + "_sha256=" + hashlib.sha256(content).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
