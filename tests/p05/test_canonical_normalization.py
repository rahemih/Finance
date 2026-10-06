from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from adapters.market_data.databento import (
    DatabentoGoldContextAdapter,
    UNDEF_TIMESTAMP,
)
from adapters.market_data.dxfeed import (
    DxFeedForexQuoteAdapter,
    DxFeedForexSubscription,
)
from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.market_data import (
    CanonicalNormalizer,
    InstrumentRole,
    SymbolMaster,
    SymbolMasterError,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOL_MASTER = ROOT / "config/market-data/symbol-master.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def normalizer() -> CanonicalNormalizer:
    return CanonicalNormalizer(SymbolMaster.from_path(SYMBOL_MASTER))


def kaiko_trade(*, received_at_ns: int = 1_759_651_200_223_656_789):
    adapter = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    )
    return adapter.parse_trade(load("kaiko_trade.json"), received_at_ns=received_at_ns)


def dx_quote(*, received_at_ns: int = 1_780_820_402_000_000_000):
    adapter = DxFeedForexQuoteAdapter(
        DxFeedForexSubscription(
            symbol="EUR/USD",
            canonical_id="FX:EUR/USD:SPOT_OTC",
        )
    )
    return adapter.parse_quote(
        load("dxfeed_eurusd_quote.json"),
        received_at_ns=received_at_ns,
    )


def gold_context(
    *,
    received_at_ns: int = 1_780_820_500_000_100_000,
    undefined_event: bool = False,
):
    payload = load("databento_gc_mbp1.json")
    if undefined_event:
        payload["ts_event"] = UNDEF_TIMESTAMP
    return DatabentoGoldContextAdapter().parse_mbp1(
        payload,
        mapped_symbol="GCZ6",
        received_at_ns=received_at_ns,
    )


class SymbolMasterTests(unittest.TestCase):
    def test_kaiko_exact_alias_resolves_btc(self):
        event = normalizer().normalize(kaiko_trade())
        self.assertEqual(event.canonical_id, "CRYPTO:BTC/USD:SPOT")
        self.assertEqual(event.provider_symbol, "btc-usd")
        self.assertEqual(event.instrument_role, InstrumentRole.TRADABLE_RESEARCH_CANDIDATE)

    def test_dxfeed_metadata_and_exact_alias_resolve_fx(self):
        event = normalizer().normalize(dx_quote())
        self.assertEqual(event.canonical_id, "FX:EUR/USD:SPOT_OTC")
        self.assertEqual(event.provider, "dxfeed")

    def test_dxfeed_claimed_canonical_mismatch_is_rejected(self):
        envelope = dx_quote()
        altered = replace(
            envelope,
            metadata=tuple(
                ("canonical_id", "CRYPTO:BTC/USD:SPOT") if key == "canonical_id" else (key, value)
                for key, value in envelope.metadata
            ),
        )
        with self.assertRaises(SymbolMasterError):
            normalizer().normalize(altered)

    def test_unknown_kaiko_alias_is_rejected(self):
        envelope = kaiko_trade()
        altered = replace(
            envelope,
            instrument=replace(envelope.instrument, code="eth-usd"),
        )
        with self.assertRaises(SymbolMasterError):
            normalizer().normalize(altered)

    def test_unknown_canonical_id_is_rejected(self):
        envelope = dx_quote()
        altered = replace(
            envelope,
            metadata=tuple(
                ("canonical_id", "FX:UNKNOWN") if key == "canonical_id" else (key, value)
                for key, value in envelope.metadata
            ),
        )
        with self.assertRaises(SymbolMasterError):
            normalizer().normalize(altered)

    def test_databento_dynamic_mapped_contract_resolves_gold(self):
        event = normalizer().normalize(gold_context())
        self.assertEqual(event.canonical_id, "COMMODITY:GOLD:GC:FUTURES:COMEX")
        self.assertEqual(event.provider_symbol, "GCZ6")
        self.assertEqual(event.instrument_role, InstrumentRole.CONTEXT_ONLY)
        provenance = dict(event.provenance)
        self.assertEqual(provenance["subscription_symbol"], "GC.v.0")
        self.assertEqual(provenance["mapped_symbol"], "GCZ6")

    def test_databento_mapped_metadata_mismatch_is_rejected(self):
        envelope = gold_context()
        altered = replace(
            envelope,
            metadata=tuple(
                ("mapped_symbol", "GCG7") if key == "mapped_symbol" else (key, value)
                for key, value in envelope.metadata
            ),
        )
        with self.assertRaises(SymbolMasterError):
            normalizer().normalize(altered)

    def test_duplicate_alias_config_is_rejected(self):
        config = {
            "schema_version": "1.0",
            "state": "TEST",
            "instruments": [
                {
                    "canonical_id": "A",
                    "asset_class": "CRYPTO",
                    "role": "TRADABLE_RESEARCH_CANDIDATE",
                    "aliases": [
                        {
                            "mode": "EXACT",
                            "provider": "kaiko",
                            "exchange": "cbse",
                            "instrument_class": "spot",
                            "code": "btc-usd",
                        }
                    ],
                },
                {
                    "canonical_id": "B",
                    "asset_class": "CRYPTO",
                    "role": "TRADABLE_RESEARCH_CANDIDATE",
                    "aliases": [
                        {
                            "mode": "EXACT",
                            "provider": "kaiko",
                            "exchange": "cbse",
                            "instrument_class": "spot",
                            "code": "btc-usd",
                        }
                    ],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "symbols.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(SymbolMasterError):
                SymbolMaster.from_path(path)


class ClockModelTests(unittest.TestCase):
    def test_kaiko_clock_preserves_event_exchange_collection_and_local(self):
        envelope = kaiko_trade()
        event = normalizer().normalize(envelope)
        self.assertEqual(event.clock.provider_event_time, envelope.ts_event)
        self.assertEqual(event.clock.exchange_time, envelope.ts_exchange)
        self.assertEqual(event.clock.collection_time, envelope.ts_collection)
        self.assertIsNone(event.clock.provider_receive_time)
        self.assertEqual(event.clock.local_receive_time_ns, envelope.received_at_ns)
        self.assertEqual(
            event.clock.event_to_local_delta_ns,
            envelope.received_at_ns - envelope.ts_event.epoch_ns,
        )

    def test_dxfeed_missing_event_time_stays_none(self):
        envelope = dx_quote()
        event = normalizer().normalize(envelope)
        self.assertIsNone(envelope.provider_event_time)
        self.assertIsNone(event.clock.provider_event_time)
        self.assertIsNone(event.clock.event_to_local_delta_ns)
        self.assertIsNone(event.clock.provider_receive_time)
        times = dict(event.clock.auxiliary_source_times)
        self.assertEqual(times["bid_time"], envelope.payload.bid_time)
        self.assertEqual(times["ask_time"], envelope.payload.ask_time)
        self.assertNotEqual(times["bid_time"], times["ask_time"])

    def test_databento_undefined_event_does_not_fall_back_to_receive(self):
        envelope = gold_context(undefined_event=True)
        event = normalizer().normalize(envelope)
        self.assertIsNone(event.clock.provider_event_time)
        self.assertIsNone(event.clock.event_to_local_delta_ns)
        self.assertEqual(
            event.clock.provider_receive_time,
            envelope.provider_receive_time,
        )
        self.assertEqual(
            event.clock.provider_receive_to_local_delta_ns,
            envelope.received_at_ns - envelope.provider_receive_time.epoch_ns,
        )

    def test_signed_event_delta_can_be_negative_without_correction(self):
        envelope = kaiko_trade()
        earlier = replace(
            envelope,
            received_at_ns=envelope.ts_event.epoch_ns - 10,
        )
        event = normalizer().normalize(earlier)
        self.assertEqual(event.clock.event_to_local_delta_ns, -10)

    def test_repeated_normalization_is_deterministic(self):
        envelope = gold_context()
        n = normalizer()
        self.assertEqual(n.normalize(envelope), n.normalize(envelope))

    def test_normalizer_preserves_original_payload(self):
        envelope = dx_quote()
        event = normalizer().normalize(envelope)
        self.assertEqual(event.payload, envelope.payload)


class GovernanceBoundaryTests(unittest.TestCase):
    def test_p04_historical_next_phase_label_is_not_live_p05_state(self):
        text = (ROOT / "scripts/ci/p04_exit.py").read_text(encoding="utf-8")
        self.assertNotIn('print("P05_STATE=', text)
        self.assertIn(
            'print("P04_CLOSURE_NEXT_PHASE_STATE=NOT_STARTED_PENDING_OWNER_AUTHORIZATION")',
            text,
        )


class BoundaryTests(unittest.TestCase):
    def test_provider_neutral_package_imports_no_adapter_modules(self):
        market_data_dir = ROOT / "packages/market_data"
        for path in market_data_dir.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("from adapters.", text)
            self.assertNotIn("import adapters.", text)


if __name__ == "__main__":
    unittest.main()
