from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.trade_flow import TradeFlowPolicy, TradePrint
from packages.order_flow_liquidity.volume_profile import VolumeProfilePolicy, build_volume_profile

ROOT = Path(__file__).resolve().parents[2]
PROFILE_POLICY_PATH = ROOT / "config/order-flow-liquidity/volume-profile-policy.json"
TRADE_POLICY_PATH = ROOT / "config/order-flow-liquidity/trade-flow-policy.json"
DATASET = "e" * 64
QUALITY = "f" * 64


def trade(*, sequence: int, price: str, size: str, event_time_ns: int) -> TradePrint:
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

    profile_policy = VolumeProfilePolicy.from_path(PROFILE_POLICY_PATH)
    trade_policy = TradeFlowPolicy.from_path(TRADE_POLICY_PATH)
    snapshot = build_volume_profile(
        [
            trade(sequence=1, price="100.1", size="2", event_time_ns=1_000),
            trade(sequence=2, price="100.9", size="1", event_time_ns=1_001),
            trade(sequence=3, price="101.1", size="4", event_time_ns=1_002),
            trade(sequence=4, price="102.1", size="2", event_time_ns=1_003),
            trade(sequence=5, price="103.1", size="1", event_time_ns=1_004),
        ],
        profile_id="btc-session-evidence",
        bucket_size_text="1",
        bucket_origin_text="100",
        profile_policy=profile_policy,
        trade_policy=trade_policy,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09C_VOLUME_PROFILE_EVIDENCE",
        "task_id": "FIN-P09-WC-001",
        "profile_policy_sha256": hashlib.sha256(PROFILE_POLICY_PATH.read_bytes()).hexdigest(),
        "trade_policy_sha256": hashlib.sha256(TRADE_POLICY_PATH.read_bytes()).hexdigest(),
        "snapshot_id": snapshot.snapshot_id,
        "profile_id": snapshot.profile_id,
        "total_volume_text": snapshot.total_volume_text,
        "poc_price_text": snapshot.poc_price_text,
        "value_area_low_text": snapshot.value_area_low_text,
        "value_area_high_text": snapshot.value_area_high_text,
        "value_area_target_bps": snapshot.value_area_target_bps,
        "value_area_achieved_bps": snapshot.value_area_achieved_bps,
        "bucket_count": len(snapshot.buckets),
        "bucket_volumes": [bucket.volume_text for bucket in snapshot.buckets],
        "quote_activity_profile_allowed": profile_policy.quote_activity_profile_allowed,
        "tick_volume_profile_allowed": profile_policy.tick_volume_profile_allowed,
        "forex_spot_global_profile_claim_allowed": profile_policy.forex_spot_global_profile_claim_allowed,
        "direct_trade_output_allowed": profile_policy.direct_trade_output_allowed,
        "production_order_flow_vendor": profile_policy.production_order_flow_vendor,
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
    print(f"P09C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
