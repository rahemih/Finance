from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.position_sizing import PositionSizingRequest, size_position


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/position-sizing-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    candidate = size_position(
        PositionSizingRequest(
            request_id="p15b-ci-candidate",
            upstream_risk_decision_id="p15a-ci-eligible",
            upstream_status="POLICY_CAPACITY_ELIGIBLE",
            side="LONG",
            account_equity="10000",
            risk_budget_bps=100,
            entry_price="100",
            stop_price="95",
            contract_multiplier="1",
            quantity_step="0.1",
            as_of_ns=1000,
        )
    )
    veto = size_position(
        PositionSizingRequest(
            request_id="p15b-ci-veto",
            upstream_risk_decision_id="p15a-ci-veto",
            upstream_status="VETO",
            side="LONG",
            account_equity="10000",
            risk_budget_bps=100,
            entry_price="100",
            stop_price="95",
            contract_multiplier="1",
            quantity_step="0.1",
            as_of_ns=1000,
        )
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15B_POSITION_SIZING_EVIDENCE",
        "task_id": "FIN-P15-WB-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "candidate": {
            "decision_id": candidate.decision_id,
            "status": candidate.status,
            "risk_amount": candidate.risk_amount,
            "candidate_quantity": candidate.candidate_quantity,
            "planned_stop_loss": candidate.planned_stop_loss,
            "leverage_authority": candidate.leverage_authority,
            "execution_authority": candidate.execution_authority,
        },
        "upstream_veto": {
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
    print(f"P15B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
