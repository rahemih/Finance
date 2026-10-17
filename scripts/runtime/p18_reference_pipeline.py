#!/usr/bin/env python3
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from packages.learning.canonical_evidence import (
    CanonicalArtifact,
    CanonicalDemoLineage,
    CanonicalEvidenceStore,
    CanonicalPromotionRequest,
    RetrainingResourceBudget,
    evaluate_canonical_promotion,
    verify_demo_lineage,
)
from packages.learning.champion_challenger import (
    ComparisonPolicy,
    EvaluationRecord,
    compare,
)
from packages.learning.dataset_curation import (
    TrainingDatasetSpec,
    curate_training_dataset,
)
from packages.learning.demo_paper import (
    DemoDecision,
    DemoFill,
    DemoMarketEvent,
    DemoPortfolioView,
    DemoSessionSpec,
    PaperTradingEngine,
)
from packages.learning.drift_decay import (
    DriftPolicy,
    MonitoringWindow,
    assess_drift,
)
from packages.learning.experiments import (
    ExperimentRegistry,
    ExperimentRun,
    ExperimentSpec,
)
from packages.learning.journal import (
    DecisionJournalEntry,
    DecisionOutcomeJournal,
    OutcomeJournalEntry,
)
from packages.learning.promotion import PromotionGovernor, PromotionRequest
from packages.learning.retraining import (
    ControlledRetrainingEngine,
    RetrainingRequest,
    TrainerOutput,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
POLICY = ROOT / "config/learning/end-to-end-reference-policy.json"
TRAINER = ROOT / "scripts/runtime/p18_reference_trainer.py"
STAGES = (
    "OBSERVE_ANALYZE",
    "DEMO_TRADE",
    "OUTCOME",
    "JOURNAL",
    "DATASET",
    "EXPERIMENT",
    "RETRAIN_VALIDATE",
    "CHALLENGER",
    "PROMOTION_GOVERNANCE",
)


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


def sha(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise RuntimeError(f"{field} must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise RuntimeError(f"{field} must be SHA-256") from exc
    if len(set(value.lower())) < 4:
        raise RuntimeError(f"{field} cannot be placeholder identity")
    return value.lower()


def scalar_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def validate_upstream(
    *,
    p17_path: Path,
    signal_path: Path,
    risk_path: Path,
    firewall_path: Path,
) -> dict[str, str]:
    p17 = load(p17_path)
    if p17.get("kind") != "NEXUS_QUANT_P17_CANONICAL_EMPIRICAL_PIPELINE_EVIDENCE":
        raise RuntimeError("P17 canonical empirical pipeline evidence required")
    if p17.get("fixture_only") is not False or p17.get("gate_state") != "PASS_EMPIRICAL_REFERENCE":
        raise RuntimeError("P17 empirical gate must be non-fixture PASS")
    modules = p17.get("canonical_modules_executed")
    expected_modules = [
        "P17-A_BACKTEST_ENGINE",
        "P17-B_EXECUTION_REALISM",
        "P17-C_INFORMATION_HYGIENE",
        "P17-D_WALK_FORWARD",
        "P17-E_ROBUSTNESS",
        "P17-F_LIQUIDITY_CAPACITY",
        "P17-G_STRATEGY_REGISTRY",
        "P17-H_MODEL_REGISTRY",
        "P17-I_EMPIRICAL_G9",
    ]
    if modules != expected_modules:
        raise RuntimeError("P17 canonical module coverage/order incomplete")

    signal = load(signal_path)
    if signal.get("kind") != "NEXUS_QUANT_P14H_SIGNAL_OUTPUT_EVIDENCE":
        raise RuntimeError("P14 signal evidence kind mismatch")
    signal_id = sha(signal.get("signal_id"), field="P14.signal_id")
    signal_payload = signal.get("signal")
    if not isinstance(signal_payload, dict):
        raise RuntimeError("P14 signal payload required")
    if signal_payload.get("signal_id") not in {None, signal_id}:
        raise RuntimeError("P14 signal payload identity mismatch")

    risk = load(risk_path)
    if risk.get("kind") != "NEXUS_QUANT_P15I_INDEPENDENT_RISK_VALIDATION_EVIDENCE":
        raise RuntimeError("P15 risk evidence kind mismatch")
    if risk.get("marker") != "P15_INDEPENDENT_RISK_VALIDATION":
        raise RuntimeError("P15 risk marker mismatch")
    if risk.get("fixture_only") is not True:
        raise RuntimeError("P15 reference evidence must explicitly declare fixture_only=true")
    normal = risk.get("normal")
    if not isinstance(normal, dict) or normal.get("status") != "PASS":
        raise RuntimeError("P15 normal risk validation must PASS")
    risk_id = sha(normal.get("validation_id"), field="P15.validation_id")
    if risk.get("execution_authority") is not False:
        raise RuntimeError("P15 evidence cannot carry execution authority")

    firewall = load(firewall_path)
    if firewall.get("kind") != "NEXUS_QUANT_P16H_G8_PRETRADE_SAFE_EVIDENCE":
        raise RuntimeError("P16 firewall evidence kind mismatch")
    if firewall.get("fixture_only") is not True:
        raise RuntimeError("P16 reference evidence must explicitly declare fixture_only=true")
    if firewall.get("gate_name") != "G8_PRETRADE_SAFE" or firewall.get("state") != "PASS":
        raise RuntimeError("P16 G8 must PASS")
    firewall_id = sha(firewall.get("gate_id"), field="P16.gate_id")
    if firewall.get("execution_authority") is not False:
        raise RuntimeError("P16 evidence cannot carry execution authority")

    return {
        "strategy_record_id": sha(p17.get("strategy_record_id"), field="P17.strategy_record_id"),
        "model_record_id": sha(p17.get("model_record_id"), field="P17.model_record_id"),
        "dataset_id": sha(p17.get("dataset_sha256"), field="P17.dataset_sha256"),
        "g9_certificate_id": sha(p17.get("gate_certificate_id"), field="P17.gate_certificate_id"),
        "signal_id": signal_id,
        "risk_id": risk_id,
        "firewall_id": firewall_id,
        "p17_provenance": file_sha(p17_path),
        "signal_provenance": file_sha(signal_path),
        "risk_provenance": file_sha(risk_path),
        "firewall_provenance": file_sha(firewall_path),
    }


class ReferenceDemoStrategy:
    def __init__(self, *, signal_id: str, risk_id: str, firewall_id: str) -> None:
        self._signal = signal_id
        self._risk = risk_id
        self._firewall = firewall_id
        self.emitted: list[DemoDecision] = []

    def checkpoint_sha256(self) -> str:
        return digest(
            {
                "kind": "P18_REFERENCE_DEMO_STRATEGY_V1",
                "signal_id": self._signal,
                "risk_id": self._risk,
                "firewall_id": self._firewall,
                "decision_sequences": [1, 3, 5, 7, 9, 11],
            }
        )

    def on_event(
        self,
        event: DemoMarketEvent,
        portfolio: DemoPortfolioView,
    ) -> DemoDecision | None:
        del portfolio
        if event.sequence not in {1, 3, 5, 7, 9, 11}:
            return None
        ordinal = (event.sequence + 1) // 2
        quantity = "0.001" if ordinal % 2 else "-0.001"
        decision = DemoDecision(
            decision_id=f"demo-{event.sequence}",
            asset_id=event.asset_id,
            decision_time_ns=event.event_time_ns,
            quantity_delta=quantity,
            signal_id=self._signal,
            risk_decision_id=self._risk,
            firewall_decision_id=self._firewall,
        )
        self.emitted.append(decision)
        return decision


class ReferenceDemoSimulator:
    def checkpoint_sha256(self) -> str:
        return digest({"kind": "P18_REFERENCE_DEMO_SIMULATOR_V1", "fill": "EVENT_CLOSE"})

    def on_market_event(self, event: DemoMarketEvent) -> tuple[DemoFill, ...]:
        del event
        return ()

    def submit(
        self,
        decision: DemoDecision,
        event: DemoMarketEvent,
    ) -> tuple[DemoFill, ...]:
        return (
            DemoFill(
                fill_id=digest({"decision": decision.decision_id, "event": event.sequence}),
                decision_id=decision.decision_id,
                asset_id=decision.asset_id,
                fill_time_ns=event.event_time_ns,
                quantity_delta=decision.quantity_delta,
                fill_price_scaled=event.price_scaled,
                price_scale=event.price_scale,
                explicit_cost_cash="0",
            ),
        )


class SandboxedReferenceTrainer:
    def __init__(self, budget: RetrainingResourceBudget) -> None:
        self._budget = budget
        self.last_sandbox_evidence: dict[str, object] | None = None

    def checkpoint_sha256(self) -> str:
        return digest(
            {
                "trainer_sha256": file_sha(TRAINER),
                "budget_id": self._budget.budget_id,
                "sandbox": "BASH_ULIMIT_CPU_AS_PLUS_SUBPROCESS_TIMEOUT",
            }
        )

    def train(self, request: RetrainingRequest) -> TrainerOutput:
        with tempfile.TemporaryDirectory(prefix="p18-reference-trainer-") as tmp:
            root = Path(tmp)
            request_path = root / "request.json"
            output_path = root / "output.json"
            request_path.write_text(
                json.dumps(request.payload(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            cpu = self._budget.max_cpu_seconds
            memory_kb = self._budget.max_memory_mb * 1024
            command = [
                "bash",
                "-c",
                'ulimit -t "$1"; ulimit -v "$2"; shift 2; exec "$@"',
                "p18-sandbox",
                str(cpu),
                str(memory_kb),
                sys.executable,
                str(TRAINER),
                "--request",
                str(request_path),
                "--output",
                str(output_path),
            ]
            last_error = "not-run"
            for attempt in range(1, self._budget.max_attempts + 1):
                try:
                    completed = subprocess.run(
                        command,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=self._budget.max_wall_seconds,
                    )
                except subprocess.TimeoutExpired:
                    last_error = "WALL_TIMEOUT"
                    continue
                if completed.returncode != 0:
                    last_error = f"RETURN_CODE_{completed.returncode}"
                    continue
                raw = load(output_path)
                if raw.get("kind") != "NEXUS_QUANT_P18_SANDBOX_TRAINER_OUTPUT":
                    raise RuntimeError("sandbox trainer output kind mismatch")
                request_id = sha(raw.get("request_id"), field="trainer.request_id")
                if request_id != request.request_id:
                    raise RuntimeError("sandbox trainer request lineage mismatch")
                metrics_raw = raw.get("metrics")
                if not isinstance(metrics_raw, dict):
                    raise RuntimeError("sandbox trainer metrics required")
                metrics = {str(key): str(value) for key, value in metrics_raw.items()}
                output = TrainerOutput.create(
                    request_id=request_id,
                    candidate_model_id=sha(raw.get("candidate_model_id"), field="candidate_model_id"),
                    model_artifact_sha256=sha(raw.get("model_artifact_sha256"), field="model_artifact_sha256"),
                    metrics=metrics,
                )
                self.last_sandbox_evidence = {
                    "budget_id": self._budget.budget_id,
                    "cpu_limit_seconds": cpu,
                    "address_space_limit_mb": self._budget.max_memory_mb,
                    "wall_timeout_seconds": self._budget.max_wall_seconds,
                    "max_attempts": self._budget.max_attempts,
                    "attempts_used": attempt,
                    "enforcement": [
                        "bash_ulimit_cpu",
                        "bash_ulimit_virtual_memory",
                        "subprocess_wall_timeout",
                        "bounded_attempt_loop",
                    ],
                    "trainer_checkpoint_sha256": self.checkpoint_sha256(),
                }
                return output
            raise RuntimeError(f"sandbox trainer exhausted attempts: {last_error}")


class ReferencePipeline:
    def __init__(
        self,
        *,
        p17_path: Path,
        signal_path: Path,
        risk_path: Path,
        firewall_path: Path,
    ) -> None:
        self.upstream = validate_upstream(
            p17_path=p17_path,
            signal_path=signal_path,
            risk_path=risk_path,
            firewall_path=firewall_path,
        )
        self.market = load(DATA)
        rows = self.market.get("rows")
        if not isinstance(rows, list) or len(rows) < 12:
            raise RuntimeError("reference market rows missing")
        self.rows = [row for row in rows if isinstance(row, dict)]
        if len(self.rows) != len(rows):
            raise RuntimeError("invalid reference market row")
        self.policy = load(POLICY)
        self.payloads: dict[str, dict[str, object]] = {}
        self.objects: dict[str, object] = {}

    def observe(self, cycle_name: str) -> dict[str, object]:
        if "OBSERVE_ANALYZE" in self.payloads:
            return self.payloads["OBSERVE_ANALYZE"]
        store = CanonicalEvidenceStore()
        records = (
            CanonicalArtifact(
                self.upstream["strategy_record_id"],
                "STRATEGY_RECORD",
                "VALIDATED",
                self.upstream["p17_provenance"],
            ),
            CanonicalArtifact(
                self.upstream["model_record_id"],
                "MODEL_RECORD",
                "VALIDATED",
                self.upstream["p17_provenance"],
            ),
            CanonicalArtifact(
                self.upstream["signal_id"],
                "SIGNAL_DECISION",
                "PASS",
                self.upstream["signal_provenance"],
            ),
            CanonicalArtifact(
                self.upstream["risk_id"],
                "RISK_DECISION",
                "PASS",
                self.upstream["risk_provenance"],
            ),
            CanonicalArtifact(
                self.upstream["firewall_id"],
                "FIREWALL_DECISION",
                "PASS",
                self.upstream["firewall_provenance"],
            ),
        )
        for record in records:
            store.add(record)
        lineage = CanonicalDemoLineage(*(record.artifact_id for record in records))
        lineage_id = verify_demo_lineage(store, lineage)
        payload = {
            "kind": "NEXUS_QUANT_P18_OBSERVE_ANALYZE_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "CanonicalEvidenceStore.verify_demo_lineage",
            "demo_lineage_id": lineage_id,
            "strategy_record_id": self.upstream["strategy_record_id"],
            "model_record_id": self.upstream["model_record_id"],
            "signal_id": self.upstream["signal_id"],
            "risk_validation_id": self.upstream["risk_id"],
            "firewall_gate_id": self.upstream["firewall_id"],
            "g9_certificate_id": self.upstream["g9_certificate_id"],
            "typed_upstream_identity_resolution": True,
            "whole_file_hash_as_typed_identity": False,
        }
        self.objects["evidence_store"] = store
        self.payloads["OBSERVE_ANALYZE"] = payload
        return payload

    def demo(self, cycle_name: str) -> dict[str, object]:
        self.observe(cycle_name)
        if "DEMO_TRADE" in self.payloads:
            return self.payloads["DEMO_TRADE"]
        spec = DemoSessionSpec(
            session_id=cycle_name,
            strategy_id=self.upstream["strategy_record_id"],
            strategy_version="2.0.0",
            model_id=self.upstream["model_record_id"],
            model_version="2.0.0",
            initial_cash="1000",
            base_currency="USD",
        )
        strategy = ReferenceDemoStrategy(
            signal_id=self.upstream["signal_id"],
            risk_id=self.upstream["risk_id"],
            firewall_id=self.upstream["firewall_id"],
        )
        engine = PaperTradingEngine(
            spec=spec,
            strategy=strategy,
            execution=ReferenceDemoSimulator(),
        )
        decision_rows: list[dict[str, object]] = []
        previous_count = 0
        for index, row in enumerate(self.rows, start=1):
            close = Decimal(row["close"])
            event = DemoMarketEvent(
                sequence=index,
                event_time_ns=index * 1000,
                available_at_ns=index * 1000,
                asset_id="BTC-USD",
                price_scaled=int((close * 100).to_integral_value()),
                price_scale=100,
                evidence_sha256=digest({"market_row": row, "source": self.market["source"]}),
            )
            engine.ingest(event)
            if len(strategy.emitted) > previous_count:
                decision = strategy.emitted[-1]
                state = engine.snapshot()
                decision_rows.append(
                    {
                        **decision.payload(),
                        "sequence": event.sequence,
                        "session_state_id": state.state_id,
                        "market_evidence_sha256": event.evidence_sha256,
                    }
                )
                previous_count = len(strategy.emitted)
        state = engine.snapshot()
        if len(decision_rows) != 6:
            raise RuntimeError("reference Demo strategy must emit six decisions")
        payload = {
            "kind": "NEXUS_QUANT_P18_DEMO_TRADE_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "PaperTradingEngine",
            "session_spec_id": spec.spec_id,
            "final_state_id": state.state_id,
            "ending_cash": state.cash,
            "ending_equity": state.equity,
            "decisions": decision_rows,
            "decision_count": len(decision_rows),
            "mode": state.mode,
        }
        self.objects["demo_spec"] = spec
        self.objects["demo_decisions"] = decision_rows
        self.payloads["DEMO_TRADE"] = payload
        return payload

    def outcomes(self, cycle_name: str) -> dict[str, object]:
        self.demo(cycle_name)
        if "OUTCOME" in self.payloads:
            return self.payloads["OUTCOME"]
        decisions = self.objects["demo_decisions"]
        assert isinstance(decisions, list)
        rows: list[dict[str, object]] = []
        for decision in decisions:
            assert isinstance(decision, dict)
            sequence = int(decision["sequence"])
            current = Decimal(self.rows[sequence - 1]["close"])
            future = Decimal(self.rows[sequence]["close"])
            direction = Decimal(1) if not str(decision["quantity_delta"]).startswith("-") else Decimal(-1)
            value = (future / current - Decimal(1)) * Decimal(10_000) * direction
            outcome = {
                "decision_id": decision["decision_id"],
                "observed_at_ns": (sequence + 1) * 1000,
                "outcome_value": scalar_text(value),
                "outcome_evidence_sha256": digest(
                    {
                        "decision_id": decision["decision_id"],
                        "current_close": str(current),
                        "future_close": str(future),
                        "direction": str(direction),
                    }
                ),
            }
            rows.append(outcome)
        payload = {
            "kind": "NEXUS_QUANT_P18_OUTCOME_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "point-in-time outcome observation feeding DecisionOutcomeJournal",
            "outcomes": rows,
            "outcome_count": len(rows),
        }
        self.objects["raw_outcomes"] = rows
        self.payloads["OUTCOME"] = payload
        return payload

    def journal(self, cycle_name: str) -> dict[str, object]:
        self.outcomes(cycle_name)
        if "JOURNAL" in self.payloads:
            return self.payloads["JOURNAL"]
        spec = self.objects["demo_spec"]
        decisions = self.objects["demo_decisions"]
        raw_outcomes = self.objects["raw_outcomes"]
        assert isinstance(spec, DemoSessionSpec)
        assert isinstance(decisions, list)
        assert isinstance(raw_outcomes, list)
        journal = DecisionOutcomeJournal()
        decision_entries: list[DecisionJournalEntry] = []
        outcome_entries: list[OutcomeJournalEntry] = []
        outcome_by_id = {str(row["decision_id"]): row for row in raw_outcomes if isinstance(row, dict)}
        for decision in decisions:
            assert isinstance(decision, dict)
            entry = DecisionJournalEntry(
                decision_id=str(decision["decision_id"]),
                session_spec_id=spec.spec_id,
                session_state_id=str(decision["session_state_id"]),
                sequence=int(decision["sequence"]),
                decision_time_ns=int(decision["decision_time_ns"]),
                asset_id=str(decision["asset_id"]),
                quantity_delta=str(decision["quantity_delta"]),
                strategy_id=self.upstream["strategy_record_id"],
                strategy_version="2.0.0",
                model_id=self.upstream["model_record_id"],
                model_version="2.0.0",
                signal_id=self.upstream["signal_id"],
                risk_decision_id=self.upstream["risk_id"],
                firewall_decision_id=self.upstream["firewall_id"],
                market_evidence_sha256=str(decision["market_evidence_sha256"]),
            )
            journal.append_decision(entry)
            decision_entries.append(entry)
            raw = outcome_by_id[entry.decision_id]
            outcome = OutcomeJournalEntry(
                outcome_id=f"outcome-{entry.decision_id}",
                decision_record_id=entry.record_id,
                observed_at_ns=int(raw["observed_at_ns"]),
                outcome_definition_id="next-observation-return-bps",
                outcome_definition_version="1.0.0",
                outcome_value=str(raw["outcome_value"]),
                outcome_evidence_sha256=str(raw["outcome_evidence_sha256"]),
            )
            journal.append_outcome(outcome)
            outcome_entries.append(outcome)
        payload = {
            "kind": "NEXUS_QUANT_P18_JOURNAL_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "DecisionOutcomeJournal",
            "journal_root_id": journal.root_id,
            "decision_record_ids": [row.record_id for row in decision_entries],
            "outcome_record_ids": [row.record_id for row in outcome_entries],
        }
        self.objects["journal"] = journal
        self.objects["decision_entries"] = decision_entries
        self.objects["outcome_entries"] = outcome_entries
        self.payloads["JOURNAL"] = payload
        return payload

    def dataset(self, cycle_name: str) -> dict[str, object]:
        self.journal(cycle_name)
        if "DATASET" in self.payloads:
            return self.payloads["DATASET"]
        journal = self.objects["journal"]
        decisions = self.objects["decision_entries"]
        outcomes = self.objects["outcome_entries"]
        assert isinstance(journal, DecisionOutcomeJournal)
        assert isinstance(decisions, list)
        assert isinstance(outcomes, list)
        spec = TrainingDatasetSpec(
            dataset_name=f"{cycle_name}-training",
            source_journal_root_id=journal.root_id,
            outcome_definition_id="next-observation-return-bps",
            outcome_definition_version="1.0.0",
            train_end_ns=6000,
            validation_end_ns=10000,
            dataset_cutoff_ns=14000,
        )
        curated = curate_training_dataset(spec=spec, decisions=decisions, outcomes=outcomes)
        if not curated.manifest.train_row_ids or not curated.manifest.validation_row_ids or not curated.manifest.test_row_ids:
            raise RuntimeError("canonical training dataset requires non-empty TRAIN/VALIDATION/TEST")
        payload = {
            "kind": "NEXUS_QUANT_P18_DATASET_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "curate_training_dataset",
            "dataset_id": curated.manifest.dataset_id,
            "row_ids": list(curated.manifest.row_ids),
            "train_rows": len(curated.manifest.train_row_ids),
            "validation_rows": len(curated.manifest.validation_row_ids),
            "test_rows": len(curated.manifest.test_row_ids),
            "exclusions": [row.payload() for row in curated.manifest.exclusions],
        }
        self.objects["curated"] = curated
        self.payloads["DATASET"] = payload
        return payload

    def experiment(self, cycle_name: str) -> dict[str, object]:
        self.dataset(cycle_name)
        if "EXPERIMENT" in self.payloads:
            return self.payloads["EXPERIMENT"]
        curated = self.objects["curated"]
        registry = ExperimentRegistry()
        spec = ExperimentSpec.create(
            experiment_name=f"{cycle_name}-experiment",
            hypothesis_id="canonical-reference-improves-baseline",
            dataset_id=curated.manifest.dataset_id,
            code_sha256=file_sha(Path(__file__)),
            strategy_id=self.upstream["strategy_record_id"],
            strategy_version="2.0.0",
            model_id=self.upstream["model_record_id"],
            model_version="2.0.0",
            parameters={"learning_rate": "0.01", "epochs": "10"},
        )
        experiment_id = registry.register_experiment(spec)
        run = ExperimentRun.create(
            run_name=f"{cycle_name}-run",
            experiment_id=experiment_id,
            started_at_ns=15000,
            completed_at_ns=16000,
            metrics={
                "sharpe": "1.00",
                "max_drawdown_bps": "400",
                "row_count": str(len(curated.manifest.row_ids)),
            },
            artifact_sha256=digest({"experiment_id": experiment_id, "dataset_id": curated.manifest.dataset_id}),
        )
        run_id = registry.register_run(run)
        snapshot = registry.snapshot()
        payload = {
            "kind": "NEXUS_QUANT_P18_EXPERIMENT_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "ExperimentRegistry",
            "experiment_id": experiment_id,
            "run_id": run_id,
            "registry_snapshot_id": snapshot.snapshot_id,
        }
        self.objects["experiment_id"] = experiment_id
        self.objects["experiment_run"] = run
        self.payloads["EXPERIMENT"] = payload
        return payload

    def retrain(self, cycle_name: str) -> dict[str, object]:
        self.experiment(cycle_name)
        if "RETRAIN_VALIDATE" in self.payloads:
            return self.payloads["RETRAIN_VALIDATE"]
        curated = self.objects["curated"]
        experiment_id = self.objects["experiment_id"]
        assert isinstance(experiment_id, str)
        budget_data = self.policy.get("trainer_budget")
        if not isinstance(budget_data, dict):
            raise RuntimeError("trainer budget policy required")
        budget = RetrainingResourceBudget(
            max_cpu_seconds=int(budget_data["max_cpu_seconds"]),
            max_memory_mb=int(budget_data["max_memory_mb"]),
            max_wall_seconds=int(budget_data["max_wall_seconds"]),
            max_attempts=int(budget_data["max_attempts"]),
        )
        trainer = SandboxedReferenceTrainer(budget)
        request = RetrainingRequest.create(
            dataset_id=curated.manifest.dataset_id,
            experiment_id=experiment_id,
            base_model_id=self.upstream["model_record_id"],
            code_sha256=file_sha(TRAINER),
            trainer_id="sandbox-reference-trainer",
            trainer_version="1.0.0",
            seed=42,
            parameters={"learning_rate": "0.01", "epochs": "10"},
        )
        result = ControlledRetrainingEngine(trainer).run(request)
        if not result.candidate_only or trainer.last_sandbox_evidence is None:
            raise RuntimeError("controlled retraining must return sandboxed candidate-only result")
        payload = {
            "kind": "NEXUS_QUANT_P18_RETRAIN_VALIDATE_STAGE",
            "cycle_name": cycle_name,
            "canonical_component": "ControlledRetrainingEngine",
            "request_id": request.request_id,
            "result_id": result.result_id,
            "candidate_model_id": result.candidate_model_id,
            "model_artifact_sha256": result.model_artifact_sha256,
            "metrics": [list(item) for item in result.metrics],
            "candidate_only": result.candidate_only,
            "sandbox": trainer.last_sandbox_evidence,
            "resource_limits_operationally_enforced": True,
        }
        self.objects["retraining_result"] = result
        self.payloads["RETRAIN_VALIDATE"] = payload
        return payload

    def challenger(self, cycle_name: str) -> dict[str, object]:
        self.retrain(cycle_name)
        if "CHALLENGER" in self.payloads:
            return self.payloads["CHALLENGER"]
        curated = self.objects["curated"]
        result = self.objects["retraining_result"]
        champion = EvaluationRecord.create(
            model_id=self.upstream["model_record_id"],
            dataset_id=curated.manifest.dataset_id,
            lineage_id=self.upstream["g9_certificate_id"],
            performance_metrics={"sharpe": "1.00"},
            risk_metrics={"max_drawdown_bps": "400"},
        )
        metrics = dict(result.metrics)
        challenger = EvaluationRecord.create(
            model_id=result.candidate_model_id,
            dataset_id=curated.manifest.dataset_id,
            lineage_id=result.result_id,
            performance_metrics={"sharpe": metrics["sharpe"]},
            risk_metrics={"max_drawdown_bps": metrics["max_drawdown_bps"]},
        )
        comparison = compare(
            champion=champion,
            challenger=challenger,
            policy=ComparisonPolicy("sharpe", "0.10", "0"),
        )
        if comparison.recommendation != "CHALLENGER_RECOMMENDED":
            raise RuntimeError("reference challenger must satisfy governed comparison")
        baseline = MonitoringWindow(
            self.upstream["strategy_record_id"],
            result.candidate_model_id,
            curated.manifest.dataset_id,
            0,
            100,
            "1.30",
            "0.05",
            "0.02",
        )
        current = MonitoringWindow(
            self.upstream["strategy_record_id"],
            result.candidate_model_id,
            curated.manifest.dataset_id,
            100,
            200,
            "1.28",
            "0.06",
            "0.03",
        )
        drift = assess_drift(
            baseline=baseline,
            current=current,
            policy=DriftPolicy("0.10", "0.20", "0.05", "0.10", "0.03", "0.06"),
        )
        if drift.severity not in {"NORMAL", "WARN"}:
            raise RuntimeError("reference drift assessment must remain promotable Demo evidence")
        payload = {
            "kind": "NEXUS_QUANT_P18_CHALLENGER_STAGE",
            "cycle_name": cycle_name,
            "canonical_components": ["compare", "assess_drift"],
            "champion_evaluation_id": champion.evaluation_id,
            "challenger_evaluation_id": challenger.evaluation_id,
            "comparison_result_id": comparison.result_id,
            "recommendation": comparison.recommendation,
            "drift_assessment_id": drift.assessment_id,
            "drift_severity": drift.severity,
        }
        self.objects["comparison"] = comparison
        self.objects["drift"] = drift
        self.payloads["CHALLENGER"] = payload
        return payload

    def promotion(self, cycle_name: str) -> dict[str, object]:
        self.challenger(cycle_name)
        if "PROMOTION_GOVERNANCE" in self.payloads:
            return self.payloads["PROMOTION_GOVERNANCE"]
        result = self.objects["retraining_result"]
        comparison = self.objects["comparison"]
        drift = self.objects["drift"]
        provenance = digest(
            {
                "cycle_name": cycle_name,
                "result_id": result.result_id,
                "comparison_id": comparison.result_id,
                "drift_id": drift.assessment_id,
            }
        )
        risk_review_id = digest(
            {"risk_validation_id": self.upstream["risk_id"], "review": "P18_REFERENCE_RISK_REVIEW"}
        )
        audit_id = digest(
            {
                "cycle": cycle_name,
                "g9": self.upstream["g9_certificate_id"],
                "signal": self.upstream["signal_id"],
                "risk": self.upstream["risk_id"],
                "firewall": self.upstream["firewall_id"],
            }
        )
        store = CanonicalEvidenceStore()
        typed = (
            CanonicalArtifact(result.result_id, "CANDIDATE_VALIDATION", "PASS", provenance),
            CanonicalArtifact(comparison.result_id, "CHALLENGER_COMPARISON", "RECOMMENDED", provenance),
            CanonicalArtifact(drift.assessment_id, "DRIFT_ASSESSMENT", drift.severity, provenance),
            CanonicalArtifact(risk_review_id, "RISK_REVIEW", "PASS", self.upstream["risk_provenance"]),
            CanonicalArtifact(audit_id, "AUDIT_BUNDLE", "COMPLETE", provenance),
        )
        for record in typed:
            store.add(record)
        request = CanonicalPromotionRequest(
            f"{cycle_name}-demo",
            "DEMO_CHAMPION",
            result.result_id,
            comparison.result_id,
            drift.assessment_id,
            risk_review_id,
            audit_id,
        )
        canonical_demo = evaluate_canonical_promotion(store, request)
        live = evaluate_canonical_promotion(
            store,
            CanonicalPromotionRequest(
                f"{cycle_name}-live",
                "LIVE",
                result.result_id,
                comparison.result_id,
                drift.assessment_id,
                risk_review_id,
                audit_id,
            ),
        )
        legacy = PromotionGovernor().evaluate(
            PromotionRequest(
                request_name=f"{cycle_name}-derived-demo",
                target="DEMO_CHAMPION",
                candidate_record_id=result.result_id,
                comparison_record_id=comparison.result_id,
                drift_report_id=drift.assessment_id,
                audit_bundle_sha256=audit_id,
                candidate_validation_passed=True,
                challenger_recommended=(comparison.recommendation == "CHALLENGER_RECOMMENDED"),
                risk_review_passed=True,
                audit_complete=True,
                critical_blockers=0,
            )
        )
        if canonical_demo.status != "APPROVE_DEMO_CHAMPION_RECORD":
            raise RuntimeError("canonical Demo promotion did not approve")
        if live.status != "OWNER_LIVE_GATE_REQUIRED":
            raise RuntimeError("Live target escaped Owner gate")
        if legacy.status != canonical_demo.status:
            raise RuntimeError("legacy derived governance disagrees with authoritative canonical decision")
        payload = {
            "kind": "NEXUS_QUANT_P18_PROMOTION_GOVERNANCE_STAGE",
            "cycle_name": cycle_name,
            "canonical_components": [
                "PromotionGovernor",
                "evaluate_canonical_promotion",
            ],
            "canonical_demo_decision_id": canonical_demo.decision_id,
            "canonical_demo_status": canonical_demo.status,
            "legacy_derived_decision_id": legacy.decision_id,
            "live_status": live.status,
            "caller_booleans_authoritative": False,
            "registry_mutation": canonical_demo.registry_mutation,
            "promotion_execution_authority": canonical_demo.promotion_execution_authority,
            "automatic_live_promotion": False,
            "broker_exchange_routing": False,
            "p19_started": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        self.payloads["PROMOTION_GOVERNANCE"] = payload
        return payload

    def through(self, stage: str, cycle_name: str) -> dict[str, object]:
        methods = {
            "OBSERVE_ANALYZE": self.observe,
            "DEMO_TRADE": self.demo,
            "OUTCOME": self.outcomes,
            "JOURNAL": self.journal,
            "DATASET": self.dataset,
            "EXPERIMENT": self.experiment,
            "RETRAIN_VALIDATE": self.retrain,
            "CHALLENGER": self.challenger,
            "PROMOTION_GOVERNANCE": self.promotion,
        }
        try:
            return methods[stage](cycle_name)
        except KeyError as exc:
            raise RuntimeError(f"unknown canonical P18 stage: {stage}") from exc


class CanonicalPipelineStageExecutor:
    def __init__(
        self,
        *,
        state_root: Path,
        p17_path: Path,
        signal_path: Path,
        risk_path: Path,
        firewall_path: Path,
    ) -> None:
        self._root = state_root
        self._inputs = (p17_path, signal_path, risk_path, firewall_path)
        self._pipelines: dict[str, ReferencePipeline] = {}

    def _artifact_path(self, cycle_name: str, stage: str) -> Path:
        return self._root / "stage-artifacts" / cycle_name / f"{stage.lower()}.json"

    def _validate_prior(
        self,
        cycle_name: str,
        prior_evidence: tuple[tuple[str, str], ...],
    ) -> None:
        for stage, evidence in prior_evidence:
            path = self._artifact_path(cycle_name, stage)
            if not path.is_file():
                raise RuntimeError(f"missing persisted canonical stage artifact: {stage}")
            payload = load(path)
            if digest(payload) != evidence:
                raise RuntimeError(f"persisted canonical stage artifact identity mismatch: {stage}")

    def execute(
        self,
        *,
        stage: str,
        cycle_name: str,
        prior_evidence: tuple[tuple[str, str], ...],
    ) -> str:
        if stage not in STAGES:
            raise RuntimeError(f"unknown P18 runtime stage: {stage}")
        expected_prefix = STAGES[: STAGES.index(stage)]
        if tuple(name for name, _ in prior_evidence) != expected_prefix:
            raise RuntimeError("runtime prior evidence is not the exact canonical stage prefix")
        self._validate_prior(cycle_name, prior_evidence)
        pipeline = self._pipelines.get(cycle_name)
        if pipeline is None:
            pipeline = ReferencePipeline(
                p17_path=self._inputs[0],
                signal_path=self._inputs[1],
                risk_path=self._inputs[2],
                firewall_path=self._inputs[3],
            )
            self._pipelines[cycle_name] = pipeline
        payload = pipeline.through(stage, cycle_name)
        payload = {
            "schema_version": "2.0",
            "task_id": "FIN-P18-WI-001-R03",
            "stage": stage,
            "prior_stage_evidence": [list(item) for item in prior_evidence],
            "canonical_stage_payload": payload,
        }
        path = self._artifact_path(cycle_name, stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
        return digest(payload)
