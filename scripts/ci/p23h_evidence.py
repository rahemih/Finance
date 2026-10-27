#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.security_ux import SecurityUxPolicy


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/dangerous-action-security-ux.json"
P03 = ROOT / "docs/05-security/p03-security-validation.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = SecurityUxPolicy.from_paths(POLICY, P03)
    request = {
        "action_id": "reference-dangerous-action",
        "action_type": "P24_PRODUCTION_PROMOTION_REQUEST",
        "target_resource": "production-promotion",
        "environment": "production",
        "requested_change_digest": "sha256:" + "c" * 64,
        "expires_at": "2026-10-27T12:00:00Z",
        "provenance_ref": "sha256:" + "d" * 64,
    }
    confirmation_id = policy.confirmation_id(request)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23H_EVIDENCE",
        "task_id": "FIN-P23-WH-001",
        "status": "PASS",
        "claim_scope": "SECURITY_UX_VALIDATION_ONLY",
        "policy_id": policy.policy_id,
        "confirmation_id": confirmation_id,
        "dangerous_action_count": len(policy.action_types),
        "owner_authorization": False,
        "risk_approval": False,
        "security_approval": False,
        "execution_approval": False,
        "production_activation": False,
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
        f"P23H_SECURITY_UX=PASS policy_id={policy.policy_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
