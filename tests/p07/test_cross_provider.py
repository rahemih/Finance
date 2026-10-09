from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import unittest

from packages.data_quality import (
    ComparisonRule,
    CrossProviderAnalyzer,
    CrossProviderError,
    CrossProviderOutcome,
    CrossProviderPolicy,
    ProviderObservation,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/data-quality/cross-provider-policy.json"
UPSTREAM = "a" * 64


def obs(
    *,
    provider: str,
    value: str,
    family: str = "DIRECT_SPOT_QUOTE",
    coverage_bps: int = 10000,
    sample_id: str = "sample-1",
    metric: str = "mid_price",
) -> ProviderObservation:
    return ProviderObservation(
        sample_id=sample_id,
        canonical_id="FX:EUR/USD:SPOT_OTC",
        metric=metric,
        comparison_family=family,
        provider=provider,
        value=Decimal(value),
        coverage_bps=coverage_bps,
        upstream_quality_evidence_sha256=UPSTREAM,
    )


def rule(
    *,
    family: str = "DIRECT_SPOT_QUOTE",
    min_provider_count: int = 2,
    min_coverage_bps: int = 9000,
    max_abs_diff: str | None = "0.01",
    max_rel_diff: str | None = "0.001",
) -> ComparisonRule:
    return ComparisonRule(
        metric="mid_price",
        comparison_family=family,
        min_provider_count=min_provider_count,
        min_coverage_bps=min_coverage_bps,
        max_abs_diff=None if max_abs_diff is None else Decimal(max_abs_diff),
        max_rel_diff=None if max_rel_diff is None else Decimal(max_rel_diff),
    )


def analyzer() -> CrossProviderAnalyzer:
    return CrossProviderAnalyzer(CrossProviderPolicy.from_path(POLICY))


class CrossProviderPolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = CrossProviderPolicy.from_path(POLICY)
        self.assertEqual(policy.production_data_quality_vendor, "NOT_SELECTED")
        self.assertEqual(policy.coverage_scale_bps, 10000)


class CrossProviderComparisonTests(unittest.TestCase):
    def test_aligned_comparable_providers_within_threshold_pass(self):
        report = analyzer().analyze(
            (obs(provider="p1", value="1.1000"), obs(provider="p2", value="1.1005")),
            (rule(),),
        )
        self.assertTrue(report.is_valid)
        self.assertEqual(report.outcome, CrossProviderOutcome.VALID)
        self.assertEqual(report.groups_evaluated, 1)

    def test_absolute_divergence_fails_closed(self):
        report = analyzer().analyze(
            (obs(provider="p1", value="1.10"), obs(provider="p2", value="1.20")),
            (rule(max_abs_diff="0.05", max_rel_diff=None),),
        )
        self.assertIn("ABS_DIVERGENCE", {issue.code for issue in report.issues})

    def test_relative_divergence_fails_closed(self):
        report = analyzer().analyze(
            (obs(provider="p1", value="100"), obs(provider="p2", value="102")),
            (rule(max_abs_diff=None, max_rel_diff="0.01"),),
        )
        self.assertIn("REL_DIVERGENCE", {issue.code for issue in report.issues})

    def test_insufficient_independent_provider_coverage_fails_closed(self):
        report = analyzer().analyze(
            (obs(provider="p1", value="1.10"),),
            (rule(),),
        )
        self.assertIn("INSUFFICIENT_PROVIDER_COVERAGE", {issue.code for issue in report.issues})

    def test_low_coverage_provider_does_not_satisfy_minimum(self):
        report = analyzer().analyze(
            (
                obs(provider="p1", value="1.10", coverage_bps=10000),
                obs(provider="p2", value="1.10", coverage_bps=8000),
            ),
            (rule(min_coverage_bps=9000),),
        )
        self.assertIn("INSUFFICIENT_PROVIDER_COVERAGE", {issue.code for issue in report.issues})

    def test_duplicate_provider_observation_fails_closed(self):
        report = analyzer().analyze(
            (obs(provider="p1", value="1.10"), obs(provider="p1", value="1.10")),
            (rule(),),
        )
        self.assertIn("DUPLICATE_PROVIDER_OBSERVATION", {issue.code for issue in report.issues})

    def test_missing_comparison_rule_fails_closed(self):
        report = analyzer().analyze(
            (obs(provider="p1", value="1.10"), obs(provider="p2", value="1.10")),
            (),
        )
        self.assertIn("MISSING_COMPARISON_RULE", {issue.code for issue in report.issues})

    def test_different_semantic_families_are_never_pairwise_compared(self):
        observations = (
            obs(provider="spot-provider", value="1.10", family="DIRECT_SPOT_QUOTE"),
            obs(provider="futures-provider", value="1.50", family="FUTURES_PROXY"),
        )
        rules = (
            rule(family="DIRECT_SPOT_QUOTE"),
            rule(family="FUTURES_PROXY"),
        )
        report = analyzer().analyze(observations, rules)
        codes = [issue.code for issue in report.issues]
        self.assertEqual(codes.count("INSUFFICIENT_PROVIDER_COVERAGE"), 2)
        self.assertNotIn("ABS_DIVERGENCE", codes)
        self.assertNotIn("REL_DIVERGENCE", codes)
        self.assertEqual(
            report.semantic_families,
            ("DIRECT_SPOT_QUOTE", "FUTURES_PROXY"),
        )

    def test_input_order_does_not_change_report(self):
        observations = (
            obs(provider="p2", value="1.20"),
            obs(provider="p1", value="1.10"),
        )
        first = analyzer().analyze(observations, (rule(max_abs_diff="0.05", max_rel_diff=None),))
        second = analyzer().analyze(tuple(reversed(observations)), (rule(max_abs_diff="0.05", max_rel_diff=None),))
        self.assertEqual(first.issues, second.issues)
        self.assertEqual(first.fingerprint, second.fingerprint)

    def test_batch_limit_fails_closed(self):
        policy = CrossProviderPolicy(
            max_observations_per_batch=1,
            coverage_scale_bps=10000,
            relative_denominator_epsilon=Decimal("0.000001"),
            production_data_quality_vendor="NOT_SELECTED",
        )
        with self.assertRaises(CrossProviderError):
            CrossProviderAnalyzer(policy).analyze(
                (obs(provider="p1", value="1.1"), obs(provider="p2", value="1.1")),
                (rule(),),
            )

    def test_invalid_upstream_digest_fails_closed(self):
        with self.assertRaises(CrossProviderError):
            ProviderObservation(
                sample_id="s",
                canonical_id="FX:EUR/USD:SPOT_OTC",
                metric="mid_price",
                comparison_family="DIRECT_SPOT_QUOTE",
                provider="p",
                value=Decimal("1"),
                coverage_bps=10000,
                upstream_quality_evidence_sha256="bad",
            )


if __name__ == "__main__":
    unittest.main()
