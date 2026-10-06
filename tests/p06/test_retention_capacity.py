from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import unittest

from packages.historical_data import (
    CostRateSet,
    RetentionCapacityError,
    RetentionCapacityPolicy,
    RetentionRights,
    estimate_capacity,
    estimate_cost,
    evaluate_growth_deviation,
    measure_compaction,
    plan_raw_retention,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/historical-data/retention-capacity-policy.json"


class RetentionCapacityPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = RetentionCapacityPolicy.from_path(POLICY)

    def test_policy_is_offline_vendor_neutral_and_non_mutating(self):
        self.assertEqual(self.policy.production_storage_vendor, "NOT_SELECTED")
        self.assertEqual(self.policy.hot_days, 7)
        self.assertEqual(self.policy.warm_min_days, 30)
        self.assertEqual(self.policy.warm_max_days, 90)
        self.assertEqual(self.policy.cold_min_days, 90)
        self.assertEqual(self.policy.planning_compression_ratios, (Decimal("3"), Decimal("5")))


class RetentionRightsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = RetentionCapacityPolicy.from_path(POLICY)

    def test_forbidden_and_unverified_raw_retention_fail_closed(self):
        for state in ("RETENTION_FORBIDDEN", "RETENTION_UNVERIFIED"):
            with self.subTest(state=state):
                with self.assertRaises(RetentionCapacityError):
                    plan_raw_retention(
                        tier="HOT",
                        requested_days=7,
                        rights=RetentionRights(state),
                        policy=self.policy,
                    )

    def test_limited_retention_requires_explicit_limit(self):
        with self.assertRaises(RetentionCapacityError):
            RetentionRights("RETENTION_ALLOWED_WITH_LIMIT")

    def test_limited_retention_enforces_limit(self):
        rights = RetentionRights("RETENTION_ALLOWED_WITH_LIMIT", max_retention_days=30)
        plan = plan_raw_retention(
            tier="WARM",
            requested_days=30,
            rights=rights,
            policy=self.policy,
        )
        self.assertEqual(plan.effective_days, 30)
        self.assertFalse(plan.production_mutation)
        with self.assertRaises(RetentionCapacityError):
            plan_raw_retention(
                tier="WARM",
                requested_days=60,
                rights=rights,
                policy=self.policy,
            )

    def test_provisional_tier_bounds_are_enforced(self):
        rights = RetentionRights("RETENTION_ALLOWED")
        for tier, days in (("HOT", 8), ("WARM", 29), ("WARM", 91), ("COLD", 89)):
            with self.subTest(tier=tier, days=days):
                with self.assertRaises(RetentionCapacityError):
                    plan_raw_retention(
                        tier=tier,
                        requested_days=days,
                        rights=rights,
                        policy=self.policy,
                    )


class CapacityMathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = RetentionCapacityPolicy.from_path(POLICY)

    def test_p02_h_storage_examples_match_exactly(self):
        examples = (
            (500, 500, Decimal("21.6"), Decimal("0.648")),
            (500, 1000, Decimal("43.2"), Decimal("1.296")),
            (2000, 500, Decimal("86.4"), Decimal("2.592")),
            (2000, 1000, Decimal("172.8"), Decimal("5.184")),
            (10000, 500, Decimal("432"), Decimal("12.96")),
            (10000, 1000, Decimal("864"), Decimal("25.92")),
        )
        for eps, size, expected_gb_day, expected_tb_30d in examples:
            with self.subTest(eps=eps, size=size):
                estimate = estimate_capacity(
                    events_per_sec=eps,
                    event_bytes=size,
                    retention_days=30,
                    compression_ratio="1",
                    partition_seconds=3600,
                    policy=self.policy,
                )
                self.assertEqual(estimate.raw_gb_per_day, expected_gb_day)
                self.assertEqual(estimate.raw_tb_for_retention, expected_tb_30d)

    def test_operating_compression_examples_match_p02_h(self):
        three = estimate_capacity(
            events_per_sec=2000,
            event_bytes=1000,
            retention_days=30,
            compression_ratio="3",
            partition_seconds=3600,
            policy=self.policy,
        )
        five = estimate_capacity(
            events_per_sec=2000,
            event_bytes=1000,
            retention_days=30,
            compression_ratio="5",
            partition_seconds=3600,
            policy=self.policy,
        )
        self.assertEqual(three.compressed_gb_per_day, Decimal("57.6"))
        self.assertEqual(five.compressed_gb_per_day, Decimal("34.56"))

    def test_partition_size_is_deterministic(self):
        estimate = estimate_capacity(
            events_per_sec=2000,
            event_bytes=1000,
            retention_days=30,
            compression_ratio="4",
            partition_seconds=3600,
            policy=self.policy,
        )
        self.assertEqual(estimate.partition_compressed_gb, Decimal("1.8"))

    def test_compaction_ratio_and_reference_lower_bound(self):
        measured = measure_compaction(
            input_bytes=4000,
            output_bytes=1000,
            policy=self.policy,
        )
        self.assertEqual(measured.compression_ratio, Decimal("4"))
        self.assertTrue(measured.meets_reference_lower_bound)

    def test_growth_deviation_trigger_is_strictly_above_fifty_percent(self):
        at_limit = evaluate_growth_deviation(
            forecast_gb="100",
            actual_gb="150",
            policy=self.policy,
        )
        over = evaluate_growth_deviation(
            forecast_gb="100",
            actual_gb="151",
            policy=self.policy,
        )
        self.assertEqual(at_limit.deviation_percent, Decimal("50"))
        self.assertFalse(at_limit.architecture_review_required)
        self.assertTrue(over.architecture_review_required)


class CostModelTests(unittest.TestCase):
    def test_missing_rates_remains_explicitly_unresolved(self):
        result = estimate_cost(
            retained_gb_month="1728",
            replay_scan_gb="100",
            egress_gb="10",
            rates=None,
        )
        self.assertEqual(result.status, "UNRESOLVED_RATE_REQUIRED")
        self.assertIsNone(result.total_cost)
        self.assertFalse(result.production_authoritative)

    def test_test_only_parametric_rates_are_exact(self):
        rates = CostRateSet(
            currency_or_unit="TEST_COST_UNITS",
            storage_gb_month_rate=Decimal("0.02"),
            replay_scan_gb_rate=Decimal("0.01"),
            egress_gb_rate=Decimal("0.005"),
            provenance="UNIT_TEST_ONLY_NOT_VENDOR_PRICE",
            production_authoritative=False,
        )
        result = estimate_cost(
            retained_gb_month="100",
            replay_scan_gb="50",
            egress_gb="20",
            rates=rates,
        )
        self.assertEqual(result.storage_cost, Decimal("2.00"))
        self.assertEqual(result.replay_scan_cost, Decimal("0.50"))
        self.assertEqual(result.egress_cost, Decimal("0.100"))
        self.assertEqual(result.total_cost, Decimal("2.600"))
        self.assertFalse(result.production_authoritative)


class DependencyBoundaryTests(unittest.TestCase):
    def test_core_module_has_no_storage_database_or_cloud_clients(self):
        text = (ROOT / "packages/historical_data/retention_capacity.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "boto3",
            "botocore",
            "psycopg",
            "sqlalchemy",
            "clickhouse",
            "timescale",
            "feast",
            "tecton",
            "adapters.",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
