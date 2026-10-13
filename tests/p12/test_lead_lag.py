from __future__ import annotations

from pathlib import Path
import unittest

from packages.market_memory.knowledge_graph import GraphNode, KnowledgeGraphPolicy
from packages.market_memory.lead_lag import (
    LeadLagError,
    LeadLagObservation,
    LeadLagPolicy,
    compute_lead_lag,
)


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/lead-lag-policy.json"
HASH_A = "a" * 64


class LeadLagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
        self.policy = LeadLagPolicy.from_path(POLICY_PATH)
        self.left = GraphNode.build(
            node_kind="ASSET",
            canonical_key="BTC",
            display_label="Bitcoin",
            policy=self.graph_policy,
        )
        self.right = GraphNode.build(
            node_kind="MARKET",
            canonical_key="DXY",
            display_label="US Dollar Index",
            policy=self.graph_policy,
        )
        self.values = (3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9)

    def observations(self, right_values: tuple[int, ...], *, regime: str = "ALIGNED_BULLISH") -> tuple[LeadLagObservation, ...]:
        return tuple(
            LeadLagObservation(
                timestamp_ns=index * 100,
                left_value=left,
                right_value=right,
                regime_label=regime,
            )
            for index, (left, right) in enumerate(zip(self.values, right_values, strict=True))
        )

    def compute(self, observations: tuple[LeadLagObservation, ...]):
        return compute_lead_lag(
            observations,
            sampling_interval_ns=100,
            regime_label="ALIGNED_BULLISH",
            left_node=self.left,
            right_node=self.right,
            provenance_sha256=(HASH_A,),
            source_dataset_versions=("history-v1",),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )

    def test_left_leads_right_one_step(self) -> None:
        right = (0,) + self.values[:-1]
        result = self.compute(self.observations(right))
        self.assertEqual(result.lead_state, "LEFT_LEADS_RIGHT")
        self.assertEqual(result.selected_lag_steps, 1)
        self.assertEqual(result.selected_lag_ns, 100)
        self.assertIsNotNone(result.edge)
        assert result.edge is not None
        self.assertEqual(result.edge.source_node_id, self.left.node_id)
        self.assertEqual(result.edge.target_node_id, self.right.node_id)
        self.assertEqual(result.edge.attribution_label, "UNATTRIBUTED")

    def test_right_leads_left_one_step(self) -> None:
        right = self.values[1:] + (0,)
        result = self.compute(self.observations(right))
        self.assertEqual(result.lead_state, "RIGHT_LEADS_LEFT")
        self.assertEqual(result.selected_lag_steps, -1)
        self.assertEqual(result.selected_lag_ns, -100)
        self.assertIsNotNone(result.edge)
        assert result.edge is not None
        self.assertEqual(result.edge.source_node_id, self.right.node_id)

    def test_contemporaneous_relationship(self) -> None:
        result = self.compute(self.observations(self.values))
        self.assertEqual(result.lead_state, "CONTEMPORANEOUS")
        self.assertEqual(result.selected_lag_steps, 0)

    def test_exact_timestamp_pairing_rejects_missing_pairs_below_minimum(self) -> None:
        observations = self.observations((0,) + self.values[:-1])[:5]
        result = self.compute(observations)
        self.assertEqual(tuple(candidate.lag_steps for candidate in result.candidates), (0,))
        self.assertEqual(result.lead_state, "CONTEMPORANEOUS")
        self.assertEqual(result.selected_lag_steps, 0)

    def test_duplicate_timestamp_fails_closed(self) -> None:
        items = list(self.observations((0,) + self.values[:-1]))
        items[1] = LeadLagObservation(
            timestamp_ns=items[0].timestamp_ns,
            left_value=items[1].left_value,
            right_value=items[1].right_value,
            regime_label=items[1].regime_label,
        )
        with self.assertRaises(LeadLagError):
            self.compute(tuple(items))

    def test_zero_variance_fails_closed(self) -> None:
        observations = tuple(
            LeadLagObservation(
                timestamp_ns=index * 100,
                left_value=1,
                right_value=2,
                regime_label="ALIGNED_BULLISH",
            )
            for index in range(15)
        )
        with self.assertRaises(LeadLagError):
            self.compute(observations)

    def test_regime_conditioning_is_deterministic(self) -> None:
        right = (0,) + self.values[:-1]
        items = list(self.observations(right))
        items[-1] = LeadLagObservation(
            timestamp_ns=items[-1].timestamp_ns,
            left_value=items[-1].left_value,
            right_value=items[-1].right_value,
            regime_label="CONFLICT",
        )
        first = self.compute(tuple(items))
        second = self.compute(tuple(reversed(items)))
        self.assertEqual(first, second)

    def test_temporal_precedence_is_not_causation(self) -> None:
        self.assertFalse(self.policy.temporal_precedence_is_causation)
        source = (ROOT / "packages/market_memory/lead_lag.py").read_text(encoding="utf-8").lower()
        for forbidden in ("likely_driver", "causes", "trade_action", "execution_authority"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
