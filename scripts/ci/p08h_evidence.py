from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping, cast

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.technical_intelligence.foundation import TechnicalEvidence
from packages.technical_intelligence.independence_correlation import (
    IndependenceCorrelationAudit,
    IndependenceCorrelationError,
    IndependenceCorrelationPolicy,
    measure_pairwise_dependence,
)

POLICY = ROOT / "config/technical-intelligence/independence-correlation-audit-policy.json"
DATASET = "a" * 64
QUALITY = "b" * 64
DEFINITION = "c" * 64

CANONICAL_POLICY_FILES = {
    "TREND": ROOT / "config/technical-intelligence/trend-family-policy.json",
    "MOMENTUM": ROOT / "config/technical-intelligence/momentum-family-policy.json",
    "MARKET_STRUCTURE_PRICE_ACTION": ROOT / "config/technical-intelligence/market-structure-price-action-policy.json",
    "VOLATILITY_MEAN_REVERSION": ROOT / "config/technical-intelligence/volatility-mean-reversion-policy.json",
    "BREAKOUT": ROOT / "config/technical-intelligence/breakout-expansion-policy.json",
    "REGIME": ROOT / "config/technical-intelligence/multi-timeframe-regime-policy.json",
}


def mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise IndependenceCorrelationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def load(path: Path) -> Mapping[str, object]:
    return mapping(
        json.loads(path.read_text(encoding="utf-8")),
        field=str(path.relative_to(ROOT)),
    )


def canonical_groups() -> dict[str, str]:
    trend = load(CANONICAL_POLICY_FILES["TREND"])
    momentum = load(CANONICAL_POLICY_FILES["MOMENTUM"])
    structure = load(CANONICAL_POLICY_FILES["MARKET_STRUCTURE_PRICE_ACTION"])
    volatility = load(CANONICAL_POLICY_FILES["VOLATILITY_MEAN_REVERSION"])
    breakout = load(CANONICAL_POLICY_FILES["BREAKOUT"])
    regime = load(CANONICAL_POLICY_FILES["REGIME"])
    return {
        "TREND": str(trend["independence_group"]),
        "MOMENTUM": str(momentum["independence_group"]),
        "MARKET_STRUCTURE": str(structure["structure_independence_group"]),
        "PRICE_ACTION": str(structure["price_action_independence_group"]),
        "VOLATILITY": str(volatility["volatility_independence_group"]),
        "MEAN_REVERSION": str(volatility["mean_reversion_independence_group"]),
        "BREAKOUT": str(breakout["independence_group"]),
        "REGIME": str(regime["independence_group"]),
    }


def evidence(
    family: str,
    *,
    direction: int,
    groups: Mapping[str, str],
) -> TechnicalEvidence:
    return TechnicalEvidence(
        definition_id=DEFINITION,
        family=family,
        independence_group=groups[family],
        symbol="CRYPTO:BTC-USD",
        timeframe="1h",
        direction=direction,
        strength_bps=5000 if direction != 0 else 0,
        confidence_bps=6000 if direction != 0 else 3000,
        event_time_ns=9000,
        as_of_time_ns=10_000,
        value_text=str(direction * 5000 if direction != 0 else 0),
        invalidation="P08-H evidence fixture",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = IndependenceCorrelationPolicy.from_path(POLICY)
    audit = IndependenceCorrelationAudit(policy=policy)
    actual_groups = canonical_groups()
    registered_groups = {
        rule.family: rule.expected_independence_group
        for rule in policy.families
    }
    if actual_groups != registered_groups:
        raise IndependenceCorrelationError(
            "P08-H registry drifted from canonical family policies"
        )

    bullish = (
        evidence("TREND", direction=1, groups=actual_groups),
        evidence("REGIME", direction=1, groups=actual_groups),
        evidence("MOMENTUM", direction=1, groups=actual_groups),
        evidence("MARKET_STRUCTURE", direction=1, groups=actual_groups),
        evidence("PRICE_ACTION", direction=1, groups=actual_groups),
        evidence("BREAKOUT", direction=1, groups=actual_groups),
        evidence("VOLATILITY", direction=0, groups=actual_groups),
        evidence("MEAN_REVERSION", direction=1, groups=actual_groups),
    )
    confirmation_audit = audit.audit_confirmations(
        bullish,
        direction=1,
    )

    relationships = {}
    pairs = (
        ("TREND", "REGIME"),
        ("MARKET_STRUCTURE", "PRICE_ACTION"),
        ("MARKET_STRUCTURE", "BREAKOUT"),
        ("PRICE_ACTION", "BREAKOUT"),
        ("VOLATILITY", "BREAKOUT"),
        ("TREND", "MOMENTUM"),
        ("TREND", "MEAN_REVERSION"),
    )
    for family_a, family_b in pairs:
        relationship = policy.relationship(family_a, family_b)
        relationships[f"{family_a}__{family_b}"] = {
            "relationship": relationship.relationship,
            "basis": relationship.basis,
        }

    positive = measure_pairwise_dependence(
        (1, 2, 3, 4, 5),
        (10, 20, 30, 40, 50),
    )
    negative = measure_pairwise_dependence(
        (1, 2, 3, 4, 5),
        (50, 40, 30, 20, 10),
    )
    zero_variance = measure_pairwise_dependence(
        (1, 1, 1, 1),
        (10, 20, 30, 40),
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08H_INDEPENDENCE_CORRELATION_AUDIT_EVIDENCE",
        "task_id": "FIN-P08-WH-001",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "canonical_family_policy_sha256": {
            key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in sorted(CANONICAL_POLICY_FILES.items())
        },
        "registered_groups_match_canonical_policies": True,
        "confirmation_audit": {
            "direction": confirmation_audit.direction,
            "supporting_families": list(
                confirmation_audit.supporting_families
            ),
            "independent_clusters": list(
                confirmation_audit.independent_clusters
            ),
            "cluster_members": [
                {
                    "cluster": cluster,
                    "families": list(families),
                }
                for cluster, families in confirmation_audit.cluster_members
            ],
            "raw_supporting_family_count": (
                confirmation_audit.raw_supporting_family_count
            ),
            "independent_cluster_count": (
                confirmation_audit.independent_cluster_count
            ),
            "collapsed_related_family_count": (
                confirmation_audit.collapsed_related_family_count
            ),
            "status": confirmation_audit.status,
        },
        "pairwise_relationships": relationships,
        "dependence_measurements": {
            "perfect_positive": {
                "sample_count": positive.sample_count,
                "pearson": positive.pearson_text,
                "spearman": positive.spearman_text,
                "status": positive.status,
                "decision_semantics": positive.decision_semantics,
            },
            "perfect_negative": {
                "sample_count": negative.sample_count,
                "pearson": negative.pearson_text,
                "spearman": negative.spearman_text,
                "status": negative.status,
                "decision_semantics": negative.decision_semantics,
            },
            "zero_variance": {
                "sample_count": zero_variance.sample_count,
                "pearson": zero_variance.pearson_text,
                "spearman": zero_variance.spearman_text,
                "status": zero_variance.status,
                "decision_semantics": zero_variance.decision_semantics,
            },
        },
        "numeric_dependence_threshold": (
            policy.numeric_dependence_threshold
        ),
        "production_fusion_threshold_owner": (
            policy.production_fusion_threshold_owner
        ),
        "score_semantics": "INDEPENDENCE_AUDIT_NOT_TRADE_PROBABILITY",
        "direct_trade_output_allowed": False,
        "country_assumption": "NONE",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "network_required": False,
        "credentials_required": False,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"P08H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
