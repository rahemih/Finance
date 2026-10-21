from __future__ import annotations
import argparse, json
from pathlib import Path
from packages.execution.reconciliation import InternalExecutionView, ReconciliationEngine, ReconciliationPolicy, ReferenceVenueObservation

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"config/execution/reconciliation-policy.json"

def view(state:str,filled:int=0,safe_hold:bool=False)->InternalExecutionView:
    return InternalExecutionView("CRYPTO","p20g-order","p20g-client",state,filled,100,100,"a"*64,"b"*64,"c"*64 if safe_hold else None,safe_hold)

def obs(status:str,filled:int=0,at:int=100)->ReferenceVenueObservation:
    return ReferenceVenueObservation("CRYPTO","p20g-order","p20g-client",status,filled,100,at,"REFERENCE_SANDBOX_FIXTURE","venue-p20g")

def build()->dict[str,object]:
    policy=ReconciliationPolicy.from_path(POLICY)
    matched_engine=ReconciliationEngine(policy); matched=matched_engine.reconcile(view("OPEN"),obs("OPEN"))
    ahead_engine=ReconciliationEngine(policy); ahead=ahead_engine.reconcile(view("SUBMIT_PENDING"),obs("OPEN"))
    hold_engine=ReconciliationEngine(policy); hold=hold_engine.reconcile(view("SUBMIT_PENDING",safe_hold=True),obs("NOT_FOUND"))
    fill_engine=ReconciliationEngine(policy); fill=fill_engine.reconcile(view("PARTIALLY_FILLED",20),obs("PARTIALLY_FILLED",30))
    return {
      "schema_version":"1.0","kind":"NEXUS_QUANT_P20G_RECONCILIATION_EVIDENCE","task_id":"FIN-P20-WG-001",
      "state":"IN_PROGRESS_REFERENCE_VALIDATED","policy_id":policy.policy_id,
      "matched":matched.payload()|{"report_id":matched.report_id},
      "venue_ahead":ahead.payload()|{"report_id":ahead.report_id},
      "unresolved_ambiguity":hold.payload()|{"report_id":hold.report_id},
      "fill_mismatch":fill.payload()|{"report_id":fill.report_id},
      "snapshot":matched_engine.snapshot(),
      "authority":{"source_mode":"EXPLICIT_REFERENCE_SANDBOX_OBSERVATION_ONLY","real_venue_query":False,
                   "automatic_oms_mutation":False,"external_order_mutation":False,"network_mode":"DISABLED",
                   "live_execution_authority":False,"live_trading":"DISABLED","auto_trading":"DISABLED",
                   "g11_execution_validated":False,"p21_started":False}
    }

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(build(),indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P20G_EVIDENCE=PASS output={args.output}"); return 0
if __name__=="__main__": raise SystemExit(main())
