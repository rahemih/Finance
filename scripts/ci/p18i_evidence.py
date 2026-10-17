#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from packages.learning.loop_operations import LearningLoopCoordinator, LearningLoopPolicy, LoopTick

STAGES=("OBSERVE_ANALYZE","DEMO_TRADE","OUTCOME","JOURNAL","DATASET","EXPERIMENT","RETRAIN_VALIDATE","CHALLENGER","PROMOTION_GOVERNANCE")

def build()->dict[str,object]:
    policy=LearningLoopPolicy(cadence_ns=1000,max_market_staleness_ns=100,max_consecutive_failures=3)
    stage_evidence=tuple((stage,chr(97+i)*64) for i,stage in enumerate(STAGES))
    complete=LearningLoopCoordinator(policy).evaluate(LoopTick(
        cycle_name="p18i-ci",tick_time_ns=10000,market_watermark_ns=9950,
        system_state="NORMAL",consecutive_failures=0,stage_evidence=stage_evidence,
    ))
    stale=LearningLoopCoordinator(policy).evaluate(LoopTick(
        cycle_name="p18i-stale",tick_time_ns=10000,market_watermark_ns=9800,
        system_state="NORMAL",consecutive_failures=0,stage_evidence=(),
    ))
    if complete.status!="CYCLE_COMPLETE_DEMO_ONLY" or stale.action!="WAIT_FOR_FRESH_DATA":
        raise RuntimeError("P18-I loop operational controls failed")
    if complete.automatic_live_promotion or complete.live_trading!="DISABLED":
        raise RuntimeError("P18-I authority boundary violated")
    return {
        "schema_version":"1.0","kind":"NEXUS_QUANT_P18I_LOOP_OPERATIONS_EVIDENCE",
        "task_id":"FIN-P18-WI-001","complete_checkpoint_id":complete.checkpoint_id,
        "complete_status":complete.status,"stale_checkpoint_id":stale.checkpoint_id,
        "stale_action":stale.action,"automated_controlled_retraining":complete.automated_controlled_retraining,
        "automatic_live_promotion":complete.automatic_live_promotion,
        "broker_exchange_routing":complete.broker_exchange_routing,
        "live_trading":complete.live_trading,"auto_trading":complete.auto_trading,
        "p19_started":False,
    }

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    payload=build();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"P18I_EVIDENCE=PASS output={a.output}");return 0
if __name__=="__main__":raise SystemExit(main())
