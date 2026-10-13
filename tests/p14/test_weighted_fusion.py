from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.evidence_contract import (
    EvidenceBundle,
    EvidenceContractPolicy,
    SignalEvidence,
)
from packages.signal_intelligence.weighted_fusion import (
    WeightedFusionError,
    WeightedFusionPolicy,
    fuse_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_POLICY_PATH = ROOT / "config/signal-intelligence/evidence-contract-policy.json"
FUSION_POLICY_PATH = ROOT / "config/signal-intelligence/weighted-evidence-fusion-policy.json"


def evidence(
    *,
    phase: str,
    source_family: str,
    family: str,
    group: str,
    direction: int,
    strength_bps: int,
    quality_bps: int,
    record_id: str,
    provenance_digit: str,
    valid_until_ns: int = 1200,
    hard_veto: bool = False,
    veto_codes: tuple[str, ...] = (),
) -> SignalEvidence:
    return SignalEvidence(
        source_phase=phase,
        source_family=source_family,
        evidence_family=family,
        independence_group=group,
        subject_id="BTC-USD",
        timeframe="1h",
        regime_label="TRENDING",
        direction=direction,
        strength_bps=strength_bps,
        quality_bps=quality_bps,
        sample_count=120,
        event_time_ns=900,
        as_of_time_ns=1000,
        valid_until_ns=valid_until_ns,
        source_record_id=record_id,
        provenance_sha256=provenance_digit * 64,
        invalidation="source invalidated",
        hard_veto=hard_veto,
        veto_codes=veto_codes,
    )


class WeightedFusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence_policy = EvidenceContractPolicy.from_path(EVIDENCE_POLICY_PATH)
        self.policy = WeightedFusionPolicy.from_path(FUSION_POLICY_PATH)

    def bundle(self, items: tuple[SignalEvidence, ...]) -> EvidenceBundle:
        return EvidenceBundle.build(
            policy=self.evidence_policy,
            subject_id="BTC-USD",
            as_of_time_ns=1000,
            evidence=items,
        )

    def canonical_three(self) -> tuple[SignalEvidence, ...]:
        return (
            evidence(
                phase="P08",
                source_family="TECHNICAL",
                family="TREND",
                group="TECH_TREND",
                direction=1,
                strength_bps=8000,
                quality_bps=9000,
                record_id="tech",
                provenance_digit="1",
            ),
            evidence(
                phase="P09",
                source_family="ORDER_FLOW_LIQUIDITY",
                family="CVD",
                group="FLOW_DELTA",
                direction=1,
                strength_bps=7000,
                quality_bps=8000,
                record_id="flow",
                provenance_digit="2",
            ),
            evidence(
                phase="P10",
                source_family="FUNDAMENTAL_MACRO",
                family="MACRO",
                group="MACRO_GROWTH",
                direction=-1,
                strength_bps=5000,
                quality_bps=8000,
                record_id="macro",
                provenance_digit="3",
            ),
        )

    def test_three_independent_groups_across_two_families_fuse(self) -> None:
        result = fuse_evidence(bundle=self.bundle(self.canonical_three()), policy=self.policy)
        self.assertEqual(result.state, "FUSED")
        self.assertEqual(result.direction, 1)
        self.assertEqual(result.signed_score_bps, 2933)
        self.assertEqual(len(result.representatives), 3)
        self.assertEqual(result.supporting_groups, ("FLOW_DELTA", "TECH_TREND"))
        self.assertEqual(result.opposing_groups, ("MACRO_GROWTH",))
        self.assertEqual(result.veto_codes, ())

    def test_same_independence_group_contributes_one_representative(self) -> None:
        base = self.canonical_three()
        weaker = evidence(
            phase="P08",
            source_family="TECHNICAL",
            family="MOMENTUM",
            group="TECH_TREND",
            direction=1,
            strength_bps=4000,
            quality_bps=5000,
            record_id="weaker-related",
            provenance_digit="4",
        )
        result = fuse_evidence(bundle=self.bundle(base + (weaker,)), policy=self.policy)
        self.assertEqual(result.state, "FUSED")
        selected = tuple(item.evidence_id for item in result.representatives if item.independence_group == "TECH_TREND")
        self.assertEqual(selected, (base[0].evidence_id,))
        self.assertEqual(result.excluded_correlated_evidence_ids, (weaker.evidence_id,))

    def test_representative_tie_breaks_by_evidence_id(self) -> None:
        left = evidence(
            phase="P08",
            source_family="TECHNICAL",
            family="A",
            group="TECH_SHARED",
            direction=1,
            strength_bps=6000,
            quality_bps=6000,
            record_id="left",
            provenance_digit="4",
        )
        right = evidence(
            phase="P08",
            source_family="TECHNICAL",
            family="B",
            group="TECH_SHARED",
            direction=-1,
            strength_bps=6000,
            quality_bps=6000,
            record_id="right",
            provenance_digit="5",
        )
        other = self.canonical_three()[1:]
        result = fuse_evidence(bundle=self.bundle((left, right) + other), policy=self.policy)
        selected = tuple(item.evidence_id for item in result.representatives if item.independence_group == "TECH_SHARED")
        self.assertEqual(selected, (min(left.evidence_id, right.evidence_id),))

    def test_expired_evidence_is_excluded_and_preserved(self) -> None:
        expired = evidence(
            phase="P11",
            source_family="NEWS_SENTIMENT",
            family="NEWS",
            group="NEWS_CONFIRMED",
            direction=1,
            strength_bps=9000,
            quality_bps=9000,
            record_id="expired",
            provenance_digit="4",
            valid_until_ns=950,
        )
        result = fuse_evidence(bundle=self.bundle(self.canonical_three() + (expired,)), policy=self.policy)
        self.assertEqual(result.state, "FUSED")
        self.assertEqual(result.excluded_expired_evidence_ids, (expired.evidence_id,))
        self.assertNotIn(expired.evidence_id, tuple(item.evidence_id for item in result.representatives))

    def test_hard_veto_is_non_bypassable(self) -> None:
        blocked = evidence(
            phase="P13",
            source_family="TIMING_OPPORTUNITY",
            family="NO_TRADE",
            group="TIMING_VETO",
            direction=0,
            strength_bps=0,
            quality_bps=10000,
            record_id="veto",
            provenance_digit="4",
            hard_veto=True,
            veto_codes=("P13_NO_TRADE",),
        )
        result = fuse_evidence(bundle=self.bundle(self.canonical_three() + (blocked,)), policy=self.policy)
        self.assertEqual(result.state, "BLOCKED")
        self.assertIsNone(result.signed_score_bps)
        self.assertEqual(result.direction, 0)
        self.assertEqual(result.veto_codes, ("P13_NO_TRADE",))
        self.assertEqual(result.representatives, ())

    def test_too_few_directional_groups_is_insufficient(self) -> None:
        result = fuse_evidence(bundle=self.bundle(self.canonical_three()[:2]), policy=self.policy)
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(result.signed_score_bps)

    def test_source_family_diversity_is_required(self) -> None:
        items = tuple(
            evidence(
                phase="P08",
                source_family="TECHNICAL",
                family=f"TECH-{index}",
                group=f"TECH-GROUP-{index}",
                direction=1,
                strength_bps=6000,
                quality_bps=7000,
                record_id=f"tech-{index}",
                provenance_digit=str(index + 1),
            )
            for index in range(3)
        )
        result = fuse_evidence(bundle=self.bundle(items), policy=self.policy)
        self.assertEqual(result.state, "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(result.signed_score_bps)

    def test_input_order_does_not_change_fusion_identity(self) -> None:
        items = self.canonical_three()
        left = fuse_evidence(bundle=self.bundle(items), policy=self.policy)
        right = fuse_evidence(bundle=self.bundle(tuple(reversed(items))), policy=self.policy)
        self.assertEqual(left.fusion_id, right.fusion_id)
        self.assertEqual(left.payload(), right.payload())

    def test_neutral_group_is_preserved_without_directional_vote(self) -> None:
        neutral = evidence(
            phase="P11",
            source_family="NEWS_SENTIMENT",
            family="NEWS",
            group="NEWS_CONTEXT",
            direction=0,
            strength_bps=8000,
            quality_bps=9000,
            record_id="neutral",
            provenance_digit="4",
        )
        result = fuse_evidence(bundle=self.bundle(self.canonical_three() + (neutral,)), policy=self.policy)
        self.assertEqual(result.state, "FUSED")
        self.assertEqual(result.neutral_groups, ("NEWS_CONTEXT",))
        self.assertEqual(result.signed_score_bps, 2200)

    def test_fusion_payload_is_explicitly_non_probabilistic(self) -> None:
        result = fuse_evidence(bundle=self.bundle(self.canonical_three()), policy=self.policy)
        self.assertIsNone(result.payload()["empirical_probability"])
        self.assertNotIn("confidence", result.payload())

    def test_policy_rejects_family_priors_llm_weighting_or_probability(self) -> None:
        original = FUSION_POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"family_prior_weights_enabled": false', '"family_prior_weights_enabled": true'),
            original.replace('"llm_weighting_authority": false', '"llm_weighting_authority": true'),
            original.replace('"empirical_probability_in_scope": false', '"empirical_probability_in_scope": true'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(WeightedFusionError):
                    WeightedFusionPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
