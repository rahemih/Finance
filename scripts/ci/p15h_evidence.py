from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.defensive_modes import (
    DefensiveModePolicy,
    DefensiveModeRequest,
    select_defensive_mode,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/defensive-mode-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = DefensiveModePolicy("p15h-ci-v1", 5000, 2500)
    normal = select_defensive_mode(
        policy=policy,
        request=DefensiveModeRequest(
            "normal",
            "capital-ok",
            "CAPITAL_SEGMENT_ELIGIBLE",
            "WITHIN_LIMITS",
            "HEALTHY",
            "HEALTHY",
            1000,
        ),
    )
    halt = select_defensive_mode(
        policy=policy,
        request=DefensiveModeRequest(
            "halt",
            "capital-veto",
            "VETO",
            "VETO",
            "CRITICAL",
            "HEALTHY",
            1000,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15H_DEFENSIVE_MODE_EVIDENCE",
        "task_id": "FIN-P15-WH-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "normal": {
            "decision_id": normal.decision_id,
            "mode": normal.mode,
            "risk_scale_bps": normal.risk_scale_bps,
        },
        "halt": {
            "decision_id": halt.decision_id,
            "mode": halt.mode,
            "risk_scale_bps": halt.risk_scale_bps,
            "reason_codes": list(halt.reason_codes),
        },
        "position_close_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P15H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
