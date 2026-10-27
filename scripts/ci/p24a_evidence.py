#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.production.readiness_dossier import ProductionReadinessDossier


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/production-readiness-dossier.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
    payload: dict[str, object] = {
        "schema_version": "1.1",
        "kind": "NEXUS_QUANT_P24A_EVIDENCE",
        "task_id": "FIN-P24-WA-001",
        "status": "PASS",
        "claim_scope": "READINESS_ASSESSMENT_ONLY",
        "dossier_id": dossier.dossier_id,
        "upstream_gate_count": len(dossier.gates),
        "production_prerequisite_count": len(dossier.prerequisites),
        "blocker_count": len(dossier.blocker_ids),
        "blocker_ids": list(dossier.blocker_ids),
        "pre_first_live_blocker_count": len(dossier.pre_first_live_blocker_ids),
        "pre_first_live_blocker_ids": list(dossier.pre_first_live_blocker_ids),
        "first_live_owner_gate_pending": dossier.first_live_owner_gate_pending,
        "p24_exit_blocker_count": len(dossier.p24_exit_blocker_ids),
        "p24_exit_blocker_ids": list(dossier.p24_exit_blocker_ids),
        "readiness_verdict": dossier.verdict,
        "p24_b_state": dossier.p24_b_state,
        "g13_state": "NOT_STARTED",
        "first_live_authorization": "NOT_GRANTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result = {**payload, "evidence_id": evidence_id}

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result) + b"\n")
    print(
        f"P24A_PRODUCTION_READINESS=PASS dossier_id={dossier.dossier_id} "
        f"verdict={dossier.verdict} blockers={len(dossier.blocker_ids)} "
        f"pre_first_live_blockers={len(dossier.pre_first_live_blocker_ids)} "
        f"exit_blockers={len(dossier.p24_exit_blocker_ids)} "
        f"p24_b={dossier.p24_b_state} evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
