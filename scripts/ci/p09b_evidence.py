from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.trade_flow import (
    QuoteContext,
    TradeFlowPolicy,
    TradePrint,
    build_flow_snapshot,
    classify_native_aggressor,
    classify_quote_test,
    classify_unknown,
    validate_trade_print,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/trade-flow-policy.json"
DATASET = "c" * 64
QUALITY = "d" * 64


def make_trade(*, sequence: int, price: str, size: str, event_time_ns: int) -> TradePrint:
    return TradePrint(
        symbol="CRYPTO:BTC-USD",
        market_class="CRYPTO_SPOT",
        source_kind="VENUE_TRADE_PRINTS",
        provider="KAIKO",
        venue="COINBASE",
        price_text=price,
        size_text=size,
        event_time_ns=event_time_ns,
        sequence=sequence,
        coverage_scope="COINBASE_ONLY",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = TradeFlowPolicy.from_path(POLICY_PATH)
    items = [
        classify_native_aggressor(
            make_trade(sequence=1, price="100", size="2", event_time_ns=1_000),
            side="BUY",
            confidence_bps=10000,
            policy=policy,
        ),
        classify_quote_test(
            make_trade(sequence=2, price="99", size="1", event_time_ns=1_001),
            quote=QuoteContext(bid_text="99", ask_text="101", as_of_time_ns=1_000),
            confidence_bps=8000,
            policy=policy,
        ),
        classify_unknown(
            make_trade(sequence=3, price="100", size="1", event_time_ns=1_002),
            policy=policy,
        ),
    ]
    snapshot = build_flow_snapshot(items, stream_id="btc-usd-evidence", cvd_start_text="5", policy=policy)

    fx = validate_trade_print(
        TradePrint(
            symbol="FX:EURUSD",
            market_class="FOREX_SPOT",
            source_kind="ECN_TRADE_PRINTS",
            provider="ECN_X",
            venue="ECN_X",
            price_text="1.1",
            size_text="100000",
            event_time_ns=1_000,
            sequence=1,
            coverage_scope="ECN_X_ONLY",
            source_dataset_version=DATASET,
            quality_evidence_sha256=QUALITY,
        ),
        policy=policy,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09B_TRADE_FLOW_EVIDENCE",
        "task_id": "FIN-P09-WB-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "snapshot_id": snapshot.snapshot_id,
        "buy_volume_text": snapshot.buy_volume_text,
        "sell_volume_text": snapshot.sell_volume_text,
        "unclassified_volume_text": snapshot.unclassified_volume_text,
        "delta_text": snapshot.delta_text,
        "cvd_start_text": snapshot.cvd_start_text,
        "cvd_end_text": snapshot.cvd_end_text,
        "classification_coverage_bps": snapshot.classification_coverage_bps,
        "weighted_classification_confidence_bps": snapshot.weighted_classification_confidence_bps,
        "forex_source_kind": fx.source_kind,
        "forex_coverage_scope": fx.coverage_scope,
        "quote_updates_as_trade_prints_allowed": policy.quote_updates_as_trade_prints_allowed,
        "tick_volume_as_trade_prints_allowed": policy.tick_volume_as_trade_prints_allowed,
        "forex_spot_global_flow_claim_allowed": policy.forex_spot_global_flow_claim_allowed,
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
    print(f"P09B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
