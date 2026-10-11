from __future__ import annotations

from pathlib import Path
import unittest

from packages.market_memory.event_study import (
    EventStudyError,
    EventStudyObservation,
    EventStudyPolicy,
    compute_event_study,
)
from packages.market_memory.knowledge_graph import GraphNode, KnowledgeGraphPolicy


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/event-study-policy.json"
HASH_A = "a" * 64


class EventStudyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
        self.policy = EventStudyPolicy.from_path(POLICY_PATH)
        self.event_node = GraphNode.build(
            node_kind="MACRO_EVENT",
            canonical_key="US:CPI",
            display_label="US CPI",
            policy=self.graph_policy,
        )
        self.target_node = GraphNode.build(
            node_kind="ASSET",
            canonical_key="BTC",
            display_label="Bitcoin",
            policy=self.graph_policy,
        )

    def observations(
        self,
        posts: tuple[int, ...],
        *,
        regime: str = "ALIGNED_BULLISH",
    ) -> tuple[EventStudyObservation, ...]:
        return tuple(
            EventStudyObservation(
                event_instance_id=f"event-{index}",
                event_time_ns=1000 + index * 1000,
                pre_time_ns=900 + index * 1000,
                post_time_ns=1100 + index * 1000,
                pre_value=100,
                post_value=post,
                regime_label=regime,
            )
            for index, post in enumerate(posts)
        )

    def compute(self, observations: tuple[EventStudyObservation, ...]):
        return compute_event_study(
            observations,
            pre_window_ns=100,
            post_window_ns=100,
            regime_label="ALIGNED_BULLISH",
            event_node=self.event_node,
            target_node=self.target_node,
            provenance_sha256=(HASH_A,),
            source_dataset_versions=("events-v1", "prices-v1"),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )

    def test_positive_event_response_is_deterministic(self) -> None:
        result = self.compute(self.observations((102, 103, 101, 102)))
        self.assertEqual(result.responses_bps, (200, 300, 100, 200))
        self.assertEqual(result.mean_response_bps, 200)
        self.assertEqual(result.dispersion_bps, 50)
        self.assertEqual(result.edge.edge_kind, "EVENT_CONTEXT")
        self.assertEqual(result.edge.attribution_label, "UNATTRIBUTED")
        self.assertIn("FUNDAMENTAL", result.edge.evidence_families)
        self.assertIn("HISTORICAL", result.edge.evidence_families)

    def test_negative_event_response_uses_symmetric_truncation(self) -> None:
        result = self.compute(self.observations((98, 97, 99)))
        self.assertEqual(result.responses_bps, (-200, -300, -100))
        self.assertEqual(result.mean_response_bps, -200)

    def test_order_and_regime_conditioning_are_deterministic(self) -> None:
        base = list(self.observations((102, 103, 101, 102)))
        base[-1] = EventStudyObservation(
            event_instance_id=base[-1].event_instance_id,
            event_time_ns=base[-1].event_time_ns,
            pre_time_ns=base[-1].pre_time_ns,
            post_time_ns=base[-1].post_time_ns,
            pre_value=base[-1].pre_value,
            post_value=base[-1].post_value,
            regime_label="CONFLICT",
        )
        first = self.compute(tuple(base))
        second = self.compute(tuple(reversed(base)))
        self.assertEqual(first, second)
        self.assertEqual(first.sample_count, 3)

    def test_window_mismatch_fails_closed(self) -> None:
        items = list(self.observations((102, 103, 101)))
        first = items[0]
        items[0] = EventStudyObservation(
            event_instance_id=first.event_instance_id,
            event_time_ns=first.event_time_ns,
            pre_time_ns=first.pre_time_ns - 1,
            post_time_ns=first.post_time_ns,
            pre_value=first.pre_value,
            post_value=first.post_value,
            regime_label=first.regime_label,
        )
        with self.assertRaises(EventStudyError):
            self.compute(tuple(items))

    def test_duplicate_identity_and_timestamp_fail_closed(self) -> None:
        items = list(self.observations((102, 103, 101)))
        second = items[1]
        items[1] = EventStudyObservation(
            event_instance_id=items[0].event_instance_id,
            event_time_ns=second.event_time_ns,
            pre_time_ns=second.pre_time_ns,
            post_time_ns=second.post_time_ns,
            pre_value=second.pre_value,
            post_value=second.post_value,
            regime_label=second.regime_label,
        )
        with self.assertRaises(EventStudyError):
            self.compute(tuple(items))

        items = list(self.observations((102, 103, 101)))
        second = items[1]
        items[1] = EventStudyObservation(
            event_instance_id=second.event_instance_id,
            event_time_ns=items[0].event_time_ns,
            pre_time_ns=items[0].pre_time_ns,
            post_time_ns=items[0].post_time_ns,
            pre_value=second.pre_value,
            post_value=second.post_value,
            regime_label=second.regime_label,
        )
        with self.assertRaises(EventStudyError):
            self.compute(tuple(items))

    def test_minimum_sample_zero_prevalue_and_outlier_fail_closed(self) -> None:
        with self.assertRaises(EventStudyError):
            self.compute(self.observations((102, 103)))

        items = list(self.observations((102, 103, 101)))
        first = items[0]
        items[0] = EventStudyObservation(
            event_instance_id=first.event_instance_id,
            event_time_ns=first.event_time_ns,
            pre_time_ns=first.pre_time_ns,
            post_time_ns=first.post_time_ns,
            pre_value=0,
            post_value=first.post_value,
            regime_label=first.regime_label,
        )
        with self.assertRaises(EventStudyError):
            self.compute(tuple(items))

        with self.assertRaises(EventStudyError):
            self.compute(self.observations((250, 103, 101)))

    def test_cira_event_context_node_kinds_are_supported(self) -> None:
        self.assertIn("CAPITAL_FLOW", self.policy.event_node_kinds)
        self.assertIn("ROTATION_EPISODE", self.policy.event_node_kinds)

    def test_event_response_is_not_causal_or_trade_authority(self) -> None:
        self.assertFalse(self.policy.event_response_is_causation)
        source = (ROOT / "packages/market_memory/event_study.py").read_text(encoding="utf-8").lower()
        for forbidden in ("likely_driver", "trade_action", "risk_approval", "execution_authority"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
