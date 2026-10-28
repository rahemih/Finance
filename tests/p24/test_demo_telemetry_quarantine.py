from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from packages.production.demo_telemetry_quarantine import (
    EXPECTED_POLICY, DemoQuarantineError, OfflineDemoTelemetry, render_html,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/p24-demo-report-policy.json"


def fixture() -> dict[str, object]:
    return {
        "schema_version": "1.0", "trace_id": "TRACE-0123456789abcdef",
        "source_kind": "SYNTHETIC_FIXTURE", "platform": "FIBO_MT5_DEMO",
        "environment": "DEMO", "currency_unit": "USD_CENTS",
        "observations": [
            {"observed_at_utc": "2026-10-01T10:00:00Z",
             "balance_minor": 10000, "equity_minor": 10000,
             "external_flow_minor": 0, "open_pnl_minor": 0,
             "quote_age_ms": 100, "connected": True,
             "trades_closed_count": 0, "rejected_orders_count": 0},
            {"observed_at_utc": "2026-10-01T10:01:00Z",
             "balance_minor": 10000, "equity_minor": 9000,
             "external_flow_minor": 0, "open_pnl_minor": -1000,
             "quote_age_ms": 1501, "connected": False,
             "trades_closed_count": 0, "rejected_orders_count": 1},
            {"observed_at_utc": "2026-10-01T10:02:00Z",
             "balance_minor": 10000, "equity_minor": 11000,
             "external_flow_minor": 0, "open_pnl_minor": 1000,
             "quote_age_ms": 200, "connected": True,
             "trades_closed_count": 1, "rejected_orders_count": 1},
        ],
    }


class DemoTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = OfflineDemoTelemetry(POLICY)

    def denied(self, changed: dict[str, object]) -> None:
        with self.assertRaises(DemoQuarantineError):
            self.loader.evaluate(changed)

    def modify(self, index: int, name: str, value: object) -> dict[str, object]:
        changed = deepcopy(fixture())
        changed["observations"][index][name] = value
        return changed

    def test_01_exact_policy(self) -> None:
        self.assertTrue(len(self.loader.policy_id) == 64)

    def test_02_policy_network_mutation_rejected(self) -> None:
        altered = {**EXPECTED_POLICY, "network_mode": "ENABLED"}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaises(DemoQuarantineError):
                OfflineDemoTelemetry(p)

    def test_03_policy_boolean_as_int_rejected(self) -> None:
        altered = {**EXPECTED_POLICY, "source_account_attested": 0}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaises(DemoQuarantineError):
                OfflineDemoTelemetry(p)

    def test_04_missing_policy_rejected(self) -> None:
        with self.assertRaises(DemoQuarantineError):
            OfflineDemoTelemetry(Path("/missing-p24wp-policy-demo.json"))

    def test_05_reference_report_computed(self) -> None:
        result = self.loader.evaluate(fixture())
        self.assertEqual(result["number_of_samples"], 3)
        self.assertEqual(result["max_drawdown_bps"], 1000)
        self.assertEqual(result["net_pnl_minor_adjusted_for_flows"], 1000)

    def test_06_no_broker_attestation(self) -> None:
        out = self.loader.evaluate(fixture())
        self.assertFalse(out["broker_source_attested"])
        self.assertFalse(out["broker_execution_certified"])
        self.assertFalse(out["real_profitability_validated"])
        self.assertFalse(out["live_execution_authority"])

    def test_07_report_replay_identical(self) -> None:
        self.assertEqual(self.loader.evaluate(fixture()), self.loader.evaluate(fixture()))

    def test_08_unknown_privacy_field_rejected(self) -> None:
        x = fixture()
        x["password"] = "should-never-appear"
        self.denied(x)

    def test_09_account_login_disallowed(self) -> None:
        x = fixture()
        x["account_number"] = 123456
        self.denied(x)

    def test_10_api_token_disallowed(self) -> None:
        x = self.modify(0, "api_key", "do-not-store")
        self.denied(x)

    def test_11_otp_disallowed(self) -> None:
        x = self.modify(1, "otp", "111111")
        self.denied(x)

    def test_12_live_environment_rejected(self) -> None:
        x = fixture()
        x["environment"] = "LIVE"
        self.denied(x)

    def test_13_noncanonical_schema_rejected(self) -> None:
        x = fixture()
        x["schema_version"] = "2.0"
        self.denied(x)

    def test_14_bad_trace_identity_rejected(self) -> None:
        x = fixture()
        x["trace_id"] = "123456"
        self.denied(x)

    def test_15_unsupported_market_platform_rejected(self) -> None:
        x = fixture()
        x["platform"] = "LIVE_FOREX"
        self.denied(x)

    def test_16_tabdeal_real_demo_not_claimed(self) -> None:
        x = fixture()
        x["platform"] = "TABDEAL_SPOT_MOCK"
        x["source_kind"] = "USER_SUPPLIED_SANITIZED_DEMO"
        self.denied(x)

    def test_17_tabdeal_mock_supported(self) -> None:
        x = fixture()
        x["platform"] = "TABDEAL_SPOT_MOCK"
        self.assertEqual(self.loader.evaluate(x)["platform"], "TABDEAL_SPOT_MOCK")

    def test_18_user_export_accepted_but_never_certified(self) -> None:
        x = fixture()
        x["source_kind"] = "USER_SUPPLIED_SANITIZED_DEMO"
        result = self.loader.evaluate(x)
        self.assertFalse(result["broker_source_attested"])

    def test_19_unknown_origin_rejected(self) -> None:
        x = fixture()
        x["source_kind"] = "REGULATOR_CERTIFIED"
        self.denied(x)

    def test_20_unknown_unit_rejected(self) -> None:
        x = fixture()
        x["currency_unit"] = "USD"
        self.denied(x)

    def test_21_missing_observation_rejected(self) -> None:
        x = fixture()
        x["observations"] = x["observations"][:1]
        self.denied(x)

    def test_22_duplicate_timestamp_rejected(self) -> None:
        x = self.modify(1, "observed_at_utc", "2026-10-01T10:00:00Z")
        self.denied(x)

    def test_23_out_of_order_timestamp_rejected(self) -> None:
        x = self.modify(1, "observed_at_utc", "2026-10-01T09:59:00Z")
        self.denied(x)

    def test_24_invalid_timestamp_rejected(self) -> None:
        self.denied(self.modify(1, "observed_at_utc", "2026-02-30T10:00:00Z"))

    def test_25_timezone_must_be_explicit_utc(self) -> None:
        self.denied(self.modify(0, "observed_at_utc", "2026-10-01T10:00:00"))

    def test_26_negative_equity_rejected(self) -> None:
        self.denied(self.modify(1, "equity_minor", -2))

    def test_27_boolean_as_int_rejected(self) -> None:
        self.denied(self.modify(1, "connected", 1))
        self.denied(self.modify(1, "quote_age_ms", True))

    def test_28_missing_equity_reconciliation_rejected(self) -> None:
        self.denied(self.modify(1, "open_pnl_minor", -777))

    def test_29_closed_trade_counter_regression_rejected(self) -> None:
        x = fixture()
        x["observations"][1]["trades_closed_count"] = 2
        self.denied(x)

    def test_30_rejected_order_counter_regression_rejected(self) -> None:
        self.denied(self.modify(2, "rejected_orders_count", 0))

    def test_31_initial_flow_must_be_zero(self) -> None:
        self.denied(self.modify(0, "external_flow_minor", 1))

    def test_32_cash_flow_adjusted_net_result(self) -> None:
        x = fixture()
        x["observations"][2]["balance_minor"] = 15000
        x["observations"][2]["equity_minor"] = 16000
        x["observations"][2]["external_flow_minor"] = 5000
        result = self.loader.evaluate(x)
        self.assertEqual(result["net_pnl_minor_adjusted_for_flows"], 1000)

    def test_33_drawdown_does_not_hide_larger_peak_drop(self) -> None:
        x = fixture()
        x["observations"][2]["equity_minor"] = 8500
        x["observations"][2]["open_pnl_minor"] = -1500
        result = self.loader.evaluate(x)
        self.assertEqual(result["max_drawdown_bps"], 1500)

    def test_34_stale_and_disconnected_counts(self) -> None:
        out = self.loader.evaluate(fixture())
        self.assertEqual(out["stale_quote_observations"], 1)
        self.assertEqual(out["disconnected_observations"], 1)

    def test_35_extra_nested_metadata_rejected(self) -> None:
        self.denied(self.modify(1, "security_question", "secret"))

    def test_36_invalid_boolean_array_rejected(self) -> None:
        self.denied(self.modify(0, "connected", [True]))

    def test_37_report_source_hash_changes_with_input(self) -> None:
        a = self.loader.evaluate(fixture())
        b = self.loader.evaluate(self.modify(1, "quote_age_ms", 1600))
        self.assertNotEqual(a["source_sha256"], b["source_sha256"])

    def test_38_html_explicitly_unattested_and_escaped(self) -> None:
        x = self.loader.evaluate(fixture())
        html = render_html(x)
        self.assertIn("UNATTESTED", html)
        self.assertIn("NO LIVE AUTHORITY", html)
        x["platform"] = "<script>alert(1)</script>"
        escaped = render_html(x)
        self.assertNotIn("<script>", escaped)
        self.assertIn("&lt;script&gt;", escaped)

    def test_39_live_and_g13_remain_disabled(self) -> None:
        x = self.loader.evaluate(fixture())
        self.assertEqual(x["g13"], "NOT_STARTED")
        self.assertEqual(x["live_trading"], "DISABLED")
        self.assertEqual(x["pre_first_live_satisfied"], 0)

    def test_40_wrong_observation_object_rejected(self) -> None:
        x = fixture()
        x["observations"][2] = ["bad"]
        self.denied(x)


if __name__ == "__main__":
    unittest.main()
