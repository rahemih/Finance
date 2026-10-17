#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from packages.learning.experiments import ExperimentRegistry, ExperimentRun, ExperimentSpec

def build() -> dict[str, object]:
    registry=ExperimentRegistry()
    spec=ExperimentSpec.create(
        experiment_name="p18d-ci", hypothesis_id="hypothesis-ci",
        dataset_id="a"*64, code_sha256="b"*64,
        strategy_id="strategy-alpha", strategy_version="1.0.0",
        model_id="model-alpha", model_version="1.0.0",
        parameters={"lr":"0.01","depth":"4"},
    )
    eid=registry.register_experiment(spec)
    rid=registry.register_run(ExperimentRun.create(
        run_name="p18d-run", experiment_id=eid,
        started_at_ns=1000, completed_at_ns=2000,
        metrics={"sharpe":"1.25","loss":"0.05"},
        artifact_sha256="c"*64,
    ))
    snap=registry.snapshot()
    if any((snap.training_execution_authority,snap.retraining_authority,snap.promotion_authority,snap.broker_exchange_routing,snap.automatic_live_promotion)):
        raise RuntimeError("P18-D authority boundary violated")
    return {
        "schema_version":"1.0","kind":"NEXUS_QUANT_P18D_EXPERIMENT_EVIDENCE",
        "task_id":"FIN-P18-WD-001","experiment_id":eid,"run_id":rid,
        "snapshot_id":snap.snapshot_id,
        "training_execution_authority":False,"retraining_authority":False,
        "promotion_authority":False,"live_trading":"DISABLED","auto_trading":"DISABLED",
        "p18_e_started":False,"p19_started":False,
    }

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    payload=build(); a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"P18D_EVIDENCE=PASS output={a.output}"); return 0
if __name__=="__main__": raise SystemExit(main())
