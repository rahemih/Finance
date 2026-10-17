from __future__ import annotations
import unittest
from packages.learning.champion_challenger import ComparisonPolicy, EvaluationRecord, ChampionChallengerError, compare

def rec(model:str,perf:str,risk:str,dataset:str="a"*64)->EvaluationRecord:
    return EvaluationRecord.create(model_id=model,dataset_id=dataset,lineage_id="d"*64,
        performance_metrics={"sharpe":perf,"accuracy":"0.60"},risk_metrics={"drawdown":risk,"ruin":"0.01"})

class TestChampionChallenger(unittest.TestCase):
    def test_recommend_challenger(self)->None:
        r=compare(champion=rec("b"*64,"1.00","0.10"),challenger=rec("c"*64,"1.05","0.10"),
            policy=ComparisonPolicy("sharpe","0.02","0"))
        self.assertEqual(r.recommendation,"CHALLENGER_RECOMMENDED"); self.assertTrue(r.risk_guard_pass)
    def test_insufficient_improvement_keeps_champion(self)->None:
        r=compare(champion=rec("b"*64,"1.00","0.10"),challenger=rec("c"*64,"1.01","0.10"),
            policy=ComparisonPolicy("sharpe","0.02","0"))
        self.assertEqual(r.recommendation,"KEEP_CHAMPION")
    def test_risk_degradation_blocks(self)->None:
        r=compare(champion=rec("b"*64,"1.00","0.10"),challenger=rec("c"*64,"1.20","0.11"),
            policy=ComparisonPolicy("sharpe","0.02","0"))
        self.assertEqual(r.recommendation,"KEEP_CHAMPION"); self.assertFalse(r.risk_guard_pass)
    def test_dataset_mismatch_fails(self)->None:
        with self.assertRaisesRegex(ChampionChallengerError,"same dataset"):
            compare(champion=rec("b"*64,"1","0.1","a"*64),challenger=rec("c"*64,"1.1","0.1","e"*64),
                policy=ComparisonPolicy("sharpe","0.02","0"))
    def test_authority_boundary(self)->None:
        r=compare(champion=rec("b"*64,"1","0.1"),challenger=rec("c"*64,"1.1","0.1"),
            policy=ComparisonPolicy("sharpe","0.02","0"))
        self.assertFalse(r.registry_mutation_authority);self.assertFalse(r.promotion_authority)
        self.assertFalse(r.automatic_live_promotion);self.assertEqual(r.live_trading,"DISABLED")
if __name__=="__main__":unittest.main()
