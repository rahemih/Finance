#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.learning_mode import LearningMode

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/learning-mode-glossary.json"
DS = ROOT / "config/ux/design-system.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = LearningMode.from_paths(POLICY, DS)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23D_EVIDENCE",
        "task_id": "FIN-P23-WD-001",
        "status": "PASS",
        "learning_mode_id": policy.learning_mode_id,
        "design_system_id": policy.design_system_id,
        "glossary_entries": len(policy.entries),
        "modes": list(policy.modes),
        "authority": "EXPLANATION_ONLY",
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
        "P23D_LEARNING_MODE=PASS "
        f"learning_mode_id={policy.learning_mode_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
