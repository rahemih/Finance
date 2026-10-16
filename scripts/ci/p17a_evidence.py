from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

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
    SimulatedFill,
    run_backtest,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/quant/backtest-engine-policy.json"


class EvidenceStrategy:
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


class EvidenceExecution:
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
                f"fill-{decision.decision_id}",
                decision.decision_id,
                decision.asset_id,
                event.event_time_ns,
                decision.quantity_delta,
                event.price_scaled,
                event.price_scale,
                "0",
            ),
        )


def build_snapshot() -> ReplaySnapshot:
    policy = ReplaySnapshotPolicy(
        frozenset(
            {"EVENT_TIME", "RECEIVE_TIME", "CONTROLLED_SIMULATION_CLOCK"}
        ),
        10,
        10,
        10,
        100_000,
        "NOT_SELECTED",
    )
    return ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=5000,
        snapshot_cutoff_ns=4999,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "p17a-fixture",
                "a" * 64,
                "1.0",
                1000,
                5000,
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
        policy=policy,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    snapshot = build_snapshot()
    result = run_backtest(
        spec=BacktestRunSpec(
            "p17a-evidence",
            snapshot.snapshot_id,
            "fixture-round-trip",
            "e" * 64,
            "f" * 64,
            "1000",
            "USD",
        ),
        snapshot=snapshot,
        events=(
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 110, 1),
        ),
        strategy=EvidenceStrategy(),
        execution=EvidenceExecution(),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17A_BACKTEST_ENGINE_EVIDENCE",
        "task_id": "FIN-P17-WA-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "snapshot_id": snapshot.snapshot_id,
        "result_id": result.result_id,
        "status": result.status,
        "event_count": result.event_count,
        "decision_ids": list(result.decision_ids),
        "fill_ids": list(result.fill_ids),
        "ending_equity": result.ending_equity,
        "pnl_cash": result.pnl_cash,
        "execution_realism_owner": result.execution_realism_owner,
        "g9_authority": result.g9_authority,
        "profitability_claim_authority": result.profitability_claim_authority,
        "execution_authority": result.execution_authority,
        "order_routing_authority": result.order_routing_authority,
        "live_trading": result.live_trading,
        "auto_trading": result.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P17A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
