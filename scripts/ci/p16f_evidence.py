from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.pretrade_firewall.daily_loss import (
    DailyLossPolicy,
    DailyLossRequest,
    evaluate_daily_loss,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-daily-loss-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = DailyLossPolicy("p16f-ci-v1", 500)
    eligible = evaluate_daily_loss(
        policy=policy,
        request=DailyLossRequest(
            "eligible",
            "e-ok",
            "PRETRADE_E_ELIGIBLE",
            "fixture-day",
            "10000",
            "9800",
            "CLEAR",
            1000,
        ),
    )
    veto = evaluate_daily_loss(
        policy=policy,
        request=DailyLossRequest(
            "veto",
            "e-ok",
            "PRETRADE_E_ELIGIBLE",
            "fixture-day",
            "10000",
            "9500",
            "CLEAR",
            1000,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16F_DAILY_LOSS_CIRCUIT_BREAKER_EVIDENCE",
        "task_id": "FIN-P16-WF-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "daily_loss_bps": eligible.daily_loss_bps,
            "circuit_state": eligible.circuit_state,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "daily_loss_bps": veto.daily_loss_bps,
            "circuit_state": veto.circuit_state,
            "reason_codes": list(veto.reason_codes),
        },
        "reset_authority": False,
        "position_close_authority": False,
        "g8_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P16F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
