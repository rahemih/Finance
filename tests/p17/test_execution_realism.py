from __future__ import annotations

import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from quant.backtesting.engine import (
    BacktestDecision,
    BacktestMarketEvent,
    BacktestPortfolioView,
    BacktestRunSpec,
    run_backtest,
)
from quant.backtesting.execution_realism import (
    ExecutionRealismError,
    ExecutionRealismPolicy,
    HistoricalDepthLevel,
    HistoricalExecutionContext,
    HistoricalExecutionSimulator,
)


REPLAY_POLICY = ReplaySnapshotPolicy(
    frozenset({"EVENT_TIME", "RECEIVE_TIME", "CONTROLLED_SIMULATION_CLOCK"}),
    10,
    10,
    10,
    100_000,
    "NOT_SELECTED",
)


def snapshot() -> ReplaySnapshot:
    return ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=10000,
        snapshot_cutoff_ns=9999,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "p17b-fixture",
                "a" * 64,
                "1.0",
                1000,
                10000,
                "b" * 64,
                "TEST_FIXTURE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("fixture-q1",),
        config_sha256="c" * 64,
        code_artifact_sha256="d" * 64,
        rights_class="TEST_FIXTURE",
        policy=REPLAY_POLICY,
    )


def spec(snap: ReplaySnapshot) -> BacktestRunSpec:
    return BacktestRunSpec(
        "p17b-fixture",
        snap.snapshot_id,
        "fixture-strategy",
        "e" * 64,
        "f" * 64,
        "1000",
        "USD",
    )


def context(
    sequence: int,
    event_time_ns: int,
    *,
    bid: int = 99,
    ask: int = 101,
    bid_qty: str = "10",
    ask_qty: str = "10",
    funding_due: bool = False,
    funding_rate_text: str | None = None,
) -> HistoricalExecutionContext:
    return HistoricalExecutionContext(
        sequence=sequence,
        event_time_ns=event_time_ns,
        available_at_ns=event_time_ns - 1,
        asset_id="BTC-USD",
        price_scale=1,
        bids=(HistoricalDepthLevel(bid, bid_qty),),
        asks=(HistoricalDepthLevel(ask, ask_qty),),
        source_evidence_sha256="1" * 64,
        funding_due=funding_due,
        funding_rate_text=funding_rate_text,
        funding_mark_price_scaled=100 if funding_due else None,
        funding_evidence_sha256="2" * 64 if funding_due else None,
    )


class BuySellStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision("buy", "BTC-USD", event.event_time_ns, "1")
        if event.sequence == 2:
            return BacktestDecision("sell", "BTC-USD", event.event_time_ns, "-1")
        return None


class BuyQuantityStrategy:
    def __init__(self, quantity: str) -> None:
        self.quantity = quantity

    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision(
                "buy",
                "BTC-USD",
                event.event_time_ns,
                self.quantity,
            )
        return None


class ShortOnceStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision("short", "BTC-USD", event.event_time_ns, "-1")
        return None


class ExecutionRealismTests(unittest.TestCase):
    def test_spread_side_prices_affect_round_trip(self) -> None:
        snap = snapshot()
        events = (
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 100, 1),
        )
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 0, 10_000),
            contexts=(context(1, 1500), context(2, 2500)),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events,
            strategy=BuySellStrategy(),
            execution=simulator,
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.ending_equity, "998")
        self.assertEqual(result.pnl_cash, "-2")
        diagnostics = simulator.diagnostics
        self.assertEqual(diagnostics[0].fill_price_scaled, 101)
        self.assertEqual(diagnostics[1].fill_price_scaled, 99)

    def test_depth_walk_creates_deterministic_vwap_slippage(self) -> None:
        snap = snapshot()
        event = BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1)
        ctx = HistoricalExecutionContext(
            1,
            1500,
            1499,
            "BTC-USD",
            1,
            (HistoricalDepthLevel(99, "10"),),
            (
                HistoricalDepthLevel(101, "1"),
                HistoricalDepthLevel(103, "1"),
            ),
            "1" * 64,
        )
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 0, 10_000),
            contexts=(ctx,),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=(event,),
            strategy=BuyQuantityStrategy("2"),
            execution=simulator,
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(simulator.diagnostics[0].fill_price_scaled, 102)
        self.assertEqual(simulator.diagnostics[0].depth_levels_consumed, 2)

    def test_participation_limit_causes_repeatable_partial_fill(self) -> None:
        snap = snapshot()
        events = (
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 100, 1),
        )
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 0, 5000),
            contexts=(
                context(1, 1500, ask_qty="1"),
                context(2, 2500, ask_qty="1"),
            ),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events,
            strategy=BuyQuantityStrategy("1"),
            execution=simulator,
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(len(result.fill_ids), 2)
        self.assertEqual(result.ending_positions, (("BTC-USD", "1"),))

    def test_explicit_latency_delays_fill(self) -> None:
        snap = snapshot()
        events = (
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2000, 1900, "BTC-USD", 100, 1),
            BacktestMarketEvent(3, 2500, 2400, "BTC-USD", 100, 1),
        )
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 1000, 10_000),
            contexts=(
                context(1, 1500),
                context(2, 2000),
                context(3, 2500),
            ),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events,
            strategy=BuyQuantityStrategy("1"),
            execution=simulator,
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(len(result.fill_ids), 1)
        self.assertEqual(simulator.diagnostics[0].context_id, context(3, 2500).context_id)

    def test_explicit_fee_is_charged(self) -> None:
        snap = snapshot()
        event = BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1)
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 100, 0, 10_000),
            contexts=(context(1, 1500, bid=99, ask=100),),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=(event,),
            strategy=BuyQuantityStrategy("1"),
            execution=simulator,
        )
        self.assertEqual(simulator.diagnostics[0].fee_cash, "1")
        self.assertEqual(result.ending_equity, "999")

    def test_positive_funding_debits_long(self) -> None:
        snap = snapshot()
        events = (
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 100, 1),
        )
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 0, 10_000),
            contexts=(
                context(1, 1500, bid=99, ask=100),
                context(
                    2,
                    2500,
                    bid=99,
                    ask=101,
                    funding_due=True,
                    funding_rate_text="0.01",
                ),
            ),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events,
            strategy=BuyQuantityStrategy("1"),
            execution=simulator,
        )
        self.assertEqual(len(result.cash_adjustment_ids), 1)
        self.assertEqual(result.ending_equity, "999")

    def test_positive_funding_credits_short(self) -> None:
        snap = snapshot()
        events = (
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 100, 1),
        )
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 0, 10_000),
            contexts=(
                context(1, 1500, bid=100, ask=101),
                context(
                    2,
                    2500,
                    bid=99,
                    ask=101,
                    funding_due=True,
                    funding_rate_text="0.01",
                ),
            ),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events,
            strategy=ShortOnceStrategy(),
            execution=simulator,
        )
        self.assertEqual(len(result.cash_adjustment_ids), 1)
        self.assertEqual(result.ending_equity, "1001")

    def test_missing_context_fails_closed(self) -> None:
        snap = snapshot()
        simulator = HistoricalExecutionSimulator(
            policy=ExecutionRealismPolicy("fixture", 0, 0, 10_000),
            contexts=(context(1, 1500),),
        )
        with self.assertRaises(ExecutionRealismError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=(
                    BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 100, 1),
                ),
                strategy=BuyQuantityStrategy("1"),
                execution=simulator,
            )

    def test_future_context_fails_closed(self) -> None:
        with self.assertRaises(ExecutionRealismError):
            HistoricalExecutionContext(
                1,
                1500,
                1501,
                "BTC-USD",
                1,
                (HistoricalDepthLevel(99, "1"),),
                (HistoricalDepthLevel(101, "1"),),
                "1" * 64,
            )

    def test_no_funding_fields_without_due_flag(self) -> None:
        with self.assertRaises(ExecutionRealismError):
            HistoricalExecutionContext(
                1,
                1500,
                1400,
                "BTC-USD",
                1,
                (HistoricalDepthLevel(99, "1"),),
                (HistoricalDepthLevel(101, "1"),),
                "1" * 64,
                funding_rate_text="0.01",
            )


if __name__ == "__main__":
    unittest.main()
