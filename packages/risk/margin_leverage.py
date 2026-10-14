from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json


class MarginLeverageError(ValueError):
    """P15-E margin/leverage input violates governed invariants."""


def _decimal(value: str, field: str, *, allow_zero: bool = False) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise MarginLeverageError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite():
        raise MarginLeverageError(f"{field} must be finite")
    if allow_zero:
        if parsed < 0:
            raise MarginLeverageError(f"{field} must be non-negative")
    elif parsed <= 0:
        raise MarginLeverageError(f"{field} must be positive")
    return parsed


def _text(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f").rstrip("0").rstrip(".") if "." in format(normalized, "f") else format(normalized, "f")


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
class MarginLeveragePolicy:
    policy_version: str
    max_leverage_milli: int
    max_margin_utilization_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise MarginLeverageError("policy_version must be non-empty")
        if self.max_leverage_milli < 0:
            raise MarginLeverageError("max_leverage_milli must be non-negative")
        if self.max_margin_utilization_bps < 0:
            raise MarginLeverageError(
                "max_margin_utilization_bps must be non-negative"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "max_leverage_milli": self.max_leverage_milli,
                "max_margin_utilization_bps": self.max_margin_utilization_bps,
            }
        )


@dataclass(frozen=True)
class MarginLeverageRequest:
    request_id: str
    upstream_portfolio_decision_id: str
    upstream_portfolio_status: str
    account_equity: str
    current_gross_notional: str
    current_margin_used: str
    candidate_notional: str
    initial_margin_rate_bps: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise MarginLeverageError("request_id must be non-empty")
        if not self.upstream_portfolio_decision_id.strip():
            raise MarginLeverageError(
                "upstream_portfolio_decision_id must be non-empty"
            )
        _decimal(self.account_equity, "account_equity")
        _decimal(
            self.current_gross_notional,
            "current_gross_notional",
            allow_zero=True,
        )
        _decimal(self.current_margin_used, "current_margin_used", allow_zero=True)
        _decimal(self.candidate_notional, "candidate_notional")
        if not 1 <= self.initial_margin_rate_bps <= 10_000:
            raise MarginLeverageError(
                "initial_margin_rate_bps must be within [1, 10000]"
            )
        if self.as_of_ns < 0:
            raise MarginLeverageError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class MarginLeverageDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    total_gross_notional: str
    candidate_initial_margin: str
    total_margin_used: str
    leverage_milli: int
    margin_utilization_bps: int
    execution_authority: bool = False


def evaluate_margin_leverage(
    *,
    policy: MarginLeveragePolicy,
    request: MarginLeverageRequest,
) -> MarginLeverageDecision:
    equity = _decimal(request.account_equity, "account_equity")
    current_gross = _decimal(
        request.current_gross_notional,
        "current_gross_notional",
        allow_zero=True,
    )
    current_margin = _decimal(
        request.current_margin_used,
        "current_margin_used",
        allow_zero=True,
    )
    candidate = _decimal(request.candidate_notional, "candidate_notional")

    total_gross = current_gross + candidate
    candidate_margin = (
        candidate * Decimal(request.initial_margin_rate_bps) / Decimal(10_000)
    )
    total_margin = current_margin + candidate_margin
    leverage_milli = _ceil_int(total_gross / equity * Decimal(1000))
    margin_utilization_bps = _ceil_int(
        total_margin / equity * Decimal(10_000)
    )

    reasons: list[str] = []
    if request.upstream_portfolio_status != "PORTFOLIO_ELIGIBLE":
        reasons.append("UPSTREAM_PORTFOLIO_NOT_ELIGIBLE")
    if leverage_milli > policy.max_leverage_milli:
        reasons.append("LEVERAGE_LIMIT_EXCEEDED")
    if margin_utilization_bps > policy.max_margin_utilization_bps:
        reasons.append("MARGIN_UTILIZATION_LIMIT_EXCEEDED")

    status = "VETO" if reasons else "MARGIN_LEVERAGE_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_portfolio_decision_id": request.upstream_portfolio_decision_id,
        "upstream_portfolio_status": request.upstream_portfolio_status,
        "account_equity": _text(equity),
        "current_gross_notional": _text(current_gross),
        "current_margin_used": _text(current_margin),
        "candidate_notional": _text(candidate),
        "initial_margin_rate_bps": request.initial_margin_rate_bps,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "total_gross_notional": _text(total_gross),
        "candidate_initial_margin": _text(candidate_margin),
        "total_margin_used": _text(total_margin),
        "leverage_milli": leverage_milli,
        "margin_utilization_bps": margin_utilization_bps,
        "execution_authority": False,
    }
    return MarginLeverageDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        total_gross_notional=_text(total_gross),
        candidate_initial_margin=_text(candidate_margin),
        total_margin_used=_text(total_margin),
        leverage_milli=leverage_milli,
        margin_utilization_bps=margin_utilization_bps,
    )
