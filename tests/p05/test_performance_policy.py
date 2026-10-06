from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/market-data/performance-policy.json"
CAPACITY = ROOT / "docs/04-architecture/capacity-cost-envelope.json"


class P05GPerformancePolicyTests(unittest.TestCase):
    def test_policy_is_bound_to_canonical_operating_envelope(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        capacity = json.loads(CAPACITY.read_text(encoding="utf-8"))
        operating = next(
            item
            for item in capacity["workload_scenarios"]
            if item["id"] == "OPERATING"
        )
        stress = next(
            item
            for item in capacity["workload_scenarios"]
            if item["id"] == "STRESS"
        )

        self.assertEqual(
            policy["operating"]["average_events_per_sec"],
            operating["average_events_per_sec"],
        )
        self.assertEqual(
            policy["operating"]["peak_events_per_sec"],
            operating["peak_events_per_sec"],
        )
        self.assertEqual(
            policy["stress_review_boundary"]["peak_events_per_sec"],
            stress["peak_events_per_sec"],
        )

    def test_soak_equivalent_is_at_least_sixty_operating_average_seconds(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        benchmark = policy["benchmark"]
        operating = policy["operating"]
        minimum = (
            operating["average_events_per_sec"]
            * benchmark["soak_equivalent_seconds"]
        )
        self.assertGreaterEqual(benchmark["soak_equivalent_events"], minimum)
        self.assertGreaterEqual(benchmark["soak_equivalent_seconds"], 60)

    def test_operating_peak_burst_and_throughput_targets_are_not_weakened(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        peak = policy["operating"]["peak_events_per_sec"]
        self.assertEqual(policy["benchmark"]["operating_peak_burst_events"], peak)
        self.assertGreaterEqual(
            policy["pass_requirements"]["canonical_stream_min_events_per_sec"],
            peak,
        )

    def test_fast_data_latency_matches_p02_h(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        fast = policy["l_fast_data"]
        self.assertEqual(fast["p95_max_ms"], 250.0)
        self.assertEqual(fast["p99_max_ms"], 1000.0)
        self.assertTrue(fast["upstream_provider_latency_excluded"])
        self.assertTrue(fast["internet_distance_excluded"])

    def test_timing_and_contract_evidence_are_not_conflated(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(
            policy["timing_evidence"],
            "NON_DETERMINISTIC_MEASUREMENT_NOT_BYTE_COMPARED",
        )
        self.assertEqual(
            policy["contract_evidence"],
            "DETERMINISTIC_BYTE_COMPARED",
        )
        self.assertFalse(policy["network_required"])
        self.assertFalse(policy["credentials_required"])
        self.assertEqual(policy["automatic_data_failover"], "DISABLED")


if __name__ == "__main__":
    unittest.main()
