#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from packages.learning.retraining import ControlledRetrainer, ResourceBudget, RetrainingRequest, TrainerResult

class Trainer:
    def train(self, request: RetrainingRequest) -> TrainerResult:
        return TrainerResult.create(
            candidate_model_id="candidate-ci",artifact_sha256="e"*64,
            metrics={"sharpe":"1.25","accuracy":"0.60"},
            cpu_seconds=10,peak_memory_mb=512,output_bytes=50000,
        )

def build() -> dict[str,object]:
    request=RetrainingRequest.create(
        request_name="p18e-ci",dataset_id="a"*64,experiment_id="b"*64,
        experiment_run_id="c"*64,base_model_id="model-alpha",base_model_version="1.0.0",
        strategy_id="strategy-alpha",strategy_version="1.0.0",code_sha256="d"*64,
        seed=42,budget=ResourceBudget(100,2048,1000000),
        minimum_metrics={"sharpe":"1.0","accuracy":"0.5"},
    )
    candidate=ControlledRetrainer().run(request,Trainer())
    if candidate.validation_status!="PASS" or candidate.promotion_authority:
        raise RuntimeError("P18-E validation/authority boundary failed")
    return {
        "schema_version":"1.0","kind":"NEXUS_QUANT_P18E_RETRAINING_EVIDENCE",
        "task_id":"FIN-P18-WE-001","request_id":request.request_id,
        "candidate_record_id":candidate.candidate_record_id,
        "validation_status":candidate.validation_status,
        "candidate_only":candidate.candidate_only,
        "promotion_authority":candidate.promotion_authority,
        "automatic_live_promotion":candidate.automatic_live_promotion,
        "live_trading":candidate.live_trading,"auto_trading":candidate.auto_trading,
        "p18_f_started":False,"p19_started":False,
    }

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    payload=build();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"P18E_EVIDENCE=PASS output={a.output}");return 0
if __name__=="__main__":raise SystemExit(main())
