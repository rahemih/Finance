from __future__ import annotations

from pathlib import Path
import unittest

from packages.market_memory.historical_analog import (
    HistoricalAnalogError,
    HistoricalAnalogPolicy,
    HistoricalFeatureState,
    find_historical_analogs,
)
from packages.market_memory.knowledge_graph import KnowledgeGraphPolicy


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/historical-analog-policy.json"
HASH_A = "a" * 64


class HistoricalAnalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
        self.policy = HistoricalAnalogPolicy.from_path(POLICY_PATH)
        self.full_features = (
            ("TREND", 2000),
            ("MOMENTUM", 1000),
            ("VOLATILITY", -500),
            ("LIQUIDITY", 500),
            ("ORDER_FLOW", 1500),
            ("MACRO", -1000),
            ("NEWS", 250),
            ("CAPITAL_FLOW", 1750),
        )

    def state(
        self,
        state_id: str,
        as_of_ns: int,
        *,
        regime: str = "ALIGNED_BULLISH",
        features: tuple[tuple[str, int], ...] | None = None,
    ) -> HistoricalFeatureState:
        return HistoricalFeatureState(
            state_id=state_id,
            as_of_ns=as_of_ns,
            regime_label=regime,
            features=self.full_features if features is None else features,
            provenance_sha256=(HASH_A,),
            source_dataset_versions=("memory-v1",),
        )

    def test_identical_state_is_maximum_similarity(self) -> None:
        result = find_historical_analogs(
            self.state("query", 1000),
            (self.state("past", 100),),
            top_k=1,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        match = result.matches[0]
        self.assertEqual(match.similarity_bps, 10000)
        self.assertEqual(match.mean_distance_bps, 0)
        self.assertEqual(match.coverage_bps, 10000)

    def test_known_distance_is_deterministic(self) -> None:
        changed = tuple((name, value + 2000 if name == "TREND" else value) for name, value in self.full_features)
        result = find_historical_analogs(
            self.state("query", 1000),
            (self.state("past", 100, features=changed),),
            top_k=1,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(result.matches[0].mean_distance_bps, 125)
        self.assertEqual(result.matches[0].similarity_bps, 9875)

    def test_regime_mismatch_is_excluded(self) -> None:
        with self.assertRaises(HistoricalAnalogError):
            find_historical_analogs(
                self.state("query", 1000),
                (self.state("past", 100, regime="CONFLICT"),),
                top_k=1,
                graph_policy=self.graph_policy,
                policy=self.policy,
            )

    def test_future_or_equal_candidate_fails_closed(self) -> None:
        for candidate_time in (1000, 1001):
            with self.assertRaises(HistoricalAnalogError):
                find_historical_analogs(
                    self.state("query", 1000),
                    (self.state("past", candidate_time),),
                    top_k=1,
                    graph_policy=self.graph_policy,
                    policy=self.policy,
                )

    def test_duplicate_identity_and_timestamp_fail_closed(self) -> None:
        with self.assertRaises(HistoricalAnalogError):
            find_historical_analogs(
                self.state("query", 1000),
                (self.state("dup", 100), self.state("dup", 200)),
                top_k=1,
                graph_policy=self.graph_policy,
                policy=self.policy,
            )
        with self.assertRaises(HistoricalAnalogError):
            find_historical_analogs(
                self.state("query", 1000),
                (self.state("a", 100), self.state("b", 100)),
                top_k=1,
                graph_policy=self.graph_policy,
                policy=self.policy,
            )

    def test_insufficient_shared_features_are_excluded(self) -> None:
        partial = (
            ("TREND", 2000),
            ("MOMENTUM", 1000),
            ("VOLATILITY", -500),
            ("LIQUIDITY", 500),
        )
        insufficient = (
            ("TREND", 2000),
            ("MOMENTUM", 1000),
            ("VOLATILITY", -500),
            ("MACRO", -1000),
        )
        result = find_historical_analogs(
            self.state("query", 1000),
            (
                self.state("enough", 100, features=partial),
                self.state("other", 200, features=insufficient),
            ),
            top_k=1,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(result.matches[0].shared_feature_count, 4)

    def test_top_k_ranking_is_order_independent(self) -> None:
        near = self.state("near", 300)
        mid_features = tuple((name, value + 1000 if name == "MOMENTUM" else value) for name, value in self.full_features)
        far_features = tuple((name, value + 3000 if name == "MOMENTUM" else value) for name, value in self.full_features)
        mid = self.state("mid", 200, features=mid_features)
        far = self.state("far", 100, features=far_features)
        first = find_historical_analogs(
            self.state("query", 1000),
            (far, near, mid),
            top_k=3,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        second = find_historical_analogs(
            self.state("query", 1000),
            (mid, far, near),
            top_k=3,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(first, second)
        self.assertEqual(tuple(item.state_id for item in first.matches), ("near", "mid", "far"))

    def test_capital_flow_is_governed_and_similarity_is_not_probability(self) -> None:
        self.assertIn("CAPITAL_FLOW", self.policy.feature_names)
        self.assertFalse(self.policy.similarity_is_probability)
        self.assertFalse(self.policy.future_outcome_consumed)
        source = (ROOT / "packages/market_memory/historical_analog.py").read_text(encoding="utf-8").lower()
        for forbidden in ("future_outcome_bps", "trade_action", "risk_approval", "execution_authority"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
