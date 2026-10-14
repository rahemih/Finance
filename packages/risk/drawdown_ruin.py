from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json


class DrawdownRuinError(ValueError):
    """P15-F drawdown/risk-of-ruin input violates governed invariants."""


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DrawdownRuinError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise DrawdownRuinError(f"{field} must be finite and positive")
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
class DrawdownRuinPolicy:
    policy_version: str
    soft_drawdown_bps: int
    hard_stop_drawdown_bps: int
    max_ruin_probability_ppm: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise DrawdownRuinError("policy_version must be non-empty")
        if not 0 <= self.soft_drawdown_bps < self.hard_stop_drawdown_bps <= 10_000:
            raise DrawdownRuinError(
                "drawdown thresholds must satisfy 0 <= soft < hard <= 10000"
            )
        if not 0 <= self.max_ruin_probability_ppm <= 1_000_000:
            raise DrawdownRuinError(
                "max_ruin_probability_ppm must be within [0, 1000000]"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "soft_drawdown_bps": self.soft_drawdown_bps,
                "hard_stop_drawdown_bps": self.hard_stop_drawdown_bps,
                "max_ruin_probability_ppm": self.max_ruin_probability_ppm,
            }
        )


@dataclass(frozen=True)
class DrawdownRuinRequest:
    request_id: str
    upstream_margin_decision_id: str
    upstream_margin_status: str
    peak_equity: str
    current_equity: str
    ruin_probability_ppm: int
    ruin_model_id: str
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise DrawdownRuinError("request_id must be non-empty")
        if not self.upstream_margin_decision_id.strip():
            raise DrawdownRuinError(
                "upstream_margin_decision_id must be non-empty"
            )
        if not self.ruin_model_id.strip():
            raise DrawdownRuinError("ruin_model_id must be non-empty")
        _decimal(self.peak_equity, "peak_equity")
        _decimal(self.current_equity, "current_equity")
        if not 0 <= self.ruin_probability_ppm <= 1_000_000:
            raise DrawdownRuinError(
                "ruin_probability_ppm must be within [0, 1000000]"
            )
        if self.as_of_ns < 0:
            raise DrawdownRuinError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class DrawdownRuinDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    drawdown_bps: int
    ruin_probability_ppm: int
    defensive_mode_authority: bool = False
    execution_authority: bool = False


def evaluate_drawdown_ruin(
    *,
    policy: DrawdownRuinPolicy,
    request: DrawdownRuinRequest,
) -> DrawdownRuinDecision:
    peak = _decimal(request.peak_equity, "peak_equity")
    current = _decimal(request.current_equity, "current_equity")
    if current >= peak:
        drawdown_bps = 0
    else:
        drawdown_bps = _ceil_int((peak - current) / peak * Decimal(10_000))

    reasons: list[str] = []
    hard_veto = False
    soft_breach = False

    if request.upstream_margin_status != "MARGIN_LEVERAGE_ELIGIBLE":
        reasons.append("UPSTREAM_MARGIN_LEVERAGE_NOT_ELIGIBLE")
        hard_veto = True
    if drawdown_bps >= policy.hard_stop_drawdown_bps:
        reasons.append("HARD_DRAWDOWN_LIMIT_REACHED")
        hard_veto = True
    elif drawdown_bps >= policy.soft_drawdown_bps:
        reasons.append("SOFT_DRAWDOWN_LIMIT_REACHED")
        soft_breach = True
    if request.ruin_probability_ppm > policy.max_ruin_probability_ppm:
        reasons.append("RUIN_PROBABILITY_LIMIT_EXCEEDED")
        hard_veto = True

    if hard_veto:
        status = "VETO"
    elif soft_breach:
        status = "DE_RISK_REQUIRED"
    else:
        status = "WITHIN_LIMITS"

    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_margin_decision_id": request.upstream_margin_decision_id,
        "upstream_margin_status": request.upstream_margin_status,
        "peak_equity": str(peak.normalize()),
        "current_equity": str(current.normalize()),
        "ruin_probability_ppm": request.ruin_probability_ppm,
        "ruin_model_id": request.ruin_model_id,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "drawdown_bps": drawdown_bps,
        "defensive_mode_authority": False,
        "execution_authority": False,
    }
    return DrawdownRuinDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        drawdown_bps=drawdown_bps,
        ruin_probability_ppm=request.ruin_probability_ppm,
    )
