from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from packages.learning.loop_operations import LearningLoopPolicy
from packages.learning.runtime import (
    BundleStageExecutor,
    ConstantSystemStateSource,
    ContinuousDemoLearningRuntime,
    FixedLagWatermarkSource,
    IncrementingClock,
    JsonCheckpointStore,
    LearningRuntimeError,
    NoopEventSink,
    NoopSleeper,
)

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


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def bundle() -> dict[str, str]:
    return {stage: h("stage-" + stage) for stage in STAGES}


def runtime(path: Path, *, start: int = 1000, lag: int = 0, executor=None):
    return ContinuousDemoLearningRuntime(
        policy=LearningLoopPolicy(
            cadence_ns=1,
            max_market_staleness_ns=50,
            max_consecutive_failures=3,
        ),
        checkpoint_store=JsonCheckpointStore(path),
        stage_executor=executor or BundleStageExecutor(bundle()),
        watermark_source=FixedLagWatermarkSource(
            evidence_sha256=h("watermark"),
            lag_ns=lag,
        ),
        system_state_source=ConstantSystemStateSource("NORMAL"),
        clock=IncrementingClock(start, 100),
        sleeper=NoopSleeper(),
        telemetry=NoopEventSink(),
        alerts=NoopEventSink(),
        max_stage_retries=2,
        retry_backoff_ns=1,
    )


class FailingExecutor:
    def execute(self, *, stage: str, cycle_name: str, prior_evidence):
        del stage, cycle_name, prior_evidence
        raise RuntimeError("expected stage failure")


class LearningRuntimeTests(unittest.TestCase):
    def test_complete_reference_cycle_is_demo_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.json"
            report = runtime(path).run_cycle("cycle-1")
            self.assertEqual(report.status, "CYCLE_COMPLETE_DEMO_ONLY")
            self.assertEqual(report.stage_count, 9)
            self.assertEqual(report.completed_cycles, 1)
            self.assertFalse(report.automatic_live_promotion)
            self.assertFalse(report.broker_exchange_routing)
            self.assertEqual(report.live_trading, "DISABLED")
            self.assertEqual(report.auto_trading, "DISABLED")

    def test_restart_resumes_from_durable_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.json"
            first = runtime(path).run_cycle(
                "cycle-resume",
                max_stage_executions=3,
            )
            self.assertEqual(first.status, "PARTIAL_CHECKPOINTED")
            saved = JsonCheckpointStore(path).load()
            self.assertIsNotNone(saved)
            assert saved is not None
            self.assertEqual(len(saved.stage_evidence), 3)

            second = runtime(path, start=5000).run_cycle("cycle-resume")
            self.assertEqual(second.status, "CYCLE_COMPLETE_DEMO_ONLY")
            self.assertEqual(second.stage_count, 9)
            self.assertEqual(second.completed_cycles, 1)

    def test_stale_market_watermark_waits(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = runtime(
                Path(temp) / "checkpoint.json",
                lag=100,
            ).run_cycle("cycle-stale")
            self.assertEqual(report.status, "WAITING")
            self.assertEqual(report.action, "WAIT_FOR_FRESH_DATA")
            self.assertEqual(report.stage_count, 0)

    def test_repeated_stage_failure_enters_safe_hold(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = runtime(
                Path(temp) / "checkpoint.json",
                executor=FailingExecutor(),
            ).run_cycle("cycle-failure")
            self.assertEqual(report.status, "SAFE_HOLD")
            self.assertEqual(report.action, "SAFE_HOLD")
            self.assertEqual(report.stage_count, 0)

    def test_twenty_cycle_soak_has_no_state_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.json"
            reports = runtime(path).run_cycles(
                cycle_prefix="soak",
                count=20,
            )
            self.assertEqual(len(reports), 20)
            self.assertTrue(
                all(row.status == "CYCLE_COMPLETE_DEMO_ONLY" for row in reports)
            )
            self.assertEqual(reports[-1].completed_cycles, 20)
            checkpoint_ids = {row.checkpoint_id for row in reports}
            self.assertEqual(len(checkpoint_ids), 20)
            saved = JsonCheckpointStore(path).load()
            self.assertIsNotNone(saved)
            assert saved is not None
            self.assertEqual(saved.completed_cycles, 20)
            self.assertEqual(len(saved.stage_evidence), 9)

    def test_stage_bundle_rejects_missing_or_placeholder_evidence(self) -> None:
        bad = bundle()
        del bad["OUTCOME"]
        with self.assertRaises(LearningRuntimeError):
            BundleStageExecutor(bad)
        bad = bundle()
        bad["OUTCOME"] = "a" * 64
        with self.assertRaises(LearningRuntimeError):
            BundleStageExecutor(bad)


if __name__ == "__main__":
    unittest.main()
