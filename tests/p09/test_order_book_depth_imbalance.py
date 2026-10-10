from __future__ import annotations

from pathlib import Path
import unittest

from packages.order_flow_liquidity.order_book import (
    OrderBookError,
    OrderBookLevel,
    OrderBookMetrics,
    OrderBookPolicy,
    OrderBookSnapshot,
    assert_no_order_book_trade_authority_fields,
    compute_order_book_metrics,
    validate_order_book,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/order-book-policy.json"
DATASET = "1" * 64
QUALITY = "2" * 64


def policy() -> OrderBookPolicy:
    return OrderBookPolicy.from_path(POLICY_PATH)


def level(price: str, size: str) -> OrderBookLevel:
    return OrderBookLevel(price_text=price, size_text=size)


def book(
    *,
    bids: tuple[OrderBookLevel, ...] | None = None,
    asks: tuple[OrderBookLevel, ...] | None = None,
    event_time_ns: int = 1_000,
    as_of_time_ns: int = 1_000,
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
        event_time_ns=event_time_ns,
        as_of_time_ns=as_of_time_ns,
        sequence=1,
        coverage_scope=coverage_scope,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
        bids=bids or (level("100", "4"), level("99", "3"), level("98", "2")),
        asks=asks or (level("102", "2"), level("103", "1"), level("104", "2")),
    )


class OrderBookPolicyTests(unittest.TestCase):
    def test_policy_is_fail_closed(self) -> None:
        p = policy()
        self.assertFalse(p.locked_or_crossed_book_allowed)
        self.assertFalse(p.forex_spot_global_book_claim_allowed)
        self.assertFalse(p.direct_trade_output_allowed)
        self.assertEqual(p.production_order_flow_vendor, "NOT_SELECTED")


class OrderBookValidationTests(unittest.TestCase):
    def test_valid_book_is_content_addressed(self) -> None:
        first = validate_order_book(book(), policy=policy())
        second = validate_order_book(book(), policy=policy())
        self.assertEqual(first.snapshot_id, second.snapshot_id)

    def test_snapshot_identity_is_content_sensitive(self) -> None:
        first = validate_order_book(book(), policy=policy())
        second = validate_order_book(
            book(bids=(level("100", "5"), level("99", "3"), level("98", "2"))),
            policy=policy(),
        )
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)

    def test_bid_ask_ordering_and_duplicates_fail_closed(self) -> None:
        with self.assertRaises(OrderBookError):
            validate_order_book(
                book(bids=(level("99", "1"), level("100", "1"))),
                policy=policy(),
            )
        with self.assertRaises(OrderBookError):
            validate_order_book(
                book(asks=(level("102", "1"), level("102", "2"))),
                policy=policy(),
            )

    def test_locked_or_crossed_book_fails_closed(self) -> None:
        with self.assertRaises(OrderBookError):
            validate_order_book(
                book(bids=(level("102", "1"),), asks=(level("102", "1"),)),
                policy=policy(),
            )
        with self.assertRaises(OrderBookError):
            validate_order_book(
                book(bids=(level("103", "1"),), asks=(level("102", "1"),)),
                policy=policy(),
            )

    def test_future_event_time_fails_closed(self) -> None:
        with self.assertRaises(OrderBookError):
            validate_order_book(book(event_time_ns=1_001, as_of_time_ns=1_000), policy=policy())

    def test_spot_fx_source_and_global_claim_fail_closed(self) -> None:
        valid = book(
            market_class="FOREX_SPOT",
            source_kind="ECN_ORDER_BOOK",
            provider="ECN_X",
            venue="ECN_X",
            coverage_scope="ECN_X_ONLY",
            symbol="FX:EURUSD",
        )
        self.assertEqual(validate_order_book(valid, policy=policy()).source_kind, "ECN_ORDER_BOOK")
        with self.assertRaises(OrderBookError):
            validate_order_book(
                book(
                    market_class="FOREX_SPOT",
                    source_kind="VENUE_ORDER_BOOK",
                    provider="FX",
                    venue="FX",
                    coverage_scope="FX_ONLY",
                    symbol="FX:EURUSD",
                ),
                policy=policy(),
            )
        with self.assertRaises(OrderBookError):
            validate_order_book(
                book(
                    market_class="FOREX_SPOT",
                    source_kind="ECN_ORDER_BOOK",
                    provider="ECN_X",
                    venue="ECN_X",
                    coverage_scope="GLOBAL_MARKET",
                    symbol="FX:EURUSD",
                ),
                policy=policy(),
            )


class OrderBookMetricsTests(unittest.TestCase):
    def test_spread_depth_and_imbalance_are_deterministic(self) -> None:
        result = compute_order_book_metrics(book(), depth_levels=2, policy=policy())
        self.assertIsInstance(result, OrderBookMetrics)
        self.assertEqual(result.best_bid_text, "100")
        self.assertEqual(result.best_ask_text, "102")
        self.assertEqual(result.mid_price_text, "101")
        self.assertEqual(result.spread_text, "2")
        self.assertEqual(result.spread_bps, 198)
        self.assertEqual(result.bid_depth_text, "7")
        self.assertEqual(result.ask_depth_text, "3")
        self.assertEqual(result.imbalance_bps, 4000)

    def test_depth_requires_comparable_levels(self) -> None:
        with self.assertRaises(OrderBookError):
            compute_order_book_metrics(book(), depth_levels=4, policy=policy())

    def test_negative_imbalance_is_bounded(self) -> None:
        result = compute_order_book_metrics(
            book(
                bids=(level("100", "1"), level("99", "1")),
                asks=(level("102", "4"), level("103", "4")),
            ),
            depth_levels=2,
            policy=policy(),
        )
        self.assertEqual(result.imbalance_bps, -6000)
        self.assertGreaterEqual(result.imbalance_bps, -10000)
        self.assertLessEqual(result.imbalance_bps, 10000)

    def test_no_trade_authority_or_network_execution_imports(self) -> None:
        assert_no_order_book_trade_authority_fields()
        source = (ROOT / "packages/order_flow_liquidity/order_book.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution", "packages.execution", "requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
