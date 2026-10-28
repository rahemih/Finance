#!/usr/bin/env python3
"""Generate no-network P24-WO synthetic fault-drill JSON, CSV, HTML evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
from pathlib import Path

from packages.execution.broker_simulation_gate import BrokerSimulationPolicy
from packages.production.offline_preproduction_lab import (
    canonical_bytes, digest, render_html, run_reference_suite,
)

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", required=True)
    parser.add_argument("--html", dest="html_path", required=True)
    parser.add_argument("--csv", dest="csv_path", required=True)
    args = parser.parse_args()

    report = run_reference_suite(ROOT / "config/production/p24-offline-lab-policy.json")
    upstream = BrokerSimulationPolicy.from_path(
        ROOT / "config/execution/broker-simulation-g11-policy.json"
    )
    report["upstream_p20_reference_policy_id"] = upstream.policy_id
    report["evidence_id"] = digest({k: v for k, v in report.items() if k != "evidence_id"})
    if report["broker_demo_events_observed"] != 0 or report["pre_live_kill_switch_certified"] is not False:
        raise RuntimeError("reference evidence scope escalated")
    j = canonical_bytes(report) + b"\n"
    h = render_html(report).encode("utf-8")
    csv_stream = io.StringIO(newline="")
    writer = csv.writer(csv_stream, lineterminator="\n")
    writer.writerow(("scenario", "state", "event_count", "fail_closed_count", "snapshot_id"))
    for item in report["scenarios"]:
        snap = item["snapshot"]
        writer.writerow((
            item["scenario"], snap["final_state"], snap["event_count"],
            snap["fail_closed_count"], snap["snapshot_id"],
        ))
    c = csv_stream.getvalue().encode("utf-8")
    for path_text, payload in ((args.json_path, j), (args.html_path, h), (args.csv_path, c)):
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"P24_WO_SYNTHETIC_REFERENCE=PASS scenarios={report['scenario_count']} "
          f"events={report['event_count']} evidence_id={report['evidence_id']}")
    print(f"json_sha256={hashlib.sha256(j).hexdigest()} "
          f"html_sha256={hashlib.sha256(h).hexdigest()} "
          f"csv_sha256={hashlib.sha256(c).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
