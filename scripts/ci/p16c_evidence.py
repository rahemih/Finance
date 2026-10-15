from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.pretrade_firewall.risk_drift import (
    PreTradeRiskDriftRequest,
    evaluate_risk_drift,
)
from packages.risk.margin_leverage import MarginLeverageDecision
from packages.risk.portfolio_correlation import PortfolioExposureDecision
from packages.risk.position_sizing import PositionSizeDecision


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-risk-drift-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    size = PositionSizeDecision(
        "size-ci",
        "size-request",
        "SIZE_CANDIDATE",
        (),
        "100",
        "1",
        "100",
        "100",
        "100",
        100,
    )
    portfolio = PortfolioExposureDecision(
        "portfolio-ci",
        "portfolio-request",
        "PORTFOLIO_ELIGIBLE",
        (),
        4000,
        2000,
        3000,
        (("BTC",),),
    )
    margin = MarginLeverageDecision(
        "margin-ci",
        "margin-request",
        "MARGIN_LEVERAGE_ELIGIBLE",
        (),
        "15000",
        "1000",
        "2000",
        1500,
        2000,
    )

    eligible = evaluate_risk_drift(
        PreTradeRiskDriftRequest(
            "eligible",
            "b-ok",
            "PRETRADE_B_ELIGIBLE",
            size,
            portfolio,
            margin,
            "100",
            4000,
            2000,
            3000,
            1500,
            2000,
            1000,
        )
    )
    veto = evaluate_risk_drift(
        PreTradeRiskDriftRequest(
            "veto",
            "b-ok",
            "PRETRADE_B_ELIGIBLE",
            size,
            portfolio,
            margin,
            "101",
            4000,
            2000,
            3000,
            1500,
            2000,
            1000,
        )
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16C_SIZE_LEVERAGE_EXPOSURE_EVIDENCE",
        "task_id": "FIN-P16-WC-001",
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
    print(f"P16C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
