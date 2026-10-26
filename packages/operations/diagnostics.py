from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast

from .system_state import SystemState


DiagnosticCategory = Literal["DATA_PIPELINE", "RECONCILIATION", "DEPENDENCY", "CAPACITY", "SECURITY", "UNKNOWN"]
DiagnosticSeverity = Literal["INFO", "WARNING", "CRITICAL", "EMERGENCY"]
DiagnosticStatus = Literal["MATCHED_RULE", "UNRESOLVED"]


class DiagnosticsError(ValueError):
    """P22-C deterministic diagnostics invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hex_id(value: str, *, field: str, length: int) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise DiagnosticsError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _epoch_ns(value: int) -> int:
    if isinstance(value, bool) or value < 0:
        raise DiagnosticsError("observed_at_ns must be a non-negative integer epoch-ns value")
    return value


def _codes(values: tuple[str, ...], *, max_count: int, max_length: int) -> tuple[str, ...]:
    if not values:
        raise DiagnosticsError("at least one symptom code is required")
    if len(values) > max_count:
        raise DiagnosticsError("symptom count exceeds policy")
    normalized: list[str] = []
    for value in values:
        item = value.strip().upper()
        if not item or len(item) > max_length:
            raise DiagnosticsError("invalid symptom code")
        if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-." for ch in item):
            raise DiagnosticsError("symptom code contains unsupported characters")
        normalized.append(item)
    if len(set(normalized)) != len(normalized):
        raise DiagnosticsError("duplicate symptom codes are forbidden")
    return tuple(sorted(normalized))


def _evidence_refs(values: tuple[str, ...], *, max_count: int, length: int) -> tuple[str, ...]:
    if not values:
        raise DiagnosticsError("at least one evidence reference is required")
    if len(values) > max_count:
        raise DiagnosticsError("evidence reference count exceeds policy")
    normalized = tuple(sorted(_hex_id(value, field="evidence_ref", length=length) for value in values))
    if len(set(normalized)) != len(normalized):
        raise DiagnosticsError("duplicate evidence references are forbidden")
    return normalized


@dataclass(frozen=True, slots=True)
class DiagnosticRule:
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    hypothesis_code: str


@dataclass(frozen=True, slots=True)
class DiagnosticsPolicy:
    rules: Mapping[str, DiagnosticRule]
    state_severity_floor: Mapping[SystemState, DiagnosticSeverity]
    max_symptom_count: int
    max_symptom_length: int
    max_evidence_ref_count: int
    evidence_ref_hex_length: int
    correlation_id_hex_length: int

    @classmethod
    def from_path(cls, path: Path) -> "DiagnosticsPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DiagnosticsError(f"invalid P22-C policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise DiagnosticsError("P22-C policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22C_DIAGNOSTICS_POLICY",
            "task_id": "FIN-P22-WC-001",
            "mode": "DETERMINISTIC_REFERENCE_AUTO_DIAGNOSTICS",
            "max_symptom_count": 8,
            "max_symptom_length": 96,
            "max_evidence_ref_count": 8,
            "evidence_ref_hex_length": 64,
            "correlation_id_hex_length": 32,
            "severity_order": ["INFO", "WARNING", "CRITICAL", "EMERGENCY"],
            "state_severity_floor": {
                "NORMAL": "INFO",
                "DEGRADED": "WARNING",
                "SAFE_MODE": "CRITICAL",
                "HALTED": "CRITICAL",
                "EMERGENCY": "EMERGENCY",
                "RECOVERY": "WARNING",
            },
            "rules": {
                "DATA_STALE": ["DATA_PIPELINE", "WARNING", "DATA_FRESHNESS_DEGRADATION"],
                "DATA_GAP": ["DATA_PIPELINE", "CRITICAL", "DATA_GAP_OR_SEQUENCE_BREAK"],
                "RECONCILIATION_MISMATCH": ["RECONCILIATION", "CRITICAL", "STATE_DIVERGENCE"],
                "DEPENDENCY_UNAVAILABLE": ["DEPENDENCY", "CRITICAL", "UPSTREAM_UNAVAILABLE"],
                "RESOURCE_EXHAUSTION": ["CAPACITY", "CRITICAL", "CAPACITY_PRESSURE"],
                "SECURITY_INTEGRITY_ALERT": ["SECURITY", "EMERGENCY", "SECURITY_INTEGRITY_RISK"],
            },
            "unknown_symptom_status": "UNRESOLVED",
            "unknown_hypothesis": "UNRESOLVED_REQUIRES_OPERATOR_REVIEW",
            "operator_review_required": True,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "automatic_remediation": False,
            "automatic_self_healing": False,
            "automatic_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise DiagnosticsError(f"P22-C policy mismatch: {key}")

        rules: dict[str, DiagnosticRule] = {
            "DATA_STALE": DiagnosticRule("DATA_PIPELINE", "WARNING", "DATA_FRESHNESS_DEGRADATION"),
            "DATA_GAP": DiagnosticRule("DATA_PIPELINE", "CRITICAL", "DATA_GAP_OR_SEQUENCE_BREAK"),
            "RECONCILIATION_MISMATCH": DiagnosticRule("RECONCILIATION", "CRITICAL", "STATE_DIVERGENCE"),
            "DEPENDENCY_UNAVAILABLE": DiagnosticRule("DEPENDENCY", "CRITICAL", "UPSTREAM_UNAVAILABLE"),
            "RESOURCE_EXHAUSTION": DiagnosticRule("CAPACITY", "CRITICAL", "CAPACITY_PRESSURE"),
            "SECURITY_INTEGRITY_ALERT": DiagnosticRule("SECURITY", "EMERGENCY", "SECURITY_INTEGRITY_RISK"),
        }
        floors: dict[SystemState, DiagnosticSeverity] = {
            "NORMAL": "INFO",
            "DEGRADED": "WARNING",
            "SAFE_MODE": "CRITICAL",
            "HALTED": "CRITICAL",
            "EMERGENCY": "EMERGENCY",
            "RECOVERY": "WARNING",
        }
        return cls(rules, floors, 8, 96, 8, 64, 32)

    @property
    def policy_id(self) -> str:
        payload = {
            "rules": {key: [rule.category, rule.severity, rule.hypothesis_code] for key, rule in sorted(self.rules.items())},
            "state_severity_floor": dict(sorted(self.state_severity_floor.items())),
            "max_symptom_count": self.max_symptom_count,
            "max_symptom_length": self.max_symptom_length,
            "max_evidence_ref_count": self.max_evidence_ref_count,
            "evidence_ref_hex_length": self.evidence_ref_hex_length,
            "correlation_id_hex_length": self.correlation_id_hex_length,
            "automatic_remediation": False,
            "automatic_self_healing": False,
            "automatic_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    report_id: str
    policy_id: str
    system_state: SystemState
    status: DiagnosticStatus
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    hypothesis_code: str
    symptom_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    observed_at_ns: int
    correlation_id: str
    operator_review_required: bool
    remediation_authority: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "system_state": self.system_state,
            "status": self.status,
            "category": self.category,
            "severity": self.severity,
            "hypothesis_code": self.hypothesis_code,
            "symptom_codes": list(self.symptom_codes),
            "evidence_refs": list(self.evidence_refs),
            "observed_at_ns": self.observed_at_ns,
            "correlation_id": self.correlation_id,
            "operator_review_required": self.operator_review_required,
            "remediation_authority": self.remediation_authority,
        }


def diagnose(
    policy: DiagnosticsPolicy,
    *,
    system_state: SystemState,
    symptom_codes: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    observed_at_ns: int,
    correlation_id: str,
) -> DiagnosticReport:
    if system_state not in policy.state_severity_floor:
        raise DiagnosticsError("unsupported system state")
    symptoms = _codes(symptom_codes, max_count=policy.max_symptom_count, max_length=policy.max_symptom_length)
    evidence = _evidence_refs(evidence_refs, max_count=policy.max_evidence_ref_count, length=policy.evidence_ref_hex_length)
    timestamp = _epoch_ns(observed_at_ns)
    correlation = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)

    severity_rank: dict[DiagnosticSeverity, int] = {"INFO": 0, "WARNING": 1, "CRITICAL": 2, "EMERGENCY": 3}
    matched: list[tuple[str, DiagnosticRule]] = []
    for symptom in symptoms:
        rule = policy.rules.get(symptom)
        if rule is not None:
            matched.append((symptom, rule))

    if matched:
        matched.sort(key=lambda item: (-severity_rank[item[1].severity], item[0]))
        _, primary = matched[0]
        status: DiagnosticStatus = "MATCHED_RULE"
        category: DiagnosticCategory = primary.category
        severity: DiagnosticSeverity = primary.severity
        hypothesis = primary.hypothesis_code
        operator_review = severity in ("CRITICAL", "EMERGENCY")
    else:
        status = "UNRESOLVED"
        category = "UNKNOWN"
        severity = "WARNING"
        hypothesis = "UNRESOLVED_REQUIRES_OPERATOR_REVIEW"
        operator_review = True

    floor = policy.state_severity_floor[system_state]
    if severity_rank[floor] > severity_rank[severity]:
        severity = floor
        operator_review = True

    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "system_state": system_state,
        "status": status,
        "category": category,
        "severity": severity,
        "hypothesis_code": hypothesis,
        "symptom_codes": list(symptoms),
        "evidence_refs": list(evidence),
        "observed_at_ns": timestamp,
        "correlation_id": correlation,
        "operator_review_required": operator_review,
        "remediation_authority": False,
    }
    report_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return DiagnosticReport(
        report_id,
        policy.policy_id,
        system_state,
        status,
        category,
        severity,
        hypothesis,
        symptoms,
        evidence,
        timestamp,
        correlation,
        operator_review,
        False,
    )
