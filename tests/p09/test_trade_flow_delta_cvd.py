from __future__ import annotations

from pathlib import Path
import unittest

from packages.order_flow_liquidity.trade_flow import (
    QuoteContext,
    TradeFlowError,
    TradeFlowPolicy,
    TradePrint,
    assert_no_trade_authority_fields,
    build_flow_snapshot,
    classify_native_aggressor,
    classify_quote_test,
    classify_tick_rule,
    classify_unknown,
    validate_trade_print,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/trade-flow-policy.json"
DATASET = "c" * 64
QUALITY = "d" * 64


def policy() -> TradeFlowPolicy:
    return TradeFlowPolicy.from_path(POLICY_PATH)


def trade(
    *,
    sequence: int = 1,
    price: str = "100",
    size: str = "1",
    event_time_ns: int = 1_000,
    market_class: str = "CRYPTO_SPOT",
    source_kind: str = "VENUE_TRADE_PRINTS",
    coverage_scope: str = "COINBASE_ONLY",
    provider: str = "KAIKO",
    venue: str = "COINBASE",
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


class TradeFlowPolicyTests(unittest.TestCase):
    def test_policy_forbids_quote_tick_synthetic_trades_and_direct_output(self) -> None:
        value = policy()
        self.assertFalse(value.quote_updates_as_trade_prints_allowed)
        self.assertFalse(value.tick_volume_as_trade_prints_allowed)
        self.assertFalse(value.forex_spot_global_flow_claim_allowed)
        self.assertFalse(value.direct_trade_output_allowed)
        self.assertTrue(value.require_contiguous_sequence_for_cvd)
        self.assertEqual(value.production_order_flow_vendor, "NOT_SELECTED")


class TradePrintValidationTests(unittest.TestCase):
    def test_native_crypto_trade_print_is_valid_and_content_addressed(self) -> None:
        first = validate_trade_print(trade(), policy=policy())
        second = validate_trade_print(trade(), policy=policy())
        self.assertEqual(first.trade_id, second.trade_id)

    def test_tick_volume_proxy_cannot_become_trade_print(self) -> None:
        with self.assertRaises(TradeFlowError):
            validate_trade_print(trade(source_kind="TICK_VOLUME_PROXY"), policy=policy())

    def test_spot_fx_requires_broker_or_ecn_scope(self) -> None:
        fx = trade(
            market_class="FOREX_SPOT",
            source_kind="BROKER_TRADE_PRINTS",
            coverage_scope="BROKER_FEED_ONLY",
            provider="BROKER_X",
            venue="BROKER_X",
            symbol="FX:EURUSD",
        )
        self.assertEqual(validate_trade_print(fx, policy=policy()).source_kind, "BROKER_TRADE_PRINTS")
        with self.assertRaises(TradeFlowError):
            validate_trade_print(
                trade(
                    market_class="FOREX_SPOT",
                    source_kind="VENUE_TRADE_PRINTS",
                    coverage_scope="GLOBAL_MARKET",
                    provider="FX",
                    venue="FX",
                    symbol="FX:EURUSD",
                ),
                policy=policy(),
            )

    def test_spot_fx_global_claim_fails_closed(self) -> None:
        for scope in ("GLOBAL_MARKET", "CONSOLIDATED_MARKET", "TOTAL_MARKET"):
            with self.subTest(scope=scope):
                with self.assertRaises(TradeFlowError):
                    validate_trade_print(
                        trade(
                            market_class="FOREX_SPOT",
                            source_kind="ECN_TRADE_PRINTS",
                            coverage_scope=scope,
                            provider="ECN_X",
                            venue="ECN_X",
                            symbol="FX:EURUSD",
                        ),
                        policy=policy(),
                    )


class AggressorClassificationTests(unittest.TestCase):
    def test_native_aggressor_provenance_is_explicit(self) -> None:
        item = classify_native_aggressor(trade(), side="BUY", confidence_bps=10000, policy=policy())
        self.assertEqual(item.aggressor_side, "BUY")
        self.assertEqual(item.classification_method, "NATIVE_AGGRESSOR_FLAG")

    def test_quote_test_buy_sell_and_mid_unknown(self) -> None:
        quote = QuoteContext(bid_text="99", ask_text="101", as_of_time_ns=900)
        buy = classify_quote_test(trade(price="101"), quote=quote, confidence_bps=8000, policy=policy())
        sell = classify_quote_test(trade(price="99"), quote=quote, confidence_bps=8000, policy=policy())
        unknown = classify_quote_test(trade(price="100"), quote=quote, confidence_bps=8000, policy=policy())
        self.assertEqual(buy.aggressor_side, "BUY")
        self.assertEqual(sell.aggressor_side, "SELL")
        self.assertEqual(unknown.aggressor_side, "UNKNOWN")
        self.assertEqual(unknown.classification_method, "UNCLASSIFIED")
        self.assertEqual(unknown.classification_confidence_bps, 0)

    def test_quote_test_future_context_fails_closed(self) -> None:
        with self.assertRaises(TradeFlowError):
            classify_quote_test(
                trade(event_time_ns=1_000),
                quote=QuoteContext(bid_text="99", ask_text="101", as_of_time_ns=1_001),
                confidence_bps=8000,
                policy=policy(),
            )

    def test_tick_rule_is_deterministic_and_point_in_time(self) -> None:
        previous = trade(sequence=1, price="100", event_time_ns=1_000)
        up = trade(sequence=2, price="101", event_time_ns=1_001)
        down = trade(sequence=2, price="99", event_time_ns=1_001)
        flat = trade(sequence=2, price="100", event_time_ns=1_001)
        self.assertEqual(
            classify_tick_rule(up, previous_trade=previous, confidence_bps=6000, policy=policy()).aggressor_side,
            "BUY",
        )
        self.assertEqual(
            classify_tick_rule(down, previous_trade=previous, confidence_bps=6000, policy=policy()).aggressor_side,
            "SELL",
        )
        self.assertEqual(
            classify_tick_rule(flat, previous_trade=previous, confidence_bps=6000, policy=policy()).aggressor_side,
            "UNKNOWN",
        )
        with self.assertRaises(TradeFlowError):
            classify_tick_rule(previous, previous_trade=up, confidence_bps=6000, policy=policy())


class FlowSnapshotTests(unittest.TestCase):
    def test_delta_cvd_coverage_and_confidence_are_deterministic(self) -> None:
        p = policy()
        items = [
            classify_native_aggressor(
                trade(sequence=1, price="100", size="2", event_time_ns=1_000),
                side="BUY",
                confidence_bps=10000,
                policy=p,
            ),
            classify_quote_test(
                trade(sequence=2, price="99", size="1", event_time_ns=1_001),
                quote=QuoteContext(bid_text="99", ask_text="101", as_of_time_ns=1_000),
                confidence_bps=8000,
                policy=p,
            ),
            classify_unknown(trade(sequence=3, price="100", size="1", event_time_ns=1_002), policy=p),
        ]
        first = build_flow_snapshot(items, stream_id="btc-usd-1", cvd_start_text="5", policy=p)
        second = build_flow_snapshot(items, stream_id="btc-usd-1", cvd_start_text="5", policy=p)
        self.assertEqual(first.buy_volume_text, "2")
        self.assertEqual(first.sell_volume_text, "1")
        self.assertEqual(first.unclassified_volume_text, "1")
        self.assertEqual(first.delta_text, "1")
        self.assertEqual(first.cvd_start_text, "5")
        self.assertEqual(first.cvd_end_text, "6")
        self.assertEqual(first.classification_coverage_bps, 7500)
        self.assertEqual(first.weighted_classification_confidence_bps, 9333)
        self.assertEqual(first.snapshot_id, second.snapshot_id)

    def test_sequence_gap_fails_closed_for_cvd(self) -> None:
        p = policy()
        items = [
            classify_native_aggressor(trade(sequence=1), side="BUY", confidence_bps=9000, policy=p),
            classify_native_aggressor(trade(sequence=3), side="SELL", confidence_bps=9000, policy=p),
        ]
        with self.assertRaises(TradeFlowError):
            build_flow_snapshot(items, stream_id="gap", cvd_start_text="0", policy=p)

    def test_mixed_stream_fails_closed(self) -> None:
        p = policy()
        items = [
            classify_native_aggressor(trade(sequence=1), side="BUY", confidence_bps=9000, policy=p),
            classify_native_aggressor(
                trade(sequence=2, venue="KRAKEN"),
                side="SELL",
                confidence_bps=9000,
                policy=p,
            ),
        ]
        with self.assertRaises(TradeFlowError):
            build_flow_snapshot(items, stream_id="mixed", cvd_start_text="0", policy=p)

    def test_all_unknown_flow_has_zero_delta_coverage_and_confidence(self) -> None:
        p = policy()
        snapshot = build_flow_snapshot(
            [classify_unknown(trade(), policy=p)],
            stream_id="unknown",
            cvd_start_text="7",
            policy=p,
        )
        self.assertEqual(snapshot.delta_text, "0")
        self.assertEqual(snapshot.cvd_end_text, "7")
        self.assertEqual(snapshot.classification_coverage_bps, 0)
        self.assertEqual(snapshot.weighted_classification_confidence_bps, 0)

    def test_no_trade_authority_or_network_execution_imports(self) -> None:
        assert_no_trade_authority_fields()
        source = (ROOT / "packages/order_flow_liquidity/trade_flow.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution", "packages.execution", "requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
