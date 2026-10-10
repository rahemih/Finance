from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.derivatives_crowding import (
    DerivativesCrowdingPolicy,
    DerivativesObservation,
    build_crowding_evidence,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/derivatives-crowding-policy.json"
DATASET = "5" * 64
QUALITY = "6" * 64


def obs(kind: str, value: str, *, unit: str, sequence: int, interval: int | None = None) -> DerivativesObservation:
    return DerivativesObservation(
        symbol="CRYPTO:BTC-PERP",
        market_class="CRYPTO_DERIVATIVE",
        metric_kind=kind,
        provider="KAIKO",
        venue="BINANCE",
        value_text=value,
        value_unit=unit,
        event_time_ns=1_900 + sequence,
        as_of_time_ns=2_000,
        sequence=sequence,
        coverage_scope="BINANCE_ONLY",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
        funding_interval_seconds=interval,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = DerivativesCrowdingPolicy.from_path(POLICY_PATH)
    snapshot = build_crowding_evidence(
        (
            obs("FUNDING_RATE", "0.0001", unit="DECIMAL_RATE", sequence=1, interval=28800),
            obs("OPEN_INTEREST", "1000000", unit="USD_NOTIONAL", sequence=2),
            obs("LONG_LIQUIDATION", "300000", unit="USD_NOTIONAL", sequence=3),
            obs("SHORT_LIQUIDATION", "100000", unit="USD_NOTIONAL", sequence=4),
        ),
        policy=policy,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09F_DERIVATIVES_CROWDING_EVIDENCE",
        "task_id": "FIN-P09-WF-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "evidence_id": snapshot.evidence_id,
        "provider": snapshot.provider,
        "venue": snapshot.venue,
        "funding_rate_text": snapshot.funding_rate_text,
        "funding_interval_seconds": snapshot.funding_interval_seconds,
        "open_interest_text": snapshot.open_interest_text,
        "open_interest_unit": snapshot.open_interest_unit,
        "total_liquidation_text": snapshot.total_liquidation_text,
        "liquidation_unit": snapshot.liquidation_unit,
        "liquidation_activity_present": snapshot.liquidation_activity_present,
        "liquidation_imbalance_bps": snapshot.liquidation_imbalance_bps,
        "evidence_complete": snapshot.evidence_complete,
        "cross_provider_aggregation_allowed": policy.cross_provider_aggregation_allowed,
        "spot_fx_derivatives_metric_allowed": policy.spot_fx_derivatives_metric_allowed,
        "crowding_score_allowed": policy.crowding_score_allowed,
        "liquidation_forecast_allowed": policy.liquidation_forecast_allowed,
        "direct_trade_output_allowed": policy.direct_trade_output_allowed,
        "production_derivatives_vendor": policy.production_derivatives_vendor,
        "country_assumption": "NONE",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "network_required": False,
        "credentials_required": False
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P09F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
