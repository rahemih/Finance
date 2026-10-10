from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent,EconomicEventPolicy,validate_economic_event
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy,OfficialSourceRegistry

ROOT=Path(__file__).resolve().parents[2]
EP=ROOT/"config/fundamental-intelligence/economic-event-policy.json"
SP=ROOT/"config/fundamental-intelligence/official-source-policy.json"
SR=ROOT/"config/fundamental-intelligence/official-source-registry.json"

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); args=p.parse_args()
    event_policy=EconomicEventPolicy.from_path(EP)
    source_policy=OfficialSourcePolicy.from_path(SP)
    registry=OfficialSourceRegistry.from_path(SR,policy=source_policy)
    samples=[
        EconomicCalendarEvent("BLS","CPI-US-2026-09","Consumer Price Index","INFLATION","US","2026-09",2_000,"America/New_York","SCHEDULED",1_000,"7"*64,"8"*64),
        EconomicCalendarEvent("ECB","ECB-2026-10","ECB monetary policy decision","CENTRAL_BANK_DECISION","EURO_AREA","2026-10",3_000,"Europe/Berlin","RELEASED",3_100,"9"*64,"a"*64,3_050),
        EconomicCalendarEvent("BEA","GDP-US-Q3-2026","Gross Domestic Product","GROWTH","US","2026-Q3",5_000,"America/New_York","RESCHEDULED",4_000,"b"*64,"c"*64,None,4_500),
    ]
    validated=[validate_economic_event(e,policy=event_policy,source_registry=registry) for e in samples]
    payload={
      "schema_version":"1.0","kind":"NEXUS_QUANT_P10B_ECONOMIC_EVENT_EVIDENCE","task_id":"FIN-P10-WB-001",
      "event_policy_sha256":hashlib.sha256(EP.read_bytes()).hexdigest(),"source_registry_id":registry.registry_id,
      "event_ids":[e.event_id for e in validated],"statuses":[e.status for e in validated],
      "numeric_release_values_allowed":event_policy.numeric_release_values_allowed,
      "forecast_values_allowed":event_policy.forecast_values_allowed,"previous_values_allowed":event_policy.previous_values_allowed,
      "production_calendar_provider":event_policy.production_calendar_provider,"country_assumption":"NONE",
      "live_trading":event_policy.live_trading,"auto_trading":event_policy.auto_trading,"network_required":False,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P10B_EVIDENCE=PASS output={args.output}"); return 0
if __name__=="__main__": raise SystemExit(main())
