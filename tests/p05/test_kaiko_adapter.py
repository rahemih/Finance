from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from adapters.market_data.kaiko import (
    API_KEY_HEADER,
    ORDER_BOOK_L2_ENDPOINT,
    TRADE_ENDPOINT,
    KaikoAdapter,
    KaikoAdapterError,
    KaikoLexicographicSequenceGuard,
    KaikoSubscription,
)
from packages.contracts.market_data import (
    MarketEventKind,
    OrderBookPayload,
    OrderBookUpdateType,
    SequenceDisposition,
    TradePayload,
    TradeSide,
)


FIXTURES = Path(__file__).parent / "fixtures"
RECEIVED_AT_NS = 1_780_820_400_999_000_111


def load_fixture(name: str) -> dict[str, object]:
    value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("fixture must be an object")
    return value


def adapter() -> KaikoAdapter:
    return KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    )


class KaikoAdapterTests(unittest.TestCase):
    def test_trade_mapping_preserves_provider_provenance_and_nanoseconds(self) -> None:
        event = adapter().parse_trade(load_fixture("kaiko_trade.json"), received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.kind, MarketEventKind.TRADE)
        self.assertEqual(event.instrument.provider, "kaiko")
        self.assertEqual(event.instrument.exchange, "cbse")
        self.assertEqual(event.instrument.instrument_class, "spot")
        self.assertEqual(event.instrument.code, "btc-usd")
        self.assertEqual(event.sequence_id, "a000001")
        self.assertEqual(event.ts_exchange.raw, "2026-10-05T09:00:00.123456789Z")
        self.assertEqual(event.ts_exchange.epoch_ns % 1_000_000_000, 123_456_789)
        self.assertEqual(event.ts_collection.epoch_ns % 1_000_000_000, 123_556_789)
        self.assertEqual(event.ts_event.epoch_ns % 1_000_000_000, 123_656_789)
        self.assertEqual(event.received_at_ns, RECEIVED_AT_NS)
        self.assertIsInstance(event.payload, TradePayload)
        payload = event.payload
        assert isinstance(payload, TradePayload)
        self.assertEqual(payload.trade_id, "trade-001")
        self.assertEqual(payload.price, Decimal("61234.50"))
        self.assertEqual(payload.amount, Decimal("0.015"))
        self.assertEqual(payload.side, TradeSide.BUY)

    def test_snapshot_mapping_preserves_snapshot_semantics(self) -> None:
        event = adapter().parse_order_book(
            load_fixture("kaiko_orderbook_snapshot.json"),
            received_at_ns=RECEIVED_AT_NS,
        )
        self.assertEqual(event.kind, MarketEventKind.ORDER_BOOK)
        self.assertIsInstance(event.payload, OrderBookPayload)
        payload = event.payload
        assert isinstance(payload, OrderBookPayload)
        self.assertEqual(payload.update_type, OrderBookUpdateType.SNAPSHOT)
        self.assertEqual(len(payload.asks), 2)
        self.assertEqual(len(payload.bids), 2)

    def test_updated_alias_normalizes_to_update_and_zero_amount_is_preserved(self) -> None:
        event = adapter().parse_order_book(
            load_fixture("kaiko_orderbook_update.json"),
            received_at_ns=RECEIVED_AT_NS,
        )
        payload = event.payload
        assert isinstance(payload, OrderBookPayload)
        self.assertEqual(payload.update_type, OrderBookUpdateType.UPDATE)
        self.assertEqual(payload.asks[0].amount, Decimal("0"))
        self.assertEqual(payload.bids[0].amount, Decimal("0.40"))

    def test_sequence_guard_is_lexicographic_without_contiguity_claim(self) -> None:
        guard = KaikoLexicographicSequenceGuard()
        self.assertEqual(guard.observe("book", "a000001"), SequenceDisposition.FIRST)
        self.assertEqual(guard.observe("book", "a000003"), SequenceDisposition.ADVANCING)
        self.assertEqual(guard.observe("book", "a000003"), SequenceDisposition.DUPLICATE)
        self.assertEqual(guard.observe("book", "a000002"), SequenceDisposition.OUT_OF_ORDER)
        self.assertEqual(guard.observe("book", "z999999"), SequenceDisposition.ADVANCING)

    def test_raw_secret_is_rejected(self) -> None:
        with self.assertRaises(KaikoAdapterError):
            KaikoSubscription(
                exchange="cbse",
                instrument_class="spot",
                code="btc-usd",
                credential_ref="real-looking-api-key",
            )

    def test_request_specs_expose_only_secret_handle_and_required_header(self) -> None:
        instance = adapter()
        trade = instance.trade_request_spec()
        book = instance.order_book_request_spec()
        self.assertEqual(trade.url, TRADE_ENDPOINT)
        self.assertEqual(book.url, ORDER_BOOK_L2_ENDPOINT)
        self.assertEqual(trade.api_key_header, API_KEY_HEADER)
        self.assertEqual(trade.credential_ref, "secret://market-data/kaiko/api-key")
        self.assertNotIn("secret://", trade.body_json)
        body = json.loads(trade.body_json)
        self.assertEqual(body["data"]["query"]["instruments"][0]["code"], "btc-usd")

    def test_wrong_instrument_is_rejected(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        fixture["code"] = "eth-usd"
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_trade(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_missing_sequence_is_rejected(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        fixture.pop("sequenceId")
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_trade(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_malformed_timestamp_is_rejected(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        fixture["tsExchange"] = "not-a-time"
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_trade(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_negative_orderbook_amount_is_rejected(self) -> None:
        fixture = load_fixture("kaiko_orderbook_update.json")
        fixture["asks"] = [{"price": "61235", "amount": "-0.01"}]
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_order_book(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_nonpositive_price_is_rejected(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        fixture["price"] = "0"
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_trade(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_trade_amount_must_be_positive(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        fixture["amount"] = "0"
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_trade(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_received_at_must_be_nonnegative_integer(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        with self.assertRaises(KaikoAdapterError):
            adapter().parse_trade(fixture, received_at_ns=-1)

    def test_parsing_is_deterministic_for_same_input_and_receive_time(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        first = adapter().parse_trade(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        second = adapter().parse_trade(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(first, second)
        self.assertEqual(first.metadata, (("partition", "1"), ("source", '"fixture"')))

    def test_unknown_trade_side_is_preserved_as_unknown(self) -> None:
        fixture = load_fixture("kaiko_trade.json")
        fixture["side"] = "UNSPECIFIED"
        event = adapter().parse_trade(fixture, received_at_ns=RECEIVED_AT_NS)
        payload = event.payload
        assert isinstance(payload, TradePayload)
        self.assertEqual(payload.side, TradeSide.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
