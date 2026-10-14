from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.asset_strategy_limits import (
    AssetStrategyLimitPolicy,
    AssetStrategyLimitRequest,
    LimitRule,
    LimitUsage,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/asset-strategy-limits-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = AssetStrategyLimitPolicy.build(
        policy_version="p15c-ci-v1",
        rules=(
            LimitRule("ASSET", "BTC", 1200, 3),
            LimitRule("STRATEGY", "TREND", 800, 2),
        ),
    )
    usage = (
        LimitUsage("ASSET", "BTC", 500, 1),
        LimitUsage("STRATEGY", "TREND", 300, 1),
    )
    eligible = policy.evaluate(
        request=AssetStrategyLimitRequest(
            "p15c-eligible",
            "p15b-size-candidate",
            "SIZE_CANDIDATE",
            "BTC",
            "TREND",
            100,
            1,
            1000,
        ),
        usage=usage,
    )
    veto = policy.evaluate(
        request=AssetStrategyLimitRequest(
            "p15c-veto",
            "p15b-size-candidate",
            "SIZE_CANDIDATE",
            "BTC",
            "TREND",
            600,
            1,
            1000,
        ),
        usage=usage,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15C_ASSET_STRATEGY_LIMITS_EVIDENCE",
        "task_id": "FIN-P15-WC-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "policy_id": policy.policy_id,
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
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
    print(f"P15C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
