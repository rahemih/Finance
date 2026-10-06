#!/usr/bin/env python3
"""Persistent P04 Engineering Foundation exit/regression check."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
TASK_CATALOG = ROOT / "docs/13-tasks/TASK-CATALOG.md"
ROADMAP = ROOT / "docs/01-roadmap/MASTER-ROADMAP-v2.0.md"
WORKFLOW = ROOT / ".github/workflows/governance.yml"

WORKSTREAMS = {
    "FIN-P04-WA-001": "Repository / Workspace Structure",
    "FIN-P04-WB-001": "Language / Runtime / Dependency Baseline",
    "FIN-P04-WC-001": "CI/CD Foundation",
    "FIN-P04-WD-001": "Config / Environment Contract",
    "FIN-P04-WE-001": "Test Harness",
    "FIN-P04-WF-001": "Dependency / License / SBOM Governance",
    "FIN-P04-WG-001": "Developer Bootstrap & Tooling",
    "FIN-P04-WH-001": "Reproducible Build / Artifact Verification",
}

REQUIRED_JSON = [
    "docs/06-engineering/workspace-structure.json",
    "docs/06-engineering/runtime-dependency-baseline.json",
    "docs/06-engineering/ci-cd-foundation.json",
    "docs/06-engineering/config-environment-contract.json",
    "docs/06-engineering/test-harness.json",
    "docs/06-engineering/dependency-license-sbom-governance.json",
    "docs/06-engineering/developer-tooling.json",
    "docs/06-engineering/reproducible-build-evidence.json",
    "docs/06-engineering/p04-engineering-foundation-closure.json",
]

REQUIRED_WORKFLOW_STEPS = [
    "Developer environment doctor",
    "Config / environment contract",
    "Foundation test harness",
    "Dependency / waiver policy",
    "Generate CycloneDX 1.7 SBOM",
    "Validate SBOM / license policy",
    "Trivy supply-chain scan",
    "Reproducible clean-source build twice",
    "P04 engineering foundation exit",
]


class ExitFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ExitFailure(message)


def read_json(relative: str) -> dict:
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
            rf"^\|\s*{re.escape(task_id)}\s*\|\s*P04\s*\|\s*{re.escape(title)}\s*\|"
            rf".*\|\s*CANONICAL_COMPLETE\s*\|.*\|\s*RELEASED\s*\|$",
            re.MULTILINE,
        )
        if pattern.search(text) is None:
            fail(f"P04_TASK_NOT_CANONICAL task={task_id}")
    print("P04_TASK_CATALOG=PASS")


def check_manifests() -> None:
    manifests = {path: read_json(path) for path in REQUIRED_JSON}

    h = manifests["docs/06-engineering/reproducible-build-evidence.json"]
    if h.get("state") != "P04-H_CANONICAL_COMPLETE":
        fail(f"P04_H_STATE_INVALID state={h.get('state')}")
    if h.get("roadmap_gate") != "NONE_DEFINED_FOR_P04":
        fail("P04_ROADMAP_GATE_INVENTED_OR_CHANGED")

    closure = manifests["docs/06-engineering/p04-engineering-foundation-closure.json"]
    if closure.get("state") != "P04_CANONICAL_COMPLETE":
        fail(f"P04_CLOSURE_STATE_INVALID state={closure.get('state')}")
    if closure.get("verdict") != "PASS":
        fail(f"P04_CLOSURE_VERDICT_INVALID verdict={closure.get('verdict')}")
    workstreams = closure.get("workstreams", {})
    if set(workstreams) != set(WORKSTREAMS):
        fail("P04_CLOSURE_WORKSTREAM_SET_INVALID")
    for task_id, state in workstreams.items():
        if state != "CANONICAL_COMPLETE":
            fail(f"P04_CLOSURE_WORKSTREAM_INVALID task={task_id} state={state}")

    next_phase = closure.get("next_phase", {})
    if next_phase.get("phase") != "P05 — Real-Time Data":
        fail("P04_NEXT_PHASE_INVALID")
    if next_phase.get("state") != "NOT_STARTED_PENDING_OWNER_AUTHORIZATION":
        fail("P04_CLOSURE_NEXT_PHASE_SNAPSHOT_CHANGED")

    print("P04_MANIFESTS=PASS")


def check_workflow() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for step in REQUIRED_WORKFLOW_STEPS:
        if f"- name: {step}" not in text:
            fail(f"P04_REQUIRED_WORKFLOW_STEP_MISSING step={step}")
    if "permissions:\n  contents: read" not in text:
        fail("P04_GOVERNANCE_PERMISSION_BASELINE_CHANGED")
    print("P04_WORKFLOW_REGRESSION=PASS")


def check_safety() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    for marker in ("LIVE_TRADING = DISABLED", "AUTO_TRADING = DISABLED"):
        if marker not in roadmap:
            fail(f"P04_SAFETY_MARKER_MISSING marker={marker}")
    closure = read_json("docs/06-engineering/p04-engineering-foundation-closure.json")
    safety = closure.get("safety", {})
    expected = {
        "production_deployment": "NONE",
        "production_infrastructure_accounts_credentials": "NONE",
        "canary": "DISABLED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    if safety != expected:
        fail(f"P04_SAFETY_CLOSURE_INVALID actual={safety}")
    print("P04_SAFETY=PASS")


def main() -> int:
    try:
        check_catalog()
        check_manifests()
        check_workflow()
        check_safety()
    except ExitFailure as exc:
        print(f"P04_ENGINEERING_FOUNDATION_EXIT=FAIL error={exc}")
        return 1

    print("P04_ENGINEERING_FOUNDATION_EXIT=PASS")
    print("P04_STATE=CANONICAL_COMPLETE")
    print("P04_CLOSURE_NEXT_PHASE_STATE=NOT_STARTED_PENDING_OWNER_AUTHORIZATION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
