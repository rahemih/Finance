#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.learning.demo_paper import (
    DemoDecision,
    DemoFill,
    DemoMarketEvent,
    DemoPortfolioView,
    DemoSessionSpec,
    PaperTradingEngine,
)


class Strategy:
    def checkpoint_sha256(self) -> str:
        return "a" * 64

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


class Simulator:
    def checkpoint_sha256(self) -> str:
        return "b" * 64

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


def build_evidence() -> dict[str, object]:
    spec = DemoSessionSpec(
        session_id="p18a-ci",
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="1.0.0",
        initial_cash="1000",
        base_currency="USD",
    )
    events = (
        DemoMarketEvent(1, 1000, 900, "BTC-USD", 100, 1, "c" * 64),
        DemoMarketEvent(2, 2000, 1900, "BTC-USD", 110, 1, "d" * 64),
    )

    engine = PaperTradingEngine(
        spec=spec,
        strategy=Strategy(),
        execution=Simulator(),
    )
    record_ids = tuple(engine.ingest(event).record_id for event in events)
    state = engine.snapshot()

    if state.cash != "1010" or state.equity != "1010":
        raise RuntimeError("P18-A deterministic round-trip accounting failed")
    if state.positions:
        raise RuntimeError("P18-A round-trip must finish flat")
    if state.live_trading != "DISABLED" or state.auto_trading != "DISABLED":
        raise RuntimeError("P18-A trading authority boundary violated")
    if state.automatic_live_promotion:
        raise RuntimeError("P18-A automatic live promotion must remain disabled")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18A_DEMO_PAPER_EVIDENCE",
        "task_id": "FIN-P18-WA-001",
        "session_spec_id": spec.spec_id,
        "record_ids": list(record_ids),
        "final_state_id": state.state_id,
        "event_count": state.event_count,
        "ending_cash": state.cash,
        "ending_equity": state.equity,
        "ending_positions": [list(item) for item in state.positions],
        "mode": state.mode,
        "automatic_live_promotion": state.automatic_live_promotion,
        "broker_exchange_routing": False,
        "live_trading": state.live_trading,
        "auto_trading": state.auto_trading,
        "p18_b_started": False,
        "p19_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_evidence()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P18A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
