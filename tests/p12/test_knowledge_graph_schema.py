from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import unittest

from packages.market_memory.knowledge_graph import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphError,
    KnowledgeGraphPolicy,
    KnowledgeGraphSnapshot,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
HASH_A = "a" * 64
HASH_B = "b" * 64


class KnowledgeGraphSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = KnowledgeGraphPolicy.from_path(POLICY_PATH)

    def node(self, kind: str, key: str) -> GraphNode:
        return GraphNode.build(
            node_kind=kind,
            canonical_key=key,
            display_label=key,
            policy=self.policy,
        )

    def edge(self, source: GraphNode, target: GraphNode, **overrides: object) -> GraphEdge:
        values: dict[str, object] = {
            "edge_kind": "OBSERVED_ASSOCIATION",
            "source_node_id": source.node_id,
            "target_node_id": target.node_id,
            "valid_from_ns": 100,
            "valid_to_ns": 200,
            "regime_label": "ALIGNED_BULLISH",
            "sample_count": 25,
            "strength_bps": 3200,
            "uncertainty_bps": 1800,
            "evidence_families": ("TECHNICAL", "ORDER_FLOW"),
            "provenance_sha256": (HASH_A, HASH_B),
            "source_dataset_versions": ("dataset-v1", "dataset-v2"),
            "attribution_label": "UNATTRIBUTED",
            "policy": self.policy,
        }
        values.update(overrides)
        return GraphEdge.build(**values)  # type: ignore[arg-type]

    def test_cira_node_kinds_are_in_canonical_ontology(self) -> None:
        self.assertIn("CAPITAL_FLOW", self.policy.node_kinds)
        self.assertIn("ROTATION_EPISODE", self.policy.node_kinds)

    def test_snapshot_identity_is_deterministic_and_order_independent(self) -> None:
        btc = self.node("ASSET", "BTC")
        dxy = self.node("MARKET", "DXY")
        flow = self.node("CAPITAL_FLOW", "BTC:INFLOW")
        first_edge = self.edge(btc, dxy)
        second_edge = GraphEdge.build(
            edge_kind="CAPITAL_FLOW_LINK",
            source_node_id=flow.node_id,
            target_node_id=btc.node_id,
            valid_from_ns=100,
            valid_to_ns=200,
            regime_label="ALIGNED_BULLISH",
            sample_count=12,
            strength_bps=2500,
            uncertainty_bps=2200,
            evidence_families=("ORDER_FLOW",),
            provenance_sha256=(HASH_A,),
            source_dataset_versions=("flow-v1",),
            attribution_label="UNATTRIBUTED",
            policy=self.policy,
        )
        first = KnowledgeGraphSnapshot.build(
            nodes=(btc, dxy, flow),
            edges=(first_edge, second_edge),
            policy=self.policy,
        )
        second = KnowledgeGraphSnapshot.build(
            nodes=(flow, btc, dxy),
            edges=(second_edge, first_edge),
            policy=self.policy,
        )
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(first.payload(), second.payload())

    def test_edge_requires_time_regime_sample_strength_uncertainty_and_lineage(self) -> None:
        btc = self.node("ASSET", "BTC")
        dxy = self.node("MARKET", "DXY")
        edge = self.edge(btc, dxy)
        self.assertEqual(edge.sample_count, 25)
        self.assertEqual(edge.regime_label, "ALIGNED_BULLISH")
        self.assertEqual(edge.strength_bps, 3200)
        self.assertEqual(edge.uncertainty_bps, 1800)
        self.assertEqual(edge.provenance_sha256, (HASH_A, HASH_B))
        self.assertEqual(edge.source_dataset_versions, ("dataset-v1", "dataset-v2"))

    def test_invalid_period_and_bounds_fail_closed(self) -> None:
        btc = self.node("ASSET", "BTC")
        dxy = self.node("MARKET", "DXY")
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, valid_to_ns=100)
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, strength_bps=10001)
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, uncertainty_bps=10001)
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, sample_count=0)

    def test_unknown_endpoint_and_duplicate_edge_fail_closed(self) -> None:
        btc = self.node("ASSET", "BTC")
        dxy = self.node("MARKET", "DXY")
        edge = self.edge(btc, dxy)
        with self.assertRaises(KnowledgeGraphError):
            KnowledgeGraphSnapshot.build(nodes=(btc,), edges=(edge,), policy=self.policy)
        with self.assertRaises(KnowledgeGraphError):
            KnowledgeGraphSnapshot.build(
                nodes=(btc, dxy),
                edges=(edge, edge),
                policy=self.policy,
            )

    def test_causality_label_and_unknown_ontology_fail_closed(self) -> None:
        with self.assertRaises(KnowledgeGraphError):
            self.node("TRADE_SIGNAL", "BTC-LONG")
        btc = self.node("ASSET", "BTC")
        dxy = self.node("MARKET", "DXY")
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, edge_kind="CAUSES")
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, attribution_label="LIKELY_DRIVER")

    def test_self_edge_and_missing_lineage_fail_closed(self) -> None:
        btc = self.node("ASSET", "BTC")
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, btc)
        dxy = self.node("MARKET", "DXY")
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, provenance_sha256=())
        with self.assertRaises(KnowledgeGraphError):
            self.edge(btc, dxy, source_dataset_versions=())

    def test_no_trade_probability_risk_or_execution_authority_fields(self) -> None:
        names = {field.name for field in fields(GraphEdge)}
        forbidden = {
            "trade_action",
            "signal_probability",
            "buy_probability",
            "sell_probability",
            "risk_approval",
            "execution_authority",
            "order",
        }
        self.assertTrue(names.isdisjoint(forbidden))
        source = (ROOT / "packages/market_memory/knowledge_graph.py").read_text(encoding="utf-8").lower()
        for forbidden_import in ("packages.execution", "adapters.execution", "import requests", "import httpx"):
            self.assertNotIn(forbidden_import, source)


if __name__ == "__main__":
    unittest.main()
