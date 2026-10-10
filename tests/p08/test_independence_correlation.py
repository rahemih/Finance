from __future__ import annotations

from pathlib import Path
import unittest

from packages.technical_intelligence.foundation import TechnicalEvidence
from packages.technical_intelligence.independence_correlation import (
    IndependenceCorrelationAudit,
    IndependenceCorrelationError,
    IndependenceCorrelationPolicy,
    measure_pairwise_dependence,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/technical-intelligence/independence-correlation-audit-policy.json"
DATASET = "a" * 64
QUALITY = "b" * 64
DEFINITION = "c" * 64

GROUPS = {
    "TREND": "price-path-trend",
    "REGIME": "trend-multitimeframe-regime",
    "MOMENTUM": "return-momentum",
    "MARKET_STRUCTURE": "swing-structure",
    "PRICE_ACTION": "candle-price-action",
    "BREAKOUT": "range-breakout-expansion",
    "VOLATILITY": "range-volatility",
    "MEAN_REVERSION": "price-deviation-mean-reversion",
}


def policy() -> IndependenceCorrelationPolicy:
    return IndependenceCorrelationPolicy.from_path(POLICY)


def audit() -> IndependenceCorrelationAudit:
    return IndependenceCorrelationAudit(policy=policy())


def evidence(
    family: str,
    *,
    direction: int,
    independence_group: str | None = None,
) -> TechnicalEvidence:
    return TechnicalEvidence(
        definition_id=DEFINITION,
        family=family,
        independence_group=(
            GROUPS[family]
            if independence_group is None
            else independence_group
        ),
        symbol="CRYPTO:BTC-USD",
        timeframe="1h",
        direction=direction,
        strength_bps=5000 if direction != 0 else 0,
        confidence_bps=6000 if direction != 0 else 3000,
        event_time_ns=9000,
        as_of_time_ns=10_000,
        value_text=str(direction * 5000 if direction != 0 else 0),
        invalidation="P08-H test fixture invalidation",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


class P08HPolicyTests(unittest.TestCase):
    def test_policy_preserves_fail_closed_and_p14_threshold_ownership(self) -> None:
        value = policy()
        self.assertEqual(value.cluster_vote_cap, 1)
        self.assertEqual(
            value.numeric_dependence_decision_semantics,
            "MEASURED_NOT_THRESHOLD_CLASSIFIED",
        )
        self.assertEqual(
            value.numeric_dependence_threshold,
            "TO_BE_CALIBRATED_BY_GOVERNED_EMPIRICAL_EVIDENCE",
        )
        self.assertEqual(value.production_fusion_threshold_owner, "P14")
        self.assertFalse(value.direct_trade_output_allowed)

    def test_registered_groups_match_canonical_design(self) -> None:
        value = policy()
        actual = {
            rule.family: rule.expected_independence_group
            for rule in value.families
        }
        self.assertEqual(actual, GROUPS)


class P08HAuditTests(unittest.TestCase):
    def test_trend_and_regime_count_as_one_cluster(self) -> None:
        result = audit().audit_confirmations(
            (
                evidence("TREND", direction=1),
                evidence("REGIME", direction=1),
            ),
            direction=1,
        )
        self.assertEqual(result.raw_supporting_family_count, 2)
        self.assertEqual(result.independent_cluster_count, 1)
        self.assertEqual(result.collapsed_related_family_count, 1)
        self.assertEqual(
            result.independent_clusters,
            ("directional-trend-regime",),
        )

    def test_structure_price_action_breakout_count_as_one_cluster(self) -> None:
        result = audit().audit_confirmations(
            (
                evidence("MARKET_STRUCTURE", direction=1),
                evidence("PRICE_ACTION", direction=1),
                evidence("BREAKOUT", direction=1),
            ),
            direction=1,
        )
        self.assertEqual(result.raw_supporting_family_count, 3)
        self.assertEqual(result.independent_cluster_count, 1)
        self.assertEqual(result.collapsed_related_family_count, 2)

    def test_separate_clusters_can_count_separately_without_threshold_claim(self) -> None:
        result = audit().audit_confirmations(
            (
                evidence("TREND", direction=1),
                evidence("MOMENTUM", direction=1),
                evidence("MEAN_REVERSION", direction=1),
            ),
            direction=1,
        )
        self.assertEqual(result.independent_cluster_count, 3)
        self.assertEqual(
            result.status,
            "CLUSTER_CAPPED_NO_NUMERIC_THRESHOLD",
        )

    def test_volatility_never_adds_directional_confirmation(self) -> None:
        result = audit().audit_confirmations(
            (
                evidence("TREND", direction=1),
                evidence("VOLATILITY", direction=0),
            ),
            direction=1,
        )
        self.assertEqual(result.raw_supporting_family_count, 1)
        self.assertEqual(result.independent_cluster_count, 1)

    def test_context_family_with_direction_fails_closed(self) -> None:
        with self.assertRaises(IndependenceCorrelationError):
            audit().validate_evidence(evidence("VOLATILITY", direction=1))

    def test_unknown_family_and_wrong_group_fail_closed(self) -> None:
        unknown = TechnicalEvidence(
            definition_id=DEFINITION,
            family="UNKNOWN",
            independence_group="unknown-group",
            symbol="CRYPTO:BTC-USD",
            timeframe="1h",
            direction=1,
            strength_bps=5000,
            confidence_bps=6000,
            event_time_ns=9000,
            as_of_time_ns=10_000,
            value_text="5000",
            invalidation="unknown fixture",
            source_dataset_version=DATASET,
            quality_evidence_sha256=QUALITY,
        )
        with self.assertRaises(IndependenceCorrelationError):
            audit().validate_evidence(unknown)
        with self.assertRaises(IndependenceCorrelationError):
            audit().validate_evidence(
                evidence(
                    "TREND",
                    direction=1,
                    independence_group="drifted-group",
                )
            )

    def test_relationship_semantics_are_symmetric(self) -> None:
        value = policy()
        forward = value.relationship("TREND", "REGIME")
        reverse = value.relationship("REGIME", "TREND")
        self.assertEqual(forward.relationship, "CLUSTERED_RELATED")
        self.assertEqual(reverse.relationship, "CLUSTERED_RELATED")
        self.assertEqual(forward.basis, reverse.basis)

        separate = value.relationship("TREND", "MOMENTUM")
        self.assertEqual(
            separate.relationship,
            "SEPARATE_CLUSTER_EMPIRICAL_MONITORING_REQUIRED",
        )

        context = value.relationship("VOLATILITY", "TREND")
        self.assertEqual(context.relationship, "CONTEXT_RELATED")


class P08HDependenceTests(unittest.TestCase):
    def test_perfect_positive_and_negative_dependence(self) -> None:
        positive = measure_pairwise_dependence(
            (1, 2, 3, 4),
            (10, 20, 30, 40),
        )
        negative = measure_pairwise_dependence(
            (1, 2, 3, 4),
            (40, 30, 20, 10),
        )
        self.assertEqual(positive.pearson_text, "1")
        self.assertEqual(positive.spearman_text, "1")
        self.assertEqual(negative.pearson_text, "-1")
        self.assertEqual(negative.spearman_text, "-1")
        self.assertEqual(
            positive.status,
            "MEASURED_NOT_THRESHOLD_CLASSIFIED",
        )
        self.assertIn(
            "NOT_AN_INDEPENDENCE_VERDICT",
            positive.decision_semantics,
        )

    def test_tied_ranks_are_deterministic(self) -> None:
        first = measure_pairwise_dependence(
            (1, 1, 2, 3),
            (2, 2, 4, 6),
        )
        second = measure_pairwise_dependence(
            (1, 1, 2, 3),
            (2, 2, 4, 6),
        )
        self.assertEqual(first, second)
        self.assertEqual(first.spearman_text, "1")

    def test_zero_variance_is_undefined_not_fabricated(self) -> None:
        value = measure_pairwise_dependence(
            (1, 1, 1),
            (1, 2, 3),
        )
        self.assertEqual(value.status, "UNDEFINED_ZERO_VARIANCE")
        self.assertIsNone(value.pearson_text)
        self.assertIsNone(value.spearman_text)

    def test_invalid_series_fail_closed(self) -> None:
        with self.assertRaises(IndependenceCorrelationError):
            measure_pairwise_dependence((1,), (2,))
        with self.assertRaises(IndependenceCorrelationError):
            measure_pairwise_dependence((1, 2), (1, 2, 3))

    def test_core_module_has_no_execution_or_network_clients(self) -> None:
        source = (
            ROOT
            / "packages/technical_intelligence/independence_correlation.py"
        ).read_text(encoding="utf-8").lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "requests",
            "httpx",
            "websocket",
            "boto3",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
