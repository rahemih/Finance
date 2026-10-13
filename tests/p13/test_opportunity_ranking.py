from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.opportunity_ranking import (
    OpportunityRankingError,
    OpportunityRankingPolicy,
    rank_opportunities,
)
from packages.timing_opportunity.opportunity_scanner import OpportunityCandidate


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/opportunity-ranking-policy.json"


class OpportunityRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = OpportunityRankingPolicy.from_path(POLICY_PATH)

    def candidate(
        self,
        *,
        candidate_id: str,
        timing_class: str = "PREFERRED",
        adjusted_edge_bps: int = 150,
        sample_count: int = 50,
        scanner_state: str = "ELIGIBLE_TIMING_CONTEXT",
        eligible: bool = True,
        asset_id: str = "BTC-USD",
    ) -> OpportunityCandidate:
        return OpportunityCandidate(
            candidate_id=candidate_id,
            window_id=f"window-{candidate_id[:6]}",
            asset_id=asset_id,
            strategy_id="trend-v1",
            timeframe="1h",
            regime_label="ALIGNED_BULLISH",
            session_labels=("EUROPE", "US"),
            sample_count=sample_count,
            adjusted_edge_bps=adjusted_edge_bps,
            timing_class=timing_class,
            scanner_state=scanner_state,
            eligible=eligible,
            provenance_sha256=("a" * 64,),
            source_dataset_versions=("p13c-v1",),
        )

    def test_preferred_outranks_standard(self) -> None:
        preferred = self.candidate(candidate_id="a" * 64, timing_class="PREFERRED", adjusted_edge_bps=100)
        standard = self.candidate(candidate_id="b" * 64, timing_class="STANDARD", adjusted_edge_bps=500)
        result = rank_opportunities((standard, preferred), policy=self.policy)
        self.assertEqual(result.ranked[0].candidate.candidate_id, preferred.candidate_id)
        self.assertEqual(result.ranked[1].candidate.candidate_id, standard.candidate_id)

    def test_adjusted_edge_and_sample_count_break_ties(self) -> None:
        higher_edge = self.candidate(candidate_id="a" * 64, adjusted_edge_bps=180, sample_count=30)
        lower_edge = self.candidate(candidate_id="b" * 64, adjusted_edge_bps=170, sample_count=100)
        result = rank_opportunities((lower_edge, higher_edge), policy=self.policy)
        self.assertEqual(result.ranked[0].candidate.candidate_id, higher_edge.candidate_id)

        sample_a = self.candidate(candidate_id="c" * 64, adjusted_edge_bps=180, sample_count=80)
        sample_b = self.candidate(candidate_id="d" * 64, adjusted_edge_bps=180, sample_count=40)
        result = rank_opportunities((sample_b, sample_a), policy=self.policy)
        self.assertEqual(result.ranked[0].candidate.candidate_id, sample_a.candidate_id)

    def test_candidate_id_is_final_tie_breaker_and_ranks_are_contiguous(self) -> None:
        first = self.candidate(candidate_id="a" * 64)
        second = self.candidate(candidate_id="b" * 64)
        result = rank_opportunities((second, first), policy=self.policy)
        self.assertEqual(tuple(item.rank_position for item in result.ranked), (1, 2))
        self.assertEqual(result.ranked[0].candidate.candidate_id, first.candidate_id)

    def test_non_eligible_candidates_are_excluded(self) -> None:
        eligible = self.candidate(candidate_id="a" * 64)
        observe = self.candidate(
            candidate_id="b" * 64,
            timing_class="WEAK",
            scanner_state="OBSERVE_ONLY",
            eligible=False,
        )
        result = rank_opportunities((observe, eligible), policy=self.policy)
        self.assertEqual(len(result.ranked), 1)
        self.assertEqual(result.excluded_candidate_ids, (observe.candidate_id,))

    def test_input_order_does_not_change_result(self) -> None:
        items = (
            self.candidate(candidate_id="c" * 64, adjusted_edge_bps=120),
            self.candidate(candidate_id="a" * 64, adjusted_edge_bps=160),
            self.candidate(candidate_id="b" * 64, adjusted_edge_bps=140),
        )
        self.assertEqual(
            rank_opportunities(items, policy=self.policy),
            rank_opportunities(tuple(reversed(items)), policy=self.policy),
        )

    def test_duplicate_candidate_id_fails_closed(self) -> None:
        item = self.candidate(candidate_id="a" * 64)
        with self.assertRaises(OpportunityRankingError):
            rank_opportunities((item, item), policy=self.policy)

    def test_eligibility_state_mismatch_fails_closed(self) -> None:
        item = self.candidate(candidate_id="a" * 64)
        with self.assertRaises(OpportunityRankingError):
            rank_opportunities((replace(item, eligible=False),), policy=self.policy)
        observe = self.candidate(
            candidate_id="b" * 64,
            timing_class="WEAK",
            scanner_state="OBSERVE_ONLY",
            eligible=False,
        )
        with self.assertRaises(OpportunityRankingError):
            rank_opportunities((replace(observe, eligible=True),), policy=self.policy)

    def test_policy_rejects_probability_no_trade_or_risk_scope(self) -> None:
        self.assertFalse(self.policy.ranking_is_probability)
        self.assertFalse(self.policy.hard_no_trade_authority)
        self.assertFalse(self.policy.signal_expiry_in_scope)
        self.assertFalse(self.policy.signal_probability_in_scope)
        self.assertFalse(self.policy.risk_approval_in_scope)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")
        raw = POLICY_PATH.read_text(encoding="utf-8").replace(
            '"ranking_is_probability": false',
            '"ranking_is_probability": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(OpportunityRankingError):
                OpportunityRankingPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
