from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re


class LearningLoopOperationsError(ValueError):
    """P18-I deterministic 24/7 learning-loop invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
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
_ACTIONS = (
    "RUN_OBSERVE_ANALYZE",
    "RUN_DEMO_TRADE",
    "CAPTURE_OUTCOME",
    "APPEND_JOURNAL",
    "CURATE_DATASET",
    "TRACK_EXPERIMENT",
    "RUN_CONTROLLED_RETRAINING",
    "EVALUATE_CHALLENGER",
    "EVALUATE_PROMOTION_GOVERNANCE",
)
_SYSTEM_STATES = {"NORMAL", "DEGRADED", "SAFE_MODE", "HALTED", "EMERGENCY"}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe_id(value: str, *, field: str) -> str:
    parsed=value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise LearningLoopOperationsError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed=value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise LearningLoopOperationsError(f"{field} must be lowercase SHA-256")
    return parsed


@dataclass(frozen=True, slots=True)
class LearningLoopPolicy:
    cadence_ns: int
    max_market_staleness_ns: int
    max_consecutive_failures: int

    def __post_init__(self) -> None:
        if min(self.cadence_ns, self.max_market_staleness_ns, self.max_consecutive_failures) <= 0:
            raise LearningLoopOperationsError("loop policy values must be positive")


@dataclass(frozen=True, slots=True)
class LoopTick:
    cycle_name: str
    tick_time_ns: int
    market_watermark_ns: int
    system_state: str
    consecutive_failures: int
    stage_evidence: tuple[tuple[str, str], ...]
    previous_checkpoint_id: str | None = None

    def __post_init__(self) -> None:
        _safe_id(self.cycle_name, field="cycle_name")
        if self.tick_time_ns < 0 or self.market_watermark_ns < 0:
            raise LearningLoopOperationsError("tick timestamps must be non-negative")
        if self.market_watermark_ns > self.tick_time_ns:
            raise LearningLoopOperationsError("market watermark cannot be in the future")
        if self.system_state not in _SYSTEM_STATES:
            raise LearningLoopOperationsError("invalid system state")
        if self.consecutive_failures < 0:
            raise LearningLoopOperationsError("consecutive_failures must be non-negative")
        if self.previous_checkpoint_id is not None:
            _sha(self.previous_checkpoint_id, field="previous_checkpoint_id")
        if len(self.stage_evidence) > len(_STAGES):
            raise LearningLoopOperationsError("too many stage evidence records")
        for index, (stage, evidence_id) in enumerate(self.stage_evidence):
            if stage != _STAGES[index]:
                raise LearningLoopOperationsError("stage evidence must be an exact ordered prefix")
            _sha(evidence_id, field=f"stage_evidence.{stage}")


@dataclass(frozen=True, slots=True)
class LoopCheckpoint:
    cycle_name: str
    tick_time_ns: int
    stage_count: int
    action: str
    status: str
    next_due_ns: int
    stage_evidence: tuple[tuple[str, str], ...]
    previous_checkpoint_id: str | None
    automated_controlled_retraining: bool = True
    automatic_live_promotion: bool = False
    broker_exchange_routing: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @property
    def checkpoint_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "schema_version":"1.0","cycle_name":self.cycle_name,
            "tick_time_ns":self.tick_time_ns,"stage_count":self.stage_count,
            "action":self.action,"status":self.status,"next_due_ns":self.next_due_ns,
            "stage_evidence":[list(item) for item in self.stage_evidence],
            "previous_checkpoint_id":self.previous_checkpoint_id,
            "automated_controlled_retraining":self.automated_controlled_retraining,
            "automatic_live_promotion":self.automatic_live_promotion,
            "broker_exchange_routing":self.broker_exchange_routing,
            "live_trading":self.live_trading,"auto_trading":self.auto_trading,
        })).hexdigest()


class LearningLoopCoordinator:
    def __init__(self, policy: LearningLoopPolicy, checkpoint: LoopCheckpoint | None = None) -> None:
        self._policy=policy
        self._checkpoint=checkpoint

    @property
    def checkpoint(self) -> LoopCheckpoint | None:
        return self._checkpoint

    def evaluate(self, tick: LoopTick) -> LoopCheckpoint:
        prior=self._checkpoint
        if prior is not None:
            if tick.previous_checkpoint_id != prior.checkpoint_id:
                raise LearningLoopOperationsError("checkpoint chain mismatch")
            if tick.tick_time_ns < prior.tick_time_ns:
                raise LearningLoopOperationsError("tick time cannot move backwards")
            if tick.cycle_name == prior.cycle_name:
                if len(tick.stage_evidence) < prior.stage_count:
                    raise LearningLoopOperationsError("cycle stage progress cannot regress")
                if len(tick.stage_evidence) > prior.stage_count + 1:
                    raise LearningLoopOperationsError("cycle may advance at most one stage per tick")
            else:
                if prior.status != "CYCLE_COMPLETE_DEMO_ONLY":
                    raise LearningLoopOperationsError("new cycle requires prior completed cycle")
                if tick.tick_time_ns < prior.next_due_ns:
                    checkpoint=self._build(tick, action="WAIT_FOR_CADENCE", status="WAITING", next_due_ns=prior.next_due_ns)
                    self._checkpoint=checkpoint
                    return checkpoint
                if tick.stage_evidence:
                    raise LearningLoopOperationsError("new cycle must begin with empty stage evidence")

        if tick.system_state in {"HALTED", "EMERGENCY"}:
            checkpoint=self._build(tick, action="HALT_SAFE", status="HALTED", next_due_ns=tick.tick_time_ns+self._policy.cadence_ns)
        elif tick.system_state == "SAFE_MODE":
            checkpoint=self._build(tick, action="SAFE_HOLD", status="SAFE_HOLD", next_due_ns=tick.tick_time_ns+self._policy.cadence_ns)
        elif tick.consecutive_failures >= self._policy.max_consecutive_failures:
            checkpoint=self._build(tick, action="SAFE_HOLD", status="SAFE_HOLD", next_due_ns=tick.tick_time_ns+self._policy.cadence_ns)
        elif tick.tick_time_ns - tick.market_watermark_ns > self._policy.max_market_staleness_ns:
            checkpoint=self._build(tick, action="WAIT_FOR_FRESH_DATA", status="WAITING", next_due_ns=tick.tick_time_ns+self._policy.cadence_ns)
        elif len(tick.stage_evidence) == len(_STAGES):
            checkpoint=self._build(tick, action="CYCLE_COMPLETE_DEMO_ONLY", status="CYCLE_COMPLETE_DEMO_ONLY", next_due_ns=tick.tick_time_ns+self._policy.cadence_ns)
        else:
            checkpoint=self._build(tick, action=_ACTIONS[len(tick.stage_evidence)], status="READY", next_due_ns=tick.tick_time_ns)
        self._checkpoint=checkpoint
        return checkpoint

    def _build(self, tick: LoopTick, *, action: str, status: str, next_due_ns: int) -> LoopCheckpoint:
        return LoopCheckpoint(
            cycle_name=tick.cycle_name,
            tick_time_ns=tick.tick_time_ns,
            stage_count=len(tick.stage_evidence),
            action=action,
            status=status,
            next_due_ns=next_due_ns,
            stage_evidence=tick.stage_evidence,
            previous_checkpoint_id=tick.previous_checkpoint_id,
        )
