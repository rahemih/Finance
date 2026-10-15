from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.data_quality.quality_slo import SloStatus
from packages.market_data.recovery import RecoveryState
from packages.market_data.streaming import StreamHealth
from packages.pretrade_firewall.health_check import (
    PreTradeHealthPolicy,
    PreTradeHealthRequest,
    evaluate_pretrade_health,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-health-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = PreTradeHealthPolicy("p16e-ci-v1", 100, 100, 500)
    eligible = evaluate_pretrade_health(
        policy=policy,
        request=PreTradeHealthRequest.build(
            request_id="eligible",
            upstream_liquidity_decision_id="d-ok",
            upstream_liquidity_status="PRETRADE_D_ELIGIBLE",
            economic_events=(),
            data_slo_status=SloStatus.HEALTHY,
            stream_health=StreamHealth.HEALTHY,
            recovery_state=RecoveryState.ACTIVE,
            system_state="NORMAL",
            as_of_ns=1000,
        ),
    )
    veto = evaluate_pretrade_health(
        policy=policy,
        request=PreTradeHealthRequest.build(
            request_id="veto",
            upstream_liquidity_decision_id="d-ok",
            upstream_liquidity_status="PRETRADE_D_ELIGIBLE",
            economic_events=(),
            data_slo_status=SloStatus.CRITICAL,
            stream_health=StreamHealth.HEALTHY,
            recovery_state=RecoveryState.ACTIVE,
            system_state="NORMAL",
            as_of_ns=1000,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16E_HEALTH_EVIDENCE",
        "task_id": "FIN-P16-WE-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
        },
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
    print(f"P16E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
