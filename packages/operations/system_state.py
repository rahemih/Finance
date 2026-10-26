from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast


SystemState = Literal["NORMAL", "DEGRADED", "SAFE_MODE", "HALTED", "EMERGENCY", "RECOVERY"]
HealthLevel = Literal["HEALTHY", "DEGRADED", "UNSAFE", "HALT_REQUIRED", "EMERGENCY"]


class SystemStateError(ValueError):
    """P22-B deterministic system-state invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _epoch_ns(value: int, *, field: str) -> int:
    if isinstance(value, bool) or value < 0:
        raise SystemStateError(f"{field} must be a non-negative integer epoch-ns value")
    return value


def _hex_id(value: str, *, field: str, length: int) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise SystemStateError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _reason_codes(values: tuple[str, ...], *, max_count: int, max_length: int) -> tuple[str, ...]:
    if len(values) > max_count:
        raise SystemStateError("reason code count exceeds policy")
    normalized: list[str] = []
    for value in values:
        item = value.strip().upper()
        if not item or len(item) > max_length:
            raise SystemStateError("invalid reason code")
        if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-." for ch in item):
            raise SystemStateError("reason code contains unsupported characters")
        normalized.append(item)
    if len(set(normalized)) != len(normalized):
        raise SystemStateError("duplicate reason codes are forbidden")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class SystemStatePolicy:
    states: tuple[SystemState, ...]
    health_levels: tuple[HealthLevel, ...]
    restricted_states: tuple[SystemState, ...]
    reason_code_max_count: int
    reason_code_max_length: int
    correlation_id_hex_length: int

    @classmethod
    def from_path(cls, path: Path) -> "SystemStatePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemStateError(f"invalid P22-B policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise SystemStateError("P22-B policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22B_SYSTEM_STATE_POLICY",
            "task_id": "FIN-P22-WB-001",
            "mode": "DETERMINISTIC_REFERENCE_SYSTEM_STATE_MACHINE",
            "states": ["NORMAL", "DEGRADED", "SAFE_MODE", "HALTED", "EMERGENCY", "RECOVERY"],
            "health_levels": ["HEALTHY", "DEGRADED", "UNSAFE", "HALT_REQUIRED", "EMERGENCY"],
            "restricted_states": ["SAFE_MODE", "HALTED", "EMERGENCY"],
            "recovery_requires_explicit_authorization": True,
            "recovery_is_two_step": True,
            "reason_code_max_count": 8,
            "reason_code_max_length": 96,
            "correlation_id_hex_length": 32,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "automatic_state_mutation": False,
            "automatic_diagnostics": False,
            "automatic_self_healing": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise SystemStateError(f"P22-B policy mismatch: {key}")
        return cls(
            states=("NORMAL", "DEGRADED", "SAFE_MODE", "HALTED", "EMERGENCY", "RECOVERY"),
            health_levels=("HEALTHY", "DEGRADED", "UNSAFE", "HALT_REQUIRED", "EMERGENCY"),
            restricted_states=("SAFE_MODE", "HALTED", "EMERGENCY"),
            reason_code_max_count=8,
            reason_code_max_length=96,
            correlation_id_hex_length=32,
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "states": self.states,
            "health_levels": self.health_levels,
            "restricted_states": self.restricted_states,
            "reason_code_max_count": self.reason_code_max_count,
            "reason_code_max_length": self.reason_code_max_length,
            "correlation_id_hex_length": self.correlation_id_hex_length,
            "recovery_requires_explicit_authorization": True,
            "recovery_is_two_step": True,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "automatic_state_mutation": False,
            "automatic_diagnostics": False,
            "automatic_self_healing": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    snapshot_id: str
    health_level: HealthLevel
    observed_at_ns: int
    correlation_id: str
    reason_codes: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "health_level": self.health_level,
            "observed_at_ns": self.observed_at_ns,
            "correlation_id": self.correlation_id,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class StateDecision:
    decision_id: str
    policy_id: str
    previous_state: SystemState
    next_state: SystemState
    snapshot_id: str
    recovery_authorized: bool
    deescalation_blocked: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "previous_state": self.previous_state,
            "next_state": self.next_state,
            "snapshot_id": self.snapshot_id,
            "recovery_authorized": self.recovery_authorized,
            "deescalation_blocked": self.deescalation_blocked,
        }


def build_health_snapshot(
    policy: SystemStatePolicy,
    *,
    health_level: HealthLevel,
    observed_at_ns: int,
    correlation_id: str,
    reason_codes: tuple[str, ...],
) -> HealthSnapshot:
    if health_level not in policy.health_levels:
        raise SystemStateError("unsupported health level")
    timestamp = _epoch_ns(observed_at_ns, field="observed_at_ns")
    correlation = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)
    reasons = _reason_codes(
        reason_codes,
        max_count=policy.reason_code_max_count,
        max_length=policy.reason_code_max_length,
    )
    if health_level == "HEALTHY" and not reasons:
        reasons = ("ALL_REQUIRED_HEALTH_CHECKS_PASS",)
    if health_level != "HEALTHY" and not reasons:
        raise SystemStateError("non-healthy snapshots require an explicit reason code")
    payload: dict[str, object] = {
        "health_level": health_level,
        "observed_at_ns": timestamp,
        "correlation_id": correlation,
        "reason_codes": list(reasons),
    }
    snapshot_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return HealthSnapshot(snapshot_id, health_level, timestamp, correlation, reasons)


def decide_system_state(
    policy: SystemStatePolicy,
    *,
    previous_state: SystemState,
    snapshot: HealthSnapshot,
    recovery_authorized: bool = False,
) -> StateDecision:
    if previous_state not in policy.states:
        raise SystemStateError("unsupported previous state")
    if recovery_authorized and snapshot.health_level != "HEALTHY":
        raise SystemStateError("recovery authorization may only accompany a HEALTHY snapshot")

    blocked = False
    if snapshot.health_level == "EMERGENCY":
        next_state: SystemState = "EMERGENCY"
    elif snapshot.health_level == "HALT_REQUIRED":
        next_state = "EMERGENCY" if previous_state == "EMERGENCY" else "HALTED"
    elif snapshot.health_level == "UNSAFE":
        next_state = previous_state if previous_state in ("HALTED", "EMERGENCY") else "SAFE_MODE"
    elif snapshot.health_level == "DEGRADED":
        next_state = previous_state if previous_state in policy.restricted_states else "DEGRADED"
    else:
        if previous_state in policy.restricted_states:
            if recovery_authorized:
                next_state = "RECOVERY"
            else:
                next_state = previous_state
                blocked = True
        elif previous_state == "RECOVERY":
            next_state = "NORMAL"
        else:
            next_state = "NORMAL"

    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "previous_state": previous_state,
        "next_state": next_state,
        "snapshot_id": snapshot.snapshot_id,
        "recovery_authorized": recovery_authorized,
        "deescalation_blocked": blocked,
    }
    decision_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return StateDecision(
        decision_id,
        policy.policy_id,
        previous_state,
        next_state,
        snapshot.snapshot_id,
        recovery_authorized,
        blocked,
    )
