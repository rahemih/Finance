from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re


class PromotionGovernanceError(ValueError):
    """P18-H fail-closed promotion governance invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_TARGETS = {"DEMO_CHAMPION", "LIVE"}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe_id(value: str, *, field: str) -> str:
    parsed=value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise PromotionGovernanceError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed=value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise PromotionGovernanceError(f"{field} must be lowercase SHA-256")
    return parsed


@dataclass(frozen=True, slots=True)
class PromotionRequest:
    request_name: str
    target: str
    candidate_record_id: str
    comparison_record_id: str
    drift_report_id: str
    audit_bundle_sha256: str
    candidate_validation_passed: bool
    challenger_recommended: bool
    risk_review_passed: bool
    audit_complete: bool
    critical_blockers: int

    def __post_init__(self) -> None:
        _safe_id(self.request_name, field="request_name")
        if self.target not in _TARGETS:
            raise PromotionGovernanceError("invalid promotion target")
        _sha(self.candidate_record_id, field="candidate_record_id")
        _sha(self.comparison_record_id, field="comparison_record_id")
        _sha(self.drift_report_id, field="drift_report_id")
        _sha(self.audit_bundle_sha256, field="audit_bundle_sha256")
        if self.critical_blockers < 0:
            raise PromotionGovernanceError("critical_blockers must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version":"1.0","request_name":self.request_name,"target":self.target,
            "candidate_record_id":self.candidate_record_id,
            "comparison_record_id":self.comparison_record_id,
            "drift_report_id":self.drift_report_id,
            "audit_bundle_sha256":self.audit_bundle_sha256,
            "candidate_validation_passed":self.candidate_validation_passed,
            "challenger_recommended":self.challenger_recommended,
            "risk_review_passed":self.risk_review_passed,
            "audit_complete":self.audit_complete,
            "critical_blockers":self.critical_blockers,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    request_id: str
    status: str
    reasons: tuple[str, ...]
    registry_mutation: bool = False
    promotion_execution_authority: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @property
    def decision_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "schema_version":"1.0","request_id":self.request_id,"status":self.status,
            "reasons":list(self.reasons),"registry_mutation":self.registry_mutation,
            "promotion_execution_authority":self.promotion_execution_authority,
            "automatic_live_promotion":self.automatic_live_promotion,
            "live_trading":self.live_trading,"auto_trading":self.auto_trading,
        })).hexdigest()


class PromotionGovernor:
    def __init__(self) -> None:
        self._names: set[str] = set()
        self._ids: set[str] = set()

    def evaluate(self, request: PromotionRequest) -> PromotionDecision:
        if request.request_name in self._names or request.request_id in self._ids:
            raise PromotionGovernanceError("duplicate or conflicting promotion request")
        self._names.add(request.request_name); self._ids.add(request.request_id)

        if request.target == "LIVE":
            return PromotionDecision(
                request_id=request.request_id,
                status="OWNER_LIVE_GATE_REQUIRED",
                reasons=("LIVE_PROMOTION_FORBIDDEN_IN_P18",),
            )

        reasons: list[str] = []
        if not request.candidate_validation_passed:
            reasons.append("CANDIDATE_VALIDATION_FAILED")
        if not request.challenger_recommended:
            reasons.append("CHALLENGER_NOT_RECOMMENDED")
        if not request.risk_review_passed:
            reasons.append("RISK_REVIEW_FAILED")
        if not request.audit_complete:
            reasons.append("AUDIT_INCOMPLETE")
        if request.critical_blockers:
            reasons.append("CRITICAL_BLOCKERS_PRESENT")

        return PromotionDecision(
            request_id=request.request_id,
            status="APPROVE_DEMO_CHAMPION_RECORD" if not reasons else "HOLD",
            reasons=tuple(reasons),
        )
