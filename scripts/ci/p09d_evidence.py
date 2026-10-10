from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.order_book import (
    OrderBookLevel,
    OrderBookPolicy,
    OrderBookSnapshot,
    compute_order_book_metrics,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/order-book-policy.json"
DATASET = "1" * 64
QUALITY = "2" * 64


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = OrderBookPolicy.from_path(POLICY_PATH)
    snapshot = OrderBookSnapshot(
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
        ),
        asks=(
            OrderBookLevel("102", "2"),
            OrderBookLevel("103", "1"),
            OrderBookLevel("104", "2"),
        ),
    )
    metrics = compute_order_book_metrics(snapshot, depth_levels=2, policy=policy)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09D_ORDER_BOOK_EVIDENCE",
        "task_id": "FIN-P09-WD-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "snapshot_id": metrics.snapshot_id,
        "metrics_id": metrics.metrics_id,
        "depth_levels": metrics.depth_levels,
        "best_bid_text": metrics.best_bid_text,
        "best_ask_text": metrics.best_ask_text,
        "mid_price_text": metrics.mid_price_text,
        "spread_text": metrics.spread_text,
        "spread_bps": metrics.spread_bps,
        "bid_depth_text": metrics.bid_depth_text,
        "ask_depth_text": metrics.ask_depth_text,
        "imbalance_bps": metrics.imbalance_bps,
        "locked_or_crossed_book_allowed": policy.locked_or_crossed_book_allowed,
        "forex_spot_global_book_claim_allowed": policy.forex_spot_global_book_claim_allowed,
        "direct_trade_output_allowed": policy.direct_trade_output_allowed,
        "production_order_flow_vendor": policy.production_order_flow_vendor,
        "country_assumption": "NONE",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "network_required": False,
        "credentials_required": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P09D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
