from __future__ import annotations

from pathlib import Path
import unittest

from packages.operations.operations_monitoring import (
    CapacityObservation,
    CostObservation,
    LatencyObservation,
    OperationsMonitoringError,
    OperationsMonitoringPolicy,
    evaluate_operations_monitoring,
)


POLICY = Path("config/operations/slo-capacity-cost-policy.json")
E1 = "1" * 64
E2 = "2" * 64
E3 = "3" * 64
E4 = "4" * 64
E5 = "5" * 64
EC = "a" * 64
EK = "b" * 64


class OperationsMonitoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = OperationsMonitoringPolicy.from_path(POLICY)

    def healthy_latency(self) -> tuple[LatencyObservation, ...]:
        return (
            LatencyObservation("L_FAST_DATA", 200, 800, 0, E1),
            LatencyObservation("L_SIGNAL_STANDARD", 1500, None, 0, E2),
            LatencyObservation("L_RISK_FIREWALL", 80, 200, 0, E3),
            LatencyObservation("L_OMS_DISPATCH", 80, None, 0, E4),
            LatencyObservation("L_UI", 1500, None, 0, E5),
        )

    def capacity(self, *, avg: int = 1000, peak: int = 10000, streams: int = 30, agents: int = 4) -> CapacityObservation:
        return CapacityObservation(avg, peak, streams, agents, EC)

    def cost(
        self,
        *,
        projected: int = 50_000_000,
        budget: int | None = 100_000_000,
        daily: int = 1_000_000,
        expected_daily: int | None = 1_000_000,
    ) -> CostObservation:
        return CostObservation(projected, budget, daily, expected_daily, EK)

    def snapshot(
        self,
        *,
        latency: tuple[LatencyObservation, ...] | None = None,
        capacity: CapacityObservation | None = None,
        cost: CostObservation | None = None,
    ):
        return evaluate_operations_monitoring(
            self.policy,
            latency_observations=latency or self.healthy_latency(),
            capacity_observation=capacity or self.capacity(),
            cost_observation=cost or self.cost(),
        )

    def test_policy_matches_canonical_p02_envelope(self) -> None:
        self.assertEqual(self.policy.latency_slos["L_FAST_DATA"].p95_ms, 250)
        self.assertEqual(self.policy.latency_slos["L_FAST_DATA"].p99_ms, 1000)
        self.assertEqual(self.policy.latency_slos["L_RISK_FIREWALL"].p95_ms, 100)
        self.assertEqual(self.policy.operating.average_events_per_second, 2000)
        self.assertEqual(self.policy.operating.peak_events_per_second, 20000)
        self.assertEqual(self.policy.stress.average_events_per_second, 10000)
        self.assertEqual(self.policy.stress.peak_events_per_second, 50000)
        self.assertEqual(self.policy.capacity_review_threshold_bps_of_operating, 7000)
        self.assertEqual((self.policy.cost_alert_bps, self.policy.cost_throttle_bps, self.policy.cost_freeze_bps), (7000, 8500, 10000))
        self.assertEqual(self.policy.daily_cost_anomaly_ratio_bps, 20000)

    def test_healthy_reference_snapshot(self) -> None:
        result = self.snapshot()
        self.assertEqual(result.highest_status, "HEALTHY")
        self.assertFalse(result.architecture_review_required)
        self.assertEqual(result.recommendations, ())
        self.assertFalse(result.execution_authority)
        self.assertFalse(result.production_sla_certified)

    def test_single_latency_miss_is_warning(self) -> None:
        latency = list(self.healthy_latency())
        latency[0] = LatencyObservation("L_FAST_DATA", 251, 900, 1, E1)
        result = self.snapshot(latency=tuple(latency))
        fast = next(item for item in result.latency if item.slo_id == "L_FAST_DATA")
        self.assertEqual(fast.status, "WARNING")
        self.assertFalse(fast.architecture_review_required)
        self.assertIn("REVIEW_LATENCY_SLO_MISS", result.recommendations)

    def test_three_consecutive_latency_misses_require_architecture_review(self) -> None:
        latency = list(self.healthy_latency())
        latency[2] = LatencyObservation("L_RISK_FIREWALL", 120, 260, 3, E3)
        result = self.snapshot(latency=tuple(latency))
        risk = next(item for item in result.latency if item.slo_id == "L_RISK_FIREWALL")
        self.assertEqual(risk.status, "CRITICAL")
        self.assertTrue(risk.architecture_review_required)
        self.assertTrue(result.architecture_review_required)
        self.assertIn("ARCHITECTURE_REVIEW_REQUIRED_FOR_REPEATED_LATENCY_MISS", result.recommendations)

    def test_capacity_review_begins_at_seventy_percent_operating(self) -> None:
        result = self.snapshot(capacity=self.capacity(avg=1400))
        avg = next(item for item in result.capacity if item.resource == "AVERAGE_EVENTS_PER_SECOND")
        self.assertEqual(avg.operating_utilization_bps, 7000)
        self.assertEqual(avg.status, "WARNING")
        self.assertFalse(avg.architecture_review_required)
        self.assertIn("REVIEW_CAPACITY_PRESSURE", result.recommendations)

    def test_stress_boundary_requires_architecture_review(self) -> None:
        result = self.snapshot(capacity=self.capacity(avg=10000))
        avg = next(item for item in result.capacity if item.resource == "AVERAGE_EVENTS_PER_SECOND")
        self.assertEqual(avg.status, "CRITICAL")
        self.assertTrue(avg.architecture_review_required)
        self.assertIn("ARCHITECTURE_REVIEW_REQUIRED_AT_STRESS_BOUNDARY", result.recommendations)

    def test_cost_without_owner_budget_is_unassessed_not_invented(self) -> None:
        result = self.snapshot(cost=self.cost(budget=None, expected_daily=None))
        self.assertEqual(result.cost.status, "UNASSESSED")
        self.assertIsNone(result.cost.budget_utilization_bps)
        self.assertIn("OWNER_MONTHLY_BUDGET_REQUIRED_FOR_COST_EVALUATION", result.cost.recommendations)

    def test_cost_guardrails_are_exact(self) -> None:
        cases = (
            (70_000_000, "WARNING", "ALERT_AND_REVIEW_COST_FORECAST"),
            (85_000_000, "WARNING", "THROTTLE_DISCRETIONARY_RESEARCH_RECOMMENDED"),
            (100_000_000, "CRITICAL", "FREEZE_DISCRETIONARY_NEW_RESEARCH_SPEND_RECOMMENDED"),
        )
        for projected, status, recommendation in cases:
            with self.subTest(projected=projected):
                result = self.snapshot(cost=self.cost(projected=projected))
                self.assertEqual(result.cost.status, status)
                self.assertIn(recommendation, result.cost.recommendations)

    def test_two_x_daily_cost_anomaly_is_warning_and_recommendation_only(self) -> None:
        result = self.snapshot(cost=self.cost(projected=50_000_000, daily=2_000_000, expected_daily=1_000_000))
        self.assertTrue(result.cost.daily_anomaly)
        self.assertEqual(result.cost.daily_cost_ratio_bps, 20000)
        self.assertEqual(result.cost.status, "WARNING")
        self.assertIn("INVESTIGATE_DAILY_COST_ANOMALY", result.cost.recommendations)
        self.assertIn("CIRCUIT_BREAK_OPTIONAL_AI_RESEARCH_RECOMMENDED", result.cost.recommendations)
        self.assertFalse(result.automatic_cost_shedding)

    def test_safety_workloads_are_protected_and_never_auto_throttled(self) -> None:
        result = self.snapshot(cost=self.cost(projected=150_000_000))
        self.assertEqual(
            result.protected_safety_workloads,
            ("RISK", "FIREWALL", "SECURITY", "AUDIT", "RECONCILIATION", "KILL_SWITCH"),
        )
        self.assertFalse(result.automatic_safety_workload_throttling)
        self.assertFalse(result.automatic_capacity_scaling)
        self.assertFalse(result.network_access)
        self.assertFalse(result.credential_access)
        self.assertFalse(result.runtime_state_mutation)
        self.assertFalse(result.external_order_authority)

    def test_snapshot_is_deterministic(self) -> None:
        first = self.snapshot()
        second = self.snapshot()
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(first.payload(), second.payload())

    def test_invalid_latency_coverage_fails_closed(self) -> None:
        with self.assertRaises(OperationsMonitoringError):
            self.snapshot(latency=self.healthy_latency()[:-1])

    def test_latency_without_canonical_p99_fails_closed(self) -> None:
        latency = list(self.healthy_latency())
        latency[1] = LatencyObservation("L_SIGNAL_STANDARD", 1500, 1700, 0, E2)
        with self.assertRaises(OperationsMonitoringError):
            self.snapshot(latency=tuple(latency))

    def test_target_met_cannot_claim_consecutive_miss_windows(self) -> None:
        latency = list(self.healthy_latency())
        latency[4] = LatencyObservation("L_UI", 1500, None, 1, E5)
        with self.assertRaises(OperationsMonitoringError):
            self.snapshot(latency=tuple(latency))


if __name__ == "__main__":
    unittest.main()
