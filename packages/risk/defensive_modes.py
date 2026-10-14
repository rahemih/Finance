from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


class DefensiveModeError(ValueError):
    """P15-H defensive-mode input violates governed invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class DefensiveModePolicy:
    policy_version: str
    reduced_risk_scale_bps: int
    defensive_scale_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise DefensiveModeError("policy_version must be non-empty")
        if not 0 <= self.defensive_scale_bps <= self.reduced_risk_scale_bps <= 10_000:
            raise DefensiveModeError(
                "scales must satisfy 0 <= defensive <= reduced <= 10000"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "normal_scale_bps": 10_000,
                "reduced_risk_scale_bps": self.reduced_risk_scale_bps,
                "defensive_scale_bps": self.defensive_scale_bps,
            }
        )


@dataclass(frozen=True)
class DefensiveModeRequest:
    request_id: str
    upstream_capital_decision_id: str
    upstream_capital_status: str
    upstream_drawdown_status: str
    data_health: str
    counterparty_health: str
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise DefensiveModeError("request_id must be non-empty")
        if not self.upstream_capital_decision_id.strip():
            raise DefensiveModeError(
                "upstream_capital_decision_id must be non-empty"
            )
        if self.upstream_capital_status not in {
            "CAPITAL_SEGMENT_ELIGIBLE",
            "VETO",
        }:
            raise DefensiveModeError("unknown upstream_capital_status")
        if self.upstream_drawdown_status not in {
            "WITHIN_LIMITS",
            "DE_RISK_REQUIRED",
            "VETO",
        }:
            raise DefensiveModeError("unknown upstream_drawdown_status")
        for field, value in (
            ("data_health", self.data_health),
            ("counterparty_health", self.counterparty_health),
        ):
            if value not in {"HEALTHY", "DEGRADED", "CRITICAL"}:
                raise DefensiveModeError(f"unknown {field}")
        if self.as_of_ns < 0:
            raise DefensiveModeError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class DefensiveModeDecision:
    decision_id: str
    request_id: str
    mode: str
    risk_scale_bps: int
    reason_codes: tuple[str, ...]
    new_risk_allowed: bool
    position_close_authority: bool = False
    execution_authority: bool = False


def select_defensive_mode(
    *,
    policy: DefensiveModePolicy,
    request: DefensiveModeRequest,
) -> DefensiveModeDecision:
    reasons: list[str] = []
    mode = "NORMAL"
    scale = 10_000

    hard_halt = (
        request.upstream_capital_status == "VETO"
        or request.upstream_drawdown_status == "VETO"
        or request.data_health == "CRITICAL"
        or request.counterparty_health == "CRITICAL"
    )
    if hard_halt:
        mode = "HALT_NEW_RISK"
        scale = 0
        if request.upstream_capital_status == "VETO":
            reasons.append("UPSTREAM_CAPITAL_VETO")
        if request.upstream_drawdown_status == "VETO":
            reasons.append("UPSTREAM_DRAWDOWN_RUIN_VETO")
        if request.data_health == "CRITICAL":
            reasons.append("CRITICAL_DATA_HEALTH")
        if request.counterparty_health == "CRITICAL":
            reasons.append("CRITICAL_COUNTERPARTY_HEALTH")
    elif request.upstream_drawdown_status == "DE_RISK_REQUIRED":
        mode = "DEFENSIVE"
        scale = policy.defensive_scale_bps
        reasons.append("DRAWDOWN_DERISK_REQUIRED")
    elif request.data_health == "DEGRADED" or request.counterparty_health == "DEGRADED":
        mode = "REDUCED_RISK"
        scale = policy.reduced_risk_scale_bps
        if request.data_health == "DEGRADED":
            reasons.append("DEGRADED_DATA_HEALTH")
        if request.counterparty_health == "DEGRADED":
            reasons.append("DEGRADED_COUNTERPARTY_HEALTH")

    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_capital_decision_id": request.upstream_capital_decision_id,
        "upstream_capital_status": request.upstream_capital_status,
        "upstream_drawdown_status": request.upstream_drawdown_status,
        "data_health": request.data_health,
        "counterparty_health": request.counterparty_health,
        "as_of_ns": request.as_of_ns,
        "mode": mode,
        "risk_scale_bps": scale,
        "reason_codes": reasons,
        "new_risk_allowed": mode != "HALT_NEW_RISK",
        "position_close_authority": False,
        "execution_authority": False,
    }
    return DefensiveModeDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        mode=mode,
        risk_scale_bps=scale,
        reason_codes=tuple(reasons),
        new_risk_allowed=mode != "HALT_NEW_RISK",
    )
