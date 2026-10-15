from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json


class DailyLossCircuitError(ValueError):
    """P16-F daily-loss / circuit-breaker input violates firewall invariants."""


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DailyLossCircuitError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise DailyLossCircuitError(f"{field} must be finite and positive")
    return parsed


def _ceil_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class DailyLossPolicy:
    policy_version: str
    max_daily_loss_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise DailyLossCircuitError("policy_version must be non-empty")
        if not 1 <= self.max_daily_loss_bps <= 10_000:
            raise DailyLossCircuitError(
                "max_daily_loss_bps must be within [1, 10000]"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "max_daily_loss_bps": self.max_daily_loss_bps,
            }
        )


@dataclass(frozen=True)
class DailyLossRequest:
    request_id: str
    upstream_health_decision_id: str
    upstream_health_status: str
    trading_day_id: str
    day_start_equity: str
    current_equity: str
    prior_circuit_state: str
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise DailyLossCircuitError("request_id must be non-empty")
        if not self.upstream_health_decision_id.strip():
            raise DailyLossCircuitError(
                "upstream_health_decision_id must be non-empty"
            )
        if self.upstream_health_status not in {"PRETRADE_E_ELIGIBLE", "VETO"}:
            raise DailyLossCircuitError("unknown upstream_health_status")
        if not self.trading_day_id.strip():
            raise DailyLossCircuitError("trading_day_id must be non-empty")
        _decimal(self.day_start_equity, "day_start_equity")
        _decimal(self.current_equity, "current_equity")
        if self.prior_circuit_state not in {"CLEAR", "TRIPPED"}:
            raise DailyLossCircuitError("prior_circuit_state must be CLEAR or TRIPPED")
        if self.as_of_ns < 0:
            raise DailyLossCircuitError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class DailyLossDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    daily_loss_bps: int
    circuit_state: str
    reset_authority: bool = False
    position_close_authority: bool = False
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_daily_loss(
    *,
    policy: DailyLossPolicy,
    request: DailyLossRequest,
) -> DailyLossDecision:
    start = _decimal(request.day_start_equity, "day_start_equity")
    current = _decimal(request.current_equity, "current_equity")

    daily_loss_bps = 0
    if current < start:
        daily_loss_bps = _ceil_int(
            (start - current) / start * Decimal(10_000)
        )

    reasons: list[str] = []
    if request.upstream_health_status == "VETO":
        reasons.append("UPSTREAM_HEALTH_VETO")
    if request.prior_circuit_state == "TRIPPED":
        reasons.append("CIRCUIT_ALREADY_TRIPPED")
    if daily_loss_bps >= policy.max_daily_loss_bps:
        reasons.append("DAILY_LOSS_LIMIT_REACHED")

    circuit_state = "TRIPPED" if (
        request.prior_circuit_state == "TRIPPED"
        or daily_loss_bps >= policy.max_daily_loss_bps
    ) else "CLEAR"
    status = "VETO" if reasons else "PRETRADE_F_ELIGIBLE"

    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_health_decision_id": request.upstream_health_decision_id,
        "upstream_health_status": request.upstream_health_status,
        "trading_day_id": request.trading_day_id,
        "day_start_equity": str(start.normalize()),
        "current_equity": str(current.normalize()),
        "prior_circuit_state": request.prior_circuit_state,
        "as_of_ns": request.as_of_ns,
        "daily_loss_bps": daily_loss_bps,
        "circuit_state": circuit_state,
        "status": status,
        "reason_codes": reasons,
        "reset_authority": False,
        "position_close_authority": False,
        "g8_authority": False,
        "execution_authority": False,
    }
    return DailyLossDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        daily_loss_bps=daily_loss_bps,
        circuit_state=circuit_state,
    )
