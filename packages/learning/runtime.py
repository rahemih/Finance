from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Mapping, Protocol, cast

from packages.learning.loop_operations import (
    LearningLoopCoordinator,
    LearningLoopPolicy,
    LoopCheckpoint,
    LoopTick,
)

_STAGES = (
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
_ACTION_TO_STAGE = {
    "RUN_OBSERVE_ANALYZE": "OBSERVE_ANALYZE",
    "RUN_DEMO_TRADE": "DEMO_TRADE",
    "CAPTURE_OUTCOME": "OUTCOME",
    "APPEND_JOURNAL": "JOURNAL",
    "CURATE_DATASET": "DATASET",
    "TRACK_EXPERIMENT": "EXPERIMENT",
    "RUN_CONTROLLED_RETRAINING": "RETRAIN_VALIDATE",
    "EVALUATE_CHALLENGER": "CHALLENGER",
    "EVALUATE_PROMOTION_GOVERNANCE": "PROMOTION_GOVERNANCE",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class LearningRuntimeError(RuntimeError):
    """P18-I operational runtime invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise LearningRuntimeError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise LearningRuntimeError(f"{field} is a degenerate placeholder identity")
    return parsed


def _as_mapping(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise LearningRuntimeError(f"{field} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise LearningRuntimeError(f"{field} keys must be strings")
    return cast(dict[str, object], value)


def _as_str(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise LearningRuntimeError(f"{field} must be a string")
    return value


def _as_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LearningRuntimeError(f"{field} must be an integer")
    return value


class Clock(Protocol):
    def now_ns(self) -> int: ...


class Sleeper(Protocol):
    def sleep_ns(self, duration_ns: int) -> None: ...


class StageExecutor(Protocol):
    def execute(
        self,
        *,
        stage: str,
        cycle_name: str,
        prior_evidence: tuple[tuple[str, str], ...],
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class WatermarkSample:
    watermark_ns: int
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.watermark_ns < 0:
            raise LearningRuntimeError("watermark_ns must be non-negative")
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha(self.evidence_sha256, field="watermark.evidence_sha256"),
        )


class MarketWatermarkSource(Protocol):
    def sample(self, now_ns: int) -> WatermarkSample: ...


class SystemStateSource(Protocol):
    def current_state(self) -> str: ...


class EventSink(Protocol):
    def emit(self, kind: str, payload: Mapping[str, object]) -> None: ...


class SystemClock:
    def now_ns(self) -> int:
        return time.time_ns()


class IncrementingClock:
    def __init__(self, start_ns: int, step_ns: int = 100) -> None:
        if start_ns < 0 or step_ns <= 0:
            raise LearningRuntimeError("invalid deterministic clock")
        self._next = start_ns
        self._step = step_ns

    def now_ns(self) -> int:
        value = self._next
        self._next += self._step
        return value


class SystemSleeper:
    def sleep_ns(self, duration_ns: int) -> None:
        if duration_ns < 0:
            raise LearningRuntimeError("sleep duration cannot be negative")
        time.sleep(duration_ns / 1_000_000_000)


class NoopSleeper:
    def sleep_ns(self, duration_ns: int) -> None:
        if duration_ns < 0:
            raise LearningRuntimeError("sleep duration cannot be negative")


class NoopEventSink:
    def emit(self, kind: str, payload: Mapping[str, object]) -> None:
        del kind, payload


class JsonlEventSink:
    def __init__(self, path: Path) -> None:
        self._path = path

    def emit(self, kind: str, payload: Mapping[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        row = {"kind": kind, "payload": dict(payload)}
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            )


class ConstantSystemStateSource:
    def __init__(self, state: str = "NORMAL") -> None:
        self._state = state

    def current_state(self) -> str:
        return self._state


class FixedLagWatermarkSource:
    def __init__(
        self,
        *,
        evidence_sha256: str,
        lag_ns: int = 0,
    ) -> None:
        self._evidence = _sha(evidence_sha256, field="watermark_source.evidence")
        if lag_ns < 0:
            raise LearningRuntimeError("watermark lag cannot be negative")
        self._lag = lag_ns

    def sample(self, now_ns: int) -> WatermarkSample:
        if now_ns < self._lag:
            return WatermarkSample(0, self._evidence)
        return WatermarkSample(now_ns - self._lag, self._evidence)


class BundleStageExecutor:
    def __init__(self, stage_evidence: Mapping[str, str]) -> None:
        if set(stage_evidence) != set(_STAGES):
            raise LearningRuntimeError("stage bundle must contain exact P18-I stages")
        self._evidence = {
            stage: _sha(value, field=f"stage_bundle.{stage}")
            for stage, value in stage_evidence.items()
        }

    def execute(
        self,
        *,
        stage: str,
        cycle_name: str,
        prior_evidence: tuple[tuple[str, str], ...],
    ) -> str:
        try:
            base_evidence = self._evidence[stage]
        except KeyError as exc:
            raise LearningRuntimeError(f"unknown runtime stage: {stage}") from exc
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "schema_version": "1.0",
                    "stage": stage,
                    "base_evidence_sha256": base_evidence,
                    "cycle_name": cycle_name,
                    "prior_stage_evidence": [list(item) for item in prior_evidence],
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class RuntimeState:
    cycle_name: str
    stage_evidence: tuple[tuple[str, str], ...]
    checkpoint: LoopCheckpoint | None
    completed_cycles: int
    consecutive_failures: int

    def __post_init__(self) -> None:
        if not self.cycle_name.strip():
            raise LearningRuntimeError("cycle_name must be non-empty")
        if self.completed_cycles < 0 or self.consecutive_failures < 0:
            raise LearningRuntimeError("runtime counters cannot be negative")
        for index, (stage, evidence) in enumerate(self.stage_evidence):
            if index >= len(_STAGES) or stage != _STAGES[index]:
                raise LearningRuntimeError("runtime stage evidence must be an exact prefix")
            _sha(evidence, field=f"runtime_state.{stage}")

    def payload(self) -> dict[str, object]:
        checkpoint: dict[str, object] | None = None
        if self.checkpoint is not None:
            checkpoint = {
                "cycle_name": self.checkpoint.cycle_name,
                "tick_time_ns": self.checkpoint.tick_time_ns,
                "stage_count": self.checkpoint.stage_count,
                "action": self.checkpoint.action,
                "status": self.checkpoint.status,
                "next_due_ns": self.checkpoint.next_due_ns,
                "stage_evidence": [list(item) for item in self.checkpoint.stage_evidence],
                "previous_checkpoint_id": self.checkpoint.previous_checkpoint_id,
            }
        return {
            "schema_version": "1.0",
            "cycle_name": self.cycle_name,
            "stage_evidence": [list(item) for item in self.stage_evidence],
            "checkpoint": checkpoint,
            "completed_cycles": self.completed_cycles,
            "consecutive_failures": self.consecutive_failures,
        }

    @property
    def state_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "RuntimeState":
        cycle_name = _as_str(payload.get("cycle_name"), field="cycle_name")
        completed_cycles = _as_int(
            payload.get("completed_cycles"),
            field="completed_cycles",
        )
        consecutive_failures = _as_int(
            payload.get("consecutive_failures"),
            field="consecutive_failures",
        )
        evidence_raw = payload.get("stage_evidence")
        if not isinstance(evidence_raw, list):
            raise LearningRuntimeError("stage_evidence must be an array")
        evidence: list[tuple[str, str]] = []
        for index, raw in enumerate(cast(list[object], evidence_raw)):
            if not isinstance(raw, list) or len(raw) != 2:
                raise LearningRuntimeError(
                    f"stage_evidence[{index}] must be a pair"
                )
            pair = cast(list[object], raw)
            evidence.append(
                (
                    _as_str(pair[0], field=f"stage_evidence[{index}].stage"),
                    _as_str(pair[1], field=f"stage_evidence[{index}].evidence"),
                )
            )

        checkpoint_raw = payload.get("checkpoint")
        checkpoint: LoopCheckpoint | None = None
        if checkpoint_raw is not None:
            row = _as_mapping(checkpoint_raw, field="checkpoint")
            cp_evidence_raw = row.get("stage_evidence")
            if not isinstance(cp_evidence_raw, list):
                raise LearningRuntimeError("checkpoint.stage_evidence must be an array")
            cp_evidence: list[tuple[str, str]] = []
            for index, raw in enumerate(cast(list[object], cp_evidence_raw)):
                if not isinstance(raw, list) or len(raw) != 2:
                    raise LearningRuntimeError("invalid checkpoint stage evidence")
                pair = cast(list[object], raw)
                cp_evidence.append(
                    (
                        _as_str(pair[0], field=f"checkpoint.stage[{index}]"),
                        _as_str(pair[1], field=f"checkpoint.evidence[{index}]"),
                    )
                )
            previous = row.get("previous_checkpoint_id")
            previous_id: str | None
            if previous is None:
                previous_id = None
            else:
                previous_id = _as_str(previous, field="previous_checkpoint_id")
            checkpoint = LoopCheckpoint(
                cycle_name=_as_str(row.get("cycle_name"), field="checkpoint.cycle_name"),
                tick_time_ns=_as_int(row.get("tick_time_ns"), field="checkpoint.tick_time_ns"),
                stage_count=_as_int(row.get("stage_count"), field="checkpoint.stage_count"),
                action=_as_str(row.get("action"), field="checkpoint.action"),
                status=_as_str(row.get("status"), field="checkpoint.status"),
                next_due_ns=_as_int(row.get("next_due_ns"), field="checkpoint.next_due_ns"),
                stage_evidence=tuple(cp_evidence),
                previous_checkpoint_id=previous_id,
            )
        return cls(
            cycle_name=cycle_name,
            stage_evidence=tuple(evidence),
            checkpoint=checkpoint,
            completed_cycles=completed_cycles,
            consecutive_failures=consecutive_failures,
        )


class JsonCheckpointStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> RuntimeState | None:
        if not self._path.exists():
            return None
        raw = cast(object, json.loads(self._path.read_text(encoding="utf-8")))
        payload = _as_mapping(raw, field="checkpoint_store")
        return RuntimeState.from_payload(payload)

    def save(self, state: RuntimeState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(state.payload(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self._path)


@dataclass(frozen=True, slots=True)
class RuntimeReport:
    cycle_name: str
    status: str
    action: str
    completed_cycles: int
    stage_count: int
    checkpoint_id: str
    runtime_state_id: str
    automatic_live_promotion: bool = False
    broker_exchange_routing: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "cycle_name": self.cycle_name,
            "status": self.status,
            "action": self.action,
            "completed_cycles": self.completed_cycles,
            "stage_count": self.stage_count,
            "checkpoint_id": self.checkpoint_id,
            "runtime_state_id": self.runtime_state_id,
            "automatic_live_promotion": self.automatic_live_promotion,
            "broker_exchange_routing": self.broker_exchange_routing,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }


class ContinuousDemoLearningRuntime:
    def __init__(
        self,
        *,
        policy: LearningLoopPolicy,
        checkpoint_store: JsonCheckpointStore,
        stage_executor: StageExecutor,
        watermark_source: MarketWatermarkSource,
        system_state_source: SystemStateSource,
        clock: Clock,
        sleeper: Sleeper,
        telemetry: EventSink,
        alerts: EventSink,
        max_stage_retries: int,
        retry_backoff_ns: int,
    ) -> None:
        if max_stage_retries < 0 or retry_backoff_ns < 0:
            raise LearningRuntimeError("runtime retry settings cannot be negative")
        self._policy = policy
        self._store = checkpoint_store
        self._executor = stage_executor
        self._watermark = watermark_source
        self._system_state = system_state_source
        self._clock = clock
        self._sleeper = sleeper
        self._telemetry = telemetry
        self._alerts = alerts
        self._max_stage_retries = max_stage_retries
        self._retry_backoff_ns = retry_backoff_ns

    def _initial_state(self, cycle_name: str) -> RuntimeState:
        loaded = self._store.load()
        if loaded is None:
            return RuntimeState(cycle_name, (), None, 0, 0)
        if loaded.cycle_name == cycle_name:
            return loaded
        if loaded.checkpoint is None or loaded.checkpoint.status != "CYCLE_COMPLETE_DEMO_ONLY":
            raise LearningRuntimeError("cannot start a new cycle before prior cycle completes")
        return RuntimeState(
            cycle_name=cycle_name,
            stage_evidence=(),
            checkpoint=loaded.checkpoint,
            completed_cycles=loaded.completed_cycles,
            consecutive_failures=0,
        )

    def _report(self, state: RuntimeState, checkpoint: LoopCheckpoint) -> RuntimeReport:
        return RuntimeReport(
            cycle_name=state.cycle_name,
            status=checkpoint.status,
            action=checkpoint.action,
            completed_cycles=state.completed_cycles,
            stage_count=len(state.stage_evidence),
            checkpoint_id=checkpoint.checkpoint_id,
            runtime_state_id=state.state_id,
        )

    def run_cycle(
        self,
        cycle_name: str,
        *,
        max_stage_executions: int | None = None,
    ) -> RuntimeReport:
        if max_stage_executions is not None and max_stage_executions < 0:
            raise LearningRuntimeError("max_stage_executions cannot be negative")
        state = self._initial_state(cycle_name)
        coordinator = LearningLoopCoordinator(self._policy, state.checkpoint)
        executed = 0

        while True:
            now = self._clock.now_ns()
            watermark = self._watermark.sample(now)
            prior = coordinator.checkpoint
            previous_id = prior.checkpoint_id if prior is not None else None
            tick = LoopTick(
                cycle_name=cycle_name,
                tick_time_ns=now,
                market_watermark_ns=watermark.watermark_ns,
                system_state=self._system_state.current_state(),
                consecutive_failures=state.consecutive_failures,
                stage_evidence=state.stage_evidence,
                previous_checkpoint_id=previous_id,
            )
            checkpoint = coordinator.evaluate(tick)
            self._telemetry.emit(
                "checkpoint",
                {
                    "cycle_name": cycle_name,
                    "action": checkpoint.action,
                    "status": checkpoint.status,
                    "stage_count": checkpoint.stage_count,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "watermark_evidence_sha256": watermark.evidence_sha256,
                },
            )

            stage = _ACTION_TO_STAGE.get(checkpoint.action)
            if stage is not None:
                if (
                    max_stage_executions is not None
                    and executed >= max_stage_executions
                ):
                    state = RuntimeState(
                        cycle_name,
                        state.stage_evidence,
                        checkpoint,
                        state.completed_cycles,
                        state.consecutive_failures,
                    )
                    self._store.save(state)
                    return RuntimeReport(
                        cycle_name=cycle_name,
                        status="PARTIAL_CHECKPOINTED",
                        action=checkpoint.action,
                        completed_cycles=state.completed_cycles,
                        stage_count=len(state.stage_evidence),
                        checkpoint_id=checkpoint.checkpoint_id,
                        runtime_state_id=state.state_id,
                    )

                attempt = 0
                while True:
                    try:
                        evidence = _sha(
                            self._executor.execute(
                                stage=stage,
                                cycle_name=cycle_name,
                                prior_evidence=state.stage_evidence,
                            ),
                            field=f"stage_executor.{stage}",
                        )
                        state = RuntimeState(
                            cycle_name,
                            state.stage_evidence + ((stage, evidence),),
                            checkpoint,
                            state.completed_cycles,
                            0,
                        )
                        self._store.save(state)
                        executed += 1
                        break
                    except Exception as exc:
                        attempt += 1
                        failures = state.consecutive_failures + 1
                        self._telemetry.emit(
                            "stage_failure",
                            {
                                "cycle_name": cycle_name,
                                "stage": stage,
                                "attempt": attempt,
                                "consecutive_failures": failures,
                                "error_type": type(exc).__name__,
                            },
                        )
                        if (
                            attempt > self._max_stage_retries
                            or failures >= self._policy.max_consecutive_failures
                        ):
                            hold_now = self._clock.now_ns()
                            hold_watermark = self._watermark.sample(hold_now)
                            hold_tick = LoopTick(
                                cycle_name=cycle_name,
                                tick_time_ns=hold_now,
                                market_watermark_ns=hold_watermark.watermark_ns,
                                system_state=self._system_state.current_state(),
                                consecutive_failures=self._policy.max_consecutive_failures,
                                stage_evidence=state.stage_evidence,
                                previous_checkpoint_id=checkpoint.checkpoint_id,
                            )
                            hold = coordinator.evaluate(hold_tick)
                            state = RuntimeState(
                                cycle_name,
                                state.stage_evidence,
                                hold,
                                state.completed_cycles,
                                self._policy.max_consecutive_failures,
                            )
                            self._store.save(state)
                            self._alerts.emit(
                                "safe_hold",
                                {
                                    "cycle_name": cycle_name,
                                    "stage": stage,
                                    "checkpoint_id": hold.checkpoint_id,
                                    "error_type": type(exc).__name__,
                                },
                            )
                            return self._report(state, hold)
                        state = RuntimeState(
                            cycle_name,
                            state.stage_evidence,
                            checkpoint,
                            state.completed_cycles,
                            failures,
                        )
                        self._store.save(state)
                        self._sleeper.sleep_ns(
                            self._retry_backoff_ns * attempt
                        )
                continue

            completed = state.completed_cycles
            if checkpoint.status == "CYCLE_COMPLETE_DEMO_ONLY":
                completed += 1
            state = RuntimeState(
                cycle_name,
                state.stage_evidence,
                checkpoint,
                completed,
                state.consecutive_failures,
            )
            self._store.save(state)
            return self._report(state, checkpoint)

    def run_cycles(self, *, cycle_prefix: str, count: int) -> tuple[RuntimeReport, ...]:
        if count <= 0:
            raise LearningRuntimeError("cycle count must be positive")
        loaded = self._store.load()
        start = loaded.completed_cycles if loaded is not None else 0
        reports: list[RuntimeReport] = []
        for offset in range(count):
            cycle_name = f"{cycle_prefix}-{start + offset + 1:06d}"
            report = self.run_cycle(cycle_name)
            reports.append(report)
            if report.status != "CYCLE_COMPLETE_DEMO_ONLY":
                break
        return tuple(reports)
