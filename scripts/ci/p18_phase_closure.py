#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED = tuple(f"P18-{letter}" for letter in "ABCDEFGHI")


def build(manifest_path: Path) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("kind") != "NEXUS_QUANT_P18_PHASE_CLOSURE":
        raise RuntimeError("P18 phase closure kind mismatch")
    if payload.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError("P18 phase is not canonical complete")
    workstreams = payload.get("workstreams")
    if not isinstance(workstreams, dict) or tuple(workstreams.keys()) != EXPECTED:
        raise RuntimeError("P18 workstream coverage mismatch")
    for workstream in EXPECTED:
        entry = workstreams[workstream]
        if not isinstance(entry, dict) or entry.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{workstream} is not canonical complete")
    required = {
        "all_locks_released": True,
        "active_task": None,
        "active_lock": None,
        "automatic_live_promotion": False,
        "registry_live_mutation": False,
        "broker_exchange_routing": False,
        "p19_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "learning_cycle_complete_status": "CYCLE_COMPLETE_DEMO_ONLY",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise RuntimeError(f"P18 phase closure invariant failed: {key}")
    if payload.get("p19_state") != "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED":
        raise RuntimeError("P19 phase boundary mismatch")
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18_PHASE_CLOSURE_EVIDENCE",
        "phase": "P18",
        "state": payload["state"],
        "workstreams": list(EXPECTED),
        "all_locks_released": payload["all_locks_released"],
        "learning_cycle_complete_status": payload["learning_cycle_complete_status"],
        "automated_controlled_retraining": payload["automated_controlled_retraining"],
        "automatic_live_promotion": payload["automatic_live_promotion"],
        "p19_state": payload["p19_state"],
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
    print(f"P18_PHASE_CLOSURE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
