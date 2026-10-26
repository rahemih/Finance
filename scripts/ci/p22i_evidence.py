from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.operations.operations_monitoring import (
    CapacityObservation,
    CostObservation,
    LatencyObservation,
    OperationsMonitoringPolicy,
    evaluate_operations_monitoring,
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _healthy_latency() -> tuple[LatencyObservation, ...]:
    return (
        LatencyObservation("L_FAST_DATA", 200, 800, 0, "1" * 64),
        LatencyObservation("L_SIGNAL_STANDARD", 1500, None, 0, "2" * 64),
        LatencyObservation("L_RISK_FIREWALL", 80, 200, 0, "3" * 64),
        LatencyObservation("L_OMS_DISPATCH", 80, None, 0, "4" * 64),
        LatencyObservation("L_UI", 1500, None, 0, "5" * 64),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy_path = Path("config/operations/slo-capacity-cost-policy.json")
    capacity_envelope_path = Path("docs/04-architecture/capacity-cost-envelope.json")
    quality_slo_path = Path("config/data-quality/quality-slo-policy.json")
    policy = OperationsMonitoringPolicy.from_path(policy_path)

    healthy = evaluate_operations_monitoring(
        policy,
        latency_observations=_healthy_latency(),
        capacity_observation=CapacityObservation(1000, 10000, 30, 4, "a" * 64),
        cost_observation=CostObservation(50_000_000, 100_000_000, 1_000_000, 1_000_000, "b" * 64),
    )

    pressure_latency = list(_healthy_latency())
    pressure_latency[2] = LatencyObservation("L_RISK_FIREWALL", 120, 260, 3, "3" * 64)
    pressure = evaluate_operations_monitoring(
        policy,
        latency_observations=tuple(pressure_latency),
        capacity_observation=CapacityObservation(10000, 50000, 200, 25, "c" * 64),
        cost_observation=CostObservation(100_000_000, 100_000_000, 2_000_000, 1_000_000, "d" * 64),
    )

    unbudgeted = evaluate_operations_monitoring(
        policy,
        latency_observations=_healthy_latency(),
        capacity_observation=CapacityObservation(1000, 10000, 30, 4, "e" * 64),
        cost_observation=CostObservation(50_000_000, None, 1_000_000, None, "f" * 64),
    )

    if healthy.highest_status != "HEALTHY":
        raise SystemExit("P22-I healthy scenario changed")
    if pressure.highest_status != "CRITICAL" or not pressure.architecture_review_required:
        raise SystemExit("P22-I pressure scenario must require architecture review")
    if "FREEZE_DISCRETIONARY_NEW_RESEARCH_SPEND_RECOMMENDED" not in pressure.recommendations:
        raise SystemExit("P22-I 100 percent budget guardrail changed")
    if "CIRCUIT_BREAK_OPTIONAL_AI_RESEARCH_RECOMMENDED" not in pressure.recommendations:
        raise SystemExit("P22-I 2x daily cost anomaly guardrail changed")
    if unbudgeted.cost.status != "UNASSESSED" or unbudgeted.cost.monthly_budget_microunits is not None:
        raise SystemExit("P22-I must not invent an owner monthly budget")
    for snapshot in (healthy, pressure, unbudgeted):
        if snapshot.execution_authority or snapshot.automatic_capacity_scaling or snapshot.automatic_cost_shedding:
            raise SystemExit("P22-I monitoring unexpectedly gained execution authority")
        if snapshot.automatic_safety_workload_throttling:
            raise SystemExit("P22-I monitoring may not throttle safety-critical workloads")
        if snapshot.production_sla_certified:
            raise SystemExit("P22-I reference evidence may not certify production SLA")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22I_SLO_CAPACITY_COST_EVIDENCE",
        "task_id": "FIN-P22-WI-001",
        "state": "REFERENCE_OPERATIONS_MONITORING_VALIDATED_PASS",
        "policy_id": policy.policy_id,
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "p02_capacity_cost_envelope_sha256": hashlib.sha256(capacity_envelope_path.read_bytes()).hexdigest(),
        "p07_quality_slo_policy_sha256": hashlib.sha256(quality_slo_path.read_bytes()).hexdigest(),
        "healthy_snapshot": {"snapshot_id": healthy.snapshot_id, **healthy.payload()},
        "pressure_snapshot": {"snapshot_id": pressure.snapshot_id, **pressure.payload()},
        "unbudgeted_snapshot": {"snapshot_id": unbudgeted.snapshot_id, **unbudgeted.payload()},
        "claim_scope": "DETERMINISTIC_REFERENCE_OPERATIONS_MONITORING",
        "safety": {
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
        },
        "next": "P22-J_NOT_STARTED",
    }
    payload["evidence_id"] = hashlib.sha256(_canonical(payload)).hexdigest()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(payload) + b"\n")
    print(f"P22I_EVIDENCE=PASS evidence_id={payload['evidence_id']} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
