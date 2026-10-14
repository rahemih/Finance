from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import json

from packages.signal_intelligence.signal_output_contract import AnalyticalSignalOutput


class PreTradeFreshnessError(ValueError):
    """P16-A signal freshness / price-deviation input violates firewall invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ceil_bps(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise PreTradeFreshnessError("invalid deviation arithmetic")
    value = Decimal(numerator) * Decimal(10_000) / Decimal(denominator)
    return int(value.to_integral_value(rounding=ROUND_CEILING))


@dataclass(frozen=True)
class PreTradeFreshnessPolicy:
    policy_version: str
    max_signal_age_ns: int
    max_price_deviation_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise PreTradeFreshnessError("policy_version must be non-empty")
        if self.max_signal_age_ns < 0:
            raise PreTradeFreshnessError("max_signal_age_ns must be non-negative")
        if not 0 <= self.max_price_deviation_bps <= 10_000:
            raise PreTradeFreshnessError(
                "max_price_deviation_bps must be within [0, 10000]"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "max_signal_age_ns": self.max_signal_age_ns,
                "max_price_deviation_bps": self.max_price_deviation_bps,
            }
        )


@dataclass(frozen=True)
class PreTradeFreshnessRequest:
    request_id: str
    signal: AnalyticalSignalOutput
    current_price_scaled: int
    current_price_scale: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PreTradeFreshnessError("request_id must be non-empty")
        if self.current_price_scaled <= 0:
            raise PreTradeFreshnessError("current_price_scaled must be positive")
        if self.current_price_scale <= 0:
            raise PreTradeFreshnessError("current_price_scale must be positive")
        if self.as_of_ns < 0:
            raise PreTradeFreshnessError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class PreTradeFreshnessDecision:
    decision_id: str
    request_id: str
    signal_id: str
    status: str
    reason_codes: tuple[str, ...]
    signal_age_ns: int
    price_deviation_bps: int
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_signal_freshness(
    *,
    policy: PreTradeFreshnessPolicy,
    request: PreTradeFreshnessRequest,
) -> PreTradeFreshnessDecision:
    signal = request.signal
    reasons: list[str] = []

    if signal.action not in {"LONG", "SHORT"}:
        reasons.append("NON_DIRECTIONAL_SIGNAL")
    if (
        signal.entry_low_scaled is None
        or signal.entry_high_scaled is None
        or signal.price_scale is None
    ):
        reasons.append("MISSING_DIRECTIONAL_GEOMETRY")
    if request.as_of_ns < signal.as_of_time_ns:
        reasons.append("FUTURE_DATED_SIGNAL")

    signal_age_ns = max(0, request.as_of_ns - signal.as_of_time_ns)

    if signal.price_scale is not None and request.current_price_scale != signal.price_scale:
        reasons.append("PRICE_SCALE_MISMATCH")

    deviation_bps = 0
    if signal.entry_low_scaled is not None and signal.entry_high_scaled is not None:
        if signal.entry_low_scaled <= 0 or signal.entry_high_scaled <= 0:
            reasons.append("INVALID_ENTRY_ZONE")
        elif signal.entry_low_scaled > signal.entry_high_scaled:
            reasons.append("INVALID_ENTRY_ZONE")
        elif request.current_price_scaled < signal.entry_low_scaled:
            deviation_bps = _ceil_bps(
                signal.entry_low_scaled - request.current_price_scaled,
                signal.entry_low_scaled,
            )
        elif request.current_price_scaled > signal.entry_high_scaled:
            deviation_bps = _ceil_bps(
                request.current_price_scaled - signal.entry_high_scaled,
                signal.entry_high_scaled,
            )

    if signal_age_ns > policy.max_signal_age_ns:
        reasons.append("SIGNAL_AGE_LIMIT_EXCEEDED")
    if deviation_bps > policy.max_price_deviation_bps:
        reasons.append("PRICE_DEVIATION_LIMIT_EXCEEDED")

    status = "VETO" if reasons else "PRETRADE_A_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "signal_id": signal.signal_id,
        "signal_action": signal.action,
        "signal_as_of_time_ns": signal.as_of_time_ns,
        "current_price_scaled": request.current_price_scaled,
        "current_price_scale": request.current_price_scale,
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "signal_age_ns": signal_age_ns,
        "price_deviation_bps": deviation_bps,
        "g8_authority": False,
        "execution_authority": False,
    }
    return PreTradeFreshnessDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        signal_id=signal.signal_id,
        status=status,
        reason_codes=tuple(reasons),
        signal_age_ns=signal_age_ns,
        price_deviation_bps=deviation_bps,
    )
