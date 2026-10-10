from __future__ import annotations

from pathlib import Path
import unittest

from packages.order_flow_liquidity.trade_flow import TradeFlowPolicy, TradePrint
from packages.order_flow_liquidity.volume_profile import (
    VolumeProfileError,
    VolumeProfilePolicy,
    assert_no_profile_trade_authority_fields,
    build_volume_profile,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_POLICY = ROOT / "config/order-flow-liquidity/volume-profile-policy.json"
TRADE_POLICY = ROOT / "config/order-flow-liquidity/trade-flow-policy.json"
DATASET = "e" * 64
QUALITY = "f" * 64


def profile_policy() -> VolumeProfilePolicy:
    return VolumeProfilePolicy.from_path(PROFILE_POLICY)


def trade_policy() -> TradeFlowPolicy:
    return TradeFlowPolicy.from_path(TRADE_POLICY)


def trade(
    *,
    sequence: int,
    price: str,
    size: str,
    event_time_ns: int,
    provider: str = "KAIKO",
    venue: str = "COINBASE",
    coverage_scope: str = "COINBASE_ONLY",
    market_class: str = "CRYPTO_SPOT",
    source_kind: str = "VENUE_TRADE_PRINTS",
    symbol: str = "CRYPTO:BTC-USD",
) -> TradePrint:
    return TradePrint(
        symbol=symbol,
        market_class=market_class,
        source_kind=source_kind,
        provider=provider,
        venue=venue,
        price_text=price,
        size_text=size,
        event_time_ns=event_time_ns,
        sequence=sequence,
        coverage_scope=coverage_scope,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


class VolumeProfilePolicyTests(unittest.TestCase):
    def test_policy_forbids_proxy_profiles_and_trade_output(self) -> None:
        p = profile_policy()
        self.assertTrue(p.require_actual_trade_prints)
        self.assertFalse(p.quote_activity_profile_allowed)
        self.assertFalse(p.tick_volume_profile_allowed)
        self.assertFalse(p.forex_spot_global_profile_claim_allowed)
        self.assertFalse(p.direct_trade_output_allowed)
        self.assertEqual(p.value_area_target_bps, 7000)
        self.assertEqual(p.poc_tie_break, "LOWEST_PRICE")
        self.assertEqual(p.value_area_tie_break, "LOWER_PRICE")


class VolumeProfileTests(unittest.TestCase):
    def test_profile_bucket_poc_and_value_area_are_deterministic(self) -> None:
        items = [
            trade(sequence=1, price="100.1", size="2", event_time_ns=1_000),
            trade(sequence=2, price="100.9", size="1", event_time_ns=1_001),
            trade(sequence=3, price="101.1", size="4", event_time_ns=1_002),
            trade(sequence=4, price="102.1", size="2", event_time_ns=1_003),
            trade(sequence=5, price="103.1", size="1", event_time_ns=1_004),
        ]
        first = build_volume_profile(
            items,
            profile_id="btc-session",
            bucket_size_text="1",
            bucket_origin_text="100",
            profile_policy=profile_policy(),
            trade_policy=trade_policy(),
        )
        second = build_volume_profile(
            items,
            profile_id="btc-session",
            bucket_size_text="1",
            bucket_origin_text="100",
            profile_policy=profile_policy(),
            trade_policy=trade_policy(),
        )
        self.assertEqual(first.total_volume_text, "10")
        self.assertEqual([b.volume_text for b in first.buckets], ["3", "4", "2", "1"])
        self.assertEqual(first.poc_price_text, "101")
        self.assertEqual(first.value_area_low_text, "100")
        self.assertEqual(first.value_area_high_text, "102")
        self.assertEqual(first.value_area_achieved_bps, 7000)
        self.assertEqual(first.snapshot_id, second.snapshot_id)

    def test_poc_tie_uses_lowest_price(self) -> None:
        items = [
            trade(sequence=1, price="100.2", size="2", event_time_ns=1_000),
            trade(sequence=2, price="101.2", size="2", event_time_ns=1_001),
            trade(sequence=3, price="102.2", size="1", event_time_ns=1_002),
        ]
        result = build_volume_profile(
            items,
            profile_id="tie",
            bucket_size_text="1",
            bucket_origin_text="100",
            profile_policy=profile_policy(),
            trade_policy=trade_policy(),
        )
        self.assertEqual(result.poc_price_text, "100")

    def test_value_area_tie_expands_lower_first(self) -> None:
        items = [
            trade(sequence=1, price="99.2", size="2", event_time_ns=1_000),
            trade(sequence=2, price="100.2", size="4", event_time_ns=1_001),
            trade(sequence=3, price="101.2", size="2", event_time_ns=1_002),
            trade(sequence=4, price="102.2", size="2", event_time_ns=1_003),
        ]
        result = build_volume_profile(
            items,
            profile_id="va-tie",
            bucket_size_text="1",
            bucket_origin_text="100",
            profile_policy=profile_policy(),
            trade_policy=trade_policy(),
        )
        self.assertEqual(result.poc_price_text, "100")
        self.assertEqual(result.value_area_low_text, "99")
        self.assertEqual(result.value_area_high_text, "102")
        self.assertGreaterEqual(result.value_area_achieved_bps, 7000)

    def test_sequence_gap_and_mixed_stream_fail_closed(self) -> None:
        p = profile_policy()
        tp = trade_policy()
        with self.assertRaises(VolumeProfileError):
            build_volume_profile(
                [
                    trade(sequence=1, price="100", size="1", event_time_ns=1_000),
                    trade(sequence=3, price="101", size="1", event_time_ns=1_001),
                ],
                profile_id="gap",
                bucket_size_text="1",
                bucket_origin_text="100",
                profile_policy=p,
                trade_policy=tp,
            )
        with self.assertRaises(VolumeProfileError):
            build_volume_profile(
                [
                    trade(sequence=1, price="100", size="1", event_time_ns=1_000),
                    trade(sequence=2, price="101", size="1", event_time_ns=1_001, venue="KRAKEN"),
                ],
                profile_id="mixed",
                bucket_size_text="1",
                bucket_origin_text="100",
                profile_policy=p,
                trade_policy=tp,
            )

    def test_reversed_event_time_fails_closed(self) -> None:
        with self.assertRaises(VolumeProfileError):
            build_volume_profile(
                [
                    trade(sequence=1, price="100", size="1", event_time_ns=1_001),
                    trade(sequence=2, price="101", size="1", event_time_ns=1_000),
                ],
                profile_id="time",
                bucket_size_text="1",
                bucket_origin_text="100",
                profile_policy=profile_policy(),
                trade_policy=trade_policy(),
            )

    def test_sparse_range_limit_fails_closed(self) -> None:
        policy_path = PROFILE_POLICY
        p = profile_policy()
        self.assertEqual(p.max_profile_bucket_count, 10000)
        with self.assertRaises(VolumeProfileError):
            build_volume_profile(
                [
                    trade(sequence=1, price="1", size="1", event_time_ns=1_000),
                    trade(sequence=2, price="20000", size="1", event_time_ns=1_001),
                ],
                profile_id="sparse",
                bucket_size_text="1",
                bucket_origin_text="0",
                profile_policy=p,
                trade_policy=trade_policy(),
            )
        self.assertTrue(policy_path.is_file())

    def test_spot_fx_global_profile_claim_fails_through_trade_validation(self) -> None:
        with self.assertRaises(ValueError):
            build_volume_profile(
                [
                    trade(
                        sequence=1,
                        price="1.1",
                        size="100000",
                        event_time_ns=1_000,
                        market_class="FOREX_SPOT",
                        source_kind="ECN_TRADE_PRINTS",
                        provider="ECN_X",
                        venue="ECN_X",
                        coverage_scope="GLOBAL_MARKET",
                        symbol="FX:EURUSD",
                    )
                ],
                profile_id="fx",
                bucket_size_text="0.0001",
                bucket_origin_text="1",
                profile_policy=profile_policy(),
                trade_policy=trade_policy(),
            )

    def test_snapshot_identity_changes_with_bucket_geometry(self) -> None:
        items = [
            trade(sequence=1, price="100.2", size="2", event_time_ns=1_000),
            trade(sequence=2, price="101.2", size="1", event_time_ns=1_001),
        ]
        one = build_volume_profile(
            items,
            profile_id="identity",
            bucket_size_text="1",
            bucket_origin_text="100",
            profile_policy=profile_policy(),
            trade_policy=trade_policy(),
        )
        two = build_volume_profile(
            items,
            profile_id="identity",
            bucket_size_text="0.5",
            bucket_origin_text="100",
            profile_policy=profile_policy(),
            trade_policy=trade_policy(),
        )
        self.assertNotEqual(one.snapshot_id, two.snapshot_id)

    def test_invalid_bucket_size_fails_closed(self) -> None:
        with self.assertRaises(VolumeProfileError):
            build_volume_profile(
                [trade(sequence=1, price="100", size="1", event_time_ns=1_000)],
                profile_id="bad-bin",
                bucket_size_text="0",
                bucket_origin_text="100",
                profile_policy=profile_policy(),
                trade_policy=trade_policy(),
            )

    def test_no_trade_authority_or_network_execution_imports(self) -> None:
        assert_no_profile_trade_authority_fields()
        source = (ROOT / "packages/order_flow_liquidity/volume_profile.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution", "packages.execution", "requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
