from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from adapters.market_data.dxfeed import (
    DxFeedAdapterError,
    DxFeedForexQuoteAdapter,
    DxFeedForexSubscription,
)
from packages.contracts.market_data import (
    MarketEventKind,
    ProviderQuoteEnvelope,
    QuoteSizeSemantics,
)


FIXTURES = Path(__file__).parent / "fixtures"
RECEIVED_AT_NS = 1_780_820_401_999_000_222


def load_fixture() -> dict[str, object]:
    value = json.loads((FIXTURES / "dxfeed_eurusd_quote.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("fixture must be an object")
    return value


def adapter(credential_ref: str | None = None) -> DxFeedForexQuoteAdapter:
    return DxFeedForexQuoteAdapter(
        DxFeedForexSubscription(
            symbol="EUR/USD",
            canonical_id="FX:EUR/USD:SPOT_OTC",
            credential_ref=credential_ref,
        )
    )


class DxFeedForexQuoteAdapterTests(unittest.TestCase):
    def test_quote_mapping_preserves_forex_provenance(self) -> None:
        event = adapter().parse_quote(load_fixture(), received_at_ns=RECEIVED_AT_NS)
        self.assertIsInstance(event, ProviderQuoteEnvelope)
        self.assertEqual(event.kind, MarketEventKind.QUOTE)
        self.assertEqual(event.instrument.provider, "dxfeed")
        self.assertEqual(event.instrument.exchange, "COMPOSITE_OTC")
        self.assertEqual(event.instrument.instrument_class, "forex_spot_otc")
        self.assertEqual(event.instrument.code, "EUR/USD")
        self.assertEqual(event.sequence_id, "0")
        self.assertIsNone(event.provider_event_time)
        self.assertEqual(event.received_at_ns, RECEIVED_AT_NS)
        self.assertEqual(event.payload.bid_price, Decimal("1.17642"))
        self.assertEqual(event.payload.ask_price, Decimal("1.17647"))
        self.assertIsNone(event.payload.bid_size)
        self.assertIsNone(event.payload.ask_size)
        self.assertEqual(
            event.payload.size_semantics,
            QuoteSizeSemantics.PROVIDER_QUOTE_SIZE_NOT_GLOBAL_SPOT_FX_VOLUME,
        )

    def test_bid_and_ask_times_are_preserved_independently(self) -> None:
        event = adapter().parse_quote(load_fixture(), received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.bid_time.raw, "1780820400000ms")
        self.assertEqual(event.payload.bid_time.epoch_ns, 1_780_820_400_000_000_000)
        self.assertEqual(event.payload.ask_time.raw, "1780820401000ms")
        self.assertEqual(event.payload.ask_time.epoch_ns, 1_780_820_401_000_000_000)

    def test_time_nano_part_is_preserved_without_timestamp_fabrication(self) -> None:
        event = adapter().parse_quote(load_fixture(), received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.time_nano_part, 123456)
        self.assertEqual(event.payload.bid_time.epoch_ns % 1_000_000, 0)
        self.assertEqual(event.payload.ask_time.epoch_ns % 1_000_000, 0)

    def test_nonzero_event_time_is_preserved(self) -> None:
        fixture = load_fixture()
        fixture["eventTime"] = 1780820401500
        event = adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)
        self.assertIsNotNone(event.provider_event_time)
        assert event.provider_event_time is not None
        self.assertEqual(event.provider_event_time.epoch_ns, 1_780_820_401_500_000_000)

    def test_finite_quote_sizes_are_preserved_but_not_called_global_volume(self) -> None:
        fixture = load_fixture()
        fixture["bidSize"] = "2.5"
        fixture["askSize"] = 3
        event = adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.bid_size, Decimal("2.5"))
        self.assertEqual(event.payload.ask_size, Decimal("3"))
        self.assertNotEqual(event.payload.size_semantics.value, "GLOBAL_SPOT_FX_VOLUME")
        self.assertIn(("global_spot_fx_volume", "FORBIDDEN"), event.metadata)

    def test_negative_size_is_rejected(self) -> None:
        fixture = load_fixture()
        fixture["bidSize"] = "-1"
        with self.assertRaises(DxFeedAdapterError):
            adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_nonpositive_or_nonfinite_price_is_rejected(self) -> None:
        for value in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(value=value):
                fixture = load_fixture()
                fixture["bidPrice"] = value
                with self.assertRaises(DxFeedAdapterError):
                    adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_wrong_symbol_is_rejected(self) -> None:
        fixture = load_fixture()
        fixture["eventSymbol"] = "USD/JPY"
        with self.assertRaises(DxFeedAdapterError):
            adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_rest_quote_wrapper_maps_identically_to_direct_quote(self) -> None:
        fixture = load_fixture()
        direct = adapter().parse_quote(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        wrapped = adapter().parse_quote(
            {"status": "OK", "Quote": {"EUR/USD": copy.deepcopy(fixture)}},
            received_at_ns=RECEIVED_AT_NS,
        )
        self.assertEqual(wrapped, direct)

    def test_raw_or_empty_credential_handle_is_rejected(self) -> None:
        for value in ("raw-token", "secret://", " "):
            with self.subTest(value=value):
                with self.assertRaises(DxFeedAdapterError):
                    adapter(value)

    def test_secret_handle_is_preserved_but_not_resolved(self) -> None:
        instance = adapter("secret://market-data/dxfeed/token")
        spec = instance.subscription_spec()
        self.assertEqual(spec.transport, "DXLINK_WEBSOCKET_REFERENCE")
        self.assertEqual(spec.event_type, "Quote")
        self.assertEqual(spec.symbol, "EUR/USD")
        self.assertEqual(spec.credential_ref, "secret://market-data/dxfeed/token")
        self.assertIsNone(spec.endpoint_ref)
        self.assertEqual(spec.intended_use, "OFFLINE_CONTRACT_ONLY")

    def test_no_credential_is_valid_for_offline_contract(self) -> None:
        spec = adapter().subscription_spec()
        self.assertIsNone(spec.credential_ref)
        self.assertIsNone(spec.endpoint_ref)

    def test_invalid_received_at_type_is_rejected(self) -> None:
        fixture = load_fixture()
        for value in (-1, True, "1780820401999000222"):
            with self.subTest(value=value):
                with self.assertRaises(DxFeedAdapterError):
                    adapter().parse_quote(fixture, received_at_ns=value)  # type: ignore[arg-type]

    def test_negative_time_nano_part_is_rejected(self) -> None:
        fixture = load_fixture()
        fixture["timeNanoPart"] = -1
        with self.assertRaises(DxFeedAdapterError):
            adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_parsing_is_deterministic(self) -> None:
        fixture = load_fixture()
        first = adapter().parse_quote(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        second = adapter().parse_quote(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
