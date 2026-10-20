#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = tuple(f"P19-{letter}" for letter in "ABCDEFGH")
MANIFESTS = {
    "P19-A": ROOT / "docs/14-shadow/p19-a-shadow-decisioning.json",
    "P19-B": ROOT / "docs/14-shadow/p19-b-data-replay.json",
    "P19-C": ROOT / "docs/14-shadow/p19-c-decision-replay.json",
    "P19-D": ROOT / "docs/14-shadow/p19-d-incident-replay.json",
    "P19-E": ROOT / "docs/14-shadow/p19-e-digital-twin-fill-slippage.json",
    "P19-F": ROOT / "docs/14-shadow/p19-f-paper-live-drift-metrics.json",
    "P19-G": ROOT / "docs/14-shadow/p19-g-deterministic-reproducibility.json",
    "P19-H": ROOT / "docs/14-shadow/p19-h-shadow-validation-gate.json",
}

def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value

def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(phase_manifest_path: Path, p19h_evidence_path: Path) -> dict[str, object]:
    phase = load(phase_manifest_path)
    if phase.get("kind") != "NEXUS_QUANT_P19_PHASE_CLOSURE":
        raise RuntimeError("P19 phase closure kind mismatch")
    if phase.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError("P19 phase is not canonical complete")
    if phase.get("roadmap_exit_gate") != "G10_SHADOW_VALIDATED":
        raise RuntimeError("P19 exit gate mismatch")
    if phase.get("gate_state") != "PASS":
        raise RuntimeError("G10 is not PASS")
    if phase.get("gate_claim_scope") != "SHADOW_REFERENCE_VALIDATION":
        raise RuntimeError("G10 claim scope mismatch")

    workstreams = phase.get("workstreams")
    if not isinstance(workstreams, dict) or tuple(workstreams.keys()) != EXPECTED:
        raise RuntimeError("P19 workstream coverage/order mismatch")

    manifest_hashes: dict[str, str] = {}
    for workstream in EXPECTED:
        row = workstreams.get(workstream)
        if not isinstance(row, dict) or row.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} phase row not canonical complete")
        manifest = load(MANIFESTS[workstream])
        if manifest.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} manifest not canonical complete")
        if manifest.get("lock") != "RELEASED":
            raise RuntimeError(f"{workstream} manifest lock not released")
        for field in (
            "production_readiness",
            "production_readiness_authority",
            "execution_authority",
            "order_routing_authority",
            "broker_exchange_routing",
            "p20_started",
            "automatic_p20_activation",
            "live_execution_validated",
            "broker_certification_validated",
            "profitability_guarantee",
        ):
            if field in manifest and manifest.get(field) is not False:
                raise RuntimeError(f"{workstream}.{field} must be false")
        if manifest.get("live_trading") != "DISABLED":
            raise RuntimeError(f"{workstream}.live_trading must be DISABLED")
        if manifest.get("auto_trading") != "DISABLED":
            raise RuntimeError(f"{workstream}.auto_trading must be DISABLED")
        manifest_hashes[workstream] = file_sha(MANIFESTS[workstream])

    h_manifest = load(MANIFESTS["P19-H"])
    if h_manifest.get("gate_state") != "PASS":
        raise RuntimeError("P19-H manifest G10 state mismatch")
    if h_manifest.get("gate_id") != phase.get("gate_id"):
        raise RuntimeError("P19-H manifest gate identity mismatch")

    p19h = load(p19h_evidence_path)
    if p19h.get("kind") != "NEXUS_QUANT_P19H_G10_SHADOW_VALIDATION_EVIDENCE":
        raise RuntimeError("P19-H evidence kind mismatch")
    if p19h.get("state") != "PASS":
        raise RuntimeError("P19-H evidence gate state mismatch")
    if p19h.get("gate_id") != phase.get("gate_id"):
        raise RuntimeError("P19-H evidence gate identity mismatch")
    if p19h.get("gate_claim_scope") != "SHADOW_REFERENCE_VALIDATION":
        raise RuntimeError("P19-H evidence claim scope mismatch")

    required = {
        "all_locks_released": True,
        "active_task": None,
        "active_lock": None,
        "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
        "live_drift_validated": False,
        "live_execution_validated": False,
        "broker_certification_validated": False,
        "production_readiness": False,
        "profitability_guarantee": False,
        "automatic_p20_activation": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p20_started": False,
        "p20_state": "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    for key, expected in required.items():
        if phase.get(key) != expected:
            raise RuntimeError(f"P19 phase closure invariant failed: {key}")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19_PHASE_CLOSURE_EVIDENCE",
        "phase": "P19",
        "state": "CANONICAL_COMPLETE",
        "workstreams": list(EXPECTED),
        "gate_name": "G10_SHADOW_VALIDATED",
        "gate_state": "PASS",
        "gate_id": phase["gate_id"],
        "gate_claim_scope": phase["gate_claim_scope"],
        "manifest_sha256": manifest_hashes,
        "p19h_evidence_sha256": file_sha(p19h_evidence_path),
        "all_locks_released": True,
        "live_empirical_status": phase["live_empirical_status"],
        "live_drift_validated": False,
        "live_execution_validated": False,
        "broker_certification_validated": False,
        "production_readiness": False,
        "p20_state": phase["p20_state"],
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--p19h", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = build(args.manifest, args.p19h)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P19_PHASE_CLOSURE=PASS gate_id={evidence['gate_id']} output={args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
