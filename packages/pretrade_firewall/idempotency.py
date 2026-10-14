from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Sequence


class IdempotencyPrecheckError(ValueError):
    """P16-B duplicate/idempotency input violates firewall invariants."""


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise IdempotencyPrecheckError(f"{field} must be lowercase SHA-256")
    return parsed


@dataclass(frozen=True)
class IdempotencyPolicy:
    policy_version: str
    replay_lookback_ns: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise IdempotencyPrecheckError("policy_version must be non-empty")
        if self.replay_lookback_ns <= 0:
            raise IdempotencyPrecheckError("replay_lookback_ns must be positive")

    @property
    def policy_id(self) -> str:
        return _sha256(
            {
                "policy_version": self.policy_version,
                "replay_lookback_ns": self.replay_lookback_ns,
            }
        )


@dataclass(frozen=True)
class PriorAdmission:
    idempotency_key: str
    intent_fingerprint_sha256: str
    admitted_at_ns: int

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            raise IdempotencyPrecheckError("prior idempotency_key must be non-empty")
        object.__setattr__(
            self,
            "intent_fingerprint_sha256",
            _sha256_text(
                self.intent_fingerprint_sha256,
                field="prior intent_fingerprint_sha256",
            ),
        )
        if self.admitted_at_ns < 0:
            raise IdempotencyPrecheckError("prior admitted_at_ns must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "idempotency_key": self.idempotency_key,
            "intent_fingerprint_sha256": self.intent_fingerprint_sha256,
            "admitted_at_ns": self.admitted_at_ns,
        }


@dataclass(frozen=True)
class IdempotencyPrecheckRequest:
    request_id: str
    upstream_freshness_decision_id: str
    upstream_freshness_status: str
    idempotency_key: str
    intent_fingerprint_sha256: str
    as_of_ns: int
    prior_admissions: tuple[PriorAdmission, ...]

    @classmethod
    def build(
        cls,
        *,
        request_id: str,
        upstream_freshness_decision_id: str,
        upstream_freshness_status: str,
        idempotency_key: str,
        intent_fingerprint_sha256: str,
        as_of_ns: int,
        prior_admissions: Sequence[PriorAdmission],
    ) -> "IdempotencyPrecheckRequest":
        return cls(
            request_id=request_id,
            upstream_freshness_decision_id=upstream_freshness_decision_id,
            upstream_freshness_status=upstream_freshness_status,
            idempotency_key=idempotency_key,
            intent_fingerprint_sha256=intent_fingerprint_sha256,
            as_of_ns=as_of_ns,
            prior_admissions=tuple(
                sorted(
                    prior_admissions,
                    key=lambda item: (
                        item.admitted_at_ns,
                        item.idempotency_key,
                        item.intent_fingerprint_sha256,
                    ),
                )
            ),
        )

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise IdempotencyPrecheckError("request_id must be non-empty")
        if not self.upstream_freshness_decision_id.strip():
            raise IdempotencyPrecheckError(
                "upstream_freshness_decision_id must be non-empty"
            )
        if self.upstream_freshness_status not in {"PRETRADE_A_ELIGIBLE", "VETO"}:
            raise IdempotencyPrecheckError("unknown upstream_freshness_status")
        if not self.idempotency_key.strip():
            raise IdempotencyPrecheckError("idempotency_key must be non-empty")
        object.__setattr__(
            self,
            "intent_fingerprint_sha256",
            _sha256_text(
                self.intent_fingerprint_sha256,
                field="intent_fingerprint_sha256",
            ),
        )
        if self.as_of_ns < 0:
            raise IdempotencyPrecheckError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class IdempotencyPrecheckDecision:
    decision_id: str
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    matched_record_count: int
    g8_authority: bool = False
    execution_authority: bool = False


def evaluate_idempotency(
    *,
    policy: IdempotencyPolicy,
    request: IdempotencyPrecheckRequest,
) -> IdempotencyPrecheckDecision:
    reasons: set[str] = set()
    matched = 0

    if request.upstream_freshness_status == "VETO":
        reasons.add("UPSTREAM_FRESHNESS_VETO")

    relevant: list[PriorAdmission] = []
    for record in request.prior_admissions:
        if record.admitted_at_ns > request.as_of_ns:
            reasons.add("FUTURE_PRIOR_ADMISSION")
            continue
        age_ns = request.as_of_ns - record.admitted_at_ns
        if age_ns <= policy.replay_lookback_ns:
            relevant.append(record)

    for record in relevant:
        key_match = record.idempotency_key == request.idempotency_key
        fingerprint_match = (
            record.intent_fingerprint_sha256 == request.intent_fingerprint_sha256
        )
        if key_match or fingerprint_match:
            matched += 1
        if key_match and fingerprint_match:
            reasons.add("DUPLICATE_IDEMPOTENCY_KEY")
        elif key_match:
            reasons.add("IDEMPOTENCY_KEY_COLLISION")
        elif fingerprint_match:
            reasons.add("DUPLICATE_INTENT_FINGERPRINT")

    reason_codes = tuple(sorted(reasons))
    status = "VETO" if reason_codes else "PRETRADE_B_ELIGIBLE"
    payload = {
        "policy_id": policy.policy_id,
        "request_id": request.request_id,
        "upstream_freshness_decision_id": request.upstream_freshness_decision_id,
        "upstream_freshness_status": request.upstream_freshness_status,
        "idempotency_key": request.idempotency_key,
        "intent_fingerprint_sha256": request.intent_fingerprint_sha256,
        "as_of_ns": request.as_of_ns,
        "prior_admissions": [item.payload() for item in request.prior_admissions],
        "status": status,
        "reason_codes": reason_codes,
        "matched_record_count": matched,
        "g8_authority": False,
        "execution_authority": False,
    }
    return IdempotencyPrecheckDecision(
        decision_id=_sha256(payload),
        request_id=request.request_id,
        status=status,
        reason_codes=reason_codes,
        matched_record_count=matched,
    )
