from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json


class PositionSizingError(ValueError):
    """P15-B position-sizing input violates governed invariants."""


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise PositionSizingError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise PositionSizingError(f"{field} must be finite and positive")
    return parsed


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PositionSizingRequest:
    request_id: str
    upstream_risk_decision_id: str
    upstream_status: str
    side: str
    account_equity: str
    risk_budget_bps: int
    entry_price: str
    stop_price: str
    contract_multiplier: str
    quantity_step: str
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PositionSizingError("request_id must be non-empty")
        if not self.upstream_risk_decision_id.strip():
            raise PositionSizingError("upstream_risk_decision_id must be non-empty")
        if self.side not in {"LONG", "SHORT"}:
            raise PositionSizingError("side must be LONG or SHORT")
        if not 1 <= self.risk_budget_bps <= 10_000:
            raise PositionSizingError("risk_budget_bps must be within [1, 10000]")
        if self.as_of_ns < 0:
            raise PositionSizingError("as_of_ns must be non-negative")
        _decimal(self.account_equity, "account_equity")
        _decimal(self.entry_price, "entry_price")
        _decimal(self.stop_price, "stop_price")
        _decimal(self.contract_multiplier, "contract_multiplier")
        _decimal(self.quantity_step, "quantity_step")


@dataclass(frozen=True)
class PositionSizeDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    risk_amount: str
    per_unit_stop_loss: str
    raw_quantity: str
    candidate_quantity: str
    planned_stop_loss: str
    risk_budget_bps: int
    leverage_authority: bool = False
    execution_authority: bool = False


def size_position(request: PositionSizingRequest) -> PositionSizeDecision:
    equity = _decimal(request.account_equity, "account_equity")
    entry = _decimal(request.entry_price, "entry_price")
    stop = _decimal(request.stop_price, "stop_price")
    multiplier = _decimal(request.contract_multiplier, "contract_multiplier")
    step = _decimal(request.quantity_step, "quantity_step")

    reasons: list[str] = []
    if request.upstream_status != "POLICY_CAPACITY_ELIGIBLE":
        reasons.append("UPSTREAM_RISK_VETO")
    if request.side == "LONG" and stop >= entry:
        reasons.append("INVALID_LONG_STOP_GEOMETRY")
    if request.side == "SHORT" and stop <= entry:
        reasons.append("INVALID_SHORT_STOP_GEOMETRY")

    risk_amount = equity * Decimal(request.risk_budget_bps) / Decimal(10_000)
    per_unit_stop_loss = abs(entry - stop) * multiplier
    raw_quantity = Decimal(0)
    candidate_quantity = Decimal(0)
    planned_stop_loss = Decimal(0)

    if per_unit_stop_loss > 0 and not reasons:
        raw_quantity = risk_amount / per_unit_stop_loss
        steps = (raw_quantity / step).to_integral_value(rounding=ROUND_FLOOR)
        candidate_quantity = steps * step
        planned_stop_loss = candidate_quantity * per_unit_stop_loss
        if candidate_quantity <= 0:
            reasons.append("SIZE_BELOW_MIN_STEP")
        if planned_stop_loss > risk_amount:
            raise PositionSizingError("planned stop loss exceeded governed risk amount")

    status = "VETO" if reasons else "SIZE_CANDIDATE"
    payload = {
        "request_id": request.request_id,
        "upstream_risk_decision_id": request.upstream_risk_decision_id,
        "upstream_status": request.upstream_status,
        "side": request.side,
        "account_equity": _decimal_text(equity),
        "risk_budget_bps": request.risk_budget_bps,
        "entry_price": _decimal_text(entry),
        "stop_price": _decimal_text(stop),
        "contract_multiplier": _decimal_text(multiplier),
        "quantity_step": _decimal_text(step),
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "risk_amount": _decimal_text(risk_amount),
        "per_unit_stop_loss": _decimal_text(per_unit_stop_loss),
        "raw_quantity": _decimal_text(raw_quantity),
        "candidate_quantity": _decimal_text(candidate_quantity),
        "planned_stop_loss": _decimal_text(planned_stop_loss),
        "leverage_authority": False,
        "execution_authority": False,
    }
    return PositionSizeDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        risk_amount=_decimal_text(risk_amount),
        per_unit_stop_loss=_decimal_text(per_unit_stop_loss),
        raw_quantity=_decimal_text(raw_quantity),
        candidate_quantity=_decimal_text(candidate_quantity),
        planned_stop_loss=_decimal_text(planned_stop_loss),
        risk_budget_bps=request.risk_budget_bps,
    )
