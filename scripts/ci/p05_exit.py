#!/usr/bin/env python3
"""Persistent P05 Real-Time Data gate/regression check."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
TASK_CATALOG = ROOT / "docs/13-tasks/TASK-CATALOG.md"
CURRENT_STATE = ROOT / "docs/02-current-state/CURRENT-STATE.md"
WORKFLOW = ROOT / ".github/workflows/governance.yml"
GATE = ROOT / "docs/07-data/p05-h-realtime-data-gate.json"

WORKSTREAMS = {
    "FIN-P05-WA-001": "Crypto Real-Time Adapter / Kaiko Baseline",
    "FIN-P05-WB-001": "Forex Real-Time Adapter / dxFeed Quote Baseline",
    "FIN-P05-WC-001": "Context Market Adapter / Databento Gold MBP-1 Baseline",
    "FIN-P05-WD-001": "Canonical Normalization / Symbol Master / Clock Model",
    "FIN-P05-WE-001": "Streaming / Heartbeat / Backpressure",
    "FIN-P05-WF-001": "Reconnect / Failover / Gap Recovery",
    "FIN-P05-WG-001": "Latency / Throughput / Soak Validation",
}

MANIFESTS = {
    "P05-A": "docs/07-data/p05-a-crypto-realtime-adapter.json",
    "P05-B": "docs/07-data/p05-b-forex-realtime-adapter.json",
    "P05-C": "docs/07-data/p05-c-context-market-adapter.json",
    "P05-D": "docs/07-data/p05-d-canonical-normalization-symbol-clock.json",
    "P05-E": "docs/07-data/p05-e-streaming-heartbeat-backpressure.json",
    "P05-F": "docs/07-data/p05-f-reconnect-failover-gap-recovery.json",
    "P05-G": "docs/07-data/p05-g-latency-throughput-soak-validation.json",
}


class GateFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise GateFailure(message)


def read_json(relative: str) -> dict[str, object]:
    path = ROOT / relative
    if not path.is_file():
        fail(f"REQUIRED_JSON_MISSING path={relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"REQUIRED_JSON_INVALID path={relative} error={exc}")
    if not isinstance(value, dict):
        fail(f"REQUIRED_JSON_OBJECT path={relative}")
    return value


def check_catalog() -> None:
    text = TASK_CATALOG.read_text(encoding="utf-8")
    for task_id, title in WORKSTREAMS.items():
        pattern = re.compile(
            rf"^\|\s*{re.escape(task_id)}\s*\|\s*P05\s*\|\s*{re.escape(title)}\s*\|"
            rf".*\|\s*CANONICAL_COMPLETE\s*\|.*\|\s*RELEASED\s*\|$",
            re.MULTILINE,
        )
        if pattern.search(text) is None:
            fail(f"P05_TASK_NOT_CANONICAL task={task_id}")
    print("P05_TASK_CATALOG=PASS")


def check_manifests() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for label, relative in MANIFESTS.items():
        value = read_json(relative)
        if value.get("state") != f"{label}_CANONICAL_COMPLETE":
            fail(f"P05_MANIFEST_STATE_INVALID workstream={label} state={value.get('state')}")
        for marker in ("canary", "live_trading", "auto_trading"):
            if value.get(marker) != "DISABLED":
                fail(
                    f"P05_SAFETY_INVALID workstream={label} marker={marker} "
                    f"value={value.get(marker)}"
                )
        result[label] = value

    e = result["P05-E"]
    buffer_value = e.get("buffer")
    if not isinstance(buffer_value, dict):
        fail("P05_E_BUFFER_MISSING")
    if buffer_value.get("max_events") != 1_200_000:
        fail(f"P05_E_BUFFER_CAPACITY_INVALID value={buffer_value.get('max_events')}")

    f = result["P05-F"]
    if f.get("automatic_data_failover") is not False:
        fail("P05_F_AUTOMATIC_FAILOVER_NOT_DISABLED")

    g = result["P05-G"]
    closure = g.get("closure_evidence")
    if not isinstance(closure, dict):
        fail("P05_G_CLOSURE_EVIDENCE_MISSING")
    measured = closure.get("measured_postmerge")
    if not isinstance(measured, dict):
        fail("P05_G_MEASURED_EVIDENCE_MISSING")
    if float(measured.get("p95_ms", 1e9)) > 250.0:
        fail("P05_G_P95_FAIL")
    if float(measured.get("p99_ms", 1e9)) > 1000.0:
        fail("P05_G_P99_FAIL")
    if float(measured.get("stream_events_per_sec", 0.0)) < 20_000.0:
        fail("P05_G_STREAM_THROUGHPUT_FAIL")
    if float(measured.get("soak_events_per_sec", 0.0)) < 2_000.0:
        fail("P05_G_SOAK_THROUGHPUT_FAIL")

    print("P05_MANIFESTS=PASS")
    return result


def check_gate() -> None:
    value = read_json("docs/07-data/p05-h-realtime-data-gate.json")
    if value.get("gate") != "G4_REALTIME_DATA":
        fail("P05_GATE_ID_INVALID")
    if value.get("verdict") != "PASS":
        fail(f"P05_GATE_VERDICT_INVALID value={value.get('verdict')}")
    criteria = value.get("criteria")
    if not isinstance(criteria, list) or len(criteria) != 16:
        fail("P05_GATE_CRITERIA_COUNT_INVALID")
    failed = [
        item
        for item in criteria
        if not isinstance(item, dict) or item.get("status") != "PASS"
    ]
    if failed:
        fail(f"P05_GATE_CRITERIA_FAILED count={len(failed)}")
    if value.get("criteria_failed") != 0:
        fail("P05_GATE_FAILED_COUNT_NONZERO")
    print("P05_GATE_MATRIX=PASS")


def check_workflow() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    required = [
        "P05 real-time data tests",
        "P05-G measured performance validation",
        "P05 real-time data gate",
        "Trivy supply-chain scan",
        "Reproducible clean-source build twice",
    ]
    for step in required:
        if f"- name: {step}" not in text:
            fail(f"P05_REQUIRED_WORKFLOW_STEP_MISSING step={step}")
    print("P05_WORKFLOW_REGRESSION=PASS")


def check_current_safety() -> None:
    text = CURRENT_STATE.read_text(encoding="utf-8")
    for marker in (
        "Live Trading: DISABLED",
        "Auto Trading: DISABLED",
        "Credentials: NONE",
    ):
        if marker not in text:
            fail(f"P05_CURRENT_SAFETY_MARKER_MISSING marker={marker}")
    print("P05_CURRENT_SAFETY=PASS")


def main() -> int:
    try:
        check_catalog()
        check_manifests()
        check_gate()
        check_workflow()
        check_current_safety()
    except GateFailure as exc:
        print(f"P05_REALTIME_DATA_GATE=FAIL error={exc}")
        return 1

    print("P05_REALTIME_DATA_GATE=PASS")
    print("G4_REALTIME_DATA=PASS_PENDING_CANONICAL_MERGE_OR_CLOSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
