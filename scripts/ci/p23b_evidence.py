#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.design_system import DesignSystem


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/design-system.json"


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

    design = DesignSystem.from_path(POLICY)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23B_EVIDENCE",
        "task_id": "FIN-P23-WB-001",
        "workstream": "P23-B",
        "design_system_id": design.design_system_id,
        "semantic_state_count": len(design.semantic_states),
        "terminology_count": len(design.terminology_ids),
        "locale": design.locale,
        "shell_direction": design.shell_direction,
        "financial_island_direction": design.financial_island_direction,
        "ltr_islands": list(design.ltr_islands),
        "safety": design.raw["safety"],
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result = {**payload, "evidence_id": evidence_id}

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result) + b"\n")
    print(
        "P23B_DESIGN_SYSTEM=PASS "
        f"design_system_id={design.design_system_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
