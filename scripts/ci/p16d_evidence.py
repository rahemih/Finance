from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.liquidity_heatmap import (
    LiquidityHeatmapBand,
    LiquidityHeatmapSnapshot,
)
from packages.order_flow_liquidity.order_book import OrderBookMetrics
from packages.pretrade_firewall.liquidity_capacity import (
    PreTradeLiquidityCapacityPolicy,
    PreTradeLiquidityCapacityRequest,
    evaluate_liquidity_capacity,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-liquidity-capacity-policy.json"


def fixture_heatmap() -> LiquidityHeatmapSnapshot:
    band = LiquidityHeatmapBand(
        0,
        50,
        "10",
        "10",
        "2000",
        "1000",
        "10",
        "10",
        "2000",
        "1000",
        "3000",
        6667,
        3333,
    )
    return LiquidityHeatmapSnapshot(
        "snapshot-ci",
        "BTC-USD",
        "CRYPTO",
        "fixture-provider",
        "fixture-venue",
        "ORDER_BOOK",
        "VENUE_SCOPED",
        1000,
        1000,
        "100",
        50,
        "0",
        "0",
        "0",
        "0",
        (band,),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metrics = OrderBookMetrics(
        "snapshot-ci",
        5,
        "99",
        "101",
        "100",
        "2",
        20,
        "10",
        "10",
        0,
    )
    policy = PreTradeLiquidityCapacityPolicy("p16d-ci-v1", 20, 50, 5000)
    heatmap = fixture_heatmap()
    eligible = evaluate_liquidity_capacity(
        policy=policy,
        request=PreTradeLiquidityCapacityRequest(
            "eligible",
            "c-ok",
            "PRETRADE_C_ELIGIBLE",
            "LONG",
            "500",
            metrics,
            heatmap,
            1000,
        ),
    )
    veto = evaluate_liquidity_capacity(
        policy=policy,
        request=PreTradeLiquidityCapacityRequest(
            "veto",
            "c-ok",
            "PRETRADE_C_ELIGIBLE",
            "LONG",
            "500.01",
            metrics,
            heatmap,
            1000,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16D_SPREAD_LIQUIDITY_CAPACITY_EVIDENCE",
        "task_id": "FIN-P16-WD-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "spread_bps": eligible.spread_bps,
            "capacity_utilization_bps": eligible.capacity_utilization_bps,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
            "capacity_utilization_bps": veto.capacity_utilization_bps,
        },
        "hidden_liquidity_inference": False,
        "fillability_claim": False,
        "slippage_or_market_impact_claim": False,
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
    print(f"P16D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
