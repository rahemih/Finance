#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.operational_screens import OperationalScreens

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/operational-screens.json"
IA = ROOT / "config/ux/information-architecture.json"
DS = ROOT / "config/ux/design-system.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    screens = OperationalScreens.from_paths(POLICY, IA, DS)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23C_EVIDENCE",
        "task_id": "FIN-P23-WC-001",
        "status": "PASS",
        "operational_screens_id": screens.operational_screens_id,
        "architecture_id": screens.architecture_id,
        "design_system_id": screens.design_system_id,
        "screen_count": len(screens.screens),
        "critical_screen_count": sum(1 for item in screens.screens if item.critical),
        "authority": "READ_ONLY_NAVIGATION",
        "p24_state": "NOT_STARTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result = {**payload, "evidence_id": evidence_id}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(result) + b"\n"
    output.write_bytes(raw)
    print(
        "P23C_OPERATIONAL_SCREENS=PASS "
        f"operational_screens_id={screens.operational_screens_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
