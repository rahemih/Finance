#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED = tuple(f"P19-{letter}" for letter in "ABCDEFGH")


def build(manifest_path: Path) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("kind") != "NEXUS_QUANT_P19_PHASE_CLOSURE":
        raise RuntimeError("P19 phase closure kind mismatch")
    if payload.get("phase") != "P19":
        raise RuntimeError("P19 phase closure phase mismatch")
    if payload.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError("P19 phase is not canonical complete")
    if payload.get("roadmap_exit_gate") != "G10_SHADOW_VALIDATED":
        raise RuntimeError("P19 exit gate mismatch")
    if payload.get("gate_state") != "PASS":
        raise RuntimeError("G10_SHADOW_VALIDATED is not PASS")
    gate_id = payload.get("gate_id")
    if not isinstance(gate_id, str) or len(gate_id) != 64:
        raise RuntimeError("P19 G10 gate_id must be SHA-256")
    try:
        int(gate_id, 16)
    except ValueError as exc:
        raise RuntimeError("P19 G10 gate_id must be SHA-256") from exc

    workstreams = payload.get("workstreams")
    if not isinstance(workstreams, dict) or tuple(workstreams.keys()) != EXPECTED:
        raise RuntimeError("P19 workstream coverage mismatch")
    for workstream in EXPECTED:
        entry = workstreams[workstream]
        if not isinstance(entry, dict):
            raise RuntimeError(f"{workstream} closure record missing")
        if entry.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} is not canonical complete")
        if entry.get("lock") != "RELEASED":
            raise RuntimeError(f"{workstream} lock is not released")

    required = {
        "all_locks_released": True,
        "active_task": None,
        "active_lock": None,
        "gate_claim_scope": "SHADOW_REFERENCE_VALIDATION",
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
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "next_phase": "P20",
        "next_phase_state": "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise RuntimeError(f"P19 phase closure invariant failed: {key}")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19_PHASE_CLOSURE_EVIDENCE",
        "phase": "P19",
        "state": payload["state"],
        "roadmap_exit_gate": payload["roadmap_exit_gate"],
        "gate_state": payload["gate_state"],
        "gate_id": gate_id,
        "gate_claim_scope": payload["gate_claim_scope"],
        "workstreams": list(EXPECTED),
        "all_locks_released": payload["all_locks_released"],
        "live_empirical_status": payload["live_empirical_status"],
        "live_drift_validated": payload["live_drift_validated"],
        "live_execution_validated": payload["live_execution_validated"],
        "broker_certification_validated": payload["broker_certification_validated"],
        "production_readiness": payload["production_readiness"],
        "next_phase": payload["next_phase"],
        "next_phase_state": payload["next_phase_state"],
        "p20_started": payload["p20_started"],
        "live_trading": payload["live_trading"],
        "auto_trading": payload["auto_trading"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = build(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "P19_PHASE_CLOSURE=PASS "
        f"gate_id={evidence['gate_id']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
