from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json

from packages.risk.defensive_modes import DefensiveModeDecision
from packages.risk.margin_leverage import MarginLeverageDecision
from packages.risk.portfolio_correlation import PortfolioExposureDecision
from packages.risk.position_sizing import PositionSizeDecision


class PreTradeRiskEnvelopeError(ValueError):
    """P16-C execution-intent risk envelope violates governed invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _decimal(
    value: str,
    field: str,
    *,
    allow_zero: bool = False,
) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise PreTradeRiskEnvelopeError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite():
        raise PreTradeRiskEnvelopeError(f"{field} must be finite")
    if allow_zero:
        if parsed < 0:
            raise PreTradeRiskEnvelopeError(f"{field} must be non-negative")
    elif parsed <= 0:
        raise PreTradeRiskEnvelopeError(f"{field} must be positive")
    return parsed


def _text(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True)
class PreTradeRiskEnvelopeRequest:
    request_id: str
    upstream_idempotency_decision_id: str
    upstream_idempotency_status: str
    p15_validation_id: str
    p15_validation_marker: str
    p15_validation_status: str
    p15_validation_final_mode: str
    p15_validation_risk_scale_bps: int
    position_size: PositionSizeDecision
    portfolio_exposure: PortfolioExposureDecision
    margin_leverage: MarginLeverageDecision
    defensive_mode: DefensiveModeDecision
    proposed_quantity: str
    quantity_step: str
    final_gross_exposure_bps: int
    final_abs_net_exposure_bps: int
    final_correlated_cluster_gross_bps: int
    final_leverage_milli: int
    final_margin_utilization_bps: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PreTradeRiskEnvelopeError("request_id must be non-empty")
        if not self.upstream_idempotency_decision_id.strip():
            raise PreTradeRiskEnvelopeError(
                "upstream_idempotency_decision_id must be non-empty"
            )
        if self.upstream_idempotency_status not in {
            "PRETRADE_B_ELIGIBLE",
            "VETO",
        }:
            raise PreTradeRiskEnvelopeError("unknown upstream_idempotency_status")
        if not self.p15_validation_id.strip():
            raise PreTradeRiskEnvelopeError("p15_validation_id must be non-empty")
        if self.p15_validation_status not in {"PASS", "FAIL"}:
            raise PreTradeRiskEnvelopeError("unknown p15_validation_status")
        if not 0 <= self.p15_validation_risk_scale_bps <= 10_000:
            raise PreTradeRiskEnvelopeError(
                "p15_validation_risk_scale_bps must be within [0, 10000]"
            )
        _decimal(self.proposed_quantity, "proposed_quantity")
        _decimal(self.quantity_step, "quantity_step")
        for field, value in (
            ("final_gross_exposure_bps", self.final_gross_exposure_bps),
            ("final_abs_net_exposure_bps", self.final_abs_net_exposure_bps),
            (
                "final_correlated_cluster_gross_bps",
                self.final_correlated_cluster_gross_bps,
            ),
            ("final_leverage_milli", self.final_leverage_milli),
            ("final_margin_utilization_bps", self.final_margin_utilization_bps),
        ):
            if value < 0:
                raise PreTradeRiskEnvelopeError(f"{field} must be non-negative")
        if self.as_of_ns < 0:
            raise PreTradeRiskEnvelopeError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class PreTradeRiskEnvelopeDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    maximum_scaled_quantity: str
    proposed_quantity: str
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_risk_envelope(
    request: PreTradeRiskEnvelopeRequest,
) -> PreTradeRiskEnvelopeDecision:
    reasons: set[str] = set()

    if request.upstream_idempotency_status == "VETO":
        reasons.add("UPSTREAM_IDEMPOTENCY_VETO")

    if (
        request.p15_validation_marker != "P15_INDEPENDENT_RISK_VALIDATION"
        or request.p15_validation_status != "PASS"
    ):
        reasons.add("P15_INDEPENDENT_VALIDATION_NOT_PASS")

    if request.position_size.status != "SIZE_CANDIDATE":
        reasons.add("P15_SIZE_NOT_ELIGIBLE")
    if request.portfolio_exposure.status != "PORTFOLIO_ELIGIBLE":
        reasons.add("P15_PORTFOLIO_NOT_ELIGIBLE")
    if request.margin_leverage.status != "MARGIN_LEVERAGE_ELIGIBLE":
        reasons.add("P15_MARGIN_LEVERAGE_NOT_ELIGIBLE")

    if (
        request.p15_validation_final_mode != request.defensive_mode.mode
        or request.p15_validation_risk_scale_bps
        != request.defensive_mode.risk_scale_bps
    ):
        reasons.add("P15_VALIDATION_DEFENSIVE_MISMATCH")

    if (
        not request.defensive_mode.new_risk_allowed
        or request.defensive_mode.mode == "HALT_NEW_RISK"
        or request.defensive_mode.risk_scale_bps == 0
    ):
        reasons.add("P15_DEFENSIVE_MODE_BLOCKS_NEW_RISK")

    authority_flags = (
        request.position_size.leverage_authority,
        request.position_size.execution_authority,
        request.portfolio_exposure.leverage_authority,
        request.portfolio_exposure.execution_authority,
        request.margin_leverage.execution_authority,
        request.defensive_mode.position_close_authority,
        request.defensive_mode.execution_authority,
    )
    if any(authority_flags):
        reasons.add("P15_AUTHORITY_ESCALATION")

    candidate = _decimal(
        request.position_size.candidate_quantity,
        "position_size.candidate_quantity",
        allow_zero=True,
    )
    proposed = _decimal(request.proposed_quantity, "proposed_quantity")
    step = _decimal(request.quantity_step, "quantity_step")
    if proposed % step != 0:
        reasons.add("QUANTITY_STEP_MISALIGNED")
    scale = Decimal(request.defensive_mode.risk_scale_bps) / Decimal(10_000)
    maximum_scaled_quantity = candidate * scale
    if proposed > maximum_scaled_quantity:
        reasons.add("SIZE_ENVELOPE_EXCEEDED")

    approved_metrics = (
        request.portfolio_exposure.gross_exposure_bps,
        request.portfolio_exposure.abs_net_exposure_bps,
        request.portfolio_exposure.max_correlated_cluster_gross_bps,
        request.margin_leverage.leverage_milli,
        request.margin_leverage.margin_utilization_bps,
    )
    if any(value < 0 for value in approved_metrics):
        reasons.add("INVALID_P15_RISK_ENVELOPE")

    if (
        request.final_gross_exposure_bps
        > request.portfolio_exposure.gross_exposure_bps
    ):
        reasons.add("GROSS_EXPOSURE_ENVELOPE_EXCEEDED")
    if (
        request.final_abs_net_exposure_bps
        > request.portfolio_exposure.abs_net_exposure_bps
    ):
        reasons.add("NET_EXPOSURE_ENVELOPE_EXCEEDED")
    if (
        request.final_correlated_cluster_gross_bps
        > request.portfolio_exposure.max_correlated_cluster_gross_bps
    ):
        reasons.add("CORRELATED_CLUSTER_ENVELOPE_EXCEEDED")
    if request.final_leverage_milli > request.margin_leverage.leverage_milli:
        reasons.add("LEVERAGE_ENVELOPE_EXCEEDED")
    if (
        request.final_margin_utilization_bps
        > request.margin_leverage.margin_utilization_bps
    ):
        reasons.add("MARGIN_UTILIZATION_ENVELOPE_EXCEEDED")

    reason_codes = tuple(sorted(reasons))
    status = "VETO" if reason_codes else "PRETRADE_C_ELIGIBLE"
    payload = {
        "request_id": request.request_id,
        "upstream_idempotency_decision_id": (
            request.upstream_idempotency_decision_id
        ),
        "upstream_idempotency_status": request.upstream_idempotency_status,
        "p15_validation_id": request.p15_validation_id,
        "p15_validation_marker": request.p15_validation_marker,
        "p15_validation_status": request.p15_validation_status,
        "p15_validation_final_mode": request.p15_validation_final_mode,
        "p15_validation_risk_scale_bps": (
            request.p15_validation_risk_scale_bps
        ),
        "position_size_decision_id": request.position_size.decision_id,
        "portfolio_exposure_decision_id": request.portfolio_exposure.decision_id,
        "margin_leverage_decision_id": request.margin_leverage.decision_id,
        "defensive_mode_decision_id": request.defensive_mode.decision_id,
        "proposed_quantity": _text(proposed),
        "quantity_step": request.quantity_step,
        "final_gross_exposure_bps": request.final_gross_exposure_bps,
        "final_abs_net_exposure_bps": request.final_abs_net_exposure_bps,
        "final_correlated_cluster_gross_bps": (
            request.final_correlated_cluster_gross_bps
        ),
        "final_leverage_milli": request.final_leverage_milli,
        "final_margin_utilization_bps": (
            request.final_margin_utilization_bps
        ),
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reason_codes,
        "maximum_scaled_quantity": _text(maximum_scaled_quantity),
        "g8_authority": False,
        "execution_authority": False,
    }
    return PreTradeRiskEnvelopeDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=reason_codes,
        maximum_scaled_quantity=_text(maximum_scaled_quantity),
        proposed_quantity=_text(proposed),
    )
