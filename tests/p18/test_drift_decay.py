from __future__ import annotations
import unittest
from packages.learning.drift_decay import DriftDecayError,DriftPolicy,MonitoringWindow,assess_drift
def win(start:int,end:int,perf:str="1.0",cal:str="0.05",drift:str="0.02",model:str="b"*64)->MonitoringWindow:
 return MonitoringWindow("a"*64,model,"c"*64,start,end,perf,cal,drift)
def policy()->DriftPolicy:return DriftPolicy("0.10","0.20","0.05","0.10","0.03","0.06")
class TestDriftDecay(unittest.TestCase):
 def test_normal(self)->None:self.assertEqual(assess_drift(baseline=win(0,100),current=win(100,200,"0.98","0.06","0.05"),policy=policy()).severity,"NORMAL")
 def test_warn(self)->None:self.assertEqual(assess_drift(baseline=win(0,100),current=win(100,200,"0.94","0.06","0.11"),policy=policy()).severity,"WARN")
 def test_decay_recommends_retrain(self)->None:
  r=assess_drift(baseline=win(0,100),current=win(100,200,"0.85","0.12","0.25"),policy=policy())
  self.assertEqual(r.severity,"DECAY");self.assertTrue(r.retrain_recommended);self.assertFalse(r.direct_retraining_authority);self.assertFalse(r.promotion_authority)
 def test_lineage_mismatch_fails(self)->None:
  with self.assertRaisesRegex(DriftDecayError,"lineage"):assess_drift(baseline=win(0,100),current=win(100,200,model="d"*64),policy=policy())
 def test_overlap_fails(self)->None:
  with self.assertRaisesRegex(DriftDecayError,"overlap"):assess_drift(baseline=win(0,100),current=win(99,200),policy=policy())
if __name__=="__main__":unittest.main()
