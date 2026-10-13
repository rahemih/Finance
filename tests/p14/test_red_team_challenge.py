from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.persian_explainability import PersianExplainabilityPolicy, explain_signal_fa
from packages.signal_intelligence.probability_uncertainty import ProbabilityUncertaintyQualification
from packages.signal_intelligence.red_team_challenge import RedTeamChallengeError, RedTeamPolicy, challenge_signal
from packages.signal_intelligence.tp_stop_probability import TPStopOutcomeProbability
from packages.signal_intelligence.weighted_fusion import FusionRepresentative, WeightedFusionResult


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/signal-intelligence/red-team-challenge-policy.json"
EXPLAIN_POLICY = PersianExplainabilityPolicy.from_path(
    ROOT / "config/signal-intelligence/persian-explainability-policy.json"
)


def rep(group: str, family: str, direction: int, score: int, digit: str) -> FusionRepresentative:
    return FusionRepresentative(digit * 64, group, family, direction, score)


def fusion(
    *,
    state: str = "FUSED",
    opposing: tuple[str, ...] = (),
    expired: tuple[str, ...] = (),
    veto: tuple[str, ...] = (),
) -> WeightedFusionResult:
    if state == "FUSED":
        return WeightedFusionResult(
            subject_id="BTC-USD",
            as_of_time_ns=3000,
            state="FUSED",
            signed_score_bps=4200,
            direction=1,
            representatives=(
                rep("TECH_TREND", "TECHNICAL", 1, 7000, "1"),
                rep("FLOW_DELTA", "ORDER_FLOW_LIQUIDITY", 1, 6200, "2"),
            ),
            supporting_groups=("FLOW_DELTA", "TECH_TREND"),
            opposing_groups=opposing,
            neutral_groups=(),
            source_families=("ORDER_FLOW_LIQUIDITY", "TECHNICAL"),
            excluded_expired_evidence_ids=expired,
            excluded_correlated_evidence_ids=(),
            veto_codes=(),
        )
    return WeightedFusionResult(
        subject_id="BTC-USD",
        as_of_time_ns=3000,
        state=state,
        signed_score_bps=None,
        direction=0,
        representatives=(),
        supporting_groups=(),
        opposing_groups=(),
        neutral_groups=(),
        source_families=("TIMING_OPPORTUNITY",),
        excluded_expired_evidence_ids=(),
        excluded_correlated_evidence_ids=(),
        veto_codes=veto,
    )


def uncertainty(
    *,
    state: str = "QUALIFIED",
    support: str = "STRONG",
    probability: int | None = 7200,
    overall: int = 800,
) -> ProbabilityUncertaintyQualification:
    return ProbabilityUncertaintyQualification(
        prediction_id="b" * 64,
        empirical_probability_bps=probability,
        sample_count=120,
        success_count=86,
        state=state,
        sample_support=support,
        confidence_level_bps=9500,
        confidence_interval_lower_bps=6300 if probability is not None else None,
        confidence_interval_upper_bps=7950 if probability is not None else None,
        interval_half_width_bps=825 if probability is not None else None,
        regime_similarity_bps=8300,
        regime_dissimilarity_bps=1700,
        regime_uncertainty_bps=800,
        overall_uncertainty_bps=overall,
        dominant_uncertainty_sources=("REGIME_EVIDENCE_UNCERTAINTY",) if state == "QUALIFIED" else ("INSUFFICIENT_CALIBRATION_DATA",),
        regime_evidence_id="c" * 64,
    )


def outcomes(
    *,
    qualification_id: str,
    state: str = "CALIBRATED_TP_STOP",
    tp: int | None = 6500,
    stop: int | None = 2500,
    neither: int | None = 1000,
    general_probability: int | None = 7200,
    overall: int = 800,
) -> TPStopOutcomeProbability:
    return TPStopOutcomeProbability(
        model_id="d" * 64,
        upstream_qualification_id=qualification_id,
        as_of_time_ns=3000,
        state=state,
        tp_first_probability_bps=tp,
        stop_first_probability_bps=stop,
        neither_probability_bps=neither,
        sample_count=60,
        tp_first_count=39,
        stop_first_count=15,
        neither_count=6,
        general_empirical_probability_bps=general_probability,
        general_overall_uncertainty_bps=overall,
        outcome_definition_sha256="e" * 64,
    )


def explanation_for(
    f: WeightedFusionResult,
    q: ProbabilityUncertaintyQualification | None = None,
    o: TPStopOutcomeProbability | None = None,
):
    return explain_signal_fa(policy=EXPLAIN_POLICY, fusion=f, uncertainty=q, outcomes=o)


class RedTeamChallengeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = RedTeamPolicy.from_path(POLICY_PATH)

    def test_blocked_fusion_is_rejected(self) -> None:
        f = fusion(state="BLOCKED", veto=("P13_NO_TRADE",))
        e = explanation_for(f)
        result = challenge_signal(policy=self.policy, fusion=f, explanation=e)
        self.assertEqual(result.disposition, "REJECT")
        self.assertEqual(tuple(item.code for item in result.findings), ("UPSTREAM_BLOCKED",))
        self.assertIsNone(result.empirical_probability_bps)

    def test_insufficient_evidence_is_rejected(self) -> None:
        f = fusion(state="INSUFFICIENT_EVIDENCE")
        e = explanation_for(f)
        result = challenge_signal(policy=self.policy, fusion=f, explanation=e)
        self.assertEqual(result.disposition, "REJECT")
        self.assertEqual(result.findings[0].code, "INSUFFICIENT_EVIDENCE")

    def test_strong_coherent_state_can_be_clear(self) -> None:
        f = fusion()
        q = uncertainty()
        o = outcomes(qualification_id=q.qualification_id)
        e = explanation_for(f, q, o)
        result = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o)
        self.assertEqual(result.disposition, "CLEAR")
        self.assertEqual(result.findings, ())
        self.assertEqual(result.empirical_probability_bps, 7200)
        self.assertEqual(result.tp_first_probability_bps, 6500)

    def test_opposing_expired_and_moderate_support_raise_caution(self) -> None:
        f = fusion(opposing=("MACRO_GROWTH",), expired=("f" * 64,))
        q = uncertainty(support="MODERATE")
        o = outcomes(qualification_id=q.qualification_id)
        e = explanation_for(f, q, o)
        result = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o)
        self.assertEqual(result.disposition, "CAUTION")
        self.assertEqual(
            {item.code for item in result.findings},
            {"LIMITED_SAMPLE_SUPPORT", "OPPOSING_EVIDENCE", "EXPIRED_EVIDENCE_EXCLUDED"},
        )

    def test_tp_not_above_stop_raises_caution(self) -> None:
        f = fusion()
        q = uncertainty()
        o = outcomes(qualification_id=q.qualification_id, tp=3000, stop=6000, neither=1000)
        e = explanation_for(f, q, o)
        result = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o)
        self.assertEqual(result.disposition, "CAUTION")
        self.assertEqual(result.findings[0].code, "TP_NOT_ABOVE_STOP")

    def test_insufficient_calibration_is_rejected(self) -> None:
        f = fusion()
        q = uncertainty(state="INSUFFICIENT_CALIBRATION_DATA", support="INSUFFICIENT", probability=None, overall=10000)
        o = outcomes(
            qualification_id=q.qualification_id,
            state="INSUFFICIENT_UPSTREAM_CALIBRATION",
            tp=None,
            stop=None,
            neither=None,
            general_probability=None,
            overall=10000,
        )
        e = explanation_for(f, q, o)
        result = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o)
        self.assertEqual(result.disposition, "REJECT")
        self.assertIn("INSUFFICIENT_CALIBRATION", {item.code for item in result.findings})

    def test_explanation_fusion_lineage_mismatch_fails_closed(self) -> None:
        f = fusion()
        q = uncertainty()
        o = outcomes(qualification_id=q.qualification_id)
        e = explanation_for(f, q, o)
        changed = WeightedFusionResult(
            subject_id=f.subject_id,
            as_of_time_ns=f.as_of_time_ns,
            state=f.state,
            signed_score_bps=4300,
            direction=f.direction,
            representatives=f.representatives,
            supporting_groups=f.supporting_groups,
            opposing_groups=f.opposing_groups,
            neutral_groups=f.neutral_groups,
            source_families=f.source_families,
            excluded_expired_evidence_ids=f.excluded_expired_evidence_ids,
            excluded_correlated_evidence_ids=f.excluded_correlated_evidence_ids,
            veto_codes=f.veto_codes,
        )
        with self.assertRaises(RedTeamChallengeError):
            challenge_signal(policy=self.policy, fusion=changed, explanation=e, uncertainty=q, outcomes=o)

    def test_tp_stop_lineage_mismatch_fails_closed(self) -> None:
        f = fusion()
        q = uncertainty()
        o = outcomes(qualification_id=q.qualification_id)
        e = explanation_for(f, q, o)
        wrong = outcomes(qualification_id="a" * 64)
        with self.assertRaises(RedTeamChallengeError):
            challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=wrong)

    def test_challenge_identity_is_deterministic_and_content_sensitive(self) -> None:
        f = fusion()
        q = uncertainty()
        o = outcomes(qualification_id=q.qualification_id)
        e = explanation_for(f, q, o)
        first = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o)
        second = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o)
        self.assertEqual(first.challenge_id, second.challenge_id)

        f2 = fusion(opposing=("MACRO_GROWTH",))
        e2 = explanation_for(f2, q, o)
        changed = challenge_signal(policy=self.policy, fusion=f2, explanation=e2, uncertainty=q, outcomes=o)
        self.assertNotEqual(first.challenge_id, changed.challenge_id)

    def test_payload_preserves_values_and_has_no_final_action(self) -> None:
        f = fusion()
        q = uncertainty()
        o = outcomes(qualification_id=q.qualification_id)
        e = explanation_for(f, q, o)
        payload = challenge_signal(policy=self.policy, fusion=f, explanation=e, uncertainty=q, outcomes=o).payload()
        self.assertEqual(payload["empirical_probability_bps"], 7200)
        self.assertEqual(payload["overall_uncertainty_bps"], 800)
        self.assertFalse(payload["probability_mutated"])
        self.assertFalse(payload["uncertainty_mutated"])
        self.assertIsNone(payload["final_signal_action"])

    def test_policy_rejects_probability_mutation_or_final_action_scope(self) -> None:
        original = POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"probability_mutation_allowed": false', '"probability_mutation_allowed": true'),
            original.replace('"final_signal_action_in_scope": false', '"final_signal_action_in_scope": true'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(RedTeamChallengeError):
                    RedTeamPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
