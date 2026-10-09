from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast

from .quarantine_routing import RouteDisposition, RoutingDecision


class QualitySloError(ValueError):
    """Quality SLO policy or observation input is invalid."""


class SloComparator(StrEnum):
    MIN_GTE = "MIN_GTE"
    MAX_LTE = "MAX_LTE"


class SloStatus(StrEnum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    NO_DATA = "NO_DATA"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise QualitySloError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise QualitySloError(f"{field} must be a positive integer")
    return value


def _bps(value: object, *, field: str, scale: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > scale:
        raise QualitySloError(f"{field} must be between 0 and {scale}")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QualitySloError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class SloRule:
    slo_id: str
    metric: str
    comparator: SloComparator
    objective_bps: int
    critical_boundary_bps: int

    def validate(self, *, scale: int) -> None:
        _text(self.slo_id, field="slo_id")
        _text(self.metric, field="metric")
        _bps(self.objective_bps, field="objective_bps", scale=scale)
        _bps(self.critical_boundary_bps, field="critical_boundary_bps", scale=scale)
        if self.comparator is SloComparator.MIN_GTE and self.critical_boundary_bps > self.objective_bps:
            raise QualitySloError("MIN_GTE critical boundary must be <= objective")
        if self.comparator is SloComparator.MAX_LTE and self.critical_boundary_bps < self.objective_bps:
            raise QualitySloError("MAX_LTE critical boundary must be >= objective")


@dataclass(frozen=True, slots=True)
class QualitySloPolicy:
    policy_version: str
    rate_scale_bps: int
    no_data_severity: SloStatus
    slos: tuple[SloRule, ...]
    production_observability_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "QualitySloPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise QualitySloError(f"invalid quality SLO policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise QualitySloError("unsupported quality SLO policy schema_version")
        if raw.get("task_id") != "FIN-P07-WG-001":
            raise QualitySloError("unexpected quality SLO task_id")
        if raw.get("no_data_severity") != "CRITICAL":
            raise QualitySloError("NO_DATA must remain blocking/critical")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise QualitySloError("reference quality SLO evaluator must be offline")
        scale = _positive_int(raw.get("rate_scale_bps"), field="rate_scale_bps")
        policy_version = _text(raw.get("policy_version"), field="policy_version")
        vendor = _text(raw.get("production_observability_vendor"), field="production_observability_vendor")

        slos_raw = raw.get("slos")
        if not isinstance(slos_raw, list) or not slos_raw:
            raise QualitySloError("slos must be a non-empty list")
        slos: list[SloRule] = []
        for idx, item in enumerate(cast(list[object], slos_raw)):
            value = _mapping(item, field=f"slos[{idx}]")
            try:
                comparator = SloComparator(_text(value.get("comparator"), field="comparator"))
            except ValueError as exc:
                raise QualitySloError("unsupported SLO comparator") from exc
            rule = SloRule(
                slo_id=_text(value.get("slo_id"), field="slo_id"),
                metric=_text(value.get("metric"), field="metric"),
                comparator=comparator,
                objective_bps=_bps(value.get("objective_bps"), field="objective_bps", scale=scale),
                critical_boundary_bps=_bps(
                    value.get("critical_boundary_bps"),
                    field="critical_boundary_bps",
                    scale=scale,
                ),
            )
            rule.validate(scale=scale)
            slos.append(rule)
        if len({rule.slo_id for rule in slos}) != len(slos):
            raise QualitySloError("SLO IDs must be unique")
        if len({rule.metric for rule in slos}) != len(slos):
            raise QualitySloError("SLO metrics must be unique")
        required_metrics = {"trusted_route_bps", "quarantine_rate_bps", "unknown_block_rate_bps"}
        if {rule.metric for rule in slos} != required_metrics:
            raise QualitySloError("policy must define exactly the canonical P07-G metrics")
        return cls(
            policy_version=policy_version,
            rate_scale_bps=scale,
            no_data_severity=SloStatus.CRITICAL,
            slos=tuple(sorted(slos, key=lambda rule: rule.slo_id)),
            production_observability_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class QualityRouteObservation:
    subject_id: str
    disposition: RouteDisposition
    decision_evidence_sha256: str

    def __post_init__(self) -> None:
        _text(self.subject_id, field="subject_id")
        if _SHA256.fullmatch(self.decision_evidence_sha256) is None:
            raise QualitySloError("decision_evidence_sha256 must be lowercase SHA-256")

    @classmethod
    def from_routing_decision(cls, decision: RoutingDecision) -> "QualityRouteObservation":
        return cls(
            subject_id=decision.subject_id,
            disposition=decision.disposition,
            decision_evidence_sha256=decision.decision_id,
        )


@dataclass(frozen=True, slots=True)
class SloEvaluation:
    slo_id: str
    metric: str
    value_bps: int | None
    status: SloStatus

    def payload(self) -> dict[str, object]:
        return {
            "slo_id": self.slo_id,
            "metric": self.metric,
            "value_bps": self.value_bps,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class QualityDashboardSnapshot:
    policy_version: str
    total_count: int
    accepted_count: int
    quarantined_count: int
    blocked_unknown_count: int
    trusted_route_bps: int | None
    quarantine_rate_bps: int | None
    unknown_block_rate_bps: int | None
    evaluations: tuple[SloEvaluation, ...]
    highest_severity: SloStatus
    blocking: bool
    decision_evidence_sha256s: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": "1.0",
            "policy_version": self.policy_version,
            "total_count": self.total_count,
            "accepted_count": self.accepted_count,
            "quarantined_count": self.quarantined_count,
            "blocked_unknown_count": self.blocked_unknown_count,
            "trusted_route_bps": self.trusted_route_bps,
            "quarantine_rate_bps": self.quarantine_rate_bps,
            "unknown_block_rate_bps": self.unknown_block_rate_bps,
            "evaluations": [value.payload() for value in self.evaluations],
            "highest_severity": self.highest_severity.value,
            "blocking": self.blocking,
            "decision_evidence_sha256s": list(self.decision_evidence_sha256s),
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class QualitySloEvaluator:
    def __init__(self, policy: QualitySloPolicy) -> None:
        self._policy = policy

    def _evaluate_rule(self, rule: SloRule, value_bps: int) -> SloStatus:
        if rule.comparator is SloComparator.MIN_GTE:
            if value_bps >= rule.objective_bps:
                return SloStatus.HEALTHY
            if value_bps >= rule.critical_boundary_bps:
                return SloStatus.WARNING
            return SloStatus.CRITICAL
        if value_bps <= rule.objective_bps:
            return SloStatus.HEALTHY
        if value_bps <= rule.critical_boundary_bps:
            return SloStatus.WARNING
        return SloStatus.CRITICAL

    def evaluate(
        self,
        observations: tuple[QualityRouteObservation, ...],
    ) -> QualityDashboardSnapshot:
        if len({item.subject_id for item in observations}) != len(observations):
            raise QualitySloError("subject observations must be unique")

        ordered = tuple(sorted(observations, key=lambda item: item.subject_id))
        evidence = tuple(sorted(item.decision_evidence_sha256 for item in ordered))
        if not ordered:
            evaluations = tuple(
                SloEvaluation(
                    slo_id=rule.slo_id,
                    metric=rule.metric,
                    value_bps=None,
                    status=SloStatus.NO_DATA,
                )
                for rule in self._policy.slos
            )
            return QualityDashboardSnapshot(
                policy_version=self._policy.policy_version,
                total_count=0,
                accepted_count=0,
                quarantined_count=0,
                blocked_unknown_count=0,
                trusted_route_bps=None,
                quarantine_rate_bps=None,
                unknown_block_rate_bps=None,
                evaluations=evaluations,
                highest_severity=self._policy.no_data_severity,
                blocking=True,
                decision_evidence_sha256s=(),
            )

        accepted = sum(item.disposition is RouteDisposition.ACCEPTED_DOWNSTREAM for item in ordered)
        quarantined = sum(item.disposition is RouteDisposition.QUARANTINED for item in ordered)
        blocked = sum(item.disposition is RouteDisposition.BLOCKED_UNKNOWN for item in ordered)
        total = len(ordered)
        if accepted + quarantined + blocked != total:
            raise QualitySloError("unsupported routing disposition")

        scale = self._policy.rate_scale_bps
        metrics = {
            "trusted_route_bps": accepted * scale // total,
            "quarantine_rate_bps": quarantined * scale // total,
            "unknown_block_rate_bps": blocked * scale // total,
        }
        evaluations = tuple(
            SloEvaluation(
                slo_id=rule.slo_id,
                metric=rule.metric,
                value_bps=metrics[rule.metric],
                status=self._evaluate_rule(rule, metrics[rule.metric]),
            )
            for rule in self._policy.slos
        )
        severity_rank = {
            SloStatus.HEALTHY: 0,
            SloStatus.WARNING: 1,
            SloStatus.CRITICAL: 2,
            SloStatus.NO_DATA: 3,
        }
        highest = max((value.status for value in evaluations), key=lambda status: severity_rank[status])
        return QualityDashboardSnapshot(
            policy_version=self._policy.policy_version,
            total_count=total,
            accepted_count=accepted,
            quarantined_count=quarantined,
            blocked_unknown_count=blocked,
            trusted_route_bps=metrics["trusted_route_bps"],
            quarantine_rate_bps=metrics["quarantine_rate_bps"],
            unknown_block_rate_bps=metrics["unknown_block_rate_bps"],
            evaluations=evaluations,
            highest_severity=highest,
            blocking=highest in {SloStatus.CRITICAL, SloStatus.NO_DATA},
            decision_evidence_sha256s=evidence,
        )
