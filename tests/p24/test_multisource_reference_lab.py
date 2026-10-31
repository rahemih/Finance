from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from packages.production.multisource_reference_lab import (
    EXPECTED_POLICY, MultiSourceReferenceLab, ROLES, ReferenceLabError,
    SyntheticQuote, digest, render_html,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/p24-multisource-reference-policy.json"
P07 = ROOT / "config/data-quality/cross-provider-policy.json"
CLOCK = 1_000_000


def fixture() -> tuple[SyntheticQuote, ...]:
    mids = {
        "DUKASCOPY_SIM": "1.10000",
        "FX_INDEPENDENT_SIM": "1.10005",
        "FIBO_SIM": "1.10015",
        "BINANCE_ARCHIVE_SIM": "70000",
        "CRYPTO_INDEPENDENT_SIM": "70002",
        "USDTIRT_SIM": "60000",
        "TABDEAL_SPOT_SIM": "4200150000",
    }
    widths = {
        "DUKASCOPY_SIM": "0.0001",
        "FX_INDEPENDENT_SIM": "0.0001",
        "FIBO_SIM": "0.0001",
        "BINANCE_ARCHIVE_SIM": "1",
        "CRYPTO_INDEPENDENT_SIM": "1",
        "USDTIRT_SIM": "1",
        "TABDEAL_SPOT_SIM": "1000",
    }
    output = []
    for provider, (market, pair, root, role) in ROLES.items():
        mid, spread = Decimal(mids[provider]), Decimal(widths[provider])
        output.append(SyntheticQuote(
            provider=provider, market=market, pair=pair, root=root, role=role,
            bid=mid - spread / 2, ask=mid + spread / 2,
            event_time_ms=CLOCK - 100, observed_time_ms=CLOCK - 60,
            lineage_sha256=digest({"SYNTHETIC_SOURCE": provider}),
        ))
    return tuple(output)


def mutate(provider: str, **changes: object) -> tuple[SyntheticQuote, ...]:
    return tuple(replace(q, **changes) if q.provider == provider else q for q in fixture())


class MultiSourceReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lab = MultiSourceReferenceLab(POLICY, P07)

    def denied(self, quotes: tuple[SyntheticQuote, ...]) -> None:
        with self.assertRaises(ReferenceLabError):
            self.lab.evaluate(quotes, CLOCK)

    def test_01_valid_fx_crypto_pair_comparison(self) -> None:
        report = self.lab.evaluate(fixture(), CLOCK)
        self.assertEqual(report["outcome"], "SYNTHETIC_CONSISTENCY_ONLY")
        self.assertEqual(report["source_count"], 7)

    def test_02_p07_reuse_evidence(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        self.assertEqual(out["p07_reference_outcomes"], {"forex": "VALID", "crypto": "VALID"})
        self.assertEqual(len(out["p07_reference_ids"]["forex"]), 64)

    def test_03_pair_conversion_btcusdt_to_btcirt(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        btc = out["comparison"][1]
        self.assertEqual(btc["pair"], "BTCIRT")
        self.assertEqual(Decimal(btc["reference_mid"]), Decimal("4200060000.0"))

    def test_04_fx_broker_is_separate_from_reference(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        self.assertEqual(out["comparison"][0]["pair"], "EURUSD")
        self.assertEqual(out["comparison"][0]["destination_mid"], "1.10015")

    def test_05_no_execution_authority(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        self.assertFalse(out["order_authority"])
        self.assertFalse(out["executability_certified"])
        self.assertEqual(out["actual_broker_fills"], 0)

    def test_06_binance_never_authenticated(self) -> None:
        self.assertFalse(EXPECTED_POLICY["binance_authenticated_access"])
        self.assertEqual(self.lab.evaluate(fixture(), CLOCK)["binance_source_role"], "SYNTHETIC_ARCHIVE_LABEL_NOT_API")

    def test_07_tv_visual_only(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        self.assertEqual(out["tradingview_role"], "HUMAN_VISUAL_ONLY")

    def test_08_identical_replay(self) -> None:
        self.assertEqual(self.lab.evaluate(fixture(), CLOCK), self.lab.evaluate(fixture(), CLOCK))

    def test_09_different_quote_changes_evidence(self) -> None:
        a = self.lab.evaluate(fixture(), CLOCK)
        b = self.lab.evaluate(mutate("FIBO_SIM", bid=Decimal("1.10014")), CLOCK)
        self.assertNotEqual(a["evidence_id"], b["evidence_id"])

    def test_10_reject_policy_network_flip(self) -> None:
        x = dict(EXPECTED_POLICY)
        x["network_mode"] = "ENABLED"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "policy.json"
            path.write_text(json.dumps(x), encoding="utf-8")
            with self.assertRaises(ReferenceLabError):
                MultiSourceReferenceLab(path, P07)

    def test_11_reject_policy_true_equals_integer(self) -> None:
        x = dict(EXPECTED_POLICY)
        x["external_order_authority"] = 0
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "policy.json"
            path.write_text(json.dumps(x), encoding="utf-8")
            with self.assertRaises(ReferenceLabError):
                MultiSourceReferenceLab(path, P07)

    def test_12_reject_missing_policy(self) -> None:
        with self.assertRaises(ReferenceLabError):
            MultiSourceReferenceLab(Path("/not-a-real-WQ-policy.json"), P07)

    def test_13_reject_inmemory_policy_id_tamper(self) -> None:
        self.lab.policy_id = "f" * 64
        with self.assertRaises(ReferenceLabError):
            self.lab.evaluate(fixture(), CLOCK)

    def test_14_reject_missing_quote(self) -> None:
        self.denied(fixture()[:-1])

    def test_15_reject_extra_quote(self) -> None:
        self.denied(fixture() + (fixture()[0],))

    def test_16_reject_duplicate_source(self) -> None:
        self.denied(fixture()[:-1] + (fixture()[0],))

    def test_17_reject_wrong_market(self) -> None:
        self.denied(mutate("DUKASCOPY_SIM", market="CRYPTO"))

    def test_18_reject_wrong_pair(self) -> None:
        self.denied(mutate("BINANCE_ARCHIVE_SIM", pair="BTCIRT"))

    def test_19_reject_false_lineage_root(self) -> None:
        self.denied(mutate("FX_INDEPENDENT_SIM", root="DUKASCOPY"))

    def test_20_reject_forged_role(self) -> None:
        self.denied(mutate("FIBO_SIM", role="EXECUTABLE"))

    def test_21_reject_unknown_provider(self) -> None:
        self.denied(mutate("FIBO_SIM", provider="UNKNOWN"))

    def test_22_reject_actual_source_mode(self) -> None:
        self.denied(mutate("DUKASCOPY_SIM", source_mode="LIVE_API"))

    def test_23_reject_malformed_provenance(self) -> None:
        self.denied(mutate("BINANCE_ARCHIVE_SIM", lineage_sha256="1234"))

    def test_24_reject_zero_bid(self) -> None:
        self.denied(mutate("FIBO_SIM", bid=Decimal(0)))

    def test_25_reject_crossed_quote(self) -> None:
        self.denied(mutate("FIBO_SIM", bid=Decimal("1.2")))

    def test_26_reject_nonfinite_decimal(self) -> None:
        self.denied(mutate("FIBO_SIM", bid=Decimal("NaN")))

    def test_27_reject_integer_substitute_decimal(self) -> None:
        self.denied(mutate("FIBO_SIM", bid=1))

    def test_28_reject_bool_time(self) -> None:
        self.denied(mutate("FIBO_SIM", event_time_ms=True))

    def test_29_future_market_timestamp_quarantined(self) -> None:
        out = self.lab.evaluate(mutate("FIBO_SIM", event_time_ms=CLOCK + 10, observed_time_ms=CLOCK + 10), CLOCK)
        self.assertIn("STALE_OR_FUTURE_MARKET_REFERENCE", out["issues"])

    def test_30_reject_noncanonical_sample(self) -> None:
        self.denied(mutate("FIBO_SIM", sample_id="other-sample"))

    def test_31_reject_correlated_reference_lineage(self) -> None:
        pair = fixture()
        shared = pair[0].lineage_sha256
        report = self.lab.evaluate(mutate("FX_INDEPENDENT_SIM", lineage_sha256=shared), CLOCK)
        self.assertEqual(report["outcome"], "QUARANTINED_NO_SIGNAL")
        self.assertIn("CORRELATED_OR_REUSED_REFERENCE_LINEAGE", report["issues"])

    def test_32_reject_stale_reference(self) -> None:
        quote = mutate("DUKASCOPY_SIM", event_time_ms=CLOCK - 5000, observed_time_ms=CLOCK - 50)
        out = self.lab.evaluate(quote, CLOCK)
        self.assertIn("STALE_OR_FUTURE_MARKET_REFERENCE", out["issues"])

    def test_33_reject_time_misalignment(self) -> None:
        quote = mutate("FIBO_SIM", event_time_ms=CLOCK - 800, observed_time_ms=CLOCK - 20)
        out = self.lab.evaluate(quote, CLOCK)
        self.assertIn("SOURCE_TIME_MISALIGNMENT", out["issues"])

    def test_34_reject_lagging_ingest(self) -> None:
        quote = mutate("FIBO_SIM", event_time_ms=CLOCK - 5000, observed_time_ms=CLOCK - 1)
        out = self.lab.evaluate(quote, CLOCK)
        self.assertIn("COLLECTION_LATENCY_VIOLATION", out["issues"])

    def test_35_fx_divergence_fails_closed(self) -> None:
        quote = mutate("FX_INDEPENDENT_SIM", bid=Decimal("1.1999"), ask=Decimal("1.2001"))
        out = self.lab.evaluate(quote, CLOCK)
        self.assertIn("P07_INDEPENDENT_REFERENCE_DIVERGENCE", out["issues"])

    def test_36_crypto_divergence_fails_closed(self) -> None:
        quote = mutate("CRYPTO_INDEPENDENT_SIM", bid=Decimal("79999"), ask=Decimal("80001"))
        out = self.lab.evaluate(quote, CLOCK)
        self.assertIn("P07_INDEPENDENT_REFERENCE_DIVERGENCE", out["issues"])

    def test_37_venue_fx_drift_fails_closed(self) -> None:
        out = self.lab.evaluate(mutate("FIBO_SIM", bid=Decimal("1.1999"), ask=Decimal("1.2001")), CLOCK)
        self.assertIn("DESTINATION_VENUE_REFERENCE_DRIFT", out["issues"])

    def test_38_venue_crypto_drift_fails_closed(self) -> None:
        out = self.lab.evaluate(mutate("TABDEAL_SPOT_SIM", bid=Decimal("5000000000"), ask=Decimal("5000001000")), CLOCK)
        self.assertIn("DESTINATION_VENUE_REFERENCE_DRIFT", out["issues"])

    def test_39_conversion_rate_changes_destination_reference(self) -> None:
        out1 = self.lab.evaluate(fixture(), CLOCK)
        out2 = self.lab.evaluate(mutate("USDTIRT_SIM", bid=Decimal("70000"), ask=Decimal("70001")), CLOCK)
        self.assertNotEqual(out1["comparison"][1]["reference_mid"], out2["comparison"][1]["reference_mid"])

    def test_40_risk_veto_cannot_be_bypassed(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK, risk_veto=True)
        self.assertEqual(out["outcome"], "QUARANTINED_NO_SIGNAL")
        self.assertIn("INDEPENDENT_A5_RISK_VETO", out["issues"])

    def test_41_bool_risk_veto_not_accepted(self) -> None:
        with self.assertRaises(ReferenceLabError):
            self.lab.evaluate(fixture(), CLOCK, risk_veto=1)

    def test_42_bool_clock_not_accepted(self) -> None:
        with self.assertRaises(ReferenceLabError):
            self.lab.evaluate(fixture(), True)

    def test_43_live_and_g13_not_promoted(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        self.assertEqual(out["pre_first_live_satisfied"], 0)
        self.assertEqual(out["live_trading"], "DISABLED")
        self.assertEqual(out["g13"], "NOT_STARTED")

    def test_44_html_synthetic_disclaimer(self) -> None:
        html = render_html(self.lab.evaluate(fixture(), CLOCK))
        self.assertIn("فقط داده ساختگی", html)
        self.assertIn("TradingView", html)

    def test_45_html_escapes_external_row(self) -> None:
        out = self.lab.evaluate(fixture(), CLOCK)
        out["comparison"][0]["note"] = "<script>alert(1)</script>"
        out["comparison"][0]["pair"] = "<script>alert(1)</script>"
        html = render_html(out)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_46_tuple_required(self) -> None:
        with self.assertRaises(ReferenceLabError):
            self.lab.evaluate(list(fixture()), CLOCK)

    def test_47_quote_type_required(self) -> None:
        a = list(fixture())
        a[0] = {"provider": "DUKASCOPY_SIM"}
        self.denied(tuple(a))

    def test_48_quote_prices_not_execution_certified(self) -> None:
        report = self.lab.evaluate(fixture(), CLOCK)
        self.assertFalse(report["independent_source_rights_verified"])
        self.assertEqual(report["real_source_quotes_observed"], 0)


if __name__ == "__main__":
    unittest.main()
