from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Mapping, Sequence


class PortfolioCorrelationError(ValueError):
    """P15-D portfolio/correlation input violates governed invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _pair_key(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


@dataclass(frozen=True)
class ExposureLeg:
    asset_id: str
    signed_exposure_bps: int

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise PortfolioCorrelationError("asset_id must be non-empty")


@dataclass(frozen=True)
class CorrelationPair:
    left_asset_id: str
    right_asset_id: str
    correlation_milli: int

    def __post_init__(self) -> None:
        if not self.left_asset_id.strip() or not self.right_asset_id.strip():
            raise PortfolioCorrelationError("correlation asset IDs must be non-empty")
        if self.left_asset_id == self.right_asset_id:
            raise PortfolioCorrelationError("correlation pair requires distinct assets")
        if not -1000 <= self.correlation_milli <= 1000:
            raise PortfolioCorrelationError(
                "correlation_milli must be within [-1000, 1000]"
            )

    @property
    def key(self) -> tuple[str, str]:
        return _pair_key(self.left_asset_id, self.right_asset_id)


@dataclass(frozen=True)
class PortfolioExposurePolicy:
    policy_version: str
    max_gross_exposure_bps: int
    max_abs_net_exposure_bps: int
    correlation_threshold_milli: int
    max_correlated_cluster_gross_bps: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise PortfolioCorrelationError("policy_version must be non-empty")
        if self.max_gross_exposure_bps < 0:
            raise PortfolioCorrelationError(
                "max_gross_exposure_bps must be non-negative"
            )
        if self.max_abs_net_exposure_bps < 0:
            raise PortfolioCorrelationError(
                "max_abs_net_exposure_bps must be non-negative"
            )
        if not 0 <= self.correlation_threshold_milli <= 1000:
            raise PortfolioCorrelationError(
                "correlation_threshold_milli must be within [0, 1000]"
            )
        if self.max_correlated_cluster_gross_bps < 0:
            raise PortfolioCorrelationError(
                "max_correlated_cluster_gross_bps must be non-negative"
            )

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "max_gross_exposure_bps": self.max_gross_exposure_bps,
                "max_abs_net_exposure_bps": self.max_abs_net_exposure_bps,
                "correlation_threshold_milli": self.correlation_threshold_milli,
                "max_correlated_cluster_gross_bps": (
                    self.max_correlated_cluster_gross_bps
                ),
            }
        )


@dataclass(frozen=True)
class PortfolioExposureRequest:
    request_id: str
    upstream_limit_decision_id: str
    upstream_limit_status: str
    candidate_asset_id: str
    candidate_signed_exposure_bps: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PortfolioCorrelationError("request_id must be non-empty")
        if not self.upstream_limit_decision_id.strip():
            raise PortfolioCorrelationError(
                "upstream_limit_decision_id must be non-empty"
            )
        if not self.candidate_asset_id.strip():
            raise PortfolioCorrelationError("candidate_asset_id must be non-empty")
        if self.candidate_signed_exposure_bps == 0:
            raise PortfolioCorrelationError(
                "candidate_signed_exposure_bps must be non-zero"
            )
        if self.as_of_ns < 0:
            raise PortfolioCorrelationError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class PortfolioExposureDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    gross_exposure_bps: int
    abs_net_exposure_bps: int
    max_correlated_cluster_gross_bps: int
    cluster_members: tuple[tuple[str, ...], ...]
    leverage_authority: bool = False
    execution_authority: bool = False


def _aggregate_exposures(
    existing: Sequence[ExposureLeg],
    candidate_asset_id: str,
    candidate_signed_exposure_bps: int,
) -> dict[str, int]:
    values: dict[str, int] = {}
    for leg in existing:
        values[leg.asset_id] = values.get(leg.asset_id, 0) + leg.signed_exposure_bps
    values[candidate_asset_id] = (
        values.get(candidate_asset_id, 0) + candidate_signed_exposure_bps
    )
    return {asset: value for asset, value in values.items() if value != 0}


def _correlation_map(
    pairs: Sequence[CorrelationPair],
) -> Mapping[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    for pair in pairs:
        if pair.key in result:
            raise PortfolioCorrelationError("duplicate correlation pair")
        result[pair.key] = pair.correlation_milli
    return result


def _clusters(
    exposures: Mapping[str, int],
    correlations: Mapping[tuple[str, str], int],
    threshold_milli: int,
) -> tuple[tuple[str, ...], ...]:
    assets = tuple(sorted(exposures))
    adjacency: dict[str, set[str]] = {asset: set() for asset in assets}
    for left, right in itertools.combinations(assets, 2):
        corr = correlations[_pair_key(left, right)]
        if abs(corr) >= threshold_milli:
            adjacency[left].add(right)
            adjacency[right].add(left)

    seen: set[str] = set()
    groups: list[tuple[str, ...]] = []
    for asset in assets:
        if asset in seen:
            continue
        stack = [asset]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - seen, reverse=True))
        groups.append(tuple(sorted(component)))
    return tuple(sorted(groups))


def evaluate_portfolio_exposure(
    *,
    policy: PortfolioExposurePolicy,
    request: PortfolioExposureRequest,
    existing: Sequence[ExposureLeg],
    correlations: Sequence[CorrelationPair],
) -> PortfolioExposureDecision:
    reasons: list[str] = []
    if request.upstream_limit_status != "LIMITS_ELIGIBLE":
        reasons.append("UPSTREAM_LIMITS_NOT_ELIGIBLE")

    exposures = _aggregate_exposures(
        existing,
        request.candidate_asset_id,
        request.candidate_signed_exposure_bps,
    )
    corr_map = _correlation_map(correlations)
    assets = tuple(sorted(exposures))
    for left, right in itertools.combinations(assets, 2):
        if _pair_key(left, right) not in corr_map:
            reasons.append(f"MISSING_CORRELATION:{left}:{right}")

    gross = sum(abs(value) for value in exposures.values())
    abs_net = abs(sum(exposures.values()))

    cluster_members: tuple[tuple[str, ...], ...] = tuple((asset,) for asset in assets)
    max_cluster_gross = max((abs(value) for value in exposures.values()), default=0)
    if not any(reason.startswith("MISSING_CORRELATION:") for reason in reasons):
        cluster_members = _clusters(
            exposures,
            corr_map,
            policy.correlation_threshold_milli,
        )
        max_cluster_gross = max(
            (
                sum(abs(exposures[asset]) for asset in cluster)
                for cluster in cluster_members
            ),
            default=0,
        )

    if gross > policy.max_gross_exposure_bps:
        reasons.append("GROSS_EXPOSURE_LIMIT_EXCEEDED")
    if abs_net > policy.max_abs_net_exposure_bps:
        reasons.append("NET_EXPOSURE_LIMIT_EXCEEDED")
    if max_cluster_gross > policy.max_correlated_cluster_gross_bps:
        reasons.append("CORRELATED_CLUSTER_LIMIT_EXCEEDED")

    status = "VETO" if reasons else "PORTFOLIO_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_limit_decision_id": request.upstream_limit_decision_id,
        "upstream_limit_status": request.upstream_limit_status,
        "candidate_asset_id": request.candidate_asset_id,
        "candidate_signed_exposure_bps": request.candidate_signed_exposure_bps,
        "as_of_ns": request.as_of_ns,
        "existing": [
            {
                "asset_id": leg.asset_id,
                "signed_exposure_bps": leg.signed_exposure_bps,
            }
            for leg in sorted(existing, key=lambda item: (item.asset_id, item.signed_exposure_bps))
        ],
        "correlations": [
            {
                "left": pair.key[0],
                "right": pair.key[1],
                "correlation_milli": pair.correlation_milli,
            }
            for pair in sorted(correlations, key=lambda item: item.key)
        ],
        "status": status,
        "reason_codes": reasons,
        "gross_exposure_bps": gross,
        "abs_net_exposure_bps": abs_net,
        "max_correlated_cluster_gross_bps": max_cluster_gross,
        "cluster_members": cluster_members,
        "leverage_authority": False,
        "execution_authority": False,
    }
    return PortfolioExposureDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        gross_exposure_bps=gross,
        abs_net_exposure_bps=abs_net,
        max_correlated_cluster_gross_bps=max_cluster_gross,
        cluster_members=cluster_members,
    )
