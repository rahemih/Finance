from __future__ import annotations

from pathlib import Path
import unittest

from packages.market_memory.conditional_correlation import (
    ConditionalCorrelationError,
    ConditionalCorrelationPolicy,
    CorrelationObservation,
    compute_conditional_correlation,
)
from packages.market_memory.knowledge_graph import GraphNode, KnowledgeGraphPolicy


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY = ROOT / "config/market-memory/knowledge-graph-policy.json"
CORR_POLICY = ROOT / "config/market-memory/conditional-correlation-policy.json"


class ConditionalCorrelationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY)
        self.policy = ConditionalCorrelationPolicy.from_path(CORR_POLICY)
        self.btc = GraphNode.build(node_kind="ASSET",canonical_key="BTC",display_label="Bitcoin",policy=self.graph_policy)
        self.dxy = GraphNode.build(node_kind="MARKET",canonical_key="DXY",display_label="DXY",policy=self.graph_policy)

    def obs(self, xs: tuple[int, ...], ys: tuple[int, ...], regimes: tuple[str, ...] | None = None):
        labels = regimes or tuple("ALIGNED_BULLISH" for _ in xs)
        return tuple(CorrelationObservation(i + 1, x, y, labels[i]) for i, (x, y) in enumerate(zip(xs, ys, strict=True)))

    def compute(self, observations, *, window_size=5, regime_label=None):
        return compute_conditional_correlation(
            observations,
            window_size=window_size,
            regime_label=regime_label,
            source_node=self.btc,
            target_node=self.dxy,
            provenance_sha256=("a"*64,),
            source_dataset_versions=("p06-v1",),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )

    def test_perfect_positive_and_negative(self) -> None:
        positive=self.compute(self.obs((1,2,3,4,5),(10,20,30,40,50)))
        negative=self.compute(self.obs((1,2,3,4,5),(50,40,30,20,10)))
        self.assertEqual(positive.correlation_bps,10000)
        self.assertEqual(negative.correlation_bps,-10000)

    def test_rolling_window_uses_latest_qualifying_observations(self) -> None:
        data=self.obs((100,1,2,3,4,5),(1,10,20,30,40,50))
        result=self.compute(data,window_size=5)
        self.assertEqual(result.valid_from_ns,2)
        self.assertEqual(result.sample_count,5)
        self.assertEqual(result.correlation_bps,10000)

    def test_regime_conditioning_is_deterministic(self) -> None:
        data=self.obs(
            (1,9,2,8,3,7,4,6),
            (10,1,20,2,30,3,40,4),
            ("ALIGNED_BULLISH","CONFLICT","ALIGNED_BULLISH","CONFLICT","ALIGNED_BULLISH","CONFLICT","ALIGNED_BULLISH","CONFLICT"),
        )
        first=self.compute(data,window_size=4,regime_label="ALIGNED_BULLISH")
        second=self.compute(tuple(reversed(data)),window_size=4,regime_label="ALIGNED_BULLISH")
        self.assertEqual(first,second)
        self.assertEqual(first.correlation_bps,10000)
        self.assertEqual(first.regime_label,"ALIGNED_BULLISH")

    def test_fail_closed_on_insufficient_zero_variance_and_duplicate_timestamp(self) -> None:
        with self.assertRaises(ConditionalCorrelationError):
            self.compute(self.obs((1,2),(2,4)),window_size=3)
        with self.assertRaises(ConditionalCorrelationError):
            self.compute(self.obs((1,1,1),(2,3,4)),window_size=3)
        duplicate=(
            CorrelationObservation(1,1,1,"NEUTRAL"),
            CorrelationObservation(1,2,2,"NEUTRAL"),
            CorrelationObservation(2,3,3,"NEUTRAL"),
        )
        with self.assertRaises(ConditionalCorrelationError):
            self.compute(duplicate,window_size=3)

    def test_edge_contract_and_uncertainty(self) -> None:
        result=self.compute(self.obs((1,2,3,4,5),(5,4,3,2,1)))
        self.assertEqual(result.edge.edge_kind,"OBSERVED_ASSOCIATION")
        self.assertEqual(result.edge.attribution_label,"UNATTRIBUTED")
        self.assertEqual(result.edge.strength_bps,result.correlation_bps)
        self.assertGreaterEqual(result.sampling_uncertainty_bps,0)
        self.assertLessEqual(result.sampling_uncertainty_bps,10000)

    def test_module_has_no_causality_network_or_execution_authority(self) -> None:
        source=(ROOT/"packages/market_memory/conditional_correlation.py").read_text(encoding="utf-8").lower()
        for forbidden in ("likely_driver","supporting_factor","packages.execution","adapters.execution","import requests","import httpx"):
            self.assertNotIn(forbidden,source)
        self.assertFalse(self.policy.correlation_is_causation)


if __name__=="__main__":
    unittest.main()
