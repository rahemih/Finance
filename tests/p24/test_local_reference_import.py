from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from packages.production.local_reference_import import (
    EXPECTED_POLICY, ImportContext, LocalImportError, LocalReferenceImport,
    render_html,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/p24-local-reference-import-policy.json"
NOW = 1_000_000


def fixture() -> bytes:
    return (
        b"event_time_ms,bid,ask\n"
        b"999000,1.1000,1.1002\n"
        b"999100,1.1001,1.1003\n"
        b"999300,1.1002,1.1004\n"
    )


class LocalReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = LocalReferenceImport(POLICY)
        self.context = ImportContext("FX_REFERENCE_CANDIDATE", "FOREX", "EURUSD", "REFERENCE_ONLY")

    def rejected(self, raw: object, *, context: object | None = None, now_ms: int = NOW) -> None:
        with self.assertRaises(LocalImportError):
            self.loader.parse(raw, context if context is not None else self.context, now_ms=now_ms)

    def test_01_baseline_exact_policy(self) -> None:
        self.assertEqual(len(self.loader.policy_id), 64)
        self.assertEqual(EXPECTED_POLICY["data_license_status"], "UNVERIFIED")

    def test_02_fixture_imports_and_normalizes_quotes(self) -> None:
        out = self.loader.parse(fixture(), self.context, now_ms=NOW)
        self.assertEqual(out["sample_count"], 3)
        self.assertEqual(out["samples"][0]["mid"], "1.1001")

    def test_03_never_certifies_source_license(self) -> None:
        out = self.loader.parse(fixture(), self.context, now_ms=NOW)
        self.assertFalse(out["source_licensed"])
        self.assertFalse(out["origin_independent_attested"])
        self.assertFalse(out["tradeable_price"])

    def test_04_no_signal_or_real_order(self) -> None:
        out = self.loader.parse(fixture(), self.context, now_ms=NOW)
        self.assertFalse(out["downstream_signal_allowed"])
        self.assertFalse(out["external_order_authority"])

    def test_05_owner_file_is_quarantined(self) -> None:
        ctx = replace(self.context, source_mode="OWNER_SUPPLIED_UNATTESTED")
        out = self.loader.parse(fixture(), ctx, now_ms=NOW)
        self.assertEqual(out["result"], "QUARANTINED_UNATTESTED_SOURCE")
        self.assertFalse(out["source_licensed"])

    def test_06_crypto_symbol_allowed_only_by_own_context(self) -> None:
        ctx = ImportContext("CRYPTO_REFERENCE_CANDIDATE", "CRYPTO", "BTCUSDT", "REFERENCE_ONLY")
        out = self.loader.parse(fixture(), ctx, now_ms=NOW)
        self.assertEqual(out["context"]["pair"], "BTCUSDT")

    def test_07_conversion_symbol_separate_from_btc(self) -> None:
        ctx = ImportContext("USDTIRT_REFERENCE_CANDIDATE", "CRYPTO", "USDTIRT", "CONVERSION_REFERENCE_ONLY")
        self.assertEqual(self.loader.parse(fixture(), ctx, now_ms=NOW)["context"]["pair"], "USDTIRT")

    def test_08_duplicate_replay_byte_identical(self) -> None:
        a = self.loader.parse(fixture(), self.context, now_ms=NOW)
        b = self.loader.parse(fixture(), self.context, now_ms=NOW)
        self.assertEqual(a, b)

    def test_09_modified_quote_changes_hash(self) -> None:
        a = self.loader.parse(fixture(), self.context, now_ms=NOW)
        b = self.loader.parse(fixture().replace(b"1.1000", b"1.10001"), self.context, now_ms=NOW)
        self.assertNotEqual(a["raw_sha256"], b["raw_sha256"])

    def test_10_network_policy_escalation_rejected(self) -> None:
        p = {**EXPECTED_POLICY, "network_mode": "ENABLED"}
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "bad.json"
            f.write_text(json.dumps(p), encoding="utf-8")
            with self.assertRaises(LocalImportError):
                LocalReferenceImport(f)

    def test_11_license_policy_escalation_rejected(self) -> None:
        p = {**EXPECTED_POLICY, "real_market_rights_verified": True}
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "bad.json"
            f.write_text(json.dumps(p), encoding="utf-8")
            with self.assertRaises(LocalImportError):
                LocalReferenceImport(f)

    def test_12_forged_runtime_policy_id_rejected(self) -> None:
        self.loader.policy_id = "f" * 64
        self.rejected(fixture())

    def test_13_missing_policy_fails_closed(self) -> None:
        with self.assertRaises(LocalImportError):
            LocalReferenceImport(Path("/missing-p24-local-import.json"))

    def test_14_unknown_provider_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, source_id="SOME_UNKNOWN_SOURCE"))

    def test_15_wrong_market_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, market="CRYPTO"))

    def test_16_wrong_quote_currency_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, pair="EURIRT"))

    def test_17_wrong_source_role_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, role="EXECUTION"))

    def test_18_fake_granted_rights_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, rights_status="GRANTED"))

    def test_19_live_environment_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, environment="LIVE"))

    def test_20_network_access_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, network_mode="ENABLED"))

    def test_21_secrets_mode_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, credential_mode="API_KEY"))

    def test_22_external_order_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, order_authority=True))

    def test_23_signal_authority_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, signal_authority=True))

    def test_24_integer_as_false_authority_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, order_authority=0))

    def test_25_bad_origin_mode_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, source_mode="BROKER_CERTIFIED"))

    def test_26_missing_csv_header_rejected(self) -> None:
        self.rejected(b"999000,1.1000,1.1002\n")

    def test_27_secret_extra_column_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask,api_key\n999000,1.1,1.2,abcd\n")

    def test_28_account_number_extra_column_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask,account_id\n999000,1.1,1.2,123\n")

    def test_29_csv_formula_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n999000,=1+1,1.2\n")

    def test_30_csv_bad_quote_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n999000,1.1,\"unterminated\n")

    def test_31_crossed_price_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n999000,2,1\n")

    def test_32_zero_and_negative_price_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n999000,0,1\n")
        self.rejected(b"event_time_ms,bid,ask\n999000,-1,1\n")

    def test_33_nonfinite_price_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n999000,NaN,1\n")
        self.rejected(b"event_time_ms,bid,ask\n999000,Infinity,1\n")

    def test_34_duplicate_timestamps_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n999000,1,2\n999000,1,2\n")

    def test_35_future_timestamp_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n1000001,1,2\n")

    def test_36_stale_reference_rejected(self) -> None:
        self.rejected(b"event_time_ms,bid,ask\n800000,1,2\n")

    def test_37_historical_mode_accepts_old_time_not_live(self) -> None:
        out = self.loader.parse(
            b"event_time_ms,bid,ask\n800000,1,2\n",
            replace(self.context, cadence="HISTORICAL_RESEARCH"), now_ms=NOW,
        )
        self.assertFalse(out["downstream_signal_allowed"])

    def test_38_empty_and_unknown_schema_rejected(self) -> None:
        self.rejected(b"")
        self.rejected(b"timestamp,price\n999000,1\n")

    def test_39_raw_data_must_be_bytes(self) -> None:
        self.rejected("event_time_ms,bid,ask\n999000,1,2\n")

    def test_40_context_must_be_typed(self) -> None:
        self.rejected(fixture(), context={"source_id": "FX_REFERENCE_CANDIDATE"})

    def test_41_bom_and_null_bytes_rejected(self) -> None:
        self.rejected(b"\xef\xbb\xbf" + fixture())
        self.rejected(fixture() + b"\x00")

    def test_42_csv_too_large_rejected(self) -> None:
        self.rejected(fixture() + b"x" * 100001)

    def test_43_utf8_invalid_rejected(self) -> None:
        self.rejected(fixture() + b"\xff")

    def test_44_html_escapes_untrusted_metadata(self) -> None:
        out = self.loader.parse(fixture(), self.context, now_ms=NOW)
        out["context"]["source_id"] = "<script>alert(1)</script>"
        html = render_html(out)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_45_g13_and_live_never_promoted(self) -> None:
        out = self.loader.parse(fixture(), self.context, now_ms=NOW)
        self.assertEqual(out["pre_first_live_satisfied"], 0)
        self.assertEqual(out["g13"], "NOT_STARTED")
        self.assertEqual(out["live_trading"], "DISABLED")

    def test_46_bool_clock_denied(self) -> None:
        self.rejected(fixture(), now_ms=True)

    def test_47_bad_cadence_rejected(self) -> None:
        self.rejected(fixture(), context=replace(self.context, cadence="REAL_TIME_TRADING"))

    def test_48_no_provider_api_required(self) -> None:
        import ast
        source = (ROOT / "packages/production/local_reference_import.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertTrue(all(not item.startswith((
            "requests", "urllib", "httpx", "socket", "MetaTrader5",
            "ccxt", "selenium", "playwright"
        )) for item in imports))


if __name__ == "__main__":
    unittest.main()
