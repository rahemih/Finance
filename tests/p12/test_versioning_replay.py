from __future__ import annotations

from pathlib import Path
import unittest

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from packages.market_memory.knowledge_graph import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphPolicy,
    KnowledgeGraphSnapshot,
)
from packages.market_memory.versioning_replay import (
    MarketMemoryReplayError,
    MarketMemoryReplayMismatch,
    MarketMemoryReplayPolicy,
    assert_market_memory_replay_equivalent,
    build_market_memory_replay_record,
    build_market_memory_version_bundle,
)


ROOT = Path(__file__).resolve().parents[2]
REPLAY_POLICY_PATH = ROOT / "config/historical-data/replay-snapshot-policy.json"
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/versioning-replay-policy.json"


class VersioningReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.replay_policy = ReplaySnapshotPolicy.from_path(REPLAY_POLICY_PATH)
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
        self.policy = MarketMemoryReplayPolicy.from_path(POLICY_PATH)
        self.replay = ReplaySnapshot.build(
            replay_start_ns=0,
            replay_end_ns=1000,
            snapshot_cutoff_ns=900,
            clock_mode="EVENT_TIME",
            scope_ids=("BTC",),
            dataset_refs=(
                ReplayDatasetRef(
                    dataset_name="market-memory",
                    dataset_version="a" * 64,
                    schema_version="1.0",
                    window_start_ns=0,
                    window_end_ns=1000,
                    membership_root_sha256="b" * 64,
                    rights_class="INTERNAL",
                ),
            ),
            feature_refs=(),
            vintage_refs=(),
            quality_rule_versions=("p12-quality-v1",),
            config_sha256="c" * 64,
            code_artifact_sha256="d" * 64,
            rights_class="INTERNAL",
            policy=self.replay_policy,
        )
        self.source = GraphNode.build(
            node_kind="MARKET",
            canonical_key="DXY",
            display_label="US Dollar Index",
            policy=self.graph_policy,
        )
        self.target = GraphNode.build(
            node_kind="ASSET",
            canonical_key="BTC",
            display_label="Bitcoin",
            policy=self.graph_policy,
        )
        self.edge = GraphEdge.build(
            edge_kind="OBSERVED_ASSOCIATION",
            source_node_id=self.source.node_id,
            target_node_id=self.target.node_id,
            valid_from_ns=100,
            valid_to_ns=401,
            regime_label="ALIGNED_BULLISH",
            sample_count=30,
            strength_bps=-2500,
            uncertainty_bps=2200,
            evidence_families=("HISTORICAL",),
            provenance_sha256=("e" * 64,),
            source_dataset_versions=("memory-v1",),
            attribution_label="UNATTRIBUTED",
            policy=self.graph_policy,
        )
        self.graph = KnowledgeGraphSnapshot.build(
            nodes=(self.target, self.source),
            edges=(self.edge,),
            policy=self.graph_policy,
        )
        self.policy_hashes = {
            "P12_A_KNOWLEDGE_GRAPH": "1" * 64,
            "P12_B_CONDITIONAL_CORRELATION": "2" * 64,
            "P12_C_LEAD_LAG": "3" * 64,
            "P12_D_EVENT_STUDY": "4" * 64,
            "P12_E_HISTORICAL_ANALOG": "5" * 64,
            "P12_F_SEASONALITY": "6" * 64,
            "P12_G_ATTRIBUTION_GUARDRAIL": "7" * 64,
        }
        self.outputs = {
            "P12_B_CONDITIONAL_CORRELATION": {"correlation_bps": -2500},
            "P12_C_LEAD_LAG": {"lead_state": "LEFT_LEADS_RIGHT"},
            "P12_D_EVENT_STUDY": {"mean_response_bps": 120},
            "P12_E_HISTORICAL_ANALOG": {"similarity_bps": 8500},
            "P12_F_SEASONALITY": {"mean_return_bps": 80},
            "P12_G_ATTRIBUTION_GUARDRAIL": {"narrative_label": "CONTEXT_ONLY"},
        }

    def bundle(self, *, as_of_ns: int = 500):
        return build_market_memory_version_bundle(
            as_of_ns=as_of_ns,
            replay_snapshot=self.replay,
            graph_snapshot=self.graph,
            component_policy_sha256=self.policy_hashes,
            policy=self.policy,
        )

    def test_bundle_identity_is_order_independent_and_binds_p06_replay(self) -> None:
        first = self.bundle()
        reversed_hashes = dict(reversed(tuple(self.policy_hashes.items())))
        second = build_market_memory_version_bundle(
            as_of_ns=500,
            replay_snapshot=self.replay,
            graph_snapshot=self.graph,
            component_policy_sha256=reversed_hashes,
            policy=self.policy,
        )
        self.assertEqual(first, second)
        self.assertEqual(first.replay_snapshot_id, self.replay.snapshot_id)
        self.assertEqual(first.graph_snapshot_id, self.graph.snapshot_id)
        self.assertEqual(first.graph_source_dataset_versions, ("memory-v1",))
        self.assertEqual(first.graph_provenance_sha256, ("e" * 64,))
        self.assertEqual(first.replay_dataset_versions, ("a" * 64,))

    def test_exact_policy_component_set_is_required(self) -> None:
        missing = dict(self.policy_hashes)
        missing.pop("P12_G_ATTRIBUTION_GUARDRAIL")
        with self.assertRaises(MarketMemoryReplayError):
            build_market_memory_version_bundle(
                as_of_ns=500,
                replay_snapshot=self.replay,
                graph_snapshot=self.graph,
                component_policy_sha256=missing,
                policy=self.policy,
            )

    def test_p06_anti_lookahead_is_enforced(self) -> None:
        with self.assertRaises(MarketMemoryReplayError):
            self.bundle(as_of_ns=950)

    def test_graph_evidence_cannot_extend_beyond_replay_as_of(self) -> None:
        with self.assertRaises(MarketMemoryReplayError):
            self.bundle(as_of_ns=300)

    def test_replay_record_is_order_independent_and_equivalent(self) -> None:
        bundle = self.bundle()
        first = build_market_memory_replay_record(
            bundle=bundle,
            component_outputs=self.outputs,
            policy=self.policy,
        )
        reversed_outputs = dict(reversed(tuple(self.outputs.items())))
        second = build_market_memory_replay_record(
            bundle=bundle,
            component_outputs=reversed_outputs,
            policy=self.policy,
        )
        self.assertEqual(first, second)
        assert_market_memory_replay_equivalent(first, second)

    def test_changed_output_fails_replay_equivalence(self) -> None:
        bundle = self.bundle()
        expected = build_market_memory_replay_record(
            bundle=bundle,
            component_outputs=self.outputs,
            policy=self.policy,
        )
        changed = dict(self.outputs)
        changed["P12_E_HISTORICAL_ANALOG"] = {"similarity_bps": 8400}
        actual = build_market_memory_replay_record(
            bundle=bundle,
            component_outputs=changed,
            policy=self.policy,
        )
        with self.assertRaises(MarketMemoryReplayMismatch):
            assert_market_memory_replay_equivalent(expected, actual)

    def test_missing_replay_component_fails_closed(self) -> None:
        bundle = self.bundle()
        missing = dict(self.outputs)
        missing.pop("P12_F_SEASONALITY")
        with self.assertRaises(MarketMemoryReplayError):
            build_market_memory_replay_record(
                bundle=bundle,
                component_outputs=missing,
                policy=self.policy,
            )

    def test_p19_boundary_and_safety_remain_explicit(self) -> None:
        self.assertEqual(self.policy.end_to_end_decision_replay_owner, "P19")
        self.assertEqual(self.policy.production_memory_version_store_vendor, "NOT_SELECTED")
        source = (ROOT / "packages/market_memory/versioning_replay.py").read_text(encoding="utf-8").lower()
        for forbidden in ("trade_action", "signal_probability", "risk_approval", "execution_authority"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
