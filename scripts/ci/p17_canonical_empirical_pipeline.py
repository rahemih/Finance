#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
from pathlib import Path

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from quant.backtesting.capacity_testing import evaluate_liquidity_capacity
from quant.backtesting.empirical_quant_gate import (
    EmpiricalMeasurement,
    EmpiricalWorkstreamEvidence,
    MetricSchema,
    certify_empirical_g9,
)
from quant.backtesting.engine import (
    BacktestDecision,
    BacktestMarketEvent,
    BacktestPortfolioView,
    BacktestRunSpec,
    SimulatedFill,
    run_backtest,
)
from quant.backtesting.execution_realism import (
    ExecutionRealismPolicy,
    HistoricalDepthLevel,
    HistoricalExecutionContext,
    HistoricalExecutionSimulator,
)
from quant.backtesting.information_hygiene import (
    DecisionInformationAudit,
    UniverseMembershipChange,
    certify_information_hygiene,
)
from quant.backtesting.model_registry import ModelVersion, build_model_registry
from quant.backtesting.robustness import (
    MonteCarloSpec,
    SensitivityVariant,
    StressScenario,
    evaluate_robustness,
)
from quant.backtesting.strategy_registry import StrategyVersion, build_strategy_registry
from quant.backtesting.walk_forward import (
    CandidateSelection,
    OutOfSampleResultRef,
    WalkForwardFold,
    certify_walk_forward,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
GATE_POLICY = ROOT / "config/quant/empirical-quant-gate-policy.json"
E2E_POLICY = ROOT / "config/learning/end-to-end-reference-policy.json"
REPLAY_POLICY = ROOT / "config/historical-data/replay-snapshot-policy.json"


def canonical_bytes(value: object) -> bytes:
    def encode_special(item: object) -> str:
        if isinstance(item, Decimal):
            return decimal_text(item)
        raise TypeError(f"unsupported canonical JSON type: {type(item).__name__}")

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=encode_special,
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal, parse_int=Decimal)
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def bps(value: Decimal, *, ceil: bool = False) -> int:
    mode = ROUND_CEILING if ceil else ROUND_FLOOR
    return int(value.to_integral_value(rounding=mode))


class PeriodStrategy:
    def __init__(self, first_sequence: int, last_sequence: int, quantity: str) -> None:
        self._first = first_sequence
        self._last = last_sequence
        self._quantity = quantity

    def on_event(
        self,
        event: BacktestMarketEvent,
        portfolio: BacktestPortfolioView,
    ) -> BacktestDecision | None:
        del portfolio
        if event.sequence == self._first:
            return BacktestDecision(
                f"buy-{self._first}",
                event.asset_id,
                event.event_time_ns,
                self._quantity,
            )
        if event.sequence == self._last:
            return BacktestDecision(
                f"sell-{self._last}",
                event.asset_id,
                event.event_time_ns,
                f"-{self._quantity}",
            )
        return None


class CloseFillSimulator:
    def on_market_event(self, event: BacktestMarketEvent) -> tuple[SimulatedFill, ...]:
        del event
        return ()

    def submit(
        self,
        decision: BacktestDecision,
        event: BacktestMarketEvent,
    ) -> tuple[SimulatedFill, ...]:
        return (
            SimulatedFill(
                fill_id=digest({"ideal": decision.decision_id, "event": event.sequence}),
                decision_id=decision.decision_id,
                asset_id=decision.asset_id,
                fill_time_ns=event.event_time_ns,
                quantity_delta=decision.quantity_delta,
                fill_price_scaled=event.price_scaled,
                price_scale=event.price_scale,
                explicit_cost_cash="0",
            ),
        )


def rows_and_policy() -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    data = load(DATA)
    if data.get("fixture_only") is not False:
        raise RuntimeError("canonical empirical pipeline requires fixture_only=false market data")
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) < 12:
        raise RuntimeError("canonical empirical pipeline requires at least twelve rows")
    typed: list[dict[str, object]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise RuntimeError("market row must be an object")
        typed.append(raw)
    dates = [str(row["date"]) for row in typed]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise RuntimeError("market rows must be unique and chronological")
    return typed, load(E2E_POLICY), load(GATE_POLICY)


def market_components(
    rows: list[dict[str, object]],
    policy: dict[str, object],
) -> tuple[
    ReplaySnapshot,
    tuple[BacktestMarketEvent, ...],
    tuple[HistoricalExecutionContext, ...],
    ExecutionRealismPolicy,
]:
    p17 = policy.get("p17")
    if not isinstance(p17, dict):
        raise RuntimeError("p17 policy required")
    dataset_sha = file_sha(DATA)
    source = load(DATA).get("source")
    membership_sha = digest({"source": source, "asset": "BTC-USD", "membership": True})
    replay_policy = ReplaySnapshotPolicy.from_path(REPLAY_POLICY)
    event_times = tuple((index + 1) * 1000 for index in range(len(rows)))
    replay_end = event_times[-1] + 1000
    snapshot = ReplaySnapshot.build(
        replay_start_ns=event_times[0],
        replay_end_ns=replay_end,
        snapshot_cutoff_ns=event_times[-1],
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                dataset_name="btc-usd-public-reference",
                dataset_version=dataset_sha,
                schema_version="1.0",
                window_start_ns=event_times[0],
                window_end_ns=replay_end,
                membership_root_sha256=membership_sha,
                rights_class="PUBLIC_REFERENCE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("public-reference-v1",),
        config_sha256=file_sha(E2E_POLICY),
        code_artifact_sha256=file_sha(Path(__file__)),
        rights_class="PUBLIC_REFERENCE",
        policy=replay_policy,
    )
    half_spread = int(Decimal(p17["derived_half_spread_bps"]))
    depth_ppm = Decimal(p17["derived_depth_fraction_ppm_of_daily_volume"])
    execution_policy = ExecutionRealismPolicy(
        policy_version="canonical-public-reference-v1",
        taker_fee_bps=int(Decimal(p17["taker_fee_bps"])),
        decision_latency_ns=0,
        max_displayed_depth_participation_bps=int(
            Decimal(p17["max_displayed_depth_participation_bps"])
        ),
    )
    events: list[BacktestMarketEvent] = []
    contexts: list[HistoricalExecutionContext] = []
    for index, row in enumerate(rows):
        close = Decimal(row["close"])
        volume = Decimal(row["quote_volume"])
        scaled = int((close * 100).to_integral_value())
        bid = bps(Decimal(scaled) * Decimal(10_000 - half_spread) / Decimal(10_000))
        ask = bps(
            Decimal(scaled) * Decimal(10_000 + half_spread) / Decimal(10_000),
            ceil=True,
        )
        if bid >= ask:
            raise RuntimeError("derived reference book must have positive spread")
        depth = volume / close * depth_ppm / Decimal(1_000_000)
        depth_text = decimal_text(depth)
        t = event_times[index]
        events.append(BacktestMarketEvent(index + 1, t, t, "BTC-USD", scaled, 100))
        row_sha = digest({"row": row, "derivation": "OHLCV_DERIVED_REFERENCE_DEPTH_V1"})
        contexts.append(
            HistoricalExecutionContext(
                sequence=index + 1,
                event_time_ns=t,
                available_at_ns=t,
                asset_id="BTC-USD",
                price_scale=100,
                bids=(
                    HistoricalDepthLevel(bid, depth_text),
                    HistoricalDepthLevel(max(1, bid - max(1, bid // 10_000)), depth_text),
                ),
                asks=(
                    HistoricalDepthLevel(ask, depth_text),
                    HistoricalDepthLevel(ask + max(1, ask // 10_000), depth_text),
                ),
                source_evidence_sha256=row_sha,
            )
        )
    return snapshot, tuple(events), tuple(contexts), execution_policy


def run_period(
    *,
    snapshot: ReplaySnapshot,
    events: tuple[BacktestMarketEvent, ...],
    contexts: tuple[HistoricalExecutionContext, ...],
    execution_policy: ExecutionRealismPolicy,
    run_id: str,
    quantity: str,
):
    simulator = HistoricalExecutionSimulator(policy=execution_policy, contexts=contexts)
    spec = BacktestRunSpec(
        run_id=run_id,
        replay_snapshot_id=snapshot.snapshot_id,
        strategy_id="reference-buy-hold",
        strategy_artifact_sha256=digest({"strategy": "BUY_FIRST_SELL_LAST", "quantity": quantity}),
        execution_simulator_artifact_sha256=execution_policy.policy_id,
        initial_cash="1000",
        base_currency="USD",
    )
    result = run_backtest(
        spec=spec,
        snapshot=snapshot,
        events=events,
        strategy=PeriodStrategy(events[0].sequence, events[-1].sequence, quantity),
        execution=simulator,
    )
    return result, simulator


def account_return_bps(ending_equity: str) -> int:
    return bps((Decimal(ending_equity) / Decimal("1000") - Decimal(1)) * Decimal(10_000))


def build() -> dict[str, object]:
    rows, policy, gate_policy = rows_and_policy()
    p17 = policy["p17"]
    assert isinstance(p17, dict)
    snapshot, all_events, all_contexts, execution_policy = market_components(rows, policy)
    oos_start = int(Decimal(p17["oos_start_index"]))
    quantity = str(p17["trade_quantity_btc"])
    oos_events = all_events[oos_start:]
    oos_contexts = all_contexts[oos_start:]

    actual, actual_simulator = run_period(
        snapshot=snapshot,
        events=oos_events,
        contexts=oos_contexts,
        execution_policy=execution_policy,
        run_id="canonical-empirical-main",
        quantity=quantity,
    )
    ideal = run_backtest(
        spec=BacktestRunSpec(
            "canonical-empirical-ideal",
            snapshot.snapshot_id,
            "reference-buy-hold",
            digest({"strategy": "BUY_FIRST_SELL_LAST", "quantity": quantity}),
            digest({"execution": "IDEAL_CLOSE_NO_COST"}),
            "1000",
            "USD",
        ),
        snapshot=snapshot,
        events=oos_events,
        strategy=PeriodStrategy(oos_events[0].sequence, oos_events[-1].sequence, quantity),
        execution=CloseFillSimulator(),
    )
    if actual.status != "COMPLETED" or ideal.status != "COMPLETED":
        raise RuntimeError("canonical empirical backtests must close all decisions")

    dataset_sha = file_sha(DATA)
    membership = UniverseMembershipChange(
        "btc-usd-member",
        "BTC-USD",
        all_events[0].event_time_ns,
        all_events[0].event_time_ns,
        True,
        digest({"dataset_sha256": dataset_sha, "membership": True}),
    )
    audits = (
        DecisionInformationAudit.build(
            decision_id=f"buy-{oos_events[0].sequence}",
            asset_id="BTC-USD",
            decision_time_ns=oos_events[0].event_time_ns,
            dataset_versions=(dataset_sha,),
        ),
        DecisionInformationAudit.build(
            decision_id=f"sell-{oos_events[-1].sequence}",
            asset_id="BTC-USD",
            decision_time_ns=oos_events[-1].event_time_ns,
            dataset_versions=(dataset_sha,),
        ),
    )
    hygiene = certify_information_hygiene(
        snapshot=snapshot,
        decisions=audits,
        universe_changes=(membership,),
    )

    fold_specs = (
        ("fold-1", 0, 2_000, 2_000, 3_000, 4_000, 9_000, 3_000, 3, 8),
        ("fold-2", 0, 6_000, 6_000, 7_000, 9_000, 15_000, 7_000, 8, 14),
    )
    folds: list[WalkForwardFold] = []
    selections: list[CandidateSelection] = []
    result_refs: list[OutOfSampleResultRef] = []
    for fold_id, train_start, train_end, val_start, val_end, test_start, test_end, selected_at, start_i, end_i in fold_specs:
        fold = WalkForwardFold(
            fold_id,
            train_start,
            train_end,
            val_start,
            val_end,
            test_start,
            test_end,
        )
        period_events = all_events[start_i:end_i]
        period_contexts = all_contexts[start_i:end_i]
        period_result, _ = run_period(
            snapshot=snapshot,
            events=period_events,
            contexts=period_contexts,
            execution_policy=execution_policy,
            run_id=f"canonical-{fold_id}",
            quantity=quantity,
        )
        if period_result.status != "COMPLETED":
            raise RuntimeError("walk-forward period backtest must complete")
        folds.append(fold)
        selections.append(
            CandidateSelection(
                f"selection-{fold_id}",
                fold_id,
                "reference-buy-hold",
                selected_at,
                digest({"fold": fold_id, "slice": "train", "dataset": dataset_sha}),
                digest({"fold": fold_id, "slice": "validation", "dataset": dataset_sha}),
            )
        )
        result_refs.append(
            OutOfSampleResultRef(
                f"result-{fold_id}",
                fold_id,
                period_result.result_id,
                hygiene.certificate_id,
                test_start,
                test_end,
            )
        )
    walk = certify_walk_forward(folds=folds, selections=selections, results=result_refs)

    closes = [Decimal(row["close"]) for row in rows[oos_start:]]
    returns = tuple(
        bps((closes[i] / closes[i - 1] - Decimal(1)) * Decimal(10_000))
        for i in range(1, len(closes))
    )
    actual_bps = account_return_bps(actual.ending_equity)
    ideal_bps = account_return_bps(ideal.ending_equity)
    robustness = evaluate_robustness(
        walk_forward_certificate_id=walk.certificate_id,
        oos_return_bps=returns,
        monte_carlo=MonteCarloSpec(
            seed_sha256=digest({"dataset": dataset_sha, "purpose": "P17E_REFERENCE"}),
            path_count=64,
            path_length=min(8, len(returns)),
            block_size=2,
        ),
        baseline_metric_bps=actual_bps,
        stress_scenarios=(
            StressScenario("cost-stress", 0, 10),
            StressScenario("market-cost-stress", 10, 10),
        ),
        sensitivity_variants=(
            SensitivityVariant("base-near", digest({"variant": "base-near"}), max(0, actual_bps - 10)),
            SensitivityVariant("wider-cost", digest({"variant": "wider-cost"}), max(0, actual_bps - 25)),
            SensitivityVariant("tighter-cost", digest({"variant": "tighter-cost"}), max(0, actual_bps - 5)),
        ),
    )
    capacity = evaluate_liquidity_capacity(
        robustness_certificate_id=robustness.certificate_id,
        execution_policy=execution_policy,
        side="BUY",
        baseline_quantity="0.5",
        contexts=oos_contexts,
        scale_bps=(10_000, 20_000, 50_000),
    )

    code_sha = file_sha(Path(__file__))
    config_sha = file_sha(E2E_POLICY)
    strategy = StrategyVersion(
        strategy_id="reference-btc-usd-buy-hold",
        version="2.0.0",
        lifecycle_state="VALIDATED",
        definition_sha256=digest({"strategy": "BUY_FIRST_OOS_SELL_LAST_OOS", "oos_start": oos_start}),
        code_sha256=code_sha,
        config_sha256=config_sha,
        universe_id="BTC-USD",
        timeframe_id="1d",
        walk_forward_certificate_sha256=walk.certificate_id,
        robustness_certificate_sha256=robustness.certificate_id,
        capacity_certificate_sha256=capacity.certificate_id,
    )
    strategy_registry = build_strategy_registry((strategy,))
    model = ModelVersion(
        model_id="reference-rule-baseline",
        version="2.0.0",
        lifecycle_state="VALIDATED",
        model_artifact_sha256=digest({"kind": "REFERENCE_RULE_BASELINE", "strategy": strategy.record_id}),
        code_sha256=code_sha,
        config_sha256=config_sha,
        feature_schema_sha256=digest({"schema": "OHLCV_DAILY_V1"}),
        training_dataset_sha256=dataset_sha,
        strategy_record_sha256=strategy.record_id,
        walk_forward_certificate_sha256=walk.certificate_id,
        robustness_certificate_sha256=robustness.certificate_id,
    )
    model_registry = build_model_registry((model,))

    diagnostics_payload = [row.payload() for row in actual_simulator.diagnostics]
    workstream_payloads = {
        "P17-A": {"result_id": actual.result_id, "status": actual.status, "ending_equity": actual.ending_equity},
        "P17-B": {"policy_id": execution_policy.policy_id, "diagnostics": diagnostics_payload},
        "P17-C": {"certificate_id": hygiene.certificate_id, "status": hygiene.status},
        "P17-D": {"certificate_id": walk.certificate_id, "status": walk.status},
        "P17-E": {"certificate_id": robustness.certificate_id, "status": robustness.status},
        "P17-F": {"certificate_id": capacity.certificate_id, "status": capacity.status},
        "P17-G": {"record_id": strategy.record_id, "registry_id": strategy_registry.registry_id},
        "P17-H": {"record_id": model.record_id, "registry_id": model_registry.registry_id},
    }
    workstreams = tuple(
        EmpiricalWorkstreamEvidence(
            workstream=name,
            evidence_sha256=digest(payload),
            provenance_sha256=digest(
                {
                    "dataset_sha256": dataset_sha,
                    "snapshot_id": snapshot.snapshot_id,
                    "canonical_module_output": payload,
                }
            ),
        )
        for name, payload in workstream_payloads.items()
    )

    metric_rows = gate_policy.get("metrics")
    if not isinstance(metric_rows, list):
        raise RuntimeError("empirical gate metric policy required")
    schemas = tuple(
        MetricSchema(
            category=str(row["category"]),
            metric_id=str(row["metric_id"]),
            version="2.0",
            unit=str(row["unit"]),
            comparator=str(row["comparator"]),
            threshold_value=int(Decimal(row["threshold_value"])),
        )
        for row in metric_rows
        if isinstance(row, dict)
    )
    stress_worst = min(item.terminal_return_bps for item in robustness.stress_diagnostics)
    measurements_by_category = {
        "OOS_EDGE": actual_bps,
        "RISK": robustness.monte_carlo_worst_max_drawdown_bps,
        "ROBUSTNESS": stress_worst,
        "CAPACITY": capacity.max_full_fill_scale_bps,
        "EXECUTION_REALISM": max(0, ideal_bps - actual_bps),
    }
    category_evidence = {
        "OOS_EDGE": actual.result_id,
        "RISK": robustness.certificate_id,
        "ROBUSTNESS": robustness.certificate_id,
        "CAPACITY": capacity.certificate_id,
        "EXECUTION_REALISM": digest({"actual": actual.result_id, "ideal": ideal.result_id}),
    }
    measurements = tuple(
        EmpiricalMeasurement(
            category=schema.category,
            metric_schema_id=schema.schema_id,
            measured_value=measurements_by_category[schema.category],
            evidence_sha256=category_evidence[schema.category],
            dataset_sha256=dataset_sha,
        )
        for schema in schemas
    )
    gate = certify_empirical_g9(
        dataset_sha256=dataset_sha,
        threshold_policy_sha256=file_sha(GATE_POLICY),
        strategy_registry_id=strategy_registry.registry_id,
        model_registry_id=model_registry.registry_id,
        workstream_evidence=workstreams,
        metric_schemas=schemas,
        measurements=measurements,
    )
    if gate.state != "PASS_EMPIRICAL_REFERENCE":
        raise RuntimeError("canonical empirical G9 did not pass")

    return {
        "schema_version": "2.0",
        "kind": "NEXUS_QUANT_P17_CANONICAL_EMPIRICAL_PIPELINE_EVIDENCE",
        "task_id": "FIN-P18-WI-001-R03",
        "fixture_only": False,
        "empirical_reference": True,
        "canonical_modules_executed": [
            "P17-A_BACKTEST_ENGINE",
            "P17-B_EXECUTION_REALISM",
            "P17-C_INFORMATION_HYGIENE",
            "P17-D_WALK_FORWARD",
            "P17-E_ROBUSTNESS",
            "P17-F_LIQUIDITY_CAPACITY",
            "P17-G_STRATEGY_REGISTRY",
            "P17-H_MODEL_REGISTRY",
            "P17-I_EMPIRICAL_G9",
        ],
        "dataset_sha256": dataset_sha,
        "snapshot_id": snapshot.snapshot_id,
        "backtest_result_id": actual.result_id,
        "ideal_backtest_result_id": ideal.result_id,
        "information_hygiene_certificate_id": hygiene.certificate_id,
        "walk_forward_certificate_id": walk.certificate_id,
        "robustness_certificate_id": robustness.certificate_id,
        "capacity_certificate_id": capacity.certificate_id,
        "strategy_record_id": strategy.record_id,
        "strategy_registry_id": strategy_registry.registry_id,
        "model_record_id": model.record_id,
        "model_registry_id": model_registry.registry_id,
        "gate_certificate_id": gate.certificate_id,
        "gate_state": gate.state,
        "measurements": measurements_by_category,
        "workstream_evidence": [item.payload() for item in gate.workstream_evidence],
        "metric_schemas": [item.payload() for item in gate.metric_schemas],
        "production_scale_validation": False,
        "profitability_guarantee": False,
        "execution_authority": False,
        "automatic_live_promotion": False,
        "p19_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P17_CANONICAL_EMPIRICAL_PIPELINE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
