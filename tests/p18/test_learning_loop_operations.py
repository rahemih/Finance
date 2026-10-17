from __future__ import annotations
import unittest
from packages.learning.loop_operations import (
    LearningLoopCoordinator, LearningLoopOperationsError, LearningLoopPolicy, LoopTick,
)

POLICY=LearningLoopPolicy(cadence_ns=1000,max_market_staleness_ns=100,max_consecutive_failures=3)
STAGES=("OBSERVE_ANALYZE","DEMO_TRADE","OUTCOME","JOURNAL","DATASET","EXPERIMENT","RETRAIN_VALIDATE","CHALLENGER","PROMOTION_GOVERNANCE")

def evidence(n: int) -> tuple[tuple[str,str],...]:
    hex_chars=("a","b","c","d","e","f","0","1","2")\n    return tuple((stage, hex_chars[i]*64) for i,stage in enumerate(STAGES[:n]))

def tick(*, n:int=0,time:int=1000,watermark:int=950,state:str="NORMAL",failures:int=0,prev:str|None=None,cycle:str="cycle-1")->LoopTick:
    return LoopTick(cycle_name=cycle,tick_time_ns=time,market_watermark_ns=watermark,system_state=state,consecutive_failures=failures,stage_evidence=evidence(n),previous_checkpoint_id=prev)

class TestLearningLoopOperations(unittest.TestCase):
    def test_initial_action_and_determinism(self)->None:
        a=LearningLoopCoordinator(POLICY).evaluate(tick())
        b=LearningLoopCoordinator(POLICY).evaluate(tick())
        self.assertEqual(a.action,"RUN_OBSERVE_ANALYZE")
        self.assertEqual(a.checkpoint_id,b.checkpoint_id)

    def test_checkpoint_progression_and_retraining_action(self)->None:
        c=LearningLoopCoordinator(POLICY)
        cp=c.evaluate(tick(n=5))
        cp2=c.evaluate(tick(n=6,time=1100,watermark=1050,prev=cp.checkpoint_id))
        self.assertEqual(cp2.action,"RUN_CONTROLLED_RETRAINING")
        self.assertTrue(cp2.automated_controlled_retraining)
        self.assertFalse(cp2.automatic_live_promotion)

    def test_skipped_stage_fails_closed(self)->None:
        with self.assertRaisesRegex(LearningLoopOperationsError,"ordered prefix"):
            LoopTick(cycle_name="x",tick_time_ns=1000,market_watermark_ns=950,system_state="NORMAL",consecutive_failures=0,stage_evidence=(("DEMO_TRADE","a"*64),))

    def test_stage_jump_fails_closed(self)->None:
        c=LearningLoopCoordinator(POLICY); cp=c.evaluate(tick(n=1))
        with self.assertRaisesRegex(LearningLoopOperationsError,"at most one"):
            c.evaluate(tick(n=3,time=1100,watermark=1050,prev=cp.checkpoint_id))

    def test_stale_data_waits(self)->None:
        cp=LearningLoopCoordinator(POLICY).evaluate(tick(time=1000,watermark=899))
        self.assertEqual(cp.action,"WAIT_FOR_FRESH_DATA")

    def test_failure_threshold_safe_holds(self)->None:
        cp=LearningLoopCoordinator(POLICY).evaluate(tick(failures=3))
        self.assertEqual(cp.action,"SAFE_HOLD")

    def test_halted_system_halts_safe(self)->None:
        cp=LearningLoopCoordinator(POLICY).evaluate(tick(state="HALTED"))
        self.assertEqual(cp.action,"HALT_SAFE")

    def test_complete_cycle_is_demo_only(self)->None:
        cp=LearningLoopCoordinator(POLICY).evaluate(tick(n=9))
        self.assertEqual(cp.status,"CYCLE_COMPLETE_DEMO_ONLY")
        self.assertFalse(cp.automatic_live_promotion)
        self.assertEqual(cp.live_trading,"DISABLED")
        self.assertEqual(cp.auto_trading,"DISABLED")

    def test_checkpoint_resume_chain_mismatch_fails(self)->None:
        c=LearningLoopCoordinator(POLICY); c.evaluate(tick())
        with self.assertRaisesRegex(LearningLoopOperationsError,"chain mismatch"):
            c.evaluate(tick(n=1,time=1100,watermark=1050,prev="f"*64))

if __name__=="__main__": unittest.main()
