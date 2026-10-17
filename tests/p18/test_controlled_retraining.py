from __future__ import annotations
import hashlib, unittest
from packages.learning.retraining import (
    ControlledRetrainingEngine, ControlledRetrainingError, RetrainingRequest, TrainerOutput
)

class Trainer:
    def checkpoint_sha256(self)->str: return "f"*64
    def train(self, request:RetrainingRequest)->TrainerOutput:
        candidate=hashlib.sha256(("candidate:"+request.request_id).encode()).hexdigest()
        return TrainerOutput.create(request_id=request.request_id,candidate_model_id=candidate,
            model_artifact_sha256="e"*64,metrics={"loss":"0.05","sharpe":"1.3"})

class BadTrainer(Trainer):
    def train(self, request:RetrainingRequest)->TrainerOutput:
        return TrainerOutput.create(request_id="d"*64,candidate_model_id="c"*64,
            model_artifact_sha256="e"*64,metrics={"loss":"0.05"})

def request()->RetrainingRequest:
    return RetrainingRequest.create(dataset_id="a"*64,experiment_id="b"*64,base_model_id="c"*64,
        code_sha256="d"*64,trainer_id="trainer-alpha",trainer_version="1.0.0",seed=42,
        parameters={"lr":"0.0100","epochs":"10"})

class TestControlledRetraining(unittest.TestCase):
    def test_deterministic_candidate_result(self)->None:
        a=ControlledRetrainingEngine(Trainer()).run(request())
        b=ControlledRetrainingEngine(Trainer()).run(request())
        self.assertEqual(a.result_id,b.result_id)
        self.assertEqual(a.candidate_model_id,b.candidate_model_id)

    def test_request_numeric_canonicalization(self)->None:
        a=request()
        b=RetrainingRequest.create(dataset_id="a"*64,experiment_id="b"*64,base_model_id="c"*64,
            code_sha256="d"*64,trainer_id="trainer-alpha",trainer_version="1.0.0",seed=42,
            parameters={"epochs":"10.0","lr":"0.01"})
        self.assertEqual(a.request_id,b.request_id)

    def test_lineage_mismatch_fails_closed(self)->None:
        with self.assertRaisesRegex(ControlledRetrainingError,"lineage mismatch"):
            ControlledRetrainingEngine(BadTrainer()).run(request())

    def test_duplicate_candidate_fails_closed(self)->None:
        engine=ControlledRetrainingEngine(Trainer()); engine.run(request())
        with self.assertRaisesRegex(ControlledRetrainingError,"duplicate candidate"):
            engine.run(request())

    def test_authority_boundary(self)->None:
        r=ControlledRetrainingEngine(Trainer()).run(request())
        self.assertTrue(r.candidate_only)
        self.assertFalse(r.champion_selection_authority)
        self.assertFalse(r.promotion_authority)
        self.assertFalse(r.automatic_live_promotion)
        self.assertFalse(r.broker_exchange_routing)
        self.assertEqual(r.live_trading,"DISABLED"); self.assertEqual(r.auto_trading,"DISABLED")

if __name__=="__main__": unittest.main()
