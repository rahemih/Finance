#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = tuple(f"P20-{letter}" for letter in "ABCDEFGHI")
MANIFESTS = {
    "P20-A": ROOT / "docs/15-execution/p20-a-adapter-contract.json",
    "P20-B": ROOT / "docs/15-execution/p20-b-crypto-execution-adapter.json",
    "P20-C": ROOT / "docs/15-execution/p20-c-forex-execution-adapter.json",
    "P20-D": ROOT / "docs/15-execution/p20-d-oms-lifecycle.json",
    "P20-E": ROOT / "docs/15-execution/p20-e-idempotency-duplicate-prevention.json",
    "P20-F": ROOT / "docs/15-execution/p20-f-retry-timeout-crash-recovery.json",
    "P20-G": ROOT / "docs/15-execution/p20-g-reconciliation.json",
    "P20-H": ROOT / "docs/15-execution/p20-h-execution-quality-metrics.json",
    "P20-I": ROOT / "docs/15-execution/p20-i-broker-simulation-g11.json",
}
REPAIR_CONTRACT = ROOT / "contracts/tasks/FIN-P20-WH-001-R01.json"
REPAIR_DOSSIER = ROOT / "docs/15-execution/P20-H-R01-QUALITY-BAND-FIX.md"


def load(path: Path) -> dict[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return cast(dict[str, object], value)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(phase_manifest_path: Path, p20i_evidence_path: Path) -> dict[str, object]:
    phase = load(phase_manifest_path)
    if phase.get("kind") != "NEXUS_QUANT_P20_PHASE_CLOSURE":
        raise RuntimeError("P20 phase closure kind mismatch")
    if phase.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError("P20 phase is not canonical complete")
    if phase.get("roadmap_exit_gate") != "G11_EXECUTION_VALIDATED":
        raise RuntimeError("P20 exit gate mismatch")
    if phase.get("gate_state") != "PASS":
        raise RuntimeError("G11 is not PASS")
    if phase.get("gate_claim_scope") != "REFERENCE_SIMULATION_EXECUTION_VALIDATION":
        raise RuntimeError("G11 claim scope mismatch")

    workstreams = phase.get("workstreams")
    if not isinstance(workstreams, dict) or tuple(workstreams.keys()) != EXPECTED:
        raise RuntimeError("P20 workstream coverage/order mismatch")

    manifest_hashes: dict[str, str] = {}
    for workstream in EXPECTED:
        row = workstreams.get(workstream)
        if not isinstance(row, dict) or row.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} phase row not canonical complete")
        manifest = load(MANIFESTS[workstream])
        if manifest.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} manifest not canonical complete")
        safety_value = manifest.get("safety")
        if not isinstance(safety_value, Mapping):
            raise RuntimeError(f"{workstream} safety block missing")
        safety = cast(Mapping[str, object], safety_value)
        if safety.get("network_mode") != "DISABLED":
            raise RuntimeError(f"{workstream}.network_mode must be DISABLED")
        if safety.get("live_execution_authority") is not False:
            raise RuntimeError(f"{workstream}.live_execution_authority must be false")
        if safety.get("live_trading") != "DISABLED":
            raise RuntimeError(f"{workstream}.live_trading must be DISABLED")
        if safety.get("auto_trading") != "DISABLED":
            raise RuntimeError(f"{workstream}.auto_trading must be DISABLED")
        closure_value = manifest.get("closure")
        if not isinstance(closure_value, Mapping):
            raise RuntimeError(f"{workstream} closure block missing")
        closure = cast(Mapping[str, object], closure_value)
        if closure.get("lock") != "RELEASED":
            raise RuntimeError(f"{workstream} lock not released")
        manifest_hashes[workstream] = file_sha(MANIFESTS[workstream])

    i_manifest = load(MANIFESTS["P20-I"])
    gate_value = i_manifest.get("gate")
    if not isinstance(gate_value, Mapping):
        raise RuntimeError("P20-I gate block missing")
    gate = cast(Mapping[str, object], gate_value)
    if gate.get("name") != "G11_EXECUTION_VALIDATED" or gate.get("status") != "PASS":
        raise RuntimeError("P20-I G11 manifest mismatch")
    if gate.get("id") != phase.get("gate_id"):
        raise RuntimeError("P20-I gate identity mismatch")
    if gate.get("scope") != phase.get("gate_claim_scope"):
        raise RuntimeError("P20-I gate scope mismatch")

    p20i = load(p20i_evidence_path)
    if p20i.get("kind") != "NEXUS_QUANT_P20I_G11_EVIDENCE":
        raise RuntimeError("P20-I evidence kind mismatch")
    evidence_gate_value = p20i.get("gate")
    if not isinstance(evidence_gate_value, Mapping):
        raise RuntimeError("P20-I evidence gate block missing")
    evidence_gate = cast(Mapping[str, object], evidence_gate_value)
    if evidence_gate.get("gate_status") != "PASS":
        raise RuntimeError("P20-I evidence G11 state mismatch")
    if evidence_gate.get("gate_id") != phase.get("gate_id"):
        raise RuntimeError("P20-I evidence gate identity mismatch")
    if evidence_gate.get("gate_scope") != phase.get("gate_claim_scope"):
        raise RuntimeError("P20-I evidence gate scope mismatch")

    repair = phase.get("repair_lineage")
    if not isinstance(repair, Mapping):
        raise RuntimeError("P20 repair lineage missing")
    repair_row = repair.get("FIN-P20-WH-001-R01")
    if not isinstance(repair_row, Mapping):
        raise RuntimeError("P20-H R01 repair row missing")
    if repair_row.get("state") != "CANONICAL_COMPLETE" or repair_row.get("lock") != "RELEASED":
        raise RuntimeError("P20-H R01 repair not canonical/released")
    if not REPAIR_CONTRACT.exists() or not REPAIR_DOSSIER.exists():
        raise RuntimeError("P20-H R01 repair artifacts missing")

    required: dict[str, object] = {
        "all_locks_released": True,
        "active_task": None,
        "active_lock": None,
        "reference_simulation_validated": True,
        "production_broker_selection": "NOT_SELECTED",
        "production_broker_certification": False,
        "real_venue_query": False,
        "credential_mode": "NONE",
        "network_mode": "DISABLED",
        "external_order_submission": False,
        "external_order_mutation": False,
        "automatic_oms_mutation": False,
        "live_execution_validated": False,
        "live_execution_authority": False,
        "production_readiness": False,
        "profitability_guarantee": False,
        "automatic_p21_activation": False,
        "p21_started": False,
        "p21_state": "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    for key, expected in required.items():
        if phase.get(key) != expected:
            raise RuntimeError(f"P20 phase closure invariant failed: {key}")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20_PHASE_CLOSURE_EVIDENCE",
        "phase": "P20",
        "state": "CANONICAL_COMPLETE",
        "workstreams": list(EXPECTED),
        "gate_name": "G11_EXECUTION_VALIDATED",
        "gate_state": "PASS",
        "gate_id": phase["gate_id"],
        "gate_claim_scope": phase["gate_claim_scope"],
        "manifest_sha256": manifest_hashes,
        "p20i_evidence_sha256": file_sha(p20i_evidence_path),
        "repair_contract_sha256": file_sha(REPAIR_CONTRACT),
        "repair_dossier_sha256": file_sha(REPAIR_DOSSIER),
        "all_locks_released": True,
        "reference_simulation_validated": True,
        "production_broker_certification": False,
        "live_execution_validated": False,
        "live_execution_authority": False,
        "production_readiness": False,
        "p21_state": phase["p21_state"],
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--p20i", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = build(args.manifest, args.p20i)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P20_PHASE_CLOSURE=PASS gate_id={evidence['gate_id']} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
