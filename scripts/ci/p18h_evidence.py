#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from packages.learning.promotion import PromotionGovernor, PromotionRequest

def build()->dict[str,object]:
    base=dict(
        candidate_record_id="a"*64,comparison_record_id="b"*64,
        drift_report_id="c"*64,audit_bundle_sha256="d"*64,
        candidate_validation_passed=True,challenger_recommended=True,
        risk_review_passed=True,audit_complete=True,critical_blockers=0,
    )
    demo=PromotionGovernor().evaluate(PromotionRequest(request_name="demo-ci",target="DEMO_CHAMPION",**base))
    live=PromotionGovernor().evaluate(PromotionRequest(request_name="live-ci",target="LIVE",**base))
    if demo.status!="APPROVE_DEMO_CHAMPION_RECORD" or live.status!="OWNER_LIVE_GATE_REQUIRED":
        raise RuntimeError("P18-H promotion governance failed")
    if demo.registry_mutation or live.promotion_execution_authority or live.automatic_live_promotion:
        raise RuntimeError("P18-H authority boundary violated")
    return {
        "schema_version":"1.0","kind":"NEXUS_QUANT_P18H_PROMOTION_EVIDENCE",
        "task_id":"FIN-P18-WH-001","demo_decision_id":demo.decision_id,
        "live_decision_id":live.decision_id,"demo_status":demo.status,"live_status":live.status,
        "registry_mutation":False,"promotion_execution_authority":False,
        "automatic_live_promotion":False,"live_trading":"DISABLED","auto_trading":"DISABLED",
        "p18_i_started":False,"p19_started":False,
    }

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    payload=build();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"P18H_EVIDENCE=PASS output={a.output}");return 0
if __name__=="__main__":raise SystemExit(main())
