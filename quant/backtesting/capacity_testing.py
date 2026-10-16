from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
import re
from typing import Sequence

from .execution_realism import (
    ExecutionRealismPolicy,
    HistoricalExecutionContext,
    HistoricalDepthLevel,
)


class CapacityTestingError(ValueError):
    """P17-F historical liquidity/capacity testing invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_CAPACITY_PROBES = 100_000


def _sha(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise CapacityTestingError(f"{field} must be lowercase SHA-256")
    return parsed


def _decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise CapacityTestingError(f"{field} must be a decimal string") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise CapacityTestingError(f"{field} must be finite and positive")
    return parsed


def _text(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _ceil_ratio_bps(numerator: Decimal, denominator: Decimal) -> int:
    value = numerator * Decimal(10_000) / denominator
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def _floor_ratio_bps(numerator: Decimal, denominator: Decimal) -> int:
    value = numerator * Decimal(10_000) / denominator
    return int(value.to_integral_value(rounding=ROUND_FLOOR))


@dataclass(frozen=True, slots=True)
class CapacityProbeDiagnostic:
    context_id: str
    scale_bps: int
    requested_quantity: str
    eligible_displayed_capacity: str
    filled_quantity: str
    fill_ratio_bps: int
    capacity_utilization_bps: int
    adverse_slippage_bps: int | None
    depth_levels_consumed: int

    def payload(self) -> dict[str, object]:
        return {
            "context_id": self.context_id,
            "scale_bps": self.scale_bps,
            "requested_quantity": self.requested_quantity,
            "eligible_displayed_capacity": self.eligible_displayed_capacity,
            "filled_quantity": self.filled_quantity,
            "fill_ratio_bps": self.fill_ratio_bps,
            "capacity_utilization_bps": self.capacity_utilization_bps,
            "adverse_slippage_bps": self.adverse_slippage_bps,
            "depth_levels_consumed": self.depth_levels_consumed,
        }


@dataclass(frozen=True, slots=True)
class CapacityScaleSummary:
    scale_bps: int
    worst_fill_ratio_bps: int
    max_capacity_utilization_bps: int
    worst_adverse_slippage_bps: int | None
    zero_fill_context_count: int
    all_contexts_full_fill: bool

    def payload(self) -> dict[str, object]:
        return {
            "scale_bps": self.scale_bps,
            "worst_fill_ratio_bps": self.worst_fill_ratio_bps,
            "max_capacity_utilization_bps": self.max_capacity_utilization_bps,
            "worst_adverse_slippage_bps": self.worst_adverse_slippage_bps,
            "zero_fill_context_count": self.zero_fill_context_count,
            "all_contexts_full_fill": self.all_contexts_full_fill,
        }


@dataclass(frozen=True, slots=True)
class LiquidityCapacityCertificate:
    certificate_id: str
    status: str
    robustness_certificate_id: str
    execution_policy_id: str
    asset_id: str
    side: str
    scale_summaries: tuple[CapacityScaleSummary, ...]
    max_full_fill_scale_bps: int
    hidden_liquidity_inference: bool = False
    market_impact_claim: bool = False
    profitability_claim_authority: bool = False
    g9_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


def _probe(
    *,
    context: HistoricalExecutionContext,
    policy: ExecutionRealismPolicy,
    side: str,
    requested: Decimal,
    scale_bps: int,
) -> CapacityProbeDiagnostic:
    levels: tuple[HistoricalDepthLevel, ...] = (
        context.asks if side == "BUY" else context.bids
    )
    eligible_capacity = Decimal(0)
    filled = Decimal(0)
    notional_scaled = Decimal(0)
    consumed = 0

    for level in levels:
        allowed = (
            level.quantity
            * Decimal(policy.max_displayed_depth_participation_bps)
            / Decimal(10_000)
        )
        eligible_capacity += allowed
        if filled >= requested or allowed <= 0:
            continue
        take = min(requested - filled, allowed)
        if take > 0:
            filled += take
            notional_scaled += take * Decimal(level.price_scaled)
            consumed += 1

    fill_ratio_bps = _floor_ratio_bps(filled, requested)
    utilization_bps = _ceil_ratio_bps(requested, eligible_capacity)

    slippage: int | None = None
    if filled > 0:
        raw_scaled = notional_scaled / filled
        rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
        fill_price = int(raw_scaled.to_integral_value(rounding=rounding))
        best = levels[0].price_scaled
        adverse = (
            Decimal(fill_price - best)
            if side == "BUY"
            else Decimal(best - fill_price)
        )
        if adverse < 0:
            raise CapacityTestingError("computed favorable slippage in adverse metric")
        slippage = _ceil_ratio_bps(adverse, Decimal(best))

    return CapacityProbeDiagnostic(
        context_id=context.context_id,
        scale_bps=scale_bps,
        requested_quantity=_text(requested),
        eligible_displayed_capacity=_text(eligible_capacity),
        filled_quantity=_text(filled),
        fill_ratio_bps=fill_ratio_bps,
        capacity_utilization_bps=utilization_bps,
        adverse_slippage_bps=slippage,
        depth_levels_consumed=consumed,
    )


def evaluate_liquidity_capacity(
    *,
    robustness_certificate_id: str,
    execution_policy: ExecutionRealismPolicy,
    side: str,
    baseline_quantity: str,
    contexts: Sequence[HistoricalExecutionContext],
    scale_bps: Sequence[int],
) -> LiquidityCapacityCertificate:
    robustness_id = _sha(
        robustness_certificate_id,
        field="robustness_certificate_id",
    )
    if side not in {"BUY", "SELL"}:
        raise CapacityTestingError("side must be BUY or SELL")
    baseline = _decimal(baseline_quantity, field="baseline_quantity")

    ordered_contexts = tuple(
        sorted(
            contexts,
            key=lambda item: (item.event_time_ns, item.sequence, item.context_id),
        )
    )
    if not ordered_contexts:
        raise CapacityTestingError("at least one historical context is required")
    context_ids = tuple(item.context_id for item in ordered_contexts)
    sequences = tuple(item.sequence for item in ordered_contexts)
    if len(context_ids) != len(set(context_ids)):
        raise CapacityTestingError("duplicate historical context_id")
    if len(sequences) != len(set(sequences)):
        raise CapacityTestingError("duplicate historical context sequence")

    asset_ids = {item.asset_id for item in ordered_contexts}
    price_scales = {item.price_scale for item in ordered_contexts}
    if len(asset_ids) != 1:
        raise CapacityTestingError("capacity test contexts must share one asset")
    if len(price_scales) != 1:
        raise CapacityTestingError("capacity test contexts must share one price scale")
    asset_id = next(iter(asset_ids))

    scales = tuple(sorted(scale_bps))
    if not scales:
        raise CapacityTestingError("at least one scale_bps value is required")
    if any(item <= 0 for item in scales):
        raise CapacityTestingError("scale_bps values must be positive")
    if len(scales) != len(set(scales)):
        raise CapacityTestingError("duplicate scale_bps")
    if len(scales) * len(ordered_contexts) > MAX_CAPACITY_PROBES:
        raise CapacityTestingError("capacity test exceeds computational safety cap")

    diagnostics: list[CapacityProbeDiagnostic] = []
    summaries: list[CapacityScaleSummary] = []
    for scale in scales:
        requested = baseline * Decimal(scale) / Decimal(10_000)
        scale_diagnostics = [
            _probe(
                context=context,
                policy=execution_policy,
                side=side,
                requested=requested,
                scale_bps=scale,
            )
            for context in ordered_contexts
        ]
        diagnostics.extend(scale_diagnostics)
        slippages = [
            item.adverse_slippage_bps
            for item in scale_diagnostics
            if item.adverse_slippage_bps is not None
        ]
        summaries.append(
            CapacityScaleSummary(
                scale_bps=scale,
                worst_fill_ratio_bps=min(
                    item.fill_ratio_bps for item in scale_diagnostics
                ),
                max_capacity_utilization_bps=max(
                    item.capacity_utilization_bps for item in scale_diagnostics
                ),
                worst_adverse_slippage_bps=(
                    None if not slippages else max(slippages)
                ),
                zero_fill_context_count=sum(
                    1 for item in scale_diagnostics if item.fill_ratio_bps == 0
                ),
                all_contexts_full_fill=all(
                    item.fill_ratio_bps == 10_000
                    for item in scale_diagnostics
                ),
            )
        )

    full_fill_scales = [
        item.scale_bps for item in summaries if item.all_contexts_full_fill
    ]
    max_full_fill_scale = max(full_fill_scales, default=0)

    body = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17F_LIQUIDITY_CAPACITY_CERTIFICATE",
        "status": "CAPACITY_EVALUATED",
        "robustness_certificate_id": robustness_id,
        "execution_policy_id": execution_policy.policy_id,
        "asset_id": asset_id,
        "side": side,
        "baseline_quantity": _text(baseline),
        "context_ids": list(context_ids),
        "scale_bps": list(scales),
        "diagnostics": [item.payload() for item in diagnostics],
        "scale_summaries": [item.payload() for item in summaries],
        "max_full_fill_scale_bps": max_full_fill_scale,
        "hidden_liquidity_inference": False,
        "market_impact_claim": False,
        "profitability_claim_authority": False,
        "g9_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    return LiquidityCapacityCertificate(
        certificate_id=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
        status="CAPACITY_EVALUATED",
        robustness_certificate_id=robustness_id,
        execution_policy_id=execution_policy.policy_id,
        asset_id=asset_id,
        side=side,
        scale_summaries=tuple(summaries),
        max_full_fill_scale_bps=max_full_fill_scale,
    )
