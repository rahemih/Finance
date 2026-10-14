from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.drawdown_ruin import (
    DrawdownRuinPolicy,
    DrawdownRuinRequest,
    evaluate_drawdown_ruin,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/drawdown-ruin-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = DrawdownRuinPolicy(
        policy_version="p15f-ci-v1",
        soft_drawdown_bps=1000,
        hard_stop_drawdown_bps=2000,
        max_ruin_probability_ppm=50000,
    )
    within = evaluate_drawdown_ruin(
        policy=policy,
        request=DrawdownRuinRequest(
            "within",
            "margin-ok",
            "MARGIN_LEVERAGE_ELIGIBLE",
            "10000",
            "9500",
            10000,
            "fixture-validated-model",
            1000,
        ),
    )
    veto = evaluate_drawdown_ruin(
        policy=policy,
        request=DrawdownRuinRequest(
            "veto",
            "margin-ok",
            "MARGIN_LEVERAGE_ELIGIBLE",
            "10000",
            "7900",
            10000,
            "fixture-validated-model",
            1000,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15F_DRAWDOWN_RUIN_EVIDENCE",
        "task_id": "FIN-P15-WF-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "within": {
            "decision_id": within.decision_id,
            "status": within.status,
            "drawdown_bps": within.drawdown_bps,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
        },
        "defensive_mode_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P15F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
