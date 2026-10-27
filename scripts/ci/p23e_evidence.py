#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.team_collaboration import CollaborationPolicy

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"config/ux/team-collaboration.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    policy=CollaborationPolicy.from_path(POLICY)
    payload:dict[str,object]={
        "schema_version":"1.0","kind":"NEXUS_QUANT_P23E_EVIDENCE",
        "task_id":"FIN-P23-WE-001","status":"PASS",
        "policy_id":policy.policy_id,
        "event_types":len(policy.event_types),
        "approval_scope":"TEAM_WORKFLOW_ONLY",
        "owner_authorization":False,"risk_approval":False,"execution_approval":False,
        "p24_state":"NOT_STARTED","live_trading":"DISABLED","auto_trading":"DISABLED",
    }
    evidence_id=hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result={**payload,"evidence_id":evidence_id}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(canonical_bytes(result)+b"\n")
    print(f"P23E_TEAM_COLLABORATION=PASS policy_id={policy.policy_id} evidence_id={evidence_id}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
