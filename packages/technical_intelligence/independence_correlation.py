from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import json
from pathlib import Path
from typing import Mapping, Sequence, cast

from .foundation import TechnicalEvidence, TechnicalFoundationError


class IndependenceCorrelationError(TechnicalFoundationError):
    """P08-H independence/correlation audit invariant failure."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise IndependenceCorrelationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise IndependenceCorrelationError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IndependenceCorrelationError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise IndependenceCorrelationError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise IndependenceCorrelationError(f"{field} must be a positive integer")
    return value


def _decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise IndependenceCorrelationError(f"{field} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise IndependenceCorrelationError(
            f"{field} must be decimal-compatible"
        ) from exc
    if not result.is_finite():
        raise IndependenceCorrelationError(f"{field} must be finite")
    return result


def _decimal_text(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
    if quantized == 0:
        return "0"
    return format(quantized.normalize(), "f")


def _pair_key(family_a: str, family_b: str) -> tuple[str, str]:
    return (
        (family_a, family_b)
        if family_a <= family_b
        else (family_b, family_a)
    )


@dataclass(frozen=True, slots=True)
class FamilyAuditRule:
    family: str
    expected_independence_group: str
    correlation_cluster: str
    directional_vote_eligible: bool
    relationship_semantics: str


@dataclass(frozen=True, slots=True)
class PairwiseRelationship:
    family_a: str
    family_b: str
    relationship: str
    basis: str


@dataclass(frozen=True, slots=True)
class IndependenceCorrelationPolicy:
    cluster_vote_cap: int
    numeric_dependence_decision_semantics: str
    numeric_dependence_threshold: str
    production_fusion_threshold_owner: str
    families: tuple[FamilyAuditRule, ...]
    explicit_pairwise_relationships: tuple[PairwiseRelationship, ...]
    direct_trade_output_allowed: bool

    @classmethod
    def from_path(cls, path: Path) -> "IndependenceCorrelationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise IndependenceCorrelationError(
                "unsupported P08-H policy schema_version"
            )
        if raw.get("unknown_family_behavior") != "FAIL_CLOSED":
            raise IndependenceCorrelationError(
                "unknown P08-H family behavior must fail closed"
            )
        if raw.get("unexpected_independence_group_behavior") != "FAIL_CLOSED":
            raise IndependenceCorrelationError(
                "unexpected independence group must fail closed"
            )
        if raw.get("numeric_dependence_decision_semantics") != "MEASURED_NOT_THRESHOLD_CLASSIFIED":
            raise IndependenceCorrelationError(
                "numeric dependence cannot create an uncalibrated verdict"
            )
        if raw.get("numeric_dependence_threshold") != "TO_BE_CALIBRATED_BY_GOVERNED_EMPIRICAL_EVIDENCE":
            raise IndependenceCorrelationError(
                "numeric dependence threshold must remain calibration-governed"
            )
        if raw.get("production_fusion_threshold_owner") != "P14":
            raise IndependenceCorrelationError(
                "production fusion threshold ownership must remain P14"
            )
        if raw.get("score_semantics") != "INDEPENDENCE_AUDIT_NOT_TRADE_PROBABILITY":
            raise IndependenceCorrelationError(
                "P08-H cannot claim trade-probability semantics"
            )

        vote_cap = _positive_int(raw.get("cluster_vote_cap"), field="cluster_vote_cap")
        if vote_cap != 1:
            raise IndependenceCorrelationError(
                "one correlation cluster may contribute at most one independent vote"
            )

        family_values = _object_list(raw.get("families"), field="families")
        families: list[FamilyAuditRule] = []
        seen_families: set[str] = set()
        for value in family_values:
            item = _mapping(value, field="family")
            family = _text(item.get("family"), field="family")
            if family in seen_families:
                raise IndependenceCorrelationError(
                    f"duplicate family audit rule: {family}"
                )
            seen_families.add(family)
            families.append(
                FamilyAuditRule(
                    family=family,
                    expected_independence_group=_text(
                        item.get("expected_independence_group"),
                        field="expected_independence_group",
                    ),
                    correlation_cluster=_text(
                        item.get("correlation_cluster"),
                        field="correlation_cluster",
                    ),
                    directional_vote_eligible=_boolean(
                        item.get("directional_vote_eligible"),
                        field="directional_vote_eligible",
                    ),
                    relationship_semantics=_text(
                        item.get("relationship_semantics"),
                        field="relationship_semantics",
                    ),
                )
            )
        if not families:
            raise IndependenceCorrelationError("P08-H family registry cannot be empty")

        relationship_values = _object_list(
            raw.get("explicit_pairwise_relationships"),
            field="explicit_pairwise_relationships",
        )
        relationships: list[PairwiseRelationship] = []
        seen_pairs: set[tuple[str, str]] = set()
        for value in relationship_values:
            item = _mapping(value, field="pairwise relationship")
            family_a = _text(item.get("family_a"), field="family_a")
            family_b = _text(item.get("family_b"), field="family_b")
            if family_a == family_b:
                raise IndependenceCorrelationError(
                    "explicit pairwise relationship requires two different families"
                )
            pair = _pair_key(family_a, family_b)
            if pair in seen_pairs:
                raise IndependenceCorrelationError(
                    f"duplicate pairwise relationship: {pair}"
                )
            if family_a not in seen_families or family_b not in seen_families:
                raise IndependenceCorrelationError(
                    "pairwise relationship references an unknown family"
                )
            seen_pairs.add(pair)
            relationship = _text(
                item.get("relationship"),
                field="relationship",
            )
            if relationship not in ("CLUSTERED_RELATED", "CONTEXT_RELATED"):
                raise IndependenceCorrelationError(
                    "explicit relationship must be CLUSTERED_RELATED or CONTEXT_RELATED"
                )
            relationships.append(
                PairwiseRelationship(
                    family_a=family_a,
                    family_b=family_b,
                    relationship=relationship,
                    basis=_text(item.get("basis"), field="basis"),
                )
            )

        direct_trade = _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        )
        if direct_trade:
            raise IndependenceCorrelationError(
                "P08-H forbids direct trade output"
            )

        return cls(
            cluster_vote_cap=vote_cap,
            numeric_dependence_decision_semantics=_text(
                raw.get("numeric_dependence_decision_semantics"),
                field="numeric_dependence_decision_semantics",
            ),
            numeric_dependence_threshold=_text(
                raw.get("numeric_dependence_threshold"),
                field="numeric_dependence_threshold",
            ),
            production_fusion_threshold_owner=_text(
                raw.get("production_fusion_threshold_owner"),
                field="production_fusion_threshold_owner",
            ),
            families=tuple(families),
            explicit_pairwise_relationships=tuple(relationships),
            direct_trade_output_allowed=direct_trade,
        )

    def family_rule(self, family: str) -> FamilyAuditRule:
        for rule in self.families:
            if rule.family == family:
                return rule
        raise IndependenceCorrelationError(
            f"unregistered P08-H family: {family}"
        )

    def relationship(self, family_a: str, family_b: str) -> PairwiseRelationship:
        rule_a = self.family_rule(family_a)
        rule_b = self.family_rule(family_b)
        if family_a == family_b:
            return PairwiseRelationship(
                family_a=family_a,
                family_b=family_b,
                relationship="CLUSTERED_RELATED",
                basis="SAME_FAMILY",
            )
        wanted = _pair_key(family_a, family_b)
        for relation in self.explicit_pairwise_relationships:
            current = _pair_key(relation.family_a, relation.family_b)
            if current == wanted:
                return relation
        if rule_a.correlation_cluster == rule_b.correlation_cluster:
            return PairwiseRelationship(
                family_a=family_a,
                family_b=family_b,
                relationship="CLUSTERED_RELATED",
                basis="SHARED_CORRELATION_CLUSTER",
            )
        if not rule_a.directional_vote_eligible or not rule_b.directional_vote_eligible:
            return PairwiseRelationship(
                family_a=family_a,
                family_b=family_b,
                relationship="CONTEXT_RELATED",
                basis="CONTEXT_ONLY_FAMILY_PRESENT",
            )
        return PairwiseRelationship(
            family_a=family_a,
            family_b=family_b,
            relationship="SEPARATE_CLUSTER_EMPIRICAL_MONITORING_REQUIRED",
            basis="NO_DIRECT_CONSTRUCTION_DEPENDENCY_REGISTERED",
        )


@dataclass(frozen=True, slots=True)
class ConfirmationAudit:
    direction: int
    supporting_families: tuple[str, ...]
    independent_clusters: tuple[str, ...]
    cluster_members: tuple[tuple[str, tuple[str, ...]], ...]
    independent_cluster_count: int
    raw_supporting_family_count: int
    collapsed_related_family_count: int
    status: str


@dataclass(frozen=True, slots=True)
class DependenceMeasurement:
    sample_count: int
    pearson_text: str | None
    spearman_text: str | None
    status: str
    decision_semantics: str


class IndependenceCorrelationAudit:
    def __init__(self, *, policy: IndependenceCorrelationPolicy) -> None:
        self._policy = policy

    def validate_evidence(self, evidence: TechnicalEvidence) -> FamilyAuditRule:
        rule = self._policy.family_rule(evidence.family)
        if evidence.independence_group != rule.expected_independence_group:
            raise IndependenceCorrelationError(
                "technical evidence independence_group does not match P08-H registry"
            )
        if not rule.directional_vote_eligible and evidence.direction != 0:
            raise IndependenceCorrelationError(
                "context-only family cannot emit a directional confirmation"
            )
        return rule

    def audit_confirmations(
        self,
        evidence: Sequence[TechnicalEvidence],
        *,
        direction: int,
    ) -> ConfirmationAudit:
        if direction not in (-1, 1):
            raise IndependenceCorrelationError(
                "confirmation audit direction must be -1 or 1"
            )
        members: dict[str, set[str]] = {}
        supporting_families: set[str] = set()
        for item in evidence:
            rule = self.validate_evidence(item)
            if not rule.directional_vote_eligible or item.direction != direction:
                continue
            supporting_families.add(item.family)
            members.setdefault(rule.correlation_cluster, set()).add(item.family)

        clusters = tuple(sorted(members))
        cluster_members = tuple(
            (cluster, tuple(sorted(members[cluster])))
            for cluster in clusters
        )
        families = tuple(sorted(supporting_families))
        collapsed = max(0, len(families) - len(clusters))
        return ConfirmationAudit(
            direction=direction,
            supporting_families=families,
            independent_clusters=clusters,
            cluster_members=cluster_members,
            independent_cluster_count=len(clusters),
            raw_supporting_family_count=len(families),
            collapsed_related_family_count=collapsed,
            status="CLUSTER_CAPPED_NO_NUMERIC_THRESHOLD",
        )


def _pearson(values_a: Sequence[Decimal], values_b: Sequence[Decimal]) -> Decimal | None:
    count = len(values_a)
    mean_a = sum(values_a, Decimal(0)) / Decimal(count)
    mean_b = sum(values_b, Decimal(0)) / Decimal(count)
    centered_a = tuple(value - mean_a for value in values_a)
    centered_b = tuple(value - mean_b for value in values_b)
    sum_sq_a = sum((value * value for value in centered_a), Decimal(0))
    sum_sq_b = sum((value * value for value in centered_b), Decimal(0))
    if sum_sq_a == 0 or sum_sq_b == 0:
        return None
    cross = sum(
        (left * right for left, right in zip(centered_a, centered_b, strict=True)),
        Decimal(0),
    )
    denominator = (sum_sq_a * sum_sq_b).sqrt()
    if denominator == 0:
        return None
    return cross / denominator


def _average_ranks(values: Sequence[Decimal]) -> tuple[Decimal, ...]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [Decimal(0)] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (Decimal(index + 1) + Decimal(end)) / Decimal(2)
        for position in range(index, end):
            original_index = ordered[position][0]
            ranks[original_index] = average_rank
        index = end
    return tuple(ranks)


def measure_pairwise_dependence(
    values_a: Sequence[object],
    values_b: Sequence[object],
) -> DependenceMeasurement:
    if len(values_a) != len(values_b):
        raise IndependenceCorrelationError(
            "dependence series must have equal length"
        )
    if len(values_a) < 2:
        raise IndependenceCorrelationError(
            "dependence measurement requires at least two observations"
        )
    left = tuple(
        _decimal(value, field="values_a")
        for value in values_a
    )
    right = tuple(
        _decimal(value, field="values_b")
        for value in values_b
    )
    pearson = _pearson(left, right)
    spearman = _pearson(_average_ranks(left), _average_ranks(right))
    status = (
        "UNDEFINED_ZERO_VARIANCE"
        if pearson is None or spearman is None
        else "MEASURED_NOT_THRESHOLD_CLASSIFIED"
    )
    return DependenceMeasurement(
        sample_count=len(left),
        pearson_text=None if pearson is None else _decimal_text(pearson),
        spearman_text=None if spearman is None else _decimal_text(spearman),
        status=status,
        decision_semantics="NUMERIC_DEPENDENCE_IS_EVIDENCE_NOT_AN_INDEPENDENCE_VERDICT",
    )
