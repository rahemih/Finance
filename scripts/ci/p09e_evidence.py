from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.liquidity_heatmap import (
    LiquidityHeatmapPolicy,
    build_liquidity_heatmap,
)
from packages.order_flow_liquidity.order_book import (
    OrderBookLevel,
    OrderBookPolicy,
    OrderBookSnapshot,
)

ROOT = Path(__file__).resolve().parents[2]
HEATMAP_POLICY_PATH = ROOT / "config/order-flow-liquidity/liquidity-heatmap-policy.json"
BOOK_POLICY_PATH = ROOT / "config/order-flow-liquidity/order-book-policy.json"
DATASET = "3" * 64
QUALITY = "4" * 64


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    heatmap_policy = LiquidityHeatmapPolicy.from_path(HEATMAP_POLICY_PATH)
    book_policy = OrderBookPolicy.from_path(BOOK_POLICY_PATH)
    book = OrderBookSnapshot(
        symbol="CRYPTO:BTC-USD",
        market_class="CRYPTO_SPOT",
        source_kind="VENUE_ORDER_BOOK",
        provider="KAIKO",
        venue="COINBASE",
        event_time_ns=1_000,
        as_of_time_ns=1_000,
        sequence=1,
        coverage_scope="COINBASE_ONLY",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
        bids=(
            OrderBookLevel("100", "4"),
            OrderBookLevel("99", "3"),
            OrderBookLevel("98", "2"),
            OrderBookLevel("90", "7"),
        ),
        asks=(
            OrderBookLevel("102", "2"),
            OrderBookLevel("103", "1"),
            OrderBookLevel("104", "2"),
            OrderBookLevel("115", "5"),
        ),
    )
    heatmap = build_liquidity_heatmap(
        book,
        heatmap_policy=heatmap_policy,
        order_book_policy=book_policy,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09E_LIQUIDITY_HEATMAP_EVIDENCE",
        "task_id": "FIN-P09-WE-001",
        "heatmap_policy_sha256": hashlib.sha256(HEATMAP_POLICY_PATH.read_bytes()).hexdigest(),
        "order_book_policy_sha256": hashlib.sha256(BOOK_POLICY_PATH.read_bytes()).hexdigest(),
        "source_snapshot_id": heatmap.source_snapshot_id,
        "heatmap_id": heatmap.heatmap_id,
        "mid_price_text": heatmap.mid_price_text,
        "max_distance_bps": heatmap.max_distance_bps,
        "bands": [band.payload() for band in heatmap.bands],
        "outside_bid_size_text": heatmap.outside_bid_size_text,
        "outside_ask_size_text": heatmap.outside_ask_size_text,
        "displayed_capacity_only": heatmap_policy.displayed_capacity_only,
        "hidden_liquidity_inference_allowed": heatmap_policy.hidden_liquidity_inference_allowed,
        "fillability_claim_allowed": heatmap_policy.fillability_claim_allowed,
        "slippage_or_market_impact_claim_allowed": heatmap_policy.slippage_or_market_impact_claim_allowed,
        "cross_provider_aggregation_allowed": heatmap_policy.cross_provider_aggregation_allowed,
        "forex_spot_global_liquidity_claim_allowed": heatmap_policy.forex_spot_global_liquidity_claim_allowed,
        "direct_trade_output_allowed": heatmap_policy.direct_trade_output_allowed,
        "production_order_flow_vendor": heatmap_policy.production_order_flow_vendor,
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
    print(f"P09E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
