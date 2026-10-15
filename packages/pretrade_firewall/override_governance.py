from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re


class OverrideGovernanceError(ValueError):
    """P16-G override request violates fail-closed governance invariants."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OVERRIDE_SCOPES = {
    "PRETRADE_VETO_REVIEW",
    "CIRCUIT_RESET_REQUEST",
    "EMERGENCY_POLICY_CHANGE_REQUEST",
}


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class OverrideGovernancePolicy:
    policy_version: str
    max_request_ttl_ns: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise OverrideGovernanceError("policy_version must be non-empty")
        if self.max_request_ttl_ns <= 0:
            raise OverrideGovernanceError("max_request_ttl_ns must be positive")

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "max_request_ttl_ns": self.max_request_ttl_ns,
            }
        )


@dataclass(frozen=True)
class OverrideRequest:
    override_request_id: str
    requested_by: str
    scope: str
    reason: str
    evidence_sha256: str
    requested_at_ns: int
    expires_at_ns: int

    def __post_init__(self) -> None:
        if not self.override_request_id.strip():
            raise OverrideGovernanceError("override_request_id must be non-empty")
        if not self.requested_by.strip():
            raise OverrideGovernanceError("requested_by must be non-empty")
        if self.scope not in _OVERRIDE_SCOPES:
            raise OverrideGovernanceError("unsupported override scope")
        if not self.reason.strip():
            raise OverrideGovernanceError("override reason must be non-empty")
        digest = self.evidence_sha256.strip().lower()
        if _SHA256.fullmatch(digest) is None:
            raise OverrideGovernanceError("evidence_sha256 must be lowercase SHA-256")
        object.__setattr__(self, "evidence_sha256", digest)
        if self.requested_at_ns < 0 or self.expires_at_ns < 0:
            raise OverrideGovernanceError("override timestamps must be non-negative")
        if self.expires_at_ns <= self.requested_at_ns:
            raise OverrideGovernanceError(
                "override expires_at_ns must be after requested_at_ns"
            )

    def payload(self) -> dict[str, object]:
        return {
            "override_request_id": self.override_request_id,
            "requested_by": self.requested_by,
            "scope": self.scope,
            "reason": self.reason,
            "evidence_sha256": self.evidence_sha256,
            "requested_at_ns": self.requested_at_ns,
            "expires_at_ns": self.expires_at_ns,
        }


@dataclass(frozen=True)
class OverrideGovernanceInput:
    request_id: str
    upstream_daily_loss_decision_id: str
    upstream_daily_loss_status: str
    override_request: OverrideRequest | None
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise OverrideGovernanceError("request_id must be non-empty")
        if not self.upstream_daily_loss_decision_id.strip():
            raise OverrideGovernanceError(
                "upstream_daily_loss_decision_id must be non-empty"
            )
        if self.upstream_daily_loss_status not in {"PRETRADE_F_ELIGIBLE", "VETO"}:
            raise OverrideGovernanceError("unknown upstream_daily_loss_status")
        if self.as_of_ns < 0:
            raise OverrideGovernanceError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class OverrideGovernanceDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    override_request_id: str | None
    approval_authority: bool = False
    reset_authority: bool = False
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_override_governance(
    *,
    policy: OverrideGovernancePolicy,
    request: OverrideGovernanceInput,
) -> OverrideGovernanceDecision:
    reasons: list[str] = []
    override = request.override_request

    if override is None:
        if request.upstream_daily_loss_status == "VETO":
            reasons.append("UPSTREAM_DAILY_LOSS_VETO")
            status = "VETO"
        else:
            status = "PRETRADE_G_ELIGIBLE"
    else:
        invalid = False
        if override.requested_at_ns > request.as_of_ns:
            reasons.append("FUTURE_OVERRIDE_REQUEST")
            invalid = True
        if override.expires_at_ns <= request.as_of_ns:
            reasons.append("EXPIRED_OVERRIDE_REQUEST")
            invalid = True
        if (
            override.expires_at_ns - override.requested_at_ns
            > policy.max_request_ttl_ns
        ):
            reasons.append("OVERRIDE_TTL_EXCEEDED")
            invalid = True

        if invalid:
            status = "VETO"
        else:
            reasons.append("EXPLICIT_APPROVAL_REQUIRED")
            if request.upstream_daily_loss_status == "VETO":
                reasons.append("UPSTREAM_VETO_REMAINS_BLOCKING")
            status = "WAITING_FOR_APPROVAL"

    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_daily_loss_decision_id": request.upstream_daily_loss_decision_id,
        "upstream_daily_loss_status": request.upstream_daily_loss_status,
        "override_request": None if override is None else override.payload(),
        "as_of_ns": request.as_of_ns,
        "status": status,
        "reason_codes": reasons,
        "approval_authority": False,
        "reset_authority": False,
        "g8_authority": False,
        "execution_authority": False,
    }
    return OverrideGovernanceDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=tuple(reasons),
        override_request_id=(
            None if override is None else override.override_request_id
        ),
    )
