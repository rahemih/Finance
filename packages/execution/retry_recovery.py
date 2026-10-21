from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast


class RetryRecoveryError(ValueError):
    """P20-F deterministic retry / timeout / crash-recovery invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RetryRecoveryError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RetryRecoveryError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RetryRecoveryError(f"{field} must be a non-negative integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise RetryRecoveryError(f"{field} must be a sha256 hex digest")
    return text


def _tuple_text(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RetryRecoveryError(f"{field} must be a non-empty list")
    items = cast(list[object], value)
    parsed = tuple(_text(x, field=field) for x in items)
    if len(set(parsed)) != len(parsed):
        raise RetryRecoveryError(f"{field} cannot contain duplicates")
    return parsed


def _tuple_int(value: object, *, field: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise RetryRecoveryError(f"{field} must be a non-empty list")
    items = cast(list[object], value)
    parsed = tuple(_positive_int(x, field=field) for x in items)
    return parsed


@dataclass(frozen=True, slots=True)
class RetryRecoveryPolicy:
    markets: tuple[str, ...]
    operations: tuple[str, ...]
    retryable_conditions: tuple[str, ...]
    safe_hold_conditions: tuple[str, ...]
    terminal_conditions: tuple[str, ...]
    max_attempts: int
    backoff_ms: tuple[int, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "RetryRecoveryPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RetryRecoveryError(f"invalid P20-F policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise RetryRecoveryError("P20-F policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20F_RETRY_RECOVERY_POLICY",
            "task_id": "FIN-P20-WF-001",
            "mode": "DETERMINISTIC_FAIL_CLOSED_RETRY_RECOVERY",
            "reconciliation_owner": "P20-G",
            "execution_quality_owner": "P20-H",
            "simulation_gate_owner": "P20-I",
            "position_management_owner": "P21",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "actual_retry_dispatch": False,
            "reconciliation_authority": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise RetryRecoveryError(f"P20-F policy mismatch: {key}")
        markets = _tuple_text(raw.get("markets"), field="markets")
        operations = _tuple_text(raw.get("operations"), field="operations")
        retryable = _tuple_text(raw.get("retryable_conditions"), field="retryable_conditions")
        safe_hold = _tuple_text(raw.get("safe_hold_conditions"), field="safe_hold_conditions")
        terminal = _tuple_text(raw.get("terminal_conditions"), field="terminal_conditions")
        max_attempts = _positive_int(raw.get("max_attempts"), field="max_attempts")
        backoff = _tuple_int(raw.get("backoff_ms"), field="backoff_ms")
        if markets != ("CRYPTO", "FOREX"):
            raise RetryRecoveryError("invalid P20-F market taxonomy")
        if operations != ("ORDER_SUBMIT", "ORDER_CANCEL"):
            raise RetryRecoveryError("invalid P20-F operation taxonomy")
        if retryable != ("PRE_DISPATCH_TIMEOUT", "PRE_DISPATCH_FAILURE", "PROCESS_CRASH_BEFORE_DISPATCH"):
            raise RetryRecoveryError("invalid retryable condition taxonomy")
        if safe_hold != ("DISPATCH_OUTCOME_UNKNOWN", "PROCESS_CRASH_AFTER_DISPATCH"):
            raise RetryRecoveryError("invalid safe-hold condition taxonomy")
        if terminal != ("ACKNOWLEDGED", "REJECTED", "CANCEL_ACKNOWLEDGED"):
            raise RetryRecoveryError("invalid terminal condition taxonomy")
        if len(backoff) != max_attempts:
            raise RetryRecoveryError("backoff schedule length must equal max_attempts")
        return cls(markets, operations, retryable, safe_hold, terminal, max_attempts, backoff, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        payload: dict[str, object] = {
            "markets": list(self.markets), "operations": list(self.operations),
            "retryable_conditions": list(self.retryable_conditions),
            "safe_hold_conditions": list(self.safe_hold_conditions),
            "terminal_conditions": list(self.terminal_conditions),
            "max_attempts": self.max_attempts, "backoff_ms": list(self.backoff_ms),
            "reconciliation_owner": "P20-G", "network_mode": "DISABLED",
            "actual_retry_dispatch": False, "live_execution_authority": False,
            "live_trading": self.live_trading, "auto_trading": self.auto_trading,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class RecoveryCheckpoint:
    market: str
    operation: str
    order_id: str
    client_order_id: str
    idempotency_key: str
    idempotency_claim_id: str
    request_id: str
    oms_record_id: str
    attempt: int
    stage: str
    observed_at_ns: int
    previous_checkpoint_id: str | None = None

    def validate(self, policy: RetryRecoveryPolicy) -> None:
        if self.market not in policy.markets:
            raise RetryRecoveryError("checkpoint market is outside P20-F policy")
        if self.operation not in policy.operations:
            raise RetryRecoveryError("checkpoint operation is outside P20-F policy")
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        _text(self.idempotency_key, field="idempotency_key")
        _sha256_hex(self.idempotency_claim_id, field="idempotency_claim_id")
        _sha256_hex(self.request_id, field="request_id")
        _sha256_hex(self.oms_record_id, field="oms_record_id")
        _positive_int(self.attempt, field="attempt")
        if self.attempt > policy.max_attempts:
            raise RetryRecoveryError("checkpoint attempt exceeds retry budget")
        if self.stage not in ("PRE_DISPATCH", "POST_DISPATCH", "TERMINAL"):
            raise RetryRecoveryError("unsupported recovery stage")
        _non_negative_int(self.observed_at_ns, field="observed_at_ns")
        if self.previous_checkpoint_id is not None:
            _sha256_hex(self.previous_checkpoint_id, field="previous_checkpoint_id")

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market, "operation": self.operation, "order_id": self.order_id,
            "client_order_id": self.client_order_id, "idempotency_key": self.idempotency_key,
            "idempotency_claim_id": self.idempotency_claim_id, "request_id": self.request_id,
            "oms_record_id": self.oms_record_id, "attempt": self.attempt, "stage": self.stage,
            "observed_at_ns": self.observed_at_ns, "previous_checkpoint_id": self.previous_checkpoint_id,
        }

    @property
    def checkpoint_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class RecoverySignal:
    condition: str
    observed_at_ns: int

    def validate(self, policy: RetryRecoveryPolicy) -> None:
        all_conditions = policy.retryable_conditions + policy.safe_hold_conditions + policy.terminal_conditions
        if self.condition not in all_conditions:
            raise RetryRecoveryError("unsupported P20-F recovery condition")
        _non_negative_int(self.observed_at_ns, field="observed_at_ns")


@dataclass(frozen=True, slots=True)
class RetryDecision:
    disposition: str
    checkpoint_id: str
    order_id: str
    client_order_id: str
    idempotency_key: str
    idempotency_claim_id: str
    request_id: str
    current_attempt: int
    next_attempt: int | None
    backoff_ms: int | None
    reconciliation_required: bool
    network_mode: str = "DISABLED"
    actual_retry_dispatch: bool = False
    external_order_submission: bool = False
    reconciliation_authority: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "disposition": self.disposition, "checkpoint_id": self.checkpoint_id,
            "order_id": self.order_id, "client_order_id": self.client_order_id,
            "idempotency_key": self.idempotency_key, "idempotency_claim_id": self.idempotency_claim_id,
            "request_id": self.request_id, "current_attempt": self.current_attempt,
            "next_attempt": self.next_attempt, "backoff_ms": self.backoff_ms,
            "reconciliation_required": self.reconciliation_required, "network_mode": self.network_mode,
            "actual_retry_dispatch": self.actual_retry_dispatch,
            "external_order_submission": self.external_order_submission,
            "reconciliation_authority": self.reconciliation_authority,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def decision_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class RetryRecoveryPlanner:
    def __init__(self, policy: RetryRecoveryPolicy) -> None:
        self._policy = policy
        self._latest: dict[str, RecoveryCheckpoint] = {}

    def record(self, checkpoint: RecoveryCheckpoint) -> str:
        checkpoint.validate(self._policy)
        previous = self._latest.get(checkpoint.order_id)
        if previous is None:
            if checkpoint.previous_checkpoint_id is not None:
                raise RetryRecoveryError("first checkpoint cannot reference previous checkpoint")
        else:
            if checkpoint.previous_checkpoint_id != previous.checkpoint_id:
                raise RetryRecoveryError("checkpoint previous-id lineage mismatch")
            for field in ("market", "operation", "client_order_id", "idempotency_key", "idempotency_claim_id", "request_id"):
                if getattr(checkpoint, field) != getattr(previous, field):
                    raise RetryRecoveryError(f"checkpoint lineage drift: {field}")
            if checkpoint.observed_at_ns < previous.observed_at_ns:
                raise RetryRecoveryError("checkpoint time cannot regress")
            if checkpoint.attempt < previous.attempt or checkpoint.attempt > previous.attempt + 1:
                raise RetryRecoveryError("checkpoint attempt progression is invalid")
        self._latest[checkpoint.order_id] = checkpoint
        return checkpoint.checkpoint_id

    def decide(self, order_id: str, signal: RecoverySignal) -> RetryDecision:
        signal.validate(self._policy)
        try:
            checkpoint = self._latest[order_id]
        except KeyError as exc:
            raise RetryRecoveryError("unknown recovery checkpoint") from exc
        if signal.observed_at_ns < checkpoint.observed_at_ns:
            raise RetryRecoveryError("recovery signal time cannot precede checkpoint")

        if signal.condition in self._policy.safe_hold_conditions:
            if checkpoint.stage != "POST_DISPATCH":
                raise RetryRecoveryError("post-dispatch ambiguity requires POST_DISPATCH checkpoint")
            return self._decision(checkpoint, "SAFE_HOLD_RECONCILIATION_REQUIRED", None, None, True)

        if signal.condition in self._policy.terminal_conditions:
            if checkpoint.stage != "TERMINAL":
                raise RetryRecoveryError("terminal condition requires TERMINAL checkpoint")
            return self._decision(checkpoint, "NO_RETRY_TERMINAL", None, None, False)

        if checkpoint.stage != "PRE_DISPATCH":
            raise RetryRecoveryError("retryable condition requires PRE_DISPATCH checkpoint")
        if checkpoint.attempt >= self._policy.max_attempts:
            return self._decision(checkpoint, "RETRY_BUDGET_EXHAUSTED", None, None, False)

        next_attempt = checkpoint.attempt + 1
        backoff = self._policy.backoff_ms[checkpoint.attempt - 1]
        return self._decision(checkpoint, "RETRY_SAME_CLAIM", next_attempt, backoff, False)

    def _decision(
        self, checkpoint: RecoveryCheckpoint, disposition: str,
        next_attempt: int | None, backoff_ms: int | None, reconciliation_required: bool
    ) -> RetryDecision:
        return RetryDecision(
            disposition=disposition, checkpoint_id=checkpoint.checkpoint_id,
            order_id=checkpoint.order_id, client_order_id=checkpoint.client_order_id,
            idempotency_key=checkpoint.idempotency_key, idempotency_claim_id=checkpoint.idempotency_claim_id,
            request_id=checkpoint.request_id, current_attempt=checkpoint.attempt,
            next_attempt=next_attempt, backoff_ms=backoff_ms,
            reconciliation_required=reconciliation_required,
        )

    def snapshot(self) -> dict[str, object]:
        checkpoints: list[dict[str, object]] = []
        for order_id in sorted(self._latest):
            cp = self._latest[order_id]
            item = dict(cp.payload())
            item["checkpoint_id"] = cp.checkpoint_id
            checkpoints.append(item)
        payload: dict[str, object] = {
            "schema_version": "1.0", "kind": "NEXUS_QUANT_P20F_RETRY_RECOVERY_SNAPSHOT",
            "task_id": "FIN-P20-WF-001", "policy_id": self._policy.policy_id,
            "checkpoints": checkpoints,
            "authority": {
                "reconciliation_owner": "P20-G", "execution_quality_owner": "P20-H",
                "simulation_gate_owner": "P20-I", "position_management_owner": "P21",
                "credential_mode": "NONE", "network_mode": "DISABLED",
                "actual_retry_dispatch": False, "external_order_submission": False,
                "reconciliation_authority": False, "live_execution_authority": False,
                "live_trading": self._policy.live_trading, "auto_trading": self._policy.auto_trading,
            },
        }
        result = dict(payload)
        result["snapshot_id"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        return result
