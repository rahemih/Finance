from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from adapters.market_data.databento import (
    DatabentoAdapterError,
    DatabentoContextSubscription,
    DatabentoGoldContextAdapter,
    UNDEF_PRICE,
    UNDEF_TIMESTAMP,
)
from packages.contracts.market_data import (
    ContextMarketRole,
    ContextQuantitySemantics,
    MarketEventKind,
    ProviderContextEnvelope,
)


FIXTURES = Path(__file__).parent / "fixtures"
RECEIVED_AT_NS = 1_780_820_500_000_123_456


def fixture() -> dict[str, object]:
    value = json.loads((FIXTURES / "databento_gc_mbp1.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("fixture must be object")
    return value


def adapter(credential_ref: str | None = None) -> DatabentoGoldContextAdapter:
    return DatabentoGoldContextAdapter(DatabentoContextSubscription(credential_ref=credential_ref))


class DatabentoContextAdapterTests(unittest.TestCase):
    def test_gc_mbp1_mapping_preserves_context_provenance(self) -> None:
        event = adapter().parse_mbp1(fixture(), mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        self.assertIsInstance(event, ProviderContextEnvelope)
        self.assertEqual(event.kind, MarketEventKind.CONTEXT_TOP_OF_BOOK)
        self.assertEqual(event.instrument.provider, "databento")
        self.assertEqual(event.instrument.exchange, "COMEX")
        self.assertEqual(event.instrument.code, "GCZ6")
        self.assertEqual(event.sequence_id, "12345")
        self.assertEqual(event.publisher_id, 1)
        self.assertEqual(event.provider_instrument_id, 424242)
        self.assertEqual(event.payload.role, ContextMarketRole.CONTEXT_ONLY)
        self.assertEqual(
            event.payload.quantity_semantics,
            ContextQuantitySemantics.CENTRALIZED_FUTURES_VENUE_QUANTITY,
        )
        self.assertIn(("subscription_symbol", "GC.v.0"), event.metadata)
        self.assertIn(("mapped_symbol", "GCZ6"), event.metadata)
        self.assertIn(("trading_authority", "NONE"), event.metadata)

    def test_wrong_rtype_is_rejected(self) -> None:
        data = fixture()
        data["rtype"] = 10
        with self.assertRaises(DatabentoAdapterError):
            adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)

    def test_nonzero_depth_is_rejected_for_mbp1_baseline(self) -> None:
        data = fixture()
        data["depth"] = 1
        with self.assertRaises(DatabentoAdapterError):
            adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)

    def test_nanosecond_timestamps_are_preserved_exactly(self) -> None:
        event = adapter().parse_mbp1(fixture(), mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        assert event.provider_event_time is not None
        self.assertEqual(event.provider_event_time.epoch_ns, 1_780_820_499_999_900_000)
        self.assertEqual(event.provider_receive_time.epoch_ns, 1_780_820_500_000_000_000)
        self.assertEqual(event.received_at_ns, RECEIVED_AT_NS)

    def test_fixed_point_prices_decode_exactly(self) -> None:
        event = adapter().parse_mbp1(fixture(), mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.event_price, Decimal("2400.10"))
        self.assertEqual(event.payload.bid_price, Decimal("2400.00"))
        self.assertEqual(event.payload.ask_price, Decimal("2400.20"))

    def test_undef_price_maps_to_none(self) -> None:
        data = fixture()
        data["price"] = UNDEF_PRICE
        levels = data["levels"]
        assert isinstance(levels, list)
        assert isinstance(levels[0], dict)
        levels[0]["bid_px"] = UNDEF_PRICE
        event = adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        self.assertIsNone(event.payload.event_price)
        self.assertIsNone(event.payload.bid_price)

    def test_undef_event_timestamp_maps_to_none(self) -> None:
        data = fixture()
        data["ts_event"] = UNDEF_TIMESTAMP
        event = adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        self.assertIsNone(event.provider_event_time)

    def test_undef_receive_timestamp_fails_closed(self) -> None:
        data = fixture()
        data["ts_recv"] = UNDEF_TIMESTAMP
        with self.assertRaises(DatabentoAdapterError):
            adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)

    def test_bbo_sizes_counts_and_event_metadata_are_preserved(self) -> None:
        event = adapter().parse_mbp1(fixture(), mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(event.payload.bid_size, 7)
        self.assertEqual(event.payload.ask_size, 6)
        self.assertEqual(event.payload.bid_count, 4)
        self.assertEqual(event.payload.ask_count, 3)
        self.assertEqual(event.payload.action, "T")
        self.assertEqual(event.payload.side, "B")
        self.assertEqual(event.payload.ts_in_delta_ns, 50000)
        self.assertEqual(event.payload.flags, 128)

    def test_negative_size_or_count_is_rejected(self) -> None:
        for field in ("bid_sz", "ask_sz", "bid_ct", "ask_ct"):
            with self.subTest(field=field):
                data = fixture()
                levels = data["levels"]
                assert isinstance(levels, list)
                assert isinstance(levels[0], dict)
                levels[0][field] = -1
                with self.assertRaises(DatabentoAdapterError):
                    adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)

    def test_inverted_defined_book_is_rejected(self) -> None:
        data = fixture()
        levels = data["levels"]
        assert isinstance(levels, list)
        assert isinstance(levels[0], dict)
        levels[0]["bid_px"] = 2400300000000
        levels[0]["ask_px"] = 2400200000000
        with self.assertRaises(DatabentoAdapterError):
            adapter().parse_mbp1(data, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)

    def test_mapped_contract_symbol_is_required(self) -> None:
        with self.assertRaises(DatabentoAdapterError):
            adapter().parse_mbp1(fixture(), mapped_symbol=" ", received_at_ns=RECEIVED_AT_NS)

    def test_raw_or_empty_credential_is_rejected(self) -> None:
        for value in ("raw-key", "secret://", " "):
            with self.subTest(value=value):
                with self.assertRaises(DatabentoAdapterError):
                    adapter(value)

    def test_offline_subscription_descriptor_does_not_select_endpoint(self) -> None:
        spec = adapter("secret://market-data/databento/api-key").subscription_spec()
        self.assertEqual(spec.dataset, "GLBX.MDP3")
        self.assertEqual(spec.schema, "mbp-1")
        self.assertEqual(spec.symbol, "GC.v.0")
        self.assertEqual(spec.stype_in, "continuous")
        self.assertEqual(spec.credential_ref, "secret://market-data/databento/api-key")
        self.assertIsNone(spec.endpoint_ref)
        self.assertEqual(spec.intended_use, "OFFLINE_CONTRACT_ONLY")
        self.assertEqual(spec.roll_lifecycle, "EXPLICIT_MAPPING_AND_RESUBSCRIBE_REQUIRED_LATER")

    def test_invalid_receive_timestamp_is_rejected(self) -> None:
        for value in (-1, True, "123"):
            with self.subTest(value=value):
                with self.assertRaises(DatabentoAdapterError):
                    adapter().parse_mbp1(fixture(), mapped_symbol="GCZ6", received_at_ns=value)  # type: ignore[arg-type]

    def test_parsing_is_deterministic(self) -> None:
        first = adapter().parse_mbp1(copy.deepcopy(fixture()), mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        second = adapter().parse_mbp1(copy.deepcopy(fixture()), mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
