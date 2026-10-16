from __future__ import annotations

from dataclasses import replace
import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from quant.backtesting.engine import (
    BacktestDecision,
    BacktestEngineError,
    BacktestMarketEvent,
    BacktestPortfolioView,
    BacktestRunSpec,
    SimulatedFill,
    run_backtest,
)


POLICY = ReplaySnapshotPolicy(
    allowed_clock_modes=frozenset(
        {"EVENT_TIME", "RECEIVE_TIME", "CONTROLLED_SIMULATION_CLOCK"}
    ),
    max_dataset_refs=10,
    max_feature_refs=10,
    max_vintage_refs=10,
    max_snapshot_bytes=100_000,
    production_replay_storage_vendor="NOT_SELECTED",
)


def snapshot() -> ReplaySnapshot:
    return ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=5000,
        snapshot_cutoff_ns=4999,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD", "ETH-USD"),
        dataset_refs=(
            ReplayDatasetRef(
                dataset_name="fixture-bars",
                dataset_version="a" * 64,
                schema_version="1.0",
                window_start_ns=1000,
                window_end_ns=5000,
                membership_root_sha256="b" * 64,
                rights_class="TEST_FIXTURE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("fixture-q1",),
        config_sha256="c" * 64,
        code_artifact_sha256="d" * 64,
        rights_class="TEST_FIXTURE",
        policy=POLICY,
    )


def spec(snap: ReplaySnapshot) -> BacktestRunSpec:
    return BacktestRunSpec(
        run_id="p17a-fixture",
        replay_snapshot_id=snap.snapshot_id,
        strategy_id="round-trip",
        strategy_artifact_sha256="e" * 64,
        execution_simulator_artifact_sha256="f" * 64,
        initial_cash="1000",
        base_currency="USD",
    )


def events() -> tuple[BacktestMarketEvent, ...]:
    return (
        BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
        BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 110, 1),
    )


class RoundTripStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision("buy-1", "BTC-USD", event.event_time_ns, "1")
        if event.sequence == 2:
            return BacktestDecision("sell-1", "BTC-USD", event.event_time_ns, "-1")
        return None


class ImmediateSimulator:
    def on_market_event(
        self,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        del event
        return ()

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        return (
            SimulatedFill(
                fill_id=f"fill-{decision.decision_id}",
                decision_id=decision.decision_id,
                asset_id=decision.asset_id,
                fill_time_ns=event.event_time_ns,
                quantity_delta=decision.quantity_delta,
                fill_price_scaled=event.price_scaled,
                price_scale=event.price_scale,
                explicit_cost_cash="0",
            ),
        )


class NoFillSimulator:
    def on_market_event(
        self,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        del event
        return ()

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        del decision, event
        return ()


class BuyOnceStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision("buy-1", "BTC-USD", event.event_time_ns, "1")
        return None


class AlwaysBuyStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        return BacktestDecision(
            f"buy-{event.sequence}",
            "BTC-USD",
            event.event_time_ns,
            "1",
        )


class OverfillSimulator(ImmediateSimulator):
    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        return (
            SimulatedFill(
                "overfill",
                decision.decision_id,
                decision.asset_id,
                event.event_time_ns,
                "2",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )


class UnknownDecisionSimulator:
    def on_market_event(
        self,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        if event.sequence != 2:
            return ()
        return (
            SimulatedFill(
                "unknown-fill",
                "not-seen",
                event.asset_id,
                event.event_time_ns,
                "1",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        del decision, event
        return ()


class DuplicateFillSimulator(ImmediateSimulator):
    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        return (
            SimulatedFill(
                "duplicate-fill",
                decision.decision_id,
                decision.asset_id,
                event.event_time_ns,
                "0.5",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
            SimulatedFill(
                "duplicate-fill",
                decision.decision_id,
                decision.asset_id,
                event.event_time_ns,
                "0.5",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )


class DelayedPartialFillSimulator:
    def __init__(self) -> None:
        self.pending_decision_id: str | None = None

    def on_market_event(
        self,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        if event.sequence != 2 or self.pending_decision_id is None:
            return ()
        return (
            SimulatedFill(
                "fill-later",
                self.pending_decision_id,
                "BTC-USD",
                event.event_time_ns,
                "0.6",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        self.pending_decision_id = decision.decision_id
        return (
            SimulatedFill(
                "fill-now",
                decision.decision_id,
                decision.asset_id,
                event.event_time_ns,
                "0.4",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )


class MultiAssetStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision("btc-buy", "BTC-USD", event.event_time_ns, "1")
        if event.sequence == 2:
            return BacktestDecision("eth-buy", "ETH-USD", event.event_time_ns, "2")
        return None


class BacktestEngineTests(unittest.TestCase):
    def test_round_trip_is_deterministic(self) -> None:
        snap = snapshot()
        left = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        right = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=tuple(reversed(events())),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        self.assertEqual(left.result_id, right.result_id)
        self.assertEqual(left.status, "COMPLETED")
        self.assertEqual(left.ending_equity, "1010")
        self.assertEqual(left.pnl_cash, "10")
        self.assertEqual(left.ending_positions, ())
        self.assertFalse(left.g9_authority)
        self.assertFalse(left.profitability_claim_authority)
        self.assertFalse(left.execution_authority)
        self.assertFalse(left.order_routing_authority)

    def test_duplicate_sequence_fails_closed(self) -> None:
        snap = snapshot()
        duplicate = (
            events()[0],
            replace(events()[1], sequence=1),
        )
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=duplicate,
                strategy=RoundTripStrategy(),
                execution=ImmediateSimulator(),
            )

    def test_decreasing_time_fails_closed(self) -> None:
        snap = snapshot()
        bad = (
            events()[0],
            replace(events()[1], event_time_ns=1200, available_at_ns=1100),
        )
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=bad,
                strategy=RoundTripStrategy(),
                execution=ImmediateSimulator(),
            )

    def test_future_information_fails_closed(self) -> None:
        with self.assertRaises(BacktestEngineError):
            BacktestMarketEvent(1, 1500, 1501, "BTC-USD", 100, 1)

    def test_snapshot_mismatch_fails_closed(self) -> None:
        snap = snapshot()
        bad_spec = replace(spec(snap), replay_snapshot_id="0" * 64)
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=bad_spec,
                snapshot=snap,
                events=events(),
                strategy=RoundTripStrategy(),
                execution=ImmediateSimulator(),
            )

    def test_event_outside_snapshot_fails_closed(self) -> None:
        snap = snapshot()
        outside = (
            BacktestMarketEvent(1, 900, 800, "BTC-USD", 100, 1),
        )
        with self.assertRaises(Exception):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=outside,
                strategy=BuyOnceStrategy(),
                execution=ImmediateSimulator(),
            )

    def test_overfill_fails_closed(self) -> None:
        snap = snapshot()
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=events(),
                strategy=BuyOnceStrategy(),
                execution=OverfillSimulator(),
            )

    def test_unknown_decision_fill_fails_closed(self) -> None:
        snap = snapshot()
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=events(),
                strategy=BuyOnceStrategy(),
                execution=UnknownDecisionSimulator(),
            )

    def test_duplicate_fill_id_fails_closed(self) -> None:
        snap = snapshot()
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=events(),
                strategy=BuyOnceStrategy(),
                execution=DuplicateFillSimulator(),
            )

    def test_delayed_partial_fills_are_accounted(self) -> None:
        snap = snapshot()
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events(),
            strategy=BuyOnceStrategy(),
            execution=DelayedPartialFillSimulator(),
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.pending_decision_ids, ())
        self.assertEqual(result.ending_positions, (("BTC-USD", "1"),))
        self.assertEqual(result.ending_equity, "1004")

    def test_multi_asset_accounting_is_deterministic(self) -> None:
        snap = snapshot()
        multi_events = (
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "ETH-USD", 50, 1),
        )
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=multi_events,
            strategy=MultiAssetStrategy(),
            execution=ImmediateSimulator(),
        )
        self.assertEqual(
            result.ending_positions,
            (("BTC-USD", "1"), ("ETH-USD", "2")),
        )
        self.assertEqual(result.ending_equity, "1000")

    def test_price_scale_drift_fails_closed(self) -> None:
        snap = snapshot()
        bad = (
            events()[0],
            replace(events()[1], price_scale=100),
        )
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=bad,
                strategy=RoundTripStrategy(),
                execution=ImmediateSimulator(),
            )

    def test_unfilled_decision_is_recorded(self) -> None:
        snap = snapshot()
        result = run_backtest(
            spec=spec(snap),
            snapshot=snap,
            events=events(),
            strategy=BuyOnceStrategy(),
            execution=NoFillSimulator(),
        )
        self.assertEqual(
            result.status,
            "COMPLETED_WITH_UNRESOLVED_DECISIONS",
        )
        self.assertEqual(result.pending_decision_ids, ("buy-1",))

    def test_overlapping_unresolved_decision_fails_closed(self) -> None:
        snap = snapshot()
        with self.assertRaises(BacktestEngineError):
            run_backtest(
                spec=spec(snap),
                snapshot=snap,
                events=events(),
                strategy=AlwaysBuyStrategy(),
                execution=NoFillSimulator(),
            )


if __name__ == "__main__":
    unittest.main()
