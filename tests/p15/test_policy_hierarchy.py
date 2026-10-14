from __future__ import annotations

from dataclasses import replace
import unittest

from packages.risk.policy_hierarchy import (
    RiskBudgetNode,
    RiskBudgetRequest,
    RiskPolicyError,
    RiskPolicyHierarchy,
)


def nodes() -> tuple[RiskBudgetNode, ...]:
    return (
        RiskBudgetNode("global", "GLOBAL", "GLOBAL", None, 10_000),
        RiskBudgetNode("portfolio-main", "PORTFOLIO", "MAIN", "global", 8_000),
        RiskBudgetNode("market-crypto", "MARKET", "CRYPTO", "portfolio-main", 6_000),
        RiskBudgetNode("asset-btc", "ASSET", "BTC", "market-crypto", 4_000),
        RiskBudgetNode("strategy-trend", "STRATEGY", "TREND", "asset-btc", 2_500),
        RiskBudgetNode("trade-candidate", "TRADE", "candidate-1", "strategy-trend", 1_000),
    )


def hierarchy(items: tuple[RiskBudgetNode, ...] | None = None) -> RiskPolicyHierarchy:
    return RiskPolicyHierarchy.build(
        policy_version="p15a-test-v1",
        effective_from_ns=1_000,
        nodes=items or nodes(),
    )


class RiskPolicyHierarchyTests(unittest.TestCase):
    def test_valid_hierarchy_builds_with_one_global_root(self) -> None:
        policy = hierarchy()
        self.assertEqual(policy.by_id["global"].budget_bps, 10_000)
        self.assertEqual(len(policy.nodes), 6)

    def test_exactly_one_global_root_is_required(self) -> None:
        without_root = tuple(item for item in nodes() if item.scope != "GLOBAL")
        with self.assertRaises(RiskPolicyError):
            hierarchy(without_root)

        duplicate_root = nodes() + (
            RiskBudgetNode("global-2", "GLOBAL", "GLOBAL-2", None, 10_000),
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(duplicate_root)

    def test_global_root_is_structurally_full_governed_budget(self) -> None:
        changed = (
            RiskBudgetNode("global", "GLOBAL", "GLOBAL", None, 9_999),
            *nodes()[1:],
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(changed)

    def test_missing_parent_and_invalid_scope_order_fail_closed(self) -> None:
        missing_parent = nodes() + (
            RiskBudgetNode("orphan", "TRADE", "orphan", "missing", 100),
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(missing_parent)

        bad_order = (
            RiskBudgetNode("global", "GLOBAL", "GLOBAL", None, 10_000),
            RiskBudgetNode("trade", "TRADE", "trade", "global", 2_000),
            RiskBudgetNode("asset", "ASSET", "asset", "trade", 1_000),
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(bad_order)

    def test_child_budget_cannot_exceed_parent(self) -> None:
        bad = (
            RiskBudgetNode("global", "GLOBAL", "GLOBAL", None, 10_000),
            RiskBudgetNode("portfolio", "PORTFOLIO", "MAIN", "global", 4_000),
            RiskBudgetNode("market", "MARKET", "CRYPTO", "portfolio", 4_001),
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(bad)

    def test_direct_child_aggregate_cannot_exceed_parent(self) -> None:
        bad = (
            RiskBudgetNode("global", "GLOBAL", "GLOBAL", None, 10_000),
            RiskBudgetNode("portfolio-a", "PORTFOLIO", "A", "global", 6_000),
            RiskBudgetNode("portfolio-b", "PORTFOLIO", "B", "global", 5_000),
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(bad)

    def test_duplicate_node_ids_fail_closed(self) -> None:
        bad = nodes() + (
            RiskBudgetNode("asset-btc", "ASSET", "BTC-DUP", "market-crypto", 100),
        )
        with self.assertRaises(RiskPolicyError):
            hierarchy(bad)

    def test_budget_bounds_fail_closed(self) -> None:
        with self.assertRaises(RiskPolicyError):
            RiskBudgetNode("x", "GLOBAL", "GLOBAL", None, 10_001)
        with self.assertRaises(RiskPolicyError):
            RiskBudgetNode("x", "GLOBAL", "GLOBAL", None, -1)

    def test_policy_identity_is_input_order_independent(self) -> None:
        first = hierarchy()
        second = hierarchy(tuple(reversed(nodes())))
        self.assertEqual(first.policy_id, second.policy_id)

    def test_disabled_node_causes_veto(self) -> None:
        changed = tuple(
            replace(item, enabled=False) if item.node_id == "asset-btc" else item
            for item in nodes()
        )
        policy = hierarchy(changed)
        decision = policy.evaluate(
            request=RiskBudgetRequest("req-1", "trade-candidate", 100, 1_100),
            utilization_bps={},
        )
        self.assertEqual(decision.status, "VETO")
        self.assertEqual(decision.limiting_node_id, "asset-btc")
        self.assertEqual(decision.reason_codes, ("RISK_NODE_DISABLED",))

    def test_increment_above_any_ancestor_remaining_budget_is_vetoed(self) -> None:
        policy = hierarchy()
        decision = policy.evaluate(
            request=RiskBudgetRequest("req-2", "trade-candidate", 400, 1_100),
            utilization_bps={"trade-candidate": 700},
        )
        self.assertEqual(decision.status, "VETO")
        self.assertEqual(decision.limiting_node_id, "trade-candidate")
        self.assertEqual(decision.reason_codes, ("RISK_BUDGET_EXCEEDED",))

    def test_utilization_outside_governed_budget_fails_closed(self) -> None:
        policy = hierarchy()
        with self.assertRaises(RiskPolicyError):
            policy.evaluate(
                request=RiskBudgetRequest("req-3", "trade-candidate", 100, 1_100),
                utilization_bps={"trade-candidate": 1_001},
            )

    def test_eligible_capacity_is_not_sizing_or_execution_approval(self) -> None:
        policy = hierarchy()
        decision = policy.evaluate(
            request=RiskBudgetRequest("req-4", "trade-candidate", 100, 1_100),
            utilization_bps={"trade-candidate": 100, "strategy-trend": 200},
        )
        self.assertEqual(decision.status, "POLICY_CAPACITY_ELIGIBLE")
        self.assertFalse(decision.position_sizing_authority)
        self.assertFalse(decision.execution_authority)

    def test_decision_identity_is_deterministic(self) -> None:
        policy = hierarchy()
        request = RiskBudgetRequest("req-5", "trade-candidate", 100, 1_100)
        left = policy.evaluate(request=request, utilization_bps={"trade-candidate": 100})
        right = policy.evaluate(request=request, utilization_bps={"trade-candidate": 100})
        self.assertEqual(left.decision_id, right.decision_id)

    def test_request_before_policy_effective_time_fails_closed(self) -> None:
        policy = hierarchy()
        with self.assertRaises(RiskPolicyError):
            policy.evaluate(
                request=RiskBudgetRequest("req-6", "trade-candidate", 100, 999),
                utilization_bps={},
            )


if __name__ == "__main__":
    unittest.main()
