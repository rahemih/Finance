from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from packages.learning.loop_operations import LearningLoopPolicy
from packages.learning.runtime import (
    ConstantSystemStateSource,
    ContinuousDemoLearningRuntime,
    FixedLagWatermarkSource,
    IncrementingClock,
    JsonCheckpointStore,
    NoopEventSink,
    NoopSleeper,
)
from scripts.runtime.p18_reference_pipeline import CanonicalPipelineStageExecutor


MODULES = [
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


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def inputs(root: Path) -> tuple[Path, Path, Path, Path]:
    p17 = write(
        root / "p17.json",
        {
            "kind": "NEXUS_QUANT_P17_CANONICAL_EMPIRICAL_PIPELINE_EVIDENCE",
            "fixture_only": False,
            "gate_state": "PASS_EMPIRICAL_REFERENCE",
            "canonical_modules_executed": MODULES,
            "strategy_record_id": h("strategy-record"),
            "model_record_id": h("model-record"),
            "dataset_sha256": h("market-dataset"),
            "gate_certificate_id": h("g9-certificate"),
        },
    )
    signal = write(
        root / "signal.json",
        {
            "kind": "NEXUS_QUANT_P14H_SIGNAL_OUTPUT_EVIDENCE",
            "signal_id": h("signal"),
            "signal": {},
        },
    )
    risk = write(
        root / "risk.json",
        {
            "kind": "NEXUS_QUANT_P15I_INDEPENDENT_RISK_VALIDATION_EVIDENCE",
            "marker": "P15_INDEPENDENT_RISK_VALIDATION",
            "fixture_only": True,
            "normal": {"validation_id": h("risk-validation"), "status": "PASS"},
            "execution_authority": False,
        },
    )
    firewall = write(
        root / "firewall.json",
        {
            "kind": "NEXUS_QUANT_P16H_G8_PRETRADE_SAFE_EVIDENCE",
            "fixture_only": True,
            "gate_name": "G8_PRETRADE_SAFE",
            "state": "PASS",
            "gate_id": h("firewall-gate"),
            "execution_authority": False,
        },
    )
    return p17, signal, risk, firewall


def runtime(root: Path, checkpoint: Path, *, start: int) -> ContinuousDemoLearningRuntime:
    p17, signal, risk, firewall = inputs(root)
    executor = CanonicalPipelineStageExecutor(
        state_root=root / "state",
        p17_path=p17,
        signal_path=signal,
        risk_path=risk,
        firewall_path=firewall,
    )
    return ContinuousDemoLearningRuntime(
        policy=LearningLoopPolicy(1, 1000, 3),
        checkpoint_store=JsonCheckpointStore(checkpoint),
        stage_executor=executor,
        watermark_source=FixedLagWatermarkSource(evidence_sha256=h("watermark"), lag_ns=0),
        system_state_source=ConstantSystemStateSource("NORMAL"),
        clock=IncrementingClock(start, 100),
        sleeper=NoopSleeper(),
        telemetry=NoopEventSink(),
        alerts=NoopEventSink(),
        max_stage_retries=1,
        retry_backoff_ns=0,
    )


class ReferencePipelineRuntimeTests(unittest.TestCase):
    def test_complete_cycle_executes_and_persists_all_canonical_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root / "checkpoint.json"
            report = runtime(root, checkpoint, start=1_000_000).run_cycle("canonical-cycle")
            self.assertEqual(report.status, "CYCLE_COMPLETE_DEMO_ONLY")
            self.assertEqual(report.stage_count, 9)
            stage_root = root / "state" / "stage-artifacts" / "canonical-cycle"
            artifacts = sorted(stage_root.glob("*.json"))
            self.assertEqual(len(artifacts), 9)
            promotion = json.loads((stage_root / "promotion_governance.json").read_text())
            payload = promotion["canonical_stage_payload"]
            self.assertEqual(payload["canonical_demo_status"], "APPROVE_DEMO_CHAMPION_RECORD")
            self.assertEqual(payload["live_status"], "OWNER_LIVE_GATE_REQUIRED")
            self.assertFalse(payload["caller_booleans_authoritative"])
            self.assertFalse(payload["p19_started"])

    def test_process_restart_revalidates_persisted_stage_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root / "checkpoint.json"
            first = runtime(root, checkpoint, start=1_000_000).run_cycle(
                "resume-cycle",
                max_stage_executions=5,
            )
            self.assertEqual(first.status, "PARTIAL_CHECKPOINTED")
            second = runtime(root, checkpoint, start=2_000_000).run_cycle("resume-cycle")
            self.assertEqual(second.status, "CYCLE_COMPLETE_DEMO_ONLY")
            self.assertEqual(second.stage_count, 9)
            self.assertEqual(second.completed_cycles, 1)


if __name__ == "__main__":
    unittest.main()
