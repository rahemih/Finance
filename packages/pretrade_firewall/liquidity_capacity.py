from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
import json

from packages.order_flow_liquidity.liquidity_heatmap import (
    LiquidityHeatmapSnapshot,
)
from packages.order_flow_liquidity.order_book import OrderBookMetrics


class PreTradeLiquidityCapacityError(ValueError):
    """P16-D spread/liquidity/capacity input violates firewall invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _decimal(value: str, field: str, *, allow_zero: bool = False) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise PreTradeLiquidityCapacityError(
            f"{field} must be a decimal string"
        ) from exc
    if not parsed.is_finite():
        raise PreTradeLiquidityCapacityError(f"{field} must be finite")
    if allow_zero:
        if parsed < 0:
            raise PreTradeLiquidityCapacityError(
                f"{field} must be non-negative"
            )
    elif parsed <= 0:
        raise PreTradeLiquidityCapacityError(f"{field} must be positive")
    return parsed


def _text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _ceil_bps(numerator: Decimal, denominator: Decimal) -> int:
    if numerator < 0 or denominator <= 0:
        raise PreTradeLiquidityCapacityError("invalid capacity arithmetic")
    value = numerator * Decimal(10_000) / denominator
    return int(value.to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True)
class PreTradeLiquidityCapacityPolicy:
    policy_version: str
    max_spread_bps: int
    capacity_band_bps: int
    max_displayed_capacity_utilization_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise PreTradeLiquidityCapacityError(
                "policy_version must be non-empty"
            )
        if self.max_spread_bps < 0:
            raise PreTradeLiquidityCapacityError(
                "max_spread_bps must be non-negative"
            )
        if self.capacity_band_bps <= 0:
            raise PreTradeLiquidityCapacityError(
                "capacity_band_bps must be positive"
            )
        if not 1 <= self.max_displayed_capacity_utilization_bps <= 10_000:
            raise PreTradeLiquidityCapacityError(
                "max_displayed_capacity_utilization_bps must be within [1, 10000]"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "max_spread_bps": self.max_spread_bps,
                "capacity_band_bps": self.capacity_band_bps,
                "max_displayed_capacity_utilization_bps": (
                    self.max_displayed_capacity_utilization_bps
                ),
            }
        )


@dataclass(frozen=True)
class PreTradeLiquidityCapacityRequest:
    request_id: str
    upstream_risk_envelope_decision_id: str
    upstream_risk_envelope_status: str
    trade_side: str
    requested_notional: str
    order_book_metrics: OrderBookMetrics
    liquidity_heatmap: LiquidityHeatmapSnapshot
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PreTradeLiquidityCapacityError(
                "request_id must be non-empty"
            )
        if not self.upstream_risk_envelope_decision_id.strip():
            raise PreTradeLiquidityCapacityError(
                "upstream_risk_envelope_decision_id must be non-empty"
            )
        if self.upstream_risk_envelope_status not in {
            "PRETRADE_C_ELIGIBLE",
            "VETO",
        }:
            raise PreTradeLiquidityCapacityError(
                "unknown upstream_risk_envelope_status"
            )
        if self.trade_side not in {"LONG", "SHORT"}:
            raise PreTradeLiquidityCapacityError(
                "trade_side must be LONG or SHORT"
            )
        _decimal(self.requested_notional, "requested_notional")
        if self.as_of_ns < 0:
            raise PreTradeLiquidityCapacityError(
                "as_of_ns must be non-negative"
            )


@dataclass(frozen=True)
class PreTradeLiquidityCapacityDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    spread_bps: int
    displayed_capacity_notional: str
    capacity_utilization_bps: int
    hidden_liquidity_inference: bool = False
    fillability_claim: bool = False
    slippage_or_market_impact_claim: bool = False
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_liquidity_capacity(
    *,
    policy: PreTradeLiquidityCapacityPolicy,
    request: PreTradeLiquidityCapacityRequest,
) -> PreTradeLiquidityCapacityDecision:
    reasons: set[str] = set()

    if request.upstream_risk_envelope_status == "VETO":
        reasons.add("UPSTREAM_RISK_ENVELOPE_VETO")

    metrics = request.order_book_metrics
    heatmap = request.liquidity_heatmap
    if metrics.snapshot_id != heatmap.source_snapshot_id:
        reasons.add("MICROSTRUCTURE_SNAPSHOT_MISMATCH")
    if metrics.spread_bps < 0:
        reasons.add("INVALID_SPREAD")
    elif metrics.spread_bps > policy.max_spread_bps:
        reasons.add("SPREAD_LIMIT_EXCEEDED")

    matching = tuple(
        band
        for band in heatmap.bands
        if band.upper_distance_bps_inclusive == policy.capacity_band_bps
    )
    displayed = Decimal(0)
    if len(matching) != 1:
        reasons.add("CAPACITY_BAND_MISSING")
    else:
        band = matching[0]
        capacity_text = (
            band.cumulative_ask_notional_text
            if request.trade_side == "LONG"
            else band.cumulative_bid_notional_text
        )
        displayed = _decimal(
            capacity_text,
            "displayed_capacity_notional",
            allow_zero=True,
        )
        if displayed <= 0:
            reasons.add("NO_DISPLAYED_CAPACITY")

    requested = _decimal(request.requested_notional, "requested_notional")
    utilization_bps = 0
    if displayed > 0:
        utilization_bps = _ceil_bps(requested, displayed)
        if (
            utilization_bps
            > policy.max_displayed_capacity_utilization_bps
        ):
            reasons.add("DISPLAYED_CAPACITY_LIMIT_EXCEEDED")

    reason_codes = tuple(sorted(reasons))
    status = "VETO" if reason_codes else "PRETRADE_D_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_risk_envelope_decision_id": (
            request.upstream_risk_envelope_decision_id
        ),
        "upstream_risk_envelope_status": (
            request.upstream_risk_envelope_status
        ),
        "trade_side": request.trade_side,
        "requested_notional": _text(requested),
        "order_book_metrics_id": metrics.metrics_id,
        "liquidity_heatmap_id": heatmap.heatmap_id,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reason_codes,
        "spread_bps": metrics.spread_bps,
        "displayed_capacity_notional": _text(displayed),
        "capacity_utilization_bps": utilization_bps,
        "hidden_liquidity_inference": False,
        "fillability_claim": False,
        "slippage_or_market_impact_claim": False,
        "g8_authority": False,
        "execution_authority": False,
    }
    return PreTradeLiquidityCapacityDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=reason_codes,
        spread_bps=metrics.spread_bps,
        displayed_capacity_notional=_text(displayed),
        capacity_utilization_bps=utilization_bps,
    )
