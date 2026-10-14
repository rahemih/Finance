from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence


class RiskPolicyError(ValueError):
    """P15-A risk-policy hierarchy input violates governed invariants."""


_SCOPE_ORDER = (
    "GLOBAL",
    "PORTFOLIO",
    "MARKET",
    "ASSET",
    "STRATEGY",
    "TRADE",
)
_SCOPE_INDEX = {scope: index for index, scope in enumerate(_SCOPE_ORDER)}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class RiskBudgetNode:
    node_id: str
    scope: str
    subject_id: str
    parent_id: str | None
    budget_bps: int
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise RiskPolicyError("node_id must be non-empty")
        if self.scope not in _SCOPE_INDEX:
            raise RiskPolicyError(f"unknown risk scope: {self.scope}")
        if not self.subject_id.strip():
            raise RiskPolicyError("subject_id must be non-empty")
        if not 0 <= self.budget_bps <= 10_000:
            raise RiskPolicyError("budget_bps must be within [0, 10000]")
        if self.scope == "GLOBAL" and self.parent_id is not None:
            raise RiskPolicyError("GLOBAL node cannot have a parent")
        if self.scope != "GLOBAL" and not self.parent_id:
            raise RiskPolicyError("non-GLOBAL node requires parent_id")

    @property
    def identity(self) -> str:
        return _sha256(
            {
                "node_id": self.node_id,
                "scope": self.scope,
                "subject_id": self.subject_id,
                "parent_id": self.parent_id,
                "budget_bps": self.budget_bps,
                "enabled": self.enabled,
            }
        )


@dataclass(frozen=True)
class RiskBudgetRequest:
    request_id: str
    leaf_node_id: str
    requested_budget_bps: int
    as_of_ns: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise RiskPolicyError("request_id must be non-empty")
        if not self.leaf_node_id.strip():
            raise RiskPolicyError("leaf_node_id must be non-empty")
        if not 1 <= self.requested_budget_bps <= 10_000:
            raise RiskPolicyError("requested_budget_bps must be within [1, 10000]")
        if self.as_of_ns < 0:
            raise RiskPolicyError("as_of_ns must be non-negative")


@dataclass(frozen=True)
class RiskBudgetDecision:
    decision_id: str
    request_id: str
    status: str
    limiting_node_id: str | None
    reason_codes: tuple[str, ...]
    evaluated_path: tuple[str, ...]
    position_sizing_authority: bool = False
    execution_authority: bool = False


@dataclass(frozen=True)
class RiskPolicyHierarchy:
    policy_version: str
    effective_from_ns: int
    nodes: tuple[RiskBudgetNode, ...]
    policy_id: str

    @classmethod
    def build(
        cls,
        *,
        policy_version: str,
        effective_from_ns: int,
        nodes: Sequence[RiskBudgetNode],
    ) -> "RiskPolicyHierarchy":
        if not policy_version.strip():
            raise RiskPolicyError("policy_version must be non-empty")
        if effective_from_ns < 0:
            raise RiskPolicyError("effective_from_ns must be non-negative")
        ordered = tuple(sorted(nodes, key=lambda item: item.node_id))
        if not ordered:
            raise RiskPolicyError("risk hierarchy must contain nodes")

        by_id = {node.node_id: node for node in ordered}
        if len(by_id) != len(ordered):
            raise RiskPolicyError("duplicate risk node_id")

        roots = [node for node in ordered if node.scope == "GLOBAL"]
        if len(roots) != 1:
            raise RiskPolicyError("exactly one GLOBAL root is required")
        root = roots[0]
        if root.budget_bps != 10_000:
            raise RiskPolicyError(
                "GLOBAL root must represent 10000 bps of the governed total risk budget"
            )

        children: dict[str, list[RiskBudgetNode]] = {node.node_id: [] for node in ordered}
        for node in ordered:
            if node.scope == "GLOBAL":
                continue
            assert node.parent_id is not None
            parent = by_id.get(node.parent_id)
            if parent is None:
                raise RiskPolicyError(f"missing parent node: {node.parent_id}")
            if _SCOPE_INDEX[parent.scope] >= _SCOPE_INDEX[node.scope]:
                raise RiskPolicyError("child scope must be below parent scope")
            if node.budget_bps > parent.budget_bps:
                raise RiskPolicyError("child budget cannot exceed parent budget")
            children[parent.node_id].append(node)

        for parent_id, direct_children in children.items():
            parent = by_id[parent_id]
            delegated = sum(child.budget_bps for child in direct_children)
            if delegated > parent.budget_bps:
                raise RiskPolicyError(
                    f"direct child budgets exceed parent budget: {parent_id}"
                )

        payload = {
            "policy_version": policy_version,
            "effective_from_ns": effective_from_ns,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "scope": node.scope,
                    "subject_id": node.subject_id,
                    "parent_id": node.parent_id,
                    "budget_bps": node.budget_bps,
                    "enabled": node.enabled,
                }
                for node in ordered
            ],
        }
        return cls(
            policy_version=policy_version,
            effective_from_ns=effective_from_ns,
            nodes=ordered,
            policy_id=_sha256(payload),
        )

    @property
    def by_id(self) -> Mapping[str, RiskBudgetNode]:
        return {node.node_id: node for node in self.nodes}

    def _path_to_root(self, leaf_node_id: str) -> tuple[RiskBudgetNode, ...]:
        by_id = self.by_id
        leaf = by_id.get(leaf_node_id)
        if leaf is None:
            raise RiskPolicyError(f"unknown leaf node: {leaf_node_id}")
        path: list[RiskBudgetNode] = []
        seen: set[str] = set()
        current = leaf
        while True:
            if current.node_id in seen:
                raise RiskPolicyError("cycle detected in risk hierarchy")
            seen.add(current.node_id)
            path.append(current)
            if current.parent_id is None:
                break
            parent = by_id.get(current.parent_id)
            if parent is None:
                raise RiskPolicyError(f"missing parent node: {current.parent_id}")
            current = parent
        return tuple(path)

    def evaluate(
        self,
        *,
        request: RiskBudgetRequest,
        utilization_bps: Mapping[str, int],
    ) -> RiskBudgetDecision:
        if request.as_of_ns < self.effective_from_ns:
            raise RiskPolicyError("request predates risk policy effective time")

        path = self._path_to_root(request.leaf_node_id)
        reasons: list[str] = []
        limiting_node_id: str | None = None

        for node in path:
            used = utilization_bps.get(node.node_id, 0)
            if not 0 <= used <= node.budget_bps:
                raise RiskPolicyError(
                    f"utilization for {node.node_id} must be within its governed budget"
                )
            if not node.enabled:
                reasons.append("RISK_NODE_DISABLED")
                limiting_node_id = node.node_id
                break
            remaining = node.budget_bps - used
            if request.requested_budget_bps > remaining:
                reasons.append("RISK_BUDGET_EXCEEDED")
                limiting_node_id = node.node_id
                break

        status = "VETO" if reasons else "POLICY_CAPACITY_ELIGIBLE"
        payload = {
            "policy_id": self.policy_id,
            "request_id": request.request_id,
            "leaf_node_id": request.leaf_node_id,
            "requested_budget_bps": request.requested_budget_bps,
            "as_of_ns": request.as_of_ns,
            "utilization_bps": {
                key: utilization_bps[key] for key in sorted(utilization_bps)
            },
            "status": status,
            "limiting_node_id": limiting_node_id,
            "reason_codes": reasons,
            "evaluated_path": [node.node_id for node in path],
            "position_sizing_authority": False,
            "execution_authority": False,
        }
        return RiskBudgetDecision(
            decision_id=_sha256(payload),
            request_id=request.request_id,
            status=status,
            limiting_node_id=limiting_node_id,
            reason_codes=tuple(reasons),
            evaluated_path=tuple(node.node_id for node in path),
        )
