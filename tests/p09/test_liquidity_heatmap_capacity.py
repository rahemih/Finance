from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from packages.order_flow_liquidity.liquidity_heatmap import (
    LiquidityHeatmapError,
    LiquidityHeatmapPolicy,
    assert_no_heatmap_execution_authority_fields,
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


def heatmap_policy() -> LiquidityHeatmapPolicy:
    return LiquidityHeatmapPolicy.from_path(HEATMAP_POLICY_PATH)


def book_policy() -> OrderBookPolicy:
    return OrderBookPolicy.from_path(BOOK_POLICY_PATH)


def level(price: str, size: str) -> OrderBookLevel:
    return OrderBookLevel(price_text=price, size_text=size)


def book(
    *,
    bids: tuple[OrderBookLevel, ...] | None = None,
    asks: tuple[OrderBookLevel, ...] | None = None,
    market_class: str = "CRYPTO_SPOT",
    source_kind: str = "VENUE_ORDER_BOOK",
    provider: str = "KAIKO",
    venue: str = "COINBASE",
    coverage_scope: str = "COINBASE_ONLY",
    symbol: str = "CRYPTO:BTC-USD",
) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        symbol=symbol,
        market_class=market_class,
        source_kind=source_kind,
        provider=provider,
        venue=venue,
        event_time_ns=1_000,
        as_of_time_ns=1_000,
        sequence=1,
        coverage_scope=coverage_scope,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
        bids=bids or (level("100", "4"), level("99", "3"), level("98", "2"), level("90", "7")),
        asks=asks or (level("102", "2"), level("103", "1"), level("104", "2"), level("115", "5")),
    )


class LiquidityHeatmapPolicyTests(unittest.TestCase):
    def test_policy_is_displayed_capacity_only(self) -> None:
        p = heatmap_policy()
        self.assertEqual(p.distance_bands_bps, (100, 250, 500, 1000))
        self.assertTrue(p.displayed_capacity_only)
        self.assertFalse(p.hidden_liquidity_inference_allowed)
        self.assertFalse(p.fillability_claim_allowed)
        self.assertFalse(p.slippage_or_market_impact_claim_allowed)
        self.assertFalse(p.cross_provider_aggregation_allowed)
        self.assertFalse(p.forex_spot_global_liquidity_claim_allowed)
        self.assertFalse(p.direct_trade_output_allowed)

    def test_non_increasing_bands_fail_closed(self) -> None:
        raw = json.loads(HEATMAP_POLICY_PATH.read_text(encoding="utf-8"))
        raw["distance_bands_bps"] = [100, 100]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(LiquidityHeatmapError):
                LiquidityHeatmapPolicy.from_path(path)


class LiquidityHeatmapTests(unittest.TestCase):
    def test_heatmap_is_deterministic_and_non_cumulative_cells_do_not_double_count(self) -> None:
        first = build_liquidity_heatmap(
            book(),
            heatmap_policy=heatmap_policy(),
            order_book_policy=book_policy(),
        )
        second = build_liquidity_heatmap(
            book(),
            heatmap_policy=heatmap_policy(),
            order_book_policy=book_policy(),
        )
        self.assertEqual(first.heatmap_id, second.heatmap_id)
        self.assertEqual(first.mid_price_text, "101")
        self.assertEqual(
            [(b.bid_size_text, b.ask_size_text) for b in first.bands[:3]],
            [("4", "2"), ("3", "1"), ("2", "2")],
        )
        self.assertEqual(first.bands[0].bid_notional_text, "400")
        self.assertEqual(first.bands[0].ask_notional_text, "204")
        self.assertEqual(first.bands[2].cumulative_bid_size_text, "9")
        self.assertEqual(first.bands[2].cumulative_ask_size_text, "5")
        self.assertEqual(first.outside_bid_size_text, "7")
        self.assertEqual(first.outside_ask_size_text, "5")

    def test_capacity_shares_are_bounded_and_sum_to_10000_when_liquidity_exists(self) -> None:
        result = build_liquidity_heatmap(
            book(),
            heatmap_policy=heatmap_policy(),
            order_book_policy=book_policy(),
        )
        for band in result.bands:
            total = band.cumulative_total_notional_text
            if total != "0":
                self.assertGreaterEqual(band.bid_capacity_share_bps, 0)
                self.assertLessEqual(band.bid_capacity_share_bps, 10000)
                self.assertEqual(
                    band.bid_capacity_share_bps + band.ask_capacity_share_bps,
                    10000,
                )

    def test_heatmap_identity_changes_with_source_content(self) -> None:
        first = build_liquidity_heatmap(
            book(),
            heatmap_policy=heatmap_policy(),
            order_book_policy=book_policy(),
        )
        second = build_liquidity_heatmap(
            book(bids=(level("100", "5"), level("99", "3"), level("98", "2"))),
            heatmap_policy=heatmap_policy(),
            order_book_policy=book_policy(),
        )
        self.assertNotEqual(first.heatmap_id, second.heatmap_id)

    def test_no_in_scope_liquidity_fails_closed(self) -> None:
        raw = json.loads(HEATMAP_POLICY_PATH.read_text(encoding="utf-8"))
        raw["distance_bands_bps"] = [1]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            tiny = LiquidityHeatmapPolicy.from_path(path)
            with self.assertRaises(LiquidityHeatmapError):
                build_liquidity_heatmap(
                    book(),
                    heatmap_policy=tiny,
                    order_book_policy=book_policy(),
                )

    def test_invalid_order_book_and_fx_global_claim_fail_through_p09d(self) -> None:
        with self.assertRaises(ValueError):
            build_liquidity_heatmap(
                book(bids=(level("102", "1"),), asks=(level("102", "1"),)),
                heatmap_policy=heatmap_policy(),
                order_book_policy=book_policy(),
            )
        with self.assertRaises(ValueError):
            build_liquidity_heatmap(
                book(
                    market_class="FOREX_SPOT",
                    source_kind="ECN_ORDER_BOOK",
                    provider="ECN_X",
                    venue="ECN_X",
                    coverage_scope="GLOBAL_MARKET",
                    symbol="FX:EURUSD",
                ),
                heatmap_policy=heatmap_policy(),
                order_book_policy=book_policy(),
            )

    def test_no_execution_authority_or_network_imports(self) -> None:
        assert_no_heatmap_execution_authority_fields()
        source = (ROOT / "packages/order_flow_liquidity/liquidity_heatmap.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution", "packages.execution", "requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
