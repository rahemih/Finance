from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.evidence_contract import (
    EvidenceBundle,
    EvidenceContractError,
    EvidenceContractPolicy,
    SignalEvidence,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/evidence-contract-policy.json"
SHA_A = "a" * 64
SHA_B = "b" * 64


def record(
    *,
    phase: str = "P08",
    family: str = "TECHNICAL",
    evidence_family: str = "TREND",
    group: str = "TECH_TREND",
    direction: int = 1,
    event_time_ns: int = 900,
    as_of_time_ns: int = 1000,
    valid_until_ns: int = 1200,
    record_id: str = "record-1",
    provenance: str = SHA_A,
    hard_veto: bool = False,
    veto_codes: tuple[str, ...] = (),
) -> SignalEvidence:
    return SignalEvidence(
        source_phase=phase,
        source_family=family,
        evidence_family=evidence_family,
        independence_group=group,
        subject_id="BTC-USD",
        timeframe="1h",
        regime_label="TRENDING",
        direction=direction,
        strength_bps=6500,
        quality_bps=8000,
        sample_count=120,
        event_time_ns=event_time_ns,
        as_of_time_ns=as_of_time_ns,
        valid_until_ns=valid_until_ns,
        source_record_id=record_id,
        provenance_sha256=provenance,
        invalidation="source evidence invalidated or superseded",
        hard_veto=hard_veto,
        veto_codes=veto_codes,
    )


class EvidenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = EvidenceContractPolicy.from_path(POLICY_PATH)

    def test_accepts_canonical_p08_to_p13_source_families(self) -> None:
        pairs = (
            ("P08", "TECHNICAL"),
            ("P09", "ORDER_FLOW_LIQUIDITY"),
            ("P10", "FUNDAMENTAL_MACRO"),
            ("P11", "NEWS_SENTIMENT"),
            ("P12", "MARKET_MEMORY"),
            ("P13", "TIMING_OPPORTUNITY"),
        )
        evidence = tuple(
            record(
                phase=phase,
                family=family,
                evidence_family=f"{family}_EVIDENCE",
                group=f"GROUP_{phase}",
                record_id=f"record-{phase}",
                provenance=f"{index + 1:x}" * 64,
            )
            for index, (phase, family) in enumerate(pairs)
        )
        bundle = EvidenceBundle.build(
            policy=self.policy,
            subject_id="BTC-USD",
            as_of_time_ns=1000,
            evidence=evidence,
        )
        self.assertEqual(bundle.source_phases, ("P08", "P09", "P10", "P11", "P12", "P13"))
        self.assertEqual(len(bundle.evidence), 6)
        self.assertFalse(bundle.hard_veto)

    def test_unknown_source_phase_or_family_fails_closed(self) -> None:
        with self.assertRaises(EvidenceContractError):
            EvidenceBundle.build(
                policy=self.policy,
                subject_id="BTC-USD",
                as_of_time_ns=1000,
                evidence=(record(phase="P07"),),
            )
        with self.assertRaises(EvidenceContractError):
            EvidenceBundle.build(
                policy=self.policy,
                subject_id="BTC-USD",
                as_of_time_ns=1000,
                evidence=(record(family="UNKNOWN"),),
            )

    def test_event_time_after_as_of_fails_closed(self) -> None:
        with self.assertRaises(EvidenceContractError):
            record(event_time_ns=1001, as_of_time_ns=1000)

    def test_validity_deadline_before_event_time_fails_closed(self) -> None:
        with self.assertRaises(EvidenceContractError):
            record(event_time_ns=900, valid_until_ns=899)

    def test_strength_quality_and_sample_bounds_fail_closed(self) -> None:
        with self.assertRaises(EvidenceContractError):
            replace(record(), strength_bps=10001)
        with self.assertRaises(EvidenceContractError):
            replace(record(), quality_bps=10001)
        with self.assertRaises(EvidenceContractError):
            replace(record(), sample_count=0)

    def test_hard_veto_requires_reason_and_codes_require_veto(self) -> None:
        with self.assertRaises(EvidenceContractError):
            record(hard_veto=True)
        with self.assertRaises(EvidenceContractError):
            record(hard_veto=False, veto_codes=("P13_NO_TRADE",))
        blocked = record(
            phase="P13",
            family="TIMING_OPPORTUNITY",
            hard_veto=True,
            veto_codes=("P13_NO_TRADE", "STALE_EVIDENCE"),
        )
        self.assertTrue(blocked.hard_veto)
        self.assertEqual(blocked.veto_codes, ("P13_NO_TRADE", "STALE_EVIDENCE"))

    def test_expired_evidence_remains_explicit(self) -> None:
        expired = record(valid_until_ns=950)
        bundle = EvidenceBundle.build(
            policy=self.policy,
            subject_id="BTC-USD",
            as_of_time_ns=1000,
            evidence=(expired,),
        )
        self.assertEqual(expired.freshness_state, "EXPIRED")
        self.assertEqual(bundle.expired_evidence_ids, (expired.evidence_id,))

    def test_evidence_identity_is_deterministic_and_content_sensitive(self) -> None:
        first = record()
        second = record()
        changed = replace(record(), strength_bps=6499)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(first.evidence_id, changed.evidence_id)

    def test_bundle_identity_is_order_independent(self) -> None:
        first = record(record_id="a", provenance=SHA_A)
        second = record(
            phase="P09",
            family="ORDER_FLOW_LIQUIDITY",
            evidence_family="FLOW",
            group="FLOW_DELTA",
            record_id="b",
            provenance=SHA_B,
        )
        left = EvidenceBundle.build(
            policy=self.policy,
            subject_id="BTC-USD",
            as_of_time_ns=1000,
            evidence=(first, second),
        )
        right = EvidenceBundle.build(
            policy=self.policy,
            subject_id="BTC-USD",
            as_of_time_ns=1000,
            evidence=(second, first),
        )
        self.assertEqual(left.bundle_id, right.bundle_id)
        self.assertEqual(left.evidence, right.evidence)

    def test_duplicate_evidence_identity_fails_closed(self) -> None:
        item = record()
        with self.assertRaises(EvidenceContractError):
            EvidenceBundle.build(
                policy=self.policy,
                subject_id="BTC-USD",
                as_of_time_ns=1000,
                evidence=(item, item),
            )

    def test_subject_and_as_of_mismatch_fail_closed(self) -> None:
        with self.assertRaises(EvidenceContractError):
            EvidenceBundle.build(
                policy=self.policy,
                subject_id="ETH-USD",
                as_of_time_ns=1000,
                evidence=(record(),),
            )
        with self.assertRaises(EvidenceContractError):
            EvidenceBundle.build(
                policy=self.policy,
                subject_id="BTC-USD",
                as_of_time_ns=1001,
                evidence=(record(),),
            )

    def test_bundle_preserves_non_bypassable_veto_without_probability(self) -> None:
        blocked = record(
            phase="P13",
            family="TIMING_OPPORTUNITY",
            evidence_family="NO_TRADE",
            group="TIMING_VETO",
            direction=0,
            hard_veto=True,
            veto_codes=("P13_NO_TRADE",),
        )
        bundle = EvidenceBundle.build(
            policy=self.policy,
            subject_id="BTC-USD",
            as_of_time_ns=1000,
            evidence=(blocked,),
        )
        payload = bundle.payload()
        self.assertTrue(bundle.hard_veto)
        self.assertEqual(bundle.veto_codes, ("P13_NO_TRADE",))
        self.assertIsNone(payload["weighted_fusion"])
        self.assertIsNone(payload["empirical_probability"])

    def test_policy_rejects_fusion_or_probability_authority(self) -> None:
        original = POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"weighted_fusion_in_scope": false', '"weighted_fusion_in_scope": true'),
            original.replace('"empirical_probability_in_scope": false', '"empirical_probability_in_scope": true'),
            original.replace('"llm_probability_authority": false', '"llm_probability_authority": true'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(EvidenceContractError):
                    EvidenceContractPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
