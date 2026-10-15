from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json

from packages.risk.margin_leverage import MarginLeverageDecision
from packages.risk.portfolio_correlation import PortfolioExposureDecision
from packages.risk.position_sizing import PositionSizeDecision


class PreTradeRiskDriftError(ValueError):
    """P16-C final risk metrics violate pre-trade revalidation invariants."""


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise PreTradeRiskDriftError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise PreTradeRiskDriftError(f"{field} must be finite and positive")
    return parsed


def _text(value: Decimal) -> str:
    normalized = value.normalize()
    value_text = format(normalized, "f")
    if "." in value_text:
        value_text = value_text.rstrip("0").rstrip(".")
    return value_text


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PreTradeRiskDriftRequest:
    request_id: str
    upstream_idempotency_decision_id: str
    upstream_idempotency_status: str
    approved_size: PositionSizeDecision
    approved_portfolio: PortfolioExposureDecision
    approved_margin: MarginLeverageDecision
    final_quantity: str
    final_gross_exposure_bps: int
    final_abs_net_exposure_bps: int
    final_max_correlated_cluster_gross_bps: int
    final_leverage_milli: int
    final_margin_utilization_bps: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PreTradeRiskDriftError("request_id must be non-empty")
        if not self.upstream_idempotency_decision_id.strip():
            raise PreTradeRiskDriftError(
                "upstream_idempotency_decision_id must be non-empty"
            )
        if self.upstream_idempotency_status not in {"PRETRADE_B_ELIGIBLE", "VETO"}:
            raise PreTradeRiskDriftError("unknown upstream_idempotency_status")
        _decimal(self.final_quantity, "final_quantity")
        for field, value in (
            ("final_gross_exposure_bps", self.final_gross_exposure_bps),
            ("final_abs_net_exposure_bps", self.final_abs_net_exposure_bps),
            (
                "final_max_correlated_cluster_gross_bps",
                self.final_max_correlated_cluster_gross_bps,
            ),
            ("final_leverage_milli", self.final_leverage_milli),
            ("final_margin_utilization_bps", self.final_margin_utilization_bps),
        ):
            if value < 0:
                raise PreTradeRiskDriftError(f"{field} must be non-negative")
        if self.as_of_ns < 0:
            raise PreTradeRiskDriftError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class PreTradeRiskDriftDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    final_quantity: str
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_risk_drift(
    request: PreTradeRiskDriftRequest,
) -> PreTradeRiskDriftDecision:
    reasons: list[str] = []

    if request.upstream_idempotency_status == "VETO":
        reasons.append("UPSTREAM_IDEMPOTENCY_VETO")
    if request.approved_size.status != "SIZE_CANDIDATE":
        reasons.append("P15_SIZE_NOT_ELIGIBLE")
    if request.approved_portfolio.status != "PORTFOLIO_ELIGIBLE":
        reasons.append("P15_PORTFOLIO_NOT_ELIGIBLE")
    if request.approved_margin.status != "MARGIN_LEVERAGE_ELIGIBLE":
        reasons.append("P15_MARGIN_LEVERAGE_NOT_ELIGIBLE")

    final_quantity = _decimal(request.final_quantity, "final_quantity")
    approved_quantity = _decimal(
        request.approved_size.candidate_quantity,
        "approved_size.candidate_quantity",
    )
    if final_quantity > approved_quantity:
        reasons.append("FINAL_SIZE_EXCEEDS_APPROVED")

    if (
        request.final_gross_exposure_bps
        > request.approved_portfolio.gross_exposure_bps
    ):
        reasons.append("FINAL_GROSS_EXPOSURE_EXCEEDS_APPROVED")
    if (
        request.final_abs_net_exposure_bps
        > request.approved_portfolio.abs_net_exposure_bps
    ):
        reasons.append("FINAL_NET_EXPOSURE_EXCEEDS_APPROVED")
    if (
        request.final_max_correlated_cluster_gross_bps
        > request.approved_portfolio.max_correlated_cluster_gross_bps
    ):
        reasons.append("FINAL_CORRELATED_CLUSTER_EXCEEDS_APPROVED")
    if request.final_leverage_milli > request.approved_margin.leverage_milli:
        reasons.append("FINAL_LEVERAGE_EXCEEDS_APPROVED")
    if (
        request.final_margin_utilization_bps
        > request.approved_margin.margin_utilization_bps
    ):
        reasons.append("FINAL_MARGIN_UTILIZATION_EXCEEDS_APPROVED")

    status = "VETO" if reasons else "PRETRADE_C_ELIGIBLE"
    payload = {
        "request_id": request.request_id,
        "upstream_idempotency_decision_id": request.upstream_idempotency_decision_id,
        "upstream_idempotency_status": request.upstream_idempotency_status,
        "approved_size_decision_id": request.approved_size.decision_id,
        "approved_portfolio_decision_id": request.approved_portfolio.decision_id,
        "approved_margin_decision_id": request.approved_margin.decision_id,
        "final_quantity": _text(final_quantity),
        "final_gross_exposure_bps": request.final_gross_exposure_bps,
        "final_abs_net_exposure_bps": request.final_abs_net_exposure_bps,
        "final_max_correlated_cluster_gross_bps": (
            request.final_max_correlated_cluster_gross_bps
        ),
        "final_leverage_milli": request.final_leverage_milli,
        "final_margin_utilization_bps": request.final_margin_utilization_bps,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "g8_authority": False,
        "execution_authority": False,
    }
    return PreTradeRiskDriftDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        final_quantity=_text(final_quantity),
    )
