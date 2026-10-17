from __future__ import annotations
import unittest
from packages.learning.retraining import (
    ControlledRetrainer, ControlledRetrainingError, ResourceBudget,
    RetrainingRequest, TrainerResult,
)

def request(name: str="rt-1") -> RetrainingRequest:
    return RetrainingRequest.create(
        request_name=name,dataset_id="a"*64,experiment_id="b"*64,
        experiment_run_id="c"*64,base_model_id="model-alpha",
        base_model_version="1.0.0",strategy_id="strategy-alpha",
        strategy_version="1.0.0",code_sha256="d"*64,seed=42,
        budget=ResourceBudget(100,2048,1000000),
        minimum_metrics={"sharpe":"1.0","accuracy":"0.5"},
    )

class Trainer:
    def __init__(self, *, sharpe: str="1.25", cpu: int=10) -> None:
        self.sharpe=sharpe; self.cpu=cpu
    def train(self, req: RetrainingRequest) -> TrainerResult:
        self.last_seed=req.seed
        return TrainerResult.create(
            candidate_model_id="candidate-alpha",artifact_sha256="e"*64,
            metrics={"sharpe":self.sharpe,"accuracy":"0.6"},
            cpu_seconds=self.cpu,peak_memory_mb=512,output_bytes=50000,
        )

class TestControlledRetraining(unittest.TestCase):
    def test_deterministic_candidate_identity(self) -> None:
        a,b=ControlledRetrainer(),ControlledRetrainer()
        ca=a.run(request(),Trainer()); cb=b.run(request(),Trainer())
        self.assertEqual(ca.candidate_record_id,cb.candidate_record_id)
        self.assertEqual(ca.validation_status,"PASS")

    def test_seed_is_preserved(self) -> None:
        trainer=Trainer(); ControlledRetrainer().run(request(),trainer)
        self.assertEqual(trainer.last_seed,42)

    def test_resource_overrun_fails_closed(self) -> None:
        with self.assertRaisesRegex(ControlledRetrainingError,"CPU budget"):
            ControlledRetrainer().run(request(),Trainer(cpu=101))

    def test_validation_failure_is_candidate_only(self) -> None:
        candidate=ControlledRetrainer().run(request(),Trainer(sharpe="0.5"))
        self.assertEqual(candidate.validation_status,"FAIL")
        self.assertTrue(candidate.candidate_only)
        self.assertFalse(candidate.promotion_authority)

    def test_duplicate_request_fails_closed(self) -> None:
        r=ControlledRetrainer(); r.run(request(),Trainer())
        with self.assertRaisesRegex(ControlledRetrainingError,"duplicate"):
            r.run(request(),Trainer())

    def test_authority_boundary(self) -> None:
        c=ControlledRetrainer().run(request(),Trainer())
        self.assertTrue(c.candidate_only)
        self.assertFalse(c.promotion_authority)
        self.assertFalse(c.broker_exchange_routing)
        self.assertFalse(c.automatic_live_promotion)
        self.assertEqual(c.live_trading,"DISABLED")
        self.assertEqual(c.auto_trading,"DISABLED")

if __name__=="__main__": unittest.main()
