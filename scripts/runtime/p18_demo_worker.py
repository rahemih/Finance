#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.learning.loop_operations import LearningLoopPolicy
from packages.learning.runtime import (
    BundleStageExecutor,
    ConstantSystemStateSource,
    ContinuousDemoLearningRuntime,
    FixedLagWatermarkSource,
    IncrementingClock,
    JsonCheckpointStore,
    JsonlEventSink,
    NoopSleeper,
    SystemClock,
    SystemSleeper,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/learning/runtime-worker-policy.json"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--alerts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--deterministic-start-ns", type=int)
    args = parser.parse_args()

    policy_data = load(POLICY_PATH)
    bundle = load(args.bundle)
    stage_evidence = bundle.get("stage_evidence")
    if not isinstance(stage_evidence, dict):
        raise RuntimeError("stage_evidence object required")
    stage_map = {str(key): str(value) for key, value in stage_evidence.items()}
    source_bundle_sha = str(bundle["source_bundle_sha256"])

    if args.deterministic_start_ns is None:
        clock = SystemClock()
        sleeper = SystemSleeper()
    else:
        clock = IncrementingClock(args.deterministic_start_ns, 100)
        sleeper = NoopSleeper()

    runtime = ContinuousDemoLearningRuntime(
        policy=LearningLoopPolicy(
            cadence_ns=int(policy_data["cadence_ns"]),
            max_market_staleness_ns=int(policy_data["max_market_staleness_ns"]),
            max_consecutive_failures=int(policy_data["max_consecutive_failures"]),
        ),
        checkpoint_store=JsonCheckpointStore(args.checkpoint),
        stage_executor=BundleStageExecutor(stage_map),
        watermark_source=FixedLagWatermarkSource(
            evidence_sha256=source_bundle_sha,
            lag_ns=0,
        ),
        system_state_source=ConstantSystemStateSource("NORMAL"),
        clock=clock,
        sleeper=sleeper,
        telemetry=JsonlEventSink(args.telemetry),
        alerts=JsonlEventSink(args.alerts),
        max_stage_retries=int(policy_data["max_stage_retries"]),
        retry_backoff_ns=int(policy_data["retry_backoff_ns"]),
    )
    reports = runtime.run_cycles(cycle_prefix="p18-reference", count=args.cycles)
    if len(reports) != args.cycles:
        raise RuntimeError("runtime stopped before requested cycle count")
    if any(row.status != "CYCLE_COMPLETE_DEMO_ONLY" for row in reports):
        raise RuntimeError("runtime cycle did not close DEMO_ONLY")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18_OPERATIONAL_RUNTIME_EVIDENCE",
        "task_id": "FIN-P18-WI-001-R01",
        "runtime_mode": policy_data["mode"],
        "source_bundle_sha256": source_bundle_sha,
        "requested_cycles": args.cycles,
        "completed_cycles": reports[-1].completed_cycles,
        "reports": [row.payload() for row in reports],
        "checkpoint_persisted": args.checkpoint.exists(),
        "telemetry_persisted": args.telemetry.exists(),
        "automatic_live_promotion": False,
        "broker_exchange_routing": False,
        "p19_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"P18_OPERATIONAL_RUNTIME=PASS cycles={args.cycles} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
