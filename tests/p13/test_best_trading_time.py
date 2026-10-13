from __future__ import annotations

from pathlib import Path
import unittest

from packages.timing_opportunity.best_trading_time import (
    BestTradingTimeError,
    BestTradingTimePolicy,
    TimingWindowEvidence,
    assess_timing_window,
    select_best_timing_window,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/best-trading-time-policy.json"


class BestTradingTimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = BestTradingTimePolicy.from_path(POLICY_PATH)

    def evidence(
        self,
        window_id: str,
        *,
        mean_edge_bps: int,
        uncertainty_bps: int,
        sample_count: int = 40,
        market_open: bool = True,
        asset_id: str = "BTCUSD",
        strategy_id: str = "TREND_V1",
        timeframe: str = "1H",
        regime_label: str = "ALIGNED_BULLISH",
    ) -> TimingWindowEvidence:
        return TimingWindowEvidence(
            window_id=window_id,
            asset_id=asset_id,
            strategy_id=strategy_id,
            timeframe=timeframe,
            regime_label=regime_label,
            session_labels=("EUROPE", "US"),
            sample_count=sample_count,
            mean_edge_bps=mean_edge_bps,
            uncertainty_bps=uncertainty_bps,
            market_open=market_open,
        )

    def test_preferred_standard_and_weak_are_conservative(self) -> None:
        preferred = assess_timing_window(self.evidence("preferred", mean_edge_bps=300, uncertainty_bps=100), policy=self.policy)
        standard = assess_timing_window(self.evidence("standard", mean_edge_bps=150, uncertainty_bps=100), policy=self.policy)
        weak = assess_timing_window(self.evidence("weak", mean_edge_bps=50, uncertainty_bps=100), policy=self.policy)
        self.assertEqual(preferred.adjusted_edge_bps, 200)
        self.assertEqual(preferred.timing_class, "PREFERRED")
        self.assertEqual(standard.timing_class, "STANDARD")
        self.assertEqual(weak.timing_class, "WEAK")

    def test_insufficient_sample_and_uncertainty_are_not_usable(self) -> None:
        low_sample = assess_timing_window(
            self.evidence("low-sample", mean_edge_bps=500, uncertainty_bps=100, sample_count=10),
            policy=self.policy,
        )
        high_uncertainty = assess_timing_window(
            self.evidence("high-u", mean_edge_bps=7000, uncertainty_bps=6000),
            policy=self.policy,
        )
        self.assertEqual(low_sample.timing_class, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(low_sample.usable)
        self.assertEqual(high_uncertainty.timing_class, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(high_uncertainty.usable)

    def test_closed_market_context_cannot_be_preferred(self) -> None:
        result = assess_timing_window(
            self.evidence("closed", mean_edge_bps=1000, uncertainty_bps=100, market_open=False),
            policy=self.policy,
        )
        self.assertEqual(result.timing_class, "CLOSED_CONTEXT")
        self.assertFalse(result.usable)

    def test_best_window_selection_is_deterministic_and_order_independent(self) -> None:
        windows = (
            self.evidence("asia", mean_edge_bps=250, uncertainty_bps=100, sample_count=50),
            self.evidence("eu-us", mean_edge_bps=500, uncertainty_bps=100, sample_count=30),
            self.evidence("us", mean_edge_bps=400, uncertainty_bps=100, sample_count=80),
        )
        first = select_best_timing_window(windows, policy=self.policy)
        second = select_best_timing_window(tuple(reversed(windows)), policy=self.policy)
        self.assertEqual(first, second)
        self.assertEqual(first.selected_window_id, "eu-us")
        self.assertEqual(first.selected.adjusted_edge_bps, 400)

    def test_selection_rejects_heterogeneous_comparison_sets(self) -> None:
        with self.assertRaises(BestTradingTimeError):
            select_best_timing_window(
                (
                    self.evidence("a", mean_edge_bps=300, uncertainty_bps=100),
                    self.evidence("b", mean_edge_bps=400, uncertainty_bps=100, asset_id="EURUSD"),
                ),
                policy=self.policy,
            )

    def test_duplicate_window_id_fails_closed(self) -> None:
        with self.assertRaises(BestTradingTimeError):
            select_best_timing_window(
                (
                    self.evidence("same", mean_edge_bps=300, uncertainty_bps=100),
                    self.evidence("same", mean_edge_bps=400, uncertainty_bps=100),
                ),
                policy=self.policy,
            )

    def test_no_usable_window_fails_closed(self) -> None:
        with self.assertRaises(BestTradingTimeError):
            select_best_timing_window(
                (
                    self.evidence("closed", mean_edge_bps=500, uncertainty_bps=100, market_open=False),
                    self.evidence("thin", mean_edge_bps=500, uncertainty_bps=100, sample_count=5),
                ),
                policy=self.policy,
            )

    def test_scope_boundaries_are_explicit(self) -> None:
        self.assertTrue(self.policy.best_window_selection_in_scope)
        self.assertFalse(self.policy.opportunity_ranking_in_scope)
        self.assertFalse(self.policy.no_trade_authority)
        self.assertFalse(self.policy.signal_probability_in_scope)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
