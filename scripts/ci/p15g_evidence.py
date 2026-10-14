from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.counterparty_capital import (
    CapitalSegmentRule,
    CounterpartyCapitalPolicy,
    CounterpartyCapitalRequest,
    CounterpartyRule,
    evaluate_counterparty_capital,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/counterparty-capital-segmentation-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = CounterpartyCapitalPolicy.build(
        policy_version="p15g-ci-v1",
        counterparties=(CounterpartyRule("venue-fixture", 4000),),
        segments=(CapitalSegmentRule("core-fixture", 7000),),
    )
    eligible = evaluate_counterparty_capital(
        policy=policy,
        request=CounterpartyCapitalRequest(
            "eligible",
            "drawdown-ok",
            "WITHIN_LIMITS",
            "venue-fixture",
            "core-fixture",
            3000,
            1000,
            2000,
            500,
            1000,
        ),
    )
    veto = evaluate_counterparty_capital(
        policy=policy,
        request=CounterpartyCapitalRequest(
            "veto",
            "drawdown-veto",
            "VETO",
            "venue-fixture",
            "core-fixture",
            3000,
            1000,
            2000,
            500,
            1000,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15G_COUNTERPARTY_CAPITAL_EVIDENCE",
        "task_id": "FIN-P15-WG-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "total_after_bps": eligible.total_after_bps,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
        },
        "venue_routing_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P15G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
