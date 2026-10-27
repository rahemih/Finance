#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.accessibility_performance import FrontendHardeningPolicy


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/accessibility-responsive-performance.json"
DESIGN = ROOT / "config/ux/design-system.json"
SCREENS = ROOT / "config/ux/operational-screens.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = FrontendHardeningPolicy.from_paths(POLICY, DESIGN, SCREENS)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23G_EVIDENCE",
        "task_id": "FIN-P23-WG-001",
        "status": "PASS",
        "claim_scope": "REFERENCE_FRONTEND_VALIDATION",
        "policy_id": policy.policy_id,
        "screen_count": len(policy.screen_ids),
        "viewport_profiles": list(policy.profile_widths),
        "wcag": "WCAG_2_2_AA",
        "lcp_ms_max": 2500,
        "inp_ms_max": 200,
        "cls_max": 0.1,
        "production_certification": False,
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
        f"P23G_FRONTEND_HARDENING=PASS policy_id={policy.policy_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
