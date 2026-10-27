#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.information_architecture import InformationArchitecture


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/information-architecture.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    architecture = InformationArchitecture.from_path(POLICY)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23A_EVIDENCE",
        "task_id": "FIN-P23-WA-001",
        "workstream": "P23-A",
        "architecture_id": architecture.architecture_id,
        "surface_count": len(architecture.surfaces),
        "workflow_count": len(architecture.workflows),
        "critical_surface_states": list(
            architecture.critical_surface_states
        ),
        "locale": architecture.locale,
        "direction": architecture.direction,
        "financial_identifier_direction": (
            architecture.financial_identifier_direction
        ),
        "safety": architecture.safety,
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result = {**payload, "evidence_id": evidence_id}

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result) + b"\n")
    print(
        "P23A_INFORMATION_ARCHITECTURE=PASS "
        f"architecture_id={architecture.architecture_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
