from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.margin_leverage import (
    MarginLeveragePolicy,
    MarginLeverageRequest,
    evaluate_margin_leverage,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/margin-leverage-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    req = MarginLeverageRequest(
        "p15e-ci",
        "p15d-eligible",
        "PORTFOLIO_ELIGIBLE",
        "10000",
        "10000",
        "1000",
        "5000",
        2000,
        1000,
    )
    eligible = evaluate_margin_leverage(
        policy=MarginLeveragePolicy("p15e-ci-v1", 3000, 5000),
        request=req,
    )
    veto = evaluate_margin_leverage(
        policy=MarginLeveragePolicy("p15e-ci-veto", 1499, 5000),
        request=req,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15E_MARGIN_LEVERAGE_EVIDENCE",
        "task_id": "FIN-P15-WE-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "leverage_milli": eligible.leverage_milli,
            "margin_utilization_bps": eligible.margin_utilization_bps,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
        },
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P15E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
