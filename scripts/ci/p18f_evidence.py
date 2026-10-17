#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from packages.learning.champion_challenger import ComparisonPolicy,EvaluationRecord,compare
def build()->dict[str,object]:
 c=EvaluationRecord.create(model_id="b"*64,dataset_id="a"*64,lineage_id="d"*64,performance_metrics={"sharpe":"1.0"},risk_metrics={"drawdown":"0.10"})
 h=EvaluationRecord.create(model_id="c"*64,dataset_id="a"*64,lineage_id="e"*64,performance_metrics={"sharpe":"1.05"},risk_metrics={"drawdown":"0.10"})
 r=compare(champion=c,challenger=h,policy=ComparisonPolicy("sharpe","0.02","0"))
 if r.recommendation!="CHALLENGER_RECOMMENDED" or r.promotion_authority:raise RuntimeError("P18-F comparison boundary failed")
 return {"schema_version":"1.0","kind":"NEXUS_QUANT_P18F_CHAMPION_CHALLENGER_EVIDENCE","task_id":"FIN-P18-WF-001","result_id":r.result_id,"recommendation":r.recommendation,"risk_guard_pass":r.risk_guard_pass,"registry_mutation_authority":False,"promotion_authority":False,"automatic_live_promotion":False,"live_trading":"DISABLED","auto_trading":"DISABLED","p18_g_started":False,"p19_started":False}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();payload=build();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n");print(f"P18F_EVIDENCE=PASS output={a.output}");return 0
if __name__=="__main__":raise SystemExit(main())
