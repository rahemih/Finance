from __future__ import annotations

from dataclasses import replace
import unittest

from packages.learning.demo_paper import (
    DemoDecision,
    DemoFill,
    DemoMarketEvent,
    DemoPaperError,
    DemoPortfolioView,
    DemoSessionSpec,
    PaperTradingEngine,
)


CHECKPOINT_A = "a" * 64
CHECKPOINT_B = "b" * 64


def spec() -> DemoSessionSpec:
    return DemoSessionSpec(
        session_id="demo-001",
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="1.0.0",
        initial_cash="1000",
        base_currency="USD",
    )


def events() -> tuple[DemoMarketEvent, ...]:
    return (
        DemoMarketEvent(1, 1000, 900, "BTC-USD", 100, 1, "c" * 64),
        DemoMarketEvent(2, 2000, 1900, "BTC-USD", 110, 1, "d" * 64),
    )


class RoundTripStrategy:
    def checkpoint_sha256(self) -> str:
        return CHECKPOINT_A

    def on_event(
        self,
        event: DemoMarketEvent,
        portfolio: DemoPortfolioView,
    ) -> DemoDecision | None:
        del portfolio
        if event.sequence == 1:
            return DemoDecision(
                "buy-1",
                event.asset_id,
                event.event_time_ns,
                "1",
                "signal-1",
                "risk-1",
                "firewall-1",
            )
        if event.sequence == 2:
            return DemoDecision(
                "sell-1",
                event.asset_id,
                event.event_time_ns,
                "-1",
                "signal-2",
                "risk-2",
                "firewall-2",
            )
        return None


class ImmediateSimulator:
    def checkpoint_sha256(self) -> str:
        return CHECKPOINT_B

    def on_market_event(
        self, event: DemoMarketEvent
    ) -> tuple[DemoFill, ...]:
        del event
        return ()

    def submit(
        self,
        decision: DemoDecision,
        event: DemoMarketEvent,
    ) -> tuple[DemoFill, ...]:
        return (
            DemoFill(
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


class UnknownFillSimulator(ImmediateSimulator):
    def on_market_event(
        self, event: DemoMarketEvent
    ) -> tuple[DemoFill, ...]:
        return (
            DemoFill(
                "unknown-fill",
                "missing",
                event.asset_id,
                event.event_time_ns,
                "1",
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )


class OverfillSimulator(ImmediateSimulator):
    def submit(
        self,
        decision: DemoDecision,
        event: DemoMarketEvent,
    ) -> tuple[DemoFill, ...]:
        return (
            DemoFill(
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


class TestDemoPaperEngine(unittest.TestCase):
    def test_deterministic_round_trip(self) -> None:
        first = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        second = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        first_records = [first.ingest(item).record_id for item in events()]
        second_records = [second.ingest(item).record_id for item in events()]
        self.assertEqual(first_records, second_records)
        self.assertEqual(first.snapshot().state_id, second.snapshot().state_id)
        self.assertEqual(first.snapshot().cash, "1010")
        self.assertEqual(first.snapshot().equity, "1010")
        self.assertEqual(first.snapshot().positions, ())

    def test_snapshot_restore_is_deterministic(self) -> None:
        ev = events()
        uninterrupted = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        uninterrupted.ingest(ev[0])
        checkpoint = uninterrupted.snapshot()
        resumed = PaperTradingEngine.restore(
            spec=spec(),
            state=checkpoint,
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        uninterrupted.ingest(ev[1])
        resumed.ingest(ev[1])
        self.assertEqual(
            uninterrupted.snapshot().state_id,
            resumed.snapshot().state_id,
        )

    def test_duplicate_sequence_fails_closed(self) -> None:
        engine = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        engine.ingest(events()[0])
        with self.assertRaisesRegex(DemoPaperError, "sequence"):
            engine.ingest(events()[0])

    def test_future_information_fails_closed(self) -> None:
        with self.assertRaisesRegex(DemoPaperError, "available_at_ns"):
            DemoMarketEvent(1, 1000, 1001, "BTC-USD", 100, 1, "e" * 64)

    def test_unknown_fill_fails_closed(self) -> None:
        engine = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=UnknownFillSimulator(),
        )
        with self.assertRaisesRegex(DemoPaperError, "unknown decision"):
            engine.ingest(events()[0])

    def test_overfill_fails_closed(self) -> None:
        engine = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=OverfillSimulator(),
        )
        with self.assertRaisesRegex(DemoPaperError, "overfills"):
            engine.ingest(events()[0])

    def test_price_scale_drift_fails_closed(self) -> None:
        engine = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        engine.ingest(events()[0])
        drifted = replace(events()[1], price_scale=10)
        with self.assertRaisesRegex(DemoPaperError, "price scale"):
            engine.ingest(drifted)

    def test_safety_authority_remains_disabled(self) -> None:
        engine = PaperTradingEngine(
            spec=spec(),
            strategy=RoundTripStrategy(),
            execution=ImmediateSimulator(),
        )
        state = engine.snapshot()
        self.assertEqual(state.mode, "DEMO_PAPER_ONLY")
        self.assertFalse(state.automatic_live_promotion)
        self.assertEqual(state.live_trading, "DISABLED")
        self.assertEqual(state.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
