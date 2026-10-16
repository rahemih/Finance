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
    run_backtest,
)
from quant.backtesting.execution_realism import (
    ExecutionRealismPolicy,
    HistoricalDepthLevel,
    HistoricalExecutionContext,
    HistoricalExecutionSimulator,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/quant/execution-realism-policy.json"


class EvidenceStrategy:
    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == 1:
            return BacktestDecision(
                "buy-3",
                "BTC-USD",
                event.event_time_ns,
                "3",
            )
        return None


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
                "p17b-fixture",
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


def context(
    sequence: int,
    event_time_ns: int,
    *,
    funding_due: bool = False,
) -> HistoricalExecutionContext:
    return HistoricalExecutionContext(
        sequence=sequence,
        event_time_ns=event_time_ns,
        available_at_ns=event_time_ns - 1,
        asset_id="BTC-USD",
        price_scale=1,
        bids=(
            HistoricalDepthLevel(99, "4"),
            HistoricalDepthLevel(98, "4"),
        ),
        asks=(
            HistoricalDepthLevel(101, "1"),
            HistoricalDepthLevel(103, "3"),
        ),
        source_evidence_sha256="1" * 64,
        funding_due=funding_due,
        funding_rate_text="0.001" if funding_due else None,
        funding_mark_price_scaled=100 if funding_due else None,
        funding_evidence_sha256="2" * 64 if funding_due else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    snapshot = build_snapshot()
    realism_policy = ExecutionRealismPolicy(
        policy_version="p17b-ci-v1",
        taker_fee_bps=10,
        decision_latency_ns=0,
        max_displayed_depth_participation_bps=5000,
    )
    simulator = HistoricalExecutionSimulator(
        policy=realism_policy,
        contexts=(
            context(1, 1500),
            context(2, 2500, funding_due=True),
        ),
    )
    result = run_backtest(
        spec=BacktestRunSpec(
            "p17b-evidence",
            snapshot.snapshot_id,
            "fixture-buy",
            "e" * 64,
            "f" * 64,
            "1000",
            "USD",
        ),
        snapshot=snapshot,
        events=(
            BacktestMarketEvent(1, 1500, 1400, "BTC-USD", 100, 1),
            BacktestMarketEvent(2, 2500, 2400, "BTC-USD", 100, 1),
        ),
        strategy=EvidenceStrategy(),
        execution=simulator,
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17B_EXECUTION_REALISM_EVIDENCE",
        "task_id": "FIN-P17-WB-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "runtime_policy_id": realism_policy.policy_id,
        "snapshot_id": snapshot.snapshot_id,
        "result_id": result.result_id,
        "status": result.status,
        "fill_ids": list(result.fill_ids),
        "cash_adjustment_ids": list(result.cash_adjustment_ids),
        "pending_decision_ids": list(result.pending_decision_ids),
        "ending_equity": result.ending_equity,
        "pnl_cash": result.pnl_cash,
        "diagnostics": [
            item.payload() for item in simulator.diagnostics
        ],
        "production_numeric_defaults": None,
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
    print(f"P17B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
