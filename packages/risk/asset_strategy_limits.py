from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence


class AssetStrategyLimitError(ValueError):
    """P15-C asset/strategy-limit input violates governed invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class LimitRule:
    scope: str
    subject_id: str
    max_risk_bps: int
    max_open_positions: int
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.scope not in {"ASSET", "STRATEGY"}:
            raise AssetStrategyLimitError("scope must be ASSET or STRATEGY")
        if not self.subject_id.strip():
            raise AssetStrategyLimitError("subject_id must be non-empty")
        if not 0 <= self.max_risk_bps <= 10_000:
            raise AssetStrategyLimitError("max_risk_bps must be within [0, 10000]")
        if self.max_open_positions < 0:
            raise AssetStrategyLimitError("max_open_positions must be non-negative")

    @property
    def key(self) -> str:
        return f"{self.scope}:{self.subject_id}"


@dataclass(frozen=True)
class LimitUsage:
    scope: str
    subject_id: str
    risk_bps: int
    open_positions: int

    def __post_init__(self) -> None:
        if self.scope not in {"ASSET", "STRATEGY"}:
            raise AssetStrategyLimitError("scope must be ASSET or STRATEGY")
        if not self.subject_id.strip():
            raise AssetStrategyLimitError("subject_id must be non-empty")
        if not 0 <= self.risk_bps <= 10_000:
            raise AssetStrategyLimitError("risk_bps must be within [0, 10000]")
        if self.open_positions < 0:
            raise AssetStrategyLimitError("open_positions must be non-negative")

    @property
    def key(self) -> str:
        return f"{self.scope}:{self.subject_id}"


@dataclass(frozen=True)
class AssetStrategyLimitRequest:
    request_id: str
    upstream_size_decision_id: str
    upstream_size_status: str
    asset_id: str
    strategy_id: str
    incremental_risk_bps: int
    incremental_positions: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise AssetStrategyLimitError("request_id must be non-empty")
        if not self.upstream_size_decision_id.strip():
            raise AssetStrategyLimitError(
                "upstream_size_decision_id must be non-empty"
            )
        if not self.asset_id.strip() or not self.strategy_id.strip():
            raise AssetStrategyLimitError("asset_id and strategy_id must be non-empty")
        if not 0 <= self.incremental_risk_bps <= 10_000:
            raise AssetStrategyLimitError(
                "incremental_risk_bps must be within [0, 10000]"
            )
        if self.incremental_positions < 0:
            raise AssetStrategyLimitError(
                "incremental_positions must be non-negative"
            )
        if self.as_of_ns < 0:
            raise AssetStrategyLimitError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class AssetStrategyLimitDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    evaluated_keys: tuple[str, ...]
    portfolio_correlation_authority: bool = False
    leverage_authority: bool = False
    execution_authority: bool = False


@dataclass(frozen=True)
class AssetStrategyLimitPolicy:
    policy_version: str
    rules: tuple[LimitRule, ...]
    policy_id: str

    @classmethod
    def build(
        cls,
        *,
        policy_version: str,
        rules: Sequence[LimitRule],
    ) -> "AssetStrategyLimitPolicy":
        if not policy_version.strip():
            raise AssetStrategyLimitError("policy_version must be non-empty")
        ordered = tuple(sorted(rules, key=lambda item: item.key))
        if not ordered:
            raise AssetStrategyLimitError("at least one limit rule is required")
        keys = [rule.key for rule in ordered]
        if len(set(keys)) != len(keys):
            raise AssetStrategyLimitError("duplicate limit rule key")
        payload = {
            "policy_version": policy_version,
            "rules": [
                {
                    "scope": rule.scope,
                    "subject_id": rule.subject_id,
                    "max_risk_bps": rule.max_risk_bps,
                    "max_open_positions": rule.max_open_positions,
                    "enabled": rule.enabled,
                }
                for rule in ordered
            ],
        }
        return cls(
            policy_version=policy_version,
            rules=ordered,
            policy_id=_sha256(payload),
        )

    @property
    def by_key(self) -> Mapping[str, LimitRule]:
        return {rule.key: rule for rule in self.rules}

    def evaluate(
        self,
        *,
        request: AssetStrategyLimitRequest,
        usage: Sequence[LimitUsage],
    ) -> AssetStrategyLimitDecision:
        reasons: list[str] = []
        if request.upstream_size_status != "SIZE_CANDIDATE":
            reasons.append("UPSTREAM_SIZE_NOT_CANDIDATE")

        usage_by_key = {item.key: item for item in usage}
        if len(usage_by_key) != len(usage):
            raise AssetStrategyLimitError("duplicate usage key")

        required = (
            f"ASSET:{request.asset_id}",
            f"STRATEGY:{request.strategy_id}",
        )
        for key in required:
            rule = self.by_key.get(key)
            current = usage_by_key.get(key)
            if rule is None:
                reasons.append(f"MISSING_RULE:{key}")
                continue
            if current is None:
                reasons.append(f"MISSING_USAGE:{key}")
                continue
            if not rule.enabled:
                reasons.append(f"LIMIT_DISABLED:{key}")
                continue
            if current.risk_bps > rule.max_risk_bps:
                raise AssetStrategyLimitError(
                    f"current usage exceeds governed risk limit: {key}"
                )
            if current.open_positions > rule.max_open_positions:
                raise AssetStrategyLimitError(
                    f"current positions exceed governed limit: {key}"
                )
            if current.risk_bps + request.incremental_risk_bps > rule.max_risk_bps:
                reasons.append(f"RISK_LIMIT_EXCEEDED:{key}")
            if (
                current.open_positions + request.incremental_positions
                > rule.max_open_positions
            ):
                reasons.append(f"POSITION_COUNT_LIMIT_EXCEEDED:{key}")

        status = "VETO" if reasons else "LIMITS_ELIGIBLE"
        payload = {
            "policy_id": self.policy_id,
            "request_id": request.request_id,
            "upstream_size_decision_id": request.upstream_size_decision_id,
            "upstream_size_status": request.upstream_size_status,
            "asset_id": request.asset_id,
            "strategy_id": request.strategy_id,
            "incremental_risk_bps": request.incremental_risk_bps,
            "incremental_positions": request.incremental_positions,
            "as_of_ns": request.as_of_ns,
            "usage": [
                {
                    "scope": item.scope,
                    "subject_id": item.subject_id,
                    "risk_bps": item.risk_bps,
                    "open_positions": item.open_positions,
                }
                for item in sorted(usage, key=lambda x: x.key)
            ],
            "status": status,
            "reason_codes": reasons,
            "evaluated_keys": required,
            "portfolio_correlation_authority": False,
            "leverage_authority": False,
            "execution_authority": False,
        }
        return AssetStrategyLimitDecision(
            decision_id=_sha256(payload),
            request_id=request.request_id,
            status=status,
            reason_codes=tuple(reasons),
            evaluated_keys=required,
        )
