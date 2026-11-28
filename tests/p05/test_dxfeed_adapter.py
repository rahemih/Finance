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

    def test_object_stringification_cannot_forge_numeric_quote(self) -> None:
        """Q03: only primitive numeric/string wire values are valid prices."""
        class ForgedPrice:
            def __str__(self) -> str:
                return "1.17642"

        for field in ("bidPrice", "askPrice"):
            with self.subTest(field=field):
                fixture = load_fixture()
                fixture[field] = ForgedPrice()
                with self.assertRaisesRegex(DxFeedAdapterError, "must be numeric"):
                    adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_object_stringification_cannot_forge_quote_size(self) -> None:
        """Q03: size fields reject custom objects even when __str__ looks numeric."""
        class ForgedSize:
            def __str__(self) -> str:
                return "2.5"

        for field in ("bidSize", "askSize"):
            with self.subTest(field=field):
                fixture = load_fixture()
                fixture[field] = ForgedSize()
                with self.assertRaisesRegex(DxFeedAdapterError, "must be numeric or NaN"):
                    adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_signalling_nan_size_is_rejected_without_quarantine_bypass(self) -> None:
        """Q03: sNaN is not a valid missing quote-size sentinel."""
        for field in ("bidSize", "askSize"):
            with self.subTest(field=field):
                fixture = load_fixture()
                fixture[field] = "sNaN"
                with self.assertRaisesRegex(DxFeedAdapterError, "finite and >= 0"):
                    adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_crossed_quotes_are_rejected_without_normalization(self) -> None:
        """Q03: inverted bid/ask must fail closed for direct and wrapped feeds."""
        for bid, ask in (("1.20", "1.19"), ("2", "1")):
            with self.subTest(bid=bid, ask=ask):
                fixture = load_fixture()
                fixture["bidPrice"] = bid
                fixture["askPrice"] = ask
                for message in (
                    fixture,
                    {"status": "OK", "Quote": {"EUR/USD": fixture}},
                ):
                    with self.assertRaisesRegex(DxFeedAdapterError, "crossed quote"):
                        adapter().parse_quote(message, received_at_ns=RECEIVED_AT_NS)

    def test_equal_bid_ask_is_not_silently_repriced(self) -> None:
        fixture = load_fixture()
        fixture["bidPrice"] = "1.17642"
        fixture["askPrice"] = "1.17642"
        event = adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.bid_price, event.payload.ask_price)

    def test_string_subclass_cannot_forge_provider_symbol(self) -> None:
        """Q03: a Python object is not an authentic wire-format symbol."""
        class ForgedSymbol(str):
            def __eq__(self, other: object) -> bool:
                return other == "EUR/USD"

        fixture = load_fixture()
        fixture["eventSymbol"] = ForgedSymbol("USD/JPY")
        with self.assertRaisesRegex(DxFeedAdapterError, "non-empty string"):
            adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_exchange_code_string_subclass_is_rejected(self) -> None:
        """Q03: provider provenance fields must be primitive wire strings."""
        class ForgedExchange(str):
            def __str__(self) -> str:
                return "SAFE"

        for field in ("bidExchangeCode", "askExchangeCode"):
            with self.subTest(field=field):
                fixture = load_fixture()
                fixture[field] = ForgedExchange("UNTRUSTED")
                with self.assertRaisesRegex(DxFeedAdapterError, "must be a string"):
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

    def test_direct_explicit_failure_status_never_promotes_quote(self) -> None:
        """Q03: a direct event cannot bypass an explicit provider failure."""
        for status in ("ERROR", "STALE", None, True, 200):
            with self.subTest(status=status):
                fixture = load_fixture()
                fixture["status"] = status
                with self.assertRaisesRegex(DxFeedAdapterError, "status must be OK"):
                    adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

    def test_wrapped_non_ok_status_never_promotes_quote(self) -> None:
        """Q03: an error response containing a plausible quote fails closed."""
        for status in ("ERROR", "STALE", None, True, 200):
            with self.subTest(status=status):
                message = {"status": status, "Quote": {"EUR/USD": load_fixture()}}
                with self.assertRaisesRegex(DxFeedAdapterError, "status must be OK"):
                    adapter().parse_quote(message, received_at_ns=RECEIVED_AT_NS)

    def test_wrapped_success_does_not_override_nested_failure(self) -> None:
        """Q03: nested provider failure must not be promoted by outer OK."""
        for status in ("ERROR", "STALE", None, True, 200):
            with self.subTest(status=status):
                quote = load_fixture()
                quote["status"] = status
                message = {"status": "OK", "Quote": {"EUR/USD": quote}}
                with self.assertRaisesRegex(DxFeedAdapterError, "nested Quote status"):
                    adapter().parse_quote(message, received_at_ns=RECEIVED_AT_NS)

    def test_wrapped_status_cannot_be_forged_by_custom_equality(self) -> None:
        """Q03: an object comparing equal to OK is not a wire status."""
        class ForgedStatus:
            def __eq__(self, other: object) -> bool:
                return other == "OK"

        message = {"status": ForgedStatus(), "Quote": {"EUR/USD": load_fixture()}}
        with self.assertRaisesRegex(DxFeedAdapterError, "status must be OK"):
            adapter().parse_quote(message, received_at_ns=RECEIVED_AT_NS)

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

    def test_time_nano_part_rejects_out_of_range_fraction(self) -> None:
        """Q03: never silently carry a malformed sub-millisecond fraction."""
        for value in (1_000_000, 1_000_001):
            with self.subTest(value=value):
                fixture = load_fixture()
                fixture["timeNanoPart"] = value
                with self.assertRaisesRegex(DxFeedAdapterError, "timeNanoPart"):
                    adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)

        fixture = load_fixture()
        fixture["timeNanoPart"] = 999_999
        event = adapter().parse_quote(fixture, received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.time_nano_part, 999_999)

    def test_parsing_is_deterministic(self) -> None:
        fixture = load_fixture()
        first = adapter().parse_quote(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        second = adapter().parse_quote(copy.deepcopy(fixture), received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
