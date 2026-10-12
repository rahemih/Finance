from __future__ import annotations

from pathlib import Path
import unittest

from packages.market_memory.attribution import (
    AttributionGuardrailError,
    AttributionGuardrailPolicy,
    assess_attribution,
)
from packages.market_memory.knowledge_graph import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/attribution-guardrail-policy.json"
HASH_A = "a" * 64


class AttributionGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
        self.policy = AttributionGuardrailPolicy.from_path(POLICY_PATH)
        self.event = GraphNode.build(
            node_kind="MACRO_EVENT",
            canonical_key="US:CPI",
            display_label="US CPI",
            policy=self.graph_policy,
        )
        self.market = GraphNode.build(
            node_kind="MARKET",
            canonical_key="DXY",
            display_label="US Dollar Index",
            policy=self.graph_policy,
        )
        self.asset = GraphNode.build(
            node_kind="ASSET",
            canonical_key="BTC",
            display_label="Bitcoin",
            policy=self.graph_policy,
        )

    def edge(
        self,
        source: GraphNode,
        target: GraphNode,
        *,
        kind: str,
        family: str,
        strength: int = 2000,
        uncertainty: int = 2500,
        samples: int = 3,
        suffix: str = "",
    ) -> GraphEdge:
        return GraphEdge.build(
            edge_kind=kind,
            source_node_id=source.node_id,
            target_node_id=target.node_id,
            valid_from_ns=100,
            valid_to_ns=200 + len(suffix),
            regime_label="ALIGNED_BULLISH",
            sample_count=samples,
            strength_bps=strength,
            uncertainty_bps=uncertainty,
            evidence_families=(family,),
            provenance_sha256=(HASH_A,),
            source_dataset_versions=(f"memory-v1{suffix}",),
            attribution_label="UNATTRIBUTED",
            policy=self.graph_policy,
        )

    def test_three_independent_families_with_event_context_can_be_likely_driver(self) -> None:
        edges = (
            self.edge(self.event, self.asset, kind="EVENT_CONTEXT", family="FUNDAMENTAL", suffix="-a"),
            self.edge(self.event, self.asset, kind="CONTEXT_LINK", family="TECHNICAL", suffix="-b"),
            self.edge(self.event, self.asset, kind="OBSERVED_ASSOCIATION", family="ORDER_FLOW", suffix="-c"),
        )
        result = assess_attribution(
            source_node=self.event,
            target_node=self.asset,
            edges=edges,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(result.narrative_label, "LIKELY_DRIVER")
        self.assertEqual(result.independent_evidence_family_count, 3)
        self.assertFalse(result.causal_proof)
        self.assertFalse(result.probability)

    def test_two_coherent_primary_families_can_be_supporting_factor(self) -> None:
        edges = (
            self.edge(self.market, self.asset, kind="OBSERVED_ASSOCIATION", family="TECHNICAL", suffix="-a"),
            self.edge(self.market, self.asset, kind="CONTEXT_LINK", family="ORDER_FLOW", suffix="-b"),
        )
        result = assess_attribution(
            source_node=self.market,
            target_node=self.asset,
            edges=edges,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(result.narrative_label, "SUPPORTING_FACTOR")
        self.assertIn("SOURCE_KIND_NOT_DRIVER_ELIGIBLE", result.reason_codes)

    def test_correlation_or_temporal_evidence_alone_cannot_be_driver(self) -> None:
        historical = self.edge(
            self.market,
            self.asset,
            kind="OBSERVED_ASSOCIATION",
            family="HISTORICAL",
            samples=20,
            strength=7000,
            uncertainty=1000,
        )
        result = assess_attribution(
            source_node=self.market,
            target_node=self.asset,
            edges=(historical,),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(result.narrative_label, "CONTEXT_ONLY")
        self.assertEqual(result.independent_evidence_family_count, 0)
        self.assertFalse(self.policy.correlation_alone_is_driver)
        self.assertFalse(self.policy.temporal_precedence_alone_is_driver)

    def test_conflicting_direction_degrades_to_context_only(self) -> None:
        edges = (
            self.edge(self.event, self.asset, kind="EVENT_CONTEXT", family="FUNDAMENTAL", strength=2500, suffix="-a"),
            self.edge(self.event, self.asset, kind="CONTEXT_LINK", family="TECHNICAL", strength=-2400, suffix="-b"),
            self.edge(self.event, self.asset, kind="OBSERVED_ASSOCIATION", family="ORDER_FLOW", strength=2300, suffix="-c"),
        )
        result = assess_attribution(
            source_node=self.event,
            target_node=self.asset,
            edges=edges,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(result.narrative_label, "CONTEXT_ONLY")
        self.assertFalse(result.direction_consistent)
        self.assertIn("DIRECTION_CONFLICT_OR_ZERO", result.reason_codes)

    def test_weak_or_high_uncertainty_evidence_degrades(self) -> None:
        weak = (
            self.edge(self.market, self.asset, kind="OBSERVED_ASSOCIATION", family="TECHNICAL", strength=200, suffix="-a"),
            self.edge(self.market, self.asset, kind="CONTEXT_LINK", family="ORDER_FLOW", strength=300, suffix="-b"),
        )
        weak_result = assess_attribution(
            source_node=self.market,
            target_node=self.asset,
            edges=weak,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(weak_result.narrative_label, "CONTEXT_ONLY")

        noisy = self.edge(
            self.event,
            self.asset,
            kind="EVENT_CONTEXT",
            family="FUNDAMENTAL",
            uncertainty=9000,
            samples=20,
        )
        noisy_result = assess_attribution(
            source_node=self.event,
            target_node=self.asset,
            edges=(noisy,),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(noisy_result.narrative_label, "INSUFFICIENT_EVIDENCE")

    def test_duplicate_endpoint_and_regime_mismatch_fail_closed(self) -> None:
        edge = self.edge(self.event, self.asset, kind="EVENT_CONTEXT", family="FUNDAMENTAL")
        with self.assertRaises(AttributionGuardrailError):
            assess_attribution(
                source_node=self.event,
                target_node=self.asset,
                edges=(edge, edge),
                graph_policy=self.graph_policy,
                policy=self.policy,
            )
        with self.assertRaises(AttributionGuardrailError):
            assess_attribution(
                source_node=self.event,
                target_node=self.market,
                edges=(edge,),
                graph_policy=self.graph_policy,
                policy=self.policy,
            )
        conflict = GraphEdge.build(
            edge_kind="CONTEXT_LINK",
            source_node_id=self.event.node_id,
            target_node_id=self.asset.node_id,
            valid_from_ns=100,
            valid_to_ns=201,
            regime_label="CONFLICT",
            sample_count=3,
            strength_bps=2000,
            uncertainty_bps=2000,
            evidence_families=("TECHNICAL",),
            provenance_sha256=(HASH_A,),
            source_dataset_versions=("memory-conflict",),
            attribution_label="UNATTRIBUTED",
            policy=self.graph_policy,
        )
        with self.assertRaises(AttributionGuardrailError):
            assess_attribution(
                source_node=self.event,
                target_node=self.asset,
                edges=(edge, conflict),
                graph_policy=self.graph_policy,
                policy=self.policy,
            )

    def test_assessment_is_order_independent_and_edges_remain_unattributed(self) -> None:
        edges = (
            self.edge(self.event, self.asset, kind="EVENT_CONTEXT", family="FUNDAMENTAL", suffix="-a"),
            self.edge(self.event, self.asset, kind="CONTEXT_LINK", family="TECHNICAL", suffix="-b"),
            self.edge(self.event, self.asset, kind="OBSERVED_ASSOCIATION", family="ORDER_FLOW", suffix="-c"),
        )
        first = assess_attribution(
            source_node=self.event,
            target_node=self.asset,
            edges=edges,
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        second = assess_attribution(
            source_node=self.event,
            target_node=self.asset,
            edges=tuple(reversed(edges)),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )
        self.assertEqual(first, second)
        self.assertEqual(first.reason_codes, tuple(sorted(first.reason_codes)))
        self.assertTrue(all(edge.attribution_label == "UNATTRIBUTED" for edge in edges))

    def test_narrative_labels_have_no_probability_or_trade_authority(self) -> None:
        self.assertFalse(self.policy.likely_driver_is_causal_proof)
        self.assertFalse(self.policy.narrative_labels_are_probability)
        source = (ROOT / "packages/market_memory/attribution.py").read_text(encoding="utf-8").lower()
        for forbidden in ("trade_action", "risk_approval", "execution_authority", "signal_probability"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
