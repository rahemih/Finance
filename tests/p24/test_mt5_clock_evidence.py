"""P24 native-clock forensic probe: pure synthetic unit and static no-order tests."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.production.mt5_clock_evidence import (
    ClockEvidenceError, parse_probe_line, review_probe_lines,
)

FIXTURE_GMT = 1793600000
ROOT = Path(__file__).resolve().parents[2]
MQL = ROOT / "tools" / "mt5" / "P24ReadOnlyClockProbe.mq5"


def line(
    sample: int = 1, *,
    gmt: int = FIXTURE_GMT, delta: int = 7202,
    symbol: str = "EURUSD", millisecond: int = 573,
) -> str:
    return (
        "P24_CLOCK_V1"
        f"|sample={sample}|symbol={symbol}"
        f"|tick_s={gmt + delta}|tick_ms={(gmt + delta) * 1000 + millisecond}"
        f"|gmt_s={gmt}|local_s={gmt + 12600}|gmt_offset_s=-12600"
        f"|server_last_s={gmt + delta}|server_est_s={gmt + delta}|status=OK"
    )


class ClockProbeTests(unittest.TestCase):
    def test_raw_plus_7202s_is_never_normalized(self) -> None:
        r = review_probe_lines([line()], tier="FOREX")
        self.assertEqual(r["samples"][0]["tick_minus_host_gmt_ms"], 7202573)
        self.assertEqual(r["samples"][0]["estimated_server_minus_host_gmt_s"], 7202)
        self.assertFalse(r["source_time_correction_applied"])
        self.assertEqual(r["assessment"], "UNVERIFIED_FAIL_CLOSED")
        self.assertFalse(r["data_freshness_certified"])

    def test_zero_delta_is_still_unverified(self) -> None:
        r = review_probe_lines([line(delta=0)], tier="FOREX")
        self.assertEqual(r["samples"][0]["tick_minus_host_gmt_ms"], 573)
        self.assertEqual(r["clock_provenance"], "BROKER_NOT_ATTESTED")
        self.assertFalse(r["live_execution_authorized"])

    def test_two_market_scopes_do_not_mix(self) -> None:
        fx = review_probe_lines([line()], tier="FOREX")
        cr = review_probe_lines([line(symbol="BTCUSD")], tier="CRYPTO")
        self.assertNotEqual(fx["evidence_sha256"], cr["evidence_sha256"])
        self.assertEqual(cr["symbol"], "BTCUSD")

    def test_three_increasing_samples(self) -> None:
        data = [line(n, gmt=FIXTURE_GMT + n) for n in range(1, 4)]
        out = review_probe_lines(data, tier="CRYPTO")
        self.assertEqual(len(out["samples"]), 3)
        self.assertTrue(all(x["tick_seconds_milliseconds_consistent"] for x in out["samples"]))

    def test_same_sample_evidence_is_deterministic(self) -> None:
        self.assertEqual(review_probe_lines([line()], tier="FOREX"),
                         review_probe_lines([line()], tier="FOREX"))
        self.assertEqual(len(review_probe_lines([line()], tier="FOREX")["evidence_sha256"]), 64)

    def test_wrong_or_missing_prefix_rejected(self) -> None:
        for bad in ("", "MT5_CLOCK_V1|" + line().split("|", 1)[1], line()[2:]):
            with self.subTest(bad=bad), self.assertRaises(ClockEvidenceError):
                parse_probe_line(bad)

    def test_account_number_injected_as_extra_field_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            parse_probe_line(line() + "|account=123456")

    def test_server_name_injected_as_extra_field_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            parse_probe_line(line() + "|server=PRIVATE")

    def test_wrong_order_rejected(self) -> None:
        parts = line().split("|")
        parts[1], parts[2] = parts[2], parts[1]
        with self.assertRaises(ClockEvidenceError):
            parse_probe_line("|".join(parts))

    def test_repeated_key_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            parse_probe_line(line().replace("|status=OK", "|sample=1"))

    def test_unsafe_symbol_rejected(self) -> None:
        for symbol in ("EUR/USD", "a b", "a"*21, "EUR;USD"):
            with self.subTest(symbol=symbol), self.assertRaises(ClockEvidenceError):
                parse_probe_line(line(symbol=symbol))

    def test_noncanonical_integers_rejected(self) -> None:
        for n in ("+1", "01", "True", "1.0"):
            with self.subTest(value=n), self.assertRaises(ClockEvidenceError):
                parse_probe_line(line().replace("sample=1", f"sample={n}"))

    def test_timestamps_outside_bounds_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            parse_probe_line(line().replace(f"gmt_s={FIXTURE_GMT}", "gmt_s=123"))

    def test_milliseconds_inconsistent_never_claim_consistency(self) -> None:
        raw = line().replace(f"tick_s={FIXTURE_GMT + 7202}", f"tick_s={FIXTURE_GMT + 7203}")
        r = review_probe_lines([raw], tier="FOREX")
        self.assertFalse(r["samples"][0]["tick_seconds_milliseconds_consistent"])
        self.assertEqual(r["samples"][0]["sanity"], "INCONSISTENT")
        self.assertFalse(r["data_freshness_certified"])

    def test_local_gmt_mismatch_never_claim_consistency(self) -> None:
        raw = line().replace("gmt_offset_s=-12600", "gmt_offset_s=-3600")
        r = review_probe_lines([raw], tier="FOREX")
        self.assertFalse(r["samples"][0]["host_gmt_local_consistent"])
        self.assertEqual(r["assessment"], "UNVERIFIED_FAIL_CLOSED")

    def test_broker_tick_regression_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            review_probe_lines([line(1, gmt=FIXTURE_GMT + 2),
                                line(2, gmt=FIXTURE_GMT)], tier="FOREX")

    def test_duplicate_or_missing_sample_rejected(self) -> None:
        for sequence in ([line(1), line(1)], [line(2)], [line(1), line(3)]):
            with self.subTest(count=len(sequence)), self.assertRaises(ClockEvidenceError):
                review_probe_lines(sequence, tier="FOREX")

    def test_mixed_symbols_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            review_probe_lines([line(1), line(2, symbol="BTCUSD")], tier="FOREX")

    def test_empty_and_four_samples_rejected(self) -> None:
        for rows in ([], [line(n) for n in range(1, 5)]):
            with self.assertRaises(ClockEvidenceError):
                review_probe_lines(rows, tier="FOREX")

    def test_unsupported_tier_rejected(self) -> None:
        with self.assertRaises(ClockEvidenceError):
            review_probe_lines([line()], tier="LIVE")

    def test_no_unverified_mql_script_execution_claims(self) -> None:
        r = review_probe_lines([line()], tier="FOREX")
        self.assertEqual(r["read_only_mt5_compilation_and_execution_in_ci"], "NOT_RUN")
        self.assertEqual(r["broker_sanctioned_order_tests"], "NOT_RUN")
        self.assertEqual(r["operational_reconnect_drill"], "NOT_RUN")
        self.assertEqual(r["pre_first_live_satisfied"], 0)
        self.assertEqual(r["live_trading"], "DISABLED")
        self.assertEqual(r["auto_trading"], "DISABLED")

    def test_native_mql5_probe_has_zero_account_trade_or_file_calls(self) -> None:
        source = MQL.read_text(encoding="utf-8")
        self.assertIn("SymbolInfoTick(", source)
        for safe_call in ("TimeCurrent(", "TimeGMT(", "TimeLocal(",
                          "TimeTradeServer(", "TimeGMTOffset("):
            self.assertIn(safe_call, source)
        import re
        for banned in (
            r"\bOrderSend\s*\(", r"\bOrderCheck\s*\(", r"\bAccountInfo\w*\s*\(",
            r"\bTerminalInfo\w*\s*\(", r"\bFileOpen\s*\(",
            r"\bWebRequest\s*\(", r"\bSocket\w+\s*\(", r"\bSymbolSelect\s*\(",
            r"\bMqlTradeRequest\b", r"\bCTrade\b",
        ):
            with self.subTest(token=banned):
                self.assertIsNone(re.search(banned, source))
        self.assertNotIn("FILE_WRITE", source)
        self.assertNotIn("trade.Buy", source)
        self.assertNotIn("trade.Sell", source)


if __name__ == "__main__":
    unittest.main()
