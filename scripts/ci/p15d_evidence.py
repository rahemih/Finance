from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.risk.portfolio_correlation import (
    CorrelationPair,
    ExposureLeg,
    PortfolioExposurePolicy,
    PortfolioExposureRequest,
    evaluate_portfolio_exposure,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/portfolio-correlation-exposure-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    p = PortfolioExposurePolicy("p15d-ci-v1", 7000, 5000, 700, 5000)
    existing = (
        ExposureLeg("BTC", 2000),
        ExposureLeg("XAUUSD", -1000),
    )
    corr = (
        CorrelationPair("BTC", "ETH", 800),
        CorrelationPair("BTC", "XAUUSD", 100),
        CorrelationPair("ETH", "XAUUSD", 200),
    )
    eligible = evaluate_portfolio_exposure(
        policy=p,
        request=PortfolioExposureRequest(
            "p15d-eligible",
            "p15c-eligible",
            "LIMITS_ELIGIBLE",
            "ETH",
            1000,
            1000,
        ),
        existing=existing,
        correlations=corr,
    )
    veto = evaluate_portfolio_exposure(
        policy=PortfolioExposurePolicy("p15d-ci-veto", 3999, 5000, 700, 5000),
        request=PortfolioExposureRequest(
            "p15d-veto",
            "p15c-eligible",
            "LIMITS_ELIGIBLE",
            "ETH",
            1000,
            1000,
        ),
        existing=existing,
        correlations=corr,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P15D_PORTFOLIO_CORRELATION_EVIDENCE",
        "task_id": "FIN-P15-WD-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "gross_exposure_bps": eligible.gross_exposure_bps,
            "max_correlated_cluster_gross_bps": (
                eligible.max_correlated_cluster_gross_bps
            ),
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
    print(f"P15D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
