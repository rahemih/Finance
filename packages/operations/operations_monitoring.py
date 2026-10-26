from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, Mapping, cast


MonitoringStatus = Literal["HEALTHY", "WARNING", "CRITICAL", "UNASSESSED"]


class OperationsMonitoringError(ValueError):
    """P22-I deterministic operations-monitoring invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OperationsMonitoringError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OperationsMonitoringError(f"{field} must be a non-negative integer")
    return value


def _string_object_dict(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise OperationsMonitoringError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise OperationsMonitoringError(f"{field} keys must be text")
        result[key] = item
    return result


def _hex_id(value: str, *, field: str, length: int = 64) -> str:
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in "0123456789abcdef" for ch in normalized):
        raise OperationsMonitoringError(f"{field} must be {length} lowercase hex characters")
    return normalized


def _ceil_ratio_bps(value: int, limit: int) -> int:
    if limit <= 0:
        raise OperationsMonitoringError("ratio limit must be positive")
    if value == 0:
        return 0
    return (value * 10_000 + limit - 1) // limit


@dataclass(frozen=True, slots=True)
class LatencyRule:
    p95_ms: int
    p99_ms: int | None


@dataclass(frozen=True, slots=True)
class CapacityEnvelope:
    average_events_per_second: int
    peak_events_per_second: int
    active_streams: int
    concurrent_agent_runs: int


@dataclass(frozen=True, slots=True)
class OperationsMonitoringPolicy:
    latency_slos: Mapping[str, LatencyRule]
    latency_review_after_consecutive_miss_windows: int
    operating: CapacityEnvelope
    stress: CapacityEnvelope
    capacity_review_threshold_bps_of_operating: int
    cost_alert_bps: int
    cost_throttle_bps: int
    cost_freeze_bps: int
    daily_cost_anomaly_ratio_bps: int
    protected_safety_workloads: tuple[str, ...]

    @classmethod
    def from_path(cls, path: Path) -> "OperationsMonitoringPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise OperationsMonitoringError(f"invalid P22-I policy JSON: {exc}") from exc
        raw = _string_object_dict(raw_value, field="P22-I policy root")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22I_SLO_CAPACITY_COST_POLICY",
            "task_id": "FIN-P22-WI-001",
            "mode": "DETERMINISTIC_REFERENCE_OPERATIONS_MONITORING",
            "latency_architecture_review_after_consecutive_miss_windows": 3,
            "capacity_review_threshold_bps_of_operating": 7000,
            "cost_guardrails_bps": {
                "alert_review": 7000,
                "throttle_discretionary_research_recommended": 8500,
                "freeze_discretionary_new_research_recommended": 10000,
            },
            "daily_cost_anomaly_ratio_bps": 20000,
            "monthly_budget_source": "CALLER_SUPPLIED",
            "cost_unit": "INTEGER_MICROUNITS_CALLER_CURRENCY",
            "protected_safety_workloads": [
                "RISK",
                "FIREWALL",
                "SECURITY",
                "AUDIT",
                "RECONCILIATION",
                "KILL_SWITCH",
            ],
            "production_sla_certification": False,
            "automatic_capacity_scaling": False,
            "automatic_cost_shedding": False,
            "automatic_safety_workload_throttling": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "runtime_state_mutation": False,
            "external_order_authority": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected_static.items():
            if raw.get(key) != expected_value:
                raise OperationsMonitoringError(f"P22-I policy mismatch: {key}")

        latency_raw = _string_object_dict(raw.get("latency_slos_ms"), field="latency_slos_ms")
        expected_latency: dict[str, tuple[int, int | None]] = {
            "L_FAST_DATA": (250, 1000),
            "L_SIGNAL_STANDARD": (2000, None),
            "L_RISK_FIREWALL": (100, 250),
            "L_OMS_DISPATCH": (100, None),
            "L_UI": (2000, None),
        }
        latency_slos: dict[str, LatencyRule] = {}
        for slo_id, expected in expected_latency.items():
            item = _string_object_dict(latency_raw.get(slo_id), field=f"latency_slos_ms.{slo_id}")
            p95 = _positive_int(item.get("p95"), field=f"{slo_id}.p95")
            p99_raw: object = item.get("p99")
            p99 = None if p99_raw is None else _positive_int(p99_raw, field=f"{slo_id}.p99")
            if (p95, p99) != expected:
                raise OperationsMonitoringError(f"latency SLO mismatch: {slo_id}")
            latency_slos[slo_id] = LatencyRule(p95_ms=p95, p99_ms=p99)
        if set(latency_raw.keys()) != set(expected_latency):
            raise OperationsMonitoringError("latency_slos_ms must contain exactly the canonical P02 latency classes")

        capacity_raw = _string_object_dict(raw.get("capacity_envelopes"), field="capacity_envelopes")

        def envelope(name: str, expected: tuple[int, int, int, int]) -> CapacityEnvelope:
            item = _string_object_dict(capacity_raw.get(name), field=f"capacity_envelopes.{name}")
            values = (
                _positive_int(item.get("average_events_per_second"), field=f"{name}.average_events_per_second"),
                _positive_int(item.get("peak_events_per_second"), field=f"{name}.peak_events_per_second"),
                _positive_int(item.get("active_streams"), field=f"{name}.active_streams"),
                _positive_int(item.get("concurrent_agent_runs"), field=f"{name}.concurrent_agent_runs"),
            )
            if values != expected:
                raise OperationsMonitoringError(f"capacity envelope mismatch: {name}")
            return CapacityEnvelope(*values)

        operating = envelope("OPERATING", (2000, 20000, 75, 10))
        stress = envelope("STRESS", (10000, 50000, 200, 25))
        if set(capacity_raw.keys()) != {"OPERATING", "STRESS"}:
            raise OperationsMonitoringError("capacity_envelopes must contain exactly OPERATING and STRESS")

        return cls(
            latency_slos=latency_slos,
            latency_review_after_consecutive_miss_windows=3,
            operating=operating,
            stress=stress,
            capacity_review_threshold_bps_of_operating=7000,
            cost_alert_bps=7000,
            cost_throttle_bps=8500,
            cost_freeze_bps=10000,
            daily_cost_anomaly_ratio_bps=20000,
            protected_safety_workloads=(
                "RISK",
                "FIREWALL",
                "SECURITY",
                "AUDIT",
                "RECONCILIATION",
                "KILL_SWITCH",
            ),
        )

    @property
    def policy_id(self) -> str:
        payload = {
            "latency_slos": {
                key: {"p95_ms": value.p95_ms, "p99_ms": value.p99_ms}
                for key, value in sorted(self.latency_slos.items())
            },
            "latency_review_after_consecutive_miss_windows": self.latency_review_after_consecutive_miss_windows,
            "operating": {
                "average_events_per_second": self.operating.average_events_per_second,
                "peak_events_per_second": self.operating.peak_events_per_second,
                "active_streams": self.operating.active_streams,
                "concurrent_agent_runs": self.operating.concurrent_agent_runs,
            },
            "stress": {
                "average_events_per_second": self.stress.average_events_per_second,
                "peak_events_per_second": self.stress.peak_events_per_second,
                "active_streams": self.stress.active_streams,
                "concurrent_agent_runs": self.stress.concurrent_agent_runs,
            },
            "capacity_review_threshold_bps_of_operating": self.capacity_review_threshold_bps_of_operating,
            "cost_guardrails_bps": {
                "alert_review": self.cost_alert_bps,
                "throttle_discretionary_research_recommended": self.cost_throttle_bps,
                "freeze_discretionary_new_research_recommended": self.cost_freeze_bps,
            },
            "daily_cost_anomaly_ratio_bps": self.daily_cost_anomaly_ratio_bps,
            "protected_safety_workloads": self.protected_safety_workloads,
            "production_sla_certification": False,
            "automatic_capacity_scaling": False,
            "automatic_cost_shedding": False,
            "automatic_safety_workload_throttling": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "runtime_state_mutation": False,
            "external_order_authority": False,
            "live_execution_authority": False,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class LatencyObservation:
    slo_id: str
    p95_ms: int
    p99_ms: int | None
    consecutive_miss_windows: int
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class CapacityObservation:
    average_events_per_second: int
    peak_events_per_second: int
    active_streams: int
    concurrent_agent_runs: int
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class CostObservation:
    projected_monthly_cost_microunits: int
    monthly_budget_microunits: int | None
    daily_cost_microunits: int
    expected_daily_cost_microunits: int | None
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class LatencyEvaluation:
    slo_id: str
    p95_observed_ms: int
    p95_target_ms: int
    p99_observed_ms: int | None
    p99_target_ms: int | None
    target_met: bool
    consecutive_miss_windows: int
    status: MonitoringStatus
    architecture_review_required: bool

    def payload(self) -> dict[str, object]:
        return {
            "slo_id": self.slo_id,
            "p95_observed_ms": self.p95_observed_ms,
            "p95_target_ms": self.p95_target_ms,
            "p99_observed_ms": self.p99_observed_ms,
            "p99_target_ms": self.p99_target_ms,
            "target_met": self.target_met,
            "consecutive_miss_windows": self.consecutive_miss_windows,
            "status": self.status,
            "architecture_review_required": self.architecture_review_required,
        }


@dataclass(frozen=True, slots=True)
class CapacityEvaluation:
    resource: str
    observed: int
    operating_limit: int
    stress_limit: int
    operating_utilization_bps: int
    status: MonitoringStatus
    architecture_review_required: bool

    def payload(self) -> dict[str, object]:
        return {
            "resource": self.resource,
            "observed": self.observed,
            "operating_limit": self.operating_limit,
            "stress_limit": self.stress_limit,
            "operating_utilization_bps": self.operating_utilization_bps,
            "status": self.status,
            "architecture_review_required": self.architecture_review_required,
        }


@dataclass(frozen=True, slots=True)
class CostEvaluation:
    projected_monthly_cost_microunits: int
    monthly_budget_microunits: int | None
    budget_utilization_bps: int | None
    daily_cost_microunits: int
    expected_daily_cost_microunits: int | None
    daily_cost_ratio_bps: int | None
    daily_anomaly: bool
    status: MonitoringStatus
    recommendations: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "projected_monthly_cost_microunits": self.projected_monthly_cost_microunits,
            "monthly_budget_microunits": self.monthly_budget_microunits,
            "budget_utilization_bps": self.budget_utilization_bps,
            "daily_cost_microunits": self.daily_cost_microunits,
            "expected_daily_cost_microunits": self.expected_daily_cost_microunits,
            "daily_cost_ratio_bps": self.daily_cost_ratio_bps,
            "daily_anomaly": self.daily_anomaly,
            "status": self.status,
            "recommendations": list(self.recommendations),
        }


@dataclass(frozen=True, slots=True)
class OperationsMonitoringSnapshot:
    snapshot_id: str
    policy_id: str
    latency: tuple[LatencyEvaluation, ...]
    capacity: tuple[CapacityEvaluation, ...]
    cost: CostEvaluation
    highest_status: MonitoringStatus
    architecture_review_required: bool
    recommendations: tuple[str, ...]
    protected_safety_workloads: tuple[str, ...]
    evidence_sha256s: tuple[str, ...]
    execution_authority: bool
    automatic_capacity_scaling: bool
    automatic_cost_shedding: bool
    automatic_safety_workload_throttling: bool
    production_sla_certified: bool
    network_access: bool
    credential_access: bool
    runtime_state_mutation: bool
    external_order_authority: bool

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "latency": [item.payload() for item in self.latency],
            "capacity": [item.payload() for item in self.capacity],
            "cost": self.cost.payload(),
            "highest_status": self.highest_status,
            "architecture_review_required": self.architecture_review_required,
            "recommendations": list(self.recommendations),
            "protected_safety_workloads": list(self.protected_safety_workloads),
            "evidence_sha256s": list(self.evidence_sha256s),
            "execution_authority": self.execution_authority,
            "automatic_capacity_scaling": self.automatic_capacity_scaling,
            "automatic_cost_shedding": self.automatic_cost_shedding,
            "automatic_safety_workload_throttling": self.automatic_safety_workload_throttling,
            "production_sla_certified": self.production_sla_certified,
            "network_access": self.network_access,
            "credential_access": self.credential_access,
            "runtime_state_mutation": self.runtime_state_mutation,
            "external_order_authority": self.external_order_authority,
        }


def _latency_evaluations(
    policy: OperationsMonitoringPolicy,
    observations: tuple[LatencyObservation, ...],
) -> tuple[LatencyEvaluation, ...]:
    if len({item.slo_id for item in observations}) != len(observations):
        raise OperationsMonitoringError("latency observations must have unique slo_id values")
    by_id = {item.slo_id: item for item in observations}
    if set(by_id) != set(policy.latency_slos):
        raise OperationsMonitoringError("latency observations must cover exactly the canonical latency SLOs")

    evaluations: list[LatencyEvaluation] = []
    for slo_id in sorted(policy.latency_slos):
        rule = policy.latency_slos[slo_id]
        item = by_id[slo_id]
        p95 = _nonnegative_int(item.p95_ms, field=f"{slo_id}.p95_ms")
        misses = _nonnegative_int(item.consecutive_miss_windows, field=f"{slo_id}.consecutive_miss_windows")
        _hex_id(item.evidence_sha256, field=f"{slo_id}.evidence_sha256")
        if rule.p99_ms is None:
            if item.p99_ms is not None:
                raise OperationsMonitoringError(f"{slo_id} does not define a canonical p99 target")
            p99 = None
        else:
            if item.p99_ms is None:
                raise OperationsMonitoringError(f"{slo_id} requires p99 observation")
            p99 = _nonnegative_int(item.p99_ms, field=f"{slo_id}.p99_ms")

        target_met = p95 <= rule.p95_ms and (rule.p99_ms is None or (p99 is not None and p99 <= rule.p99_ms))
        if target_met and misses != 0:
            raise OperationsMonitoringError(f"{slo_id} target-met observation must reset consecutive_miss_windows to zero")
        review = (not target_met) and misses >= policy.latency_review_after_consecutive_miss_windows
        status: MonitoringStatus = "HEALTHY" if target_met else ("CRITICAL" if review else "WARNING")
        evaluations.append(
            LatencyEvaluation(
                slo_id=slo_id,
                p95_observed_ms=p95,
                p95_target_ms=rule.p95_ms,
                p99_observed_ms=p99,
                p99_target_ms=rule.p99_ms,
                target_met=target_met,
                consecutive_miss_windows=misses,
                status=status,
                architecture_review_required=review,
            )
        )
    return tuple(evaluations)


def _capacity_evaluations(
    policy: OperationsMonitoringPolicy,
    observation: CapacityObservation,
) -> tuple[CapacityEvaluation, ...]:
    _hex_id(observation.evidence_sha256, field="capacity.evidence_sha256")
    raw = (
        ("AVERAGE_EVENTS_PER_SECOND", _nonnegative_int(observation.average_events_per_second, field="average_events_per_second"), policy.operating.average_events_per_second, policy.stress.average_events_per_second),
        ("PEAK_EVENTS_PER_SECOND", _nonnegative_int(observation.peak_events_per_second, field="peak_events_per_second"), policy.operating.peak_events_per_second, policy.stress.peak_events_per_second),
        ("ACTIVE_STREAMS", _nonnegative_int(observation.active_streams, field="active_streams"), policy.operating.active_streams, policy.stress.active_streams),
        ("CONCURRENT_AGENT_RUNS", _nonnegative_int(observation.concurrent_agent_runs, field="concurrent_agent_runs"), policy.operating.concurrent_agent_runs, policy.stress.concurrent_agent_runs),
    )
    evaluations: list[CapacityEvaluation] = []
    for resource, observed, operating_limit, stress_limit in raw:
        utilization = _ceil_ratio_bps(observed, operating_limit)
        critical = observed >= stress_limit
        warning = utilization >= policy.capacity_review_threshold_bps_of_operating
        status: MonitoringStatus = "CRITICAL" if critical else ("WARNING" if warning else "HEALTHY")
        evaluations.append(
            CapacityEvaluation(
                resource=resource,
                observed=observed,
                operating_limit=operating_limit,
                stress_limit=stress_limit,
                operating_utilization_bps=utilization,
                status=status,
                architecture_review_required=critical,
            )
        )
    return tuple(evaluations)


def _cost_evaluation(policy: OperationsMonitoringPolicy, observation: CostObservation) -> CostEvaluation:
    projected = _nonnegative_int(observation.projected_monthly_cost_microunits, field="projected_monthly_cost_microunits")
    daily = _nonnegative_int(observation.daily_cost_microunits, field="daily_cost_microunits")
    _hex_id(observation.evidence_sha256, field="cost.evidence_sha256")

    budget = observation.monthly_budget_microunits
    if budget is not None:
        budget = _positive_int(budget, field="monthly_budget_microunits")
    expected_daily = observation.expected_daily_cost_microunits
    if expected_daily is not None:
        expected_daily = _positive_int(expected_daily, field="expected_daily_cost_microunits")

    budget_utilization = None if budget is None else _ceil_ratio_bps(projected, budget)
    daily_ratio = None if expected_daily is None else _ceil_ratio_bps(daily, expected_daily)
    daily_anomaly = daily_ratio is not None and daily_ratio >= policy.daily_cost_anomaly_ratio_bps

    recommendations: list[str] = []
    if budget_utilization is None:
        status: MonitoringStatus = "UNASSESSED"
        recommendations.append("OWNER_MONTHLY_BUDGET_REQUIRED_FOR_COST_EVALUATION")
    elif budget_utilization >= policy.cost_freeze_bps:
        status = "CRITICAL"
        recommendations.append("FREEZE_DISCRETIONARY_NEW_RESEARCH_SPEND_RECOMMENDED")
    elif budget_utilization >= policy.cost_throttle_bps:
        status = "WARNING"
        recommendations.append("THROTTLE_DISCRETIONARY_RESEARCH_RECOMMENDED")
    elif budget_utilization >= policy.cost_alert_bps:
        status = "WARNING"
        recommendations.append("ALERT_AND_REVIEW_COST_FORECAST")
    else:
        status = "HEALTHY"

    if daily_anomaly:
        recommendations.extend(
            (
                "INVESTIGATE_DAILY_COST_ANOMALY",
                "CIRCUIT_BREAK_OPTIONAL_AI_RESEARCH_RECOMMENDED",
            )
        )
        if status in ("HEALTHY", "UNASSESSED"):
            status = "WARNING"

    return CostEvaluation(
        projected_monthly_cost_microunits=projected,
        monthly_budget_microunits=budget,
        budget_utilization_bps=budget_utilization,
        daily_cost_microunits=daily,
        expected_daily_cost_microunits=expected_daily,
        daily_cost_ratio_bps=daily_ratio,
        daily_anomaly=daily_anomaly,
        status=status,
        recommendations=tuple(sorted(set(recommendations))),
    )


def evaluate_operations_monitoring(
    policy: OperationsMonitoringPolicy,
    *,
    latency_observations: tuple[LatencyObservation, ...],
    capacity_observation: CapacityObservation,
    cost_observation: CostObservation,
) -> OperationsMonitoringSnapshot:
    latency = _latency_evaluations(policy, latency_observations)
    capacity = _capacity_evaluations(policy, capacity_observation)
    cost = _cost_evaluation(policy, cost_observation)

    rank: dict[MonitoringStatus, int] = {
        "HEALTHY": 0,
        "UNASSESSED": 1,
        "WARNING": 2,
        "CRITICAL": 3,
    }
    statuses: list[MonitoringStatus] = []
    statuses.extend(item.status for item in latency)
    statuses.extend(item.status for item in capacity)
    statuses.append(cost.status)
    highest: MonitoringStatus = "HEALTHY"
    for status in statuses:
        if rank[status] > rank[highest]:
            highest = status
    architecture_review_required = any(item.architecture_review_required for item in latency) or any(
        item.architecture_review_required for item in capacity
    )

    recommendations = list(cost.recommendations)
    if any(item.status == "WARNING" for item in latency):
        recommendations.append("REVIEW_LATENCY_SLO_MISS")
    if any(item.architecture_review_required for item in latency):
        recommendations.append("ARCHITECTURE_REVIEW_REQUIRED_FOR_REPEATED_LATENCY_MISS")
    if any(item.status == "WARNING" for item in capacity):
        recommendations.append("REVIEW_CAPACITY_PRESSURE")
    if any(item.architecture_review_required for item in capacity):
        recommendations.append("ARCHITECTURE_REVIEW_REQUIRED_AT_STRESS_BOUNDARY")

    evidence = tuple(
        sorted(
            {
                *(_hex_id(item.evidence_sha256, field=f"latency[{item.slo_id}].evidence_sha256") for item in latency_observations),
                _hex_id(capacity_observation.evidence_sha256, field="capacity.evidence_sha256"),
                _hex_id(cost_observation.evidence_sha256, field="cost.evidence_sha256"),
            }
        )
    )

    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "latency": [item.payload() for item in latency],
        "capacity": [item.payload() for item in capacity],
        "cost": cost.payload(),
        "highest_status": highest,
        "architecture_review_required": architecture_review_required,
        "recommendations": sorted(set(recommendations)),
        "protected_safety_workloads": list(policy.protected_safety_workloads),
        "evidence_sha256s": list(evidence),
        "execution_authority": False,
        "automatic_capacity_scaling": False,
        "automatic_cost_shedding": False,
        "automatic_safety_workload_throttling": False,
        "production_sla_certified": False,
        "network_access": False,
        "credential_access": False,
        "runtime_state_mutation": False,
        "external_order_authority": False,
    }
    snapshot_id = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return OperationsMonitoringSnapshot(
        snapshot_id=snapshot_id,
        policy_id=policy.policy_id,
        latency=latency,
        capacity=capacity,
        cost=cost,
        highest_status=highest,
        architecture_review_required=architecture_review_required,
        recommendations=tuple(sorted(set(recommendations))),
        protected_safety_workloads=policy.protected_safety_workloads,
        evidence_sha256s=evidence,
        execution_authority=False,
        automatic_capacity_scaling=False,
        automatic_cost_shedding=False,
        automatic_safety_workload_throttling=False,
        production_sla_certified=False,
        network_access=False,
        credential_access=False,
        runtime_state_mutation=False,
        external_order_authority=False,
    )
