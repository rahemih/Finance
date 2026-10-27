#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.p23_e2e_validation import P23E2EValidation


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/p23-e2e-validation.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    validation = P23E2EValidation.from_root(POLICY, ROOT)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23I_EVIDENCE",
        "task_id": "FIN-P23-WI-001",
        "status": "PASS",
        "claim_scope": "REFERENCE_UX_E2E_VALIDATION",
        "validation_id": validation.validation_id,
        "upstream_workstreams": [item.workstream for item in validation.upstream],
        "upstream_manifest_sha256": {
            item.workstream: item.manifest_sha256 for item in validation.upstream
        },
        "reference_journey_count": len(validation.journeys),
        "canonical_surface_count": len(validation.canonical_surfaces),
        "browser_runtime_certification": False,
        "production_readiness": False,
        "p24_state": "NOT_STARTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result = {**payload, "evidence_id": evidence_id}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result) + b"\n")
    print(
        f"P23I_E2E_VALIDATION=PASS validation_id={validation.validation_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
