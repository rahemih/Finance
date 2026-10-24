from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.execution.execution_quality import (
    ExecutionQualityError,
    ExecutionQualityLedger,
    ExecutionQualityObservation,
    ExecutionQualityPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/execution-quality-policy.json"
RID = "a" * 64


def sample(
    *,
    market: str = "CRYPTO",
    order_id: str = "order-001",
    side: str = "BUY",
    filled: int = 100_000,
    ordered: int = 100_000,
    arrival: int = 10_000,
    fill_price: int | None = 10_010,
    submit: int = 1_000_000_000,
    ack: int = 1_100_000_000,
    first_fill: int | None = 1_200_000_000,
    terminal: int = 1_300_000_000,
    verdict: str = "MATCHED",
) -> ExecutionQualityObservation:
    if filled == 0:
        fill_price = None
        first_fill = None
    return ExecutionQualityObservation(
        market=market,
        order_id=order_id,
        client_order_id=f"client-{order_id}",
        reconciliation_report_id=RID,
        reconciliation_verdict=verdict,
        side=side,
        order_type="LIMIT",
        terminal_status="FILLED" if filled == ordered else ("PARTIALLY_FILLED" if filled else "CANCELED"),
        ordered_quantity_scaled=ordered,
        filled_quantity_scaled=filled,
        quantity_scale=100,
        arrival_price_scaled=arrival,
        average_fill_price_scaled=fill_price,
        price_scale=100,
        submit_time_ns=submit,
        ack_time_ns=ack,
        first_fill_time_ns=first_fill,
        terminal_time_ns=terminal,
        source_ref=f"reference://{market.lower()}/{order_id}",
    )


class ExecutionQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ExecutionQualityPolicy.from_path(POLICY)

    def test_policy_is_reference_only_zero_authority(self) -> None:
        self.assertEqual(self.policy.markets, ("CRYPTO", "FOREX"))
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_non_matched_reconciliation_fails_closed(self) -> None:
        with self.assertRaises(ExecutionQualityError):
            ExecutionQualityLedger(self.policy).add(sample(verdict="VENUE_AHEAD"))

    def test_latency_and_fill_ratio_are_deterministic(self) -> None:
        metric = ExecutionQualityLedger(self.policy).add(sample())
        self.assertEqual(metric.ack_latency_ns, 100_000_000)
        self.assertEqual(metric.first_fill_latency_ns, 200_000_000)
        self.assertEqual(metric.terminal_latency_ns, 300_000_000)
        self.assertEqual(metric.fill_ratio_ppm, 1_000_000)

    def test_buy_and_sell_adverse_slippage_direction(self) -> None:
        buy = ExecutionQualityLedger(self.policy).add(sample(fill_price=10_010))
        sell = ExecutionQualityLedger(self.policy).add(sample(side="SELL", fill_price=9_990))
        self.assertEqual(buy.adverse_slippage_ppm, 1_000)
        self.assertEqual(sell.adverse_slippage_ppm, 1_000)
        improved = ExecutionQualityLedger(self.policy).add(sample(side="BUY", fill_price=9_990))
        self.assertEqual(improved.adverse_slippage_ppm, -1_000)

    def test_unfilled_sample_has_no_slippage(self) -> None:
        metric = ExecutionQualityLedger(self.policy).add(sample(filled=0))
        self.assertIsNone(metric.adverse_slippage_ppm)
        self.assertIsNone(metric.first_fill_latency_ns)
        self.assertEqual(metric.fill_ratio_ppm, 0)

    def test_time_geometry_fails_closed(self) -> None:
        with self.assertRaises(ExecutionQualityError):
            ExecutionQualityLedger(self.policy).add(sample(ack=999_999_999))
        with self.assertRaises(ExecutionQualityError):
            ExecutionQualityLedger(self.policy).add(sample(first_fill=1_050_000_000))

    def test_exact_duplicate_is_idempotent(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        first = ledger.add(sample())
        second = ledger.add(sample())
        self.assertEqual(first, second)
        self.assertEqual(first.metric_id, second.metric_id)

    def test_conflicting_duplicate_order_fails_closed(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(sample())
        with self.assertRaises(ExecutionQualityError):
            ledger.add(sample(fill_price=10_020))

    def test_summary_percentiles_are_deterministic(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(
            sample(
                order_id="a",
                ack=1_100_000_000,
                first_fill=1_200_000_000,
                terminal=1_300_000_000,
            )
        )
        ledger.add(
            sample(
                order_id="b",
                ack=1_200_000_000,
                first_fill=1_300_000_000,
                terminal=1_500_000_000,
            )
        )
        ledger.add(
            sample(
                order_id="c",
                ack=1_300_000_000,
                first_fill=1_400_000_000,
                terminal=1_700_000_000,
            )
        )
        first = ledger.summary()
        second = ledger.summary()
        self.assertEqual(first, second)
        ack = first["ack_latency_ns"]
        assert isinstance(ack, dict)
        self.assertEqual(ack["p50"], 200_000_000)
        self.assertEqual(ack["p95"], 300_000_000)

    def test_reference_fail_band_is_threshold_bound(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(sample(ack=7_000_000_000, first_fill=7_100_000_000, terminal=7_200_000_000))
        self.assertEqual(ledger.summary()["quality_band"], "REFERENCE_FAIL")

    def test_healthy_full_fill_is_within_reference_budget(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(sample())
        self.assertEqual(ledger.summary()["quality_band"], "WITHIN_REFERENCE_BUDGET")

    def test_near_minimum_fill_is_degraded_reference(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(sample(filled=96_000, ordered=100_000))
        self.assertEqual(ledger.summary()["quality_band"], "DEGRADED_REFERENCE")

    def test_below_minimum_fill_is_reference_fail(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(sample(filled=94_900, ordered=100_000))
        self.assertEqual(ledger.summary()["quality_band"], "REFERENCE_FAIL")

    def test_summary_explicitly_denies_production_and_live_authority(self) -> None:
        ledger = ExecutionQualityLedger(self.policy)
        ledger.add(sample())
        authority = ledger.summary()["authority"]
        assert isinstance(authority, dict)
        self.assertTrue(authority["reference_only"])
        self.assertFalse(authority["real_venue_query"])
        self.assertFalse(authority["production_execution_certification"])
        self.assertFalse(authority["broker_certification"])
        self.assertFalse(authority["external_order_submission"])
        self.assertFalse(authority["live_execution_authority"])
        self.assertFalse(authority["g11_execution_validated"])


if __name__ == "__main__":
    unittest.main()
