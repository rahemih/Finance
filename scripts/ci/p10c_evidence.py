from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy
from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent,EconomicEventPolicy
from packages.fundamental_intelligence.release_history import EconomicReleaseHistory,ReleaseHistoryPolicy
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy,OfficialSourceRegistry

ROOT=Path(__file__).resolve().parents[2]
RP=ROOT/"config/fundamental-intelligence/release-history-policy.json"; EP=ROOT/"config/fundamental-intelligence/economic-event-policy.json"
SP=ROOT/"config/fundamental-intelligence/official-source-policy.json"; SR=ROOT/"config/fundamental-intelligence/official-source-registry.json"
MP=ROOT/"config/historical-data/macro-vintage-policy.json"

def v(observation:int,release:int,observed:int,revision:int,value:str)->MacroVintage:
    digest=hashlib.sha256(f"{observation}:{release}:{observed}:{revision}:{value}".encode()).hexdigest()
    return MacroVintage("MACRO:CPI:US",observation,release,observed,revision,value,"INDEX","BLS","d"*64,digest,f"bls/{digest}.raw",f"rev-{revision}")

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); args=p.parse_args()
    rp=ReleaseHistoryPolicy.from_path(RP); ep=EconomicEventPolicy.from_path(EP)
    sp=OfficialSourcePolicy.from_path(SP); sr=OfficialSourceRegistry.from_path(SR,policy=sp); mp=MacroVintagePolicy.from_path(MP)
    event=EconomicCalendarEvent("BLS","CPI-2026-09","Consumer Price Index","INFLATION","US","2026-09",100,"America/New_York","RELEASED",105,"e"*64,"f"*64,100)
    vintages=(v(10,10,15,0,"98.0"),v(10,90,95,1,"99.0"),v(10,120,125,2,"99.5"),v(20,100,110,0,"100.0"),v(20,200,205,1,"100.4"))
    h=EconomicReleaseHistory(event=event,vintages=vintages,current_observation_time_ns=20,policy=rp,event_policy=ep,source_registry=sr,macro_policy=mp)
    previous=h.previous_at_first_release
    payload={
      "schema_version":"1.0","kind":"NEXUS_QUANT_P10C_RELEASE_HISTORY_EVIDENCE","task_id":"FIN-P10-WC-001",
      "history_id":h.history_id,"first_release_vintage_id":h.first_release.vintage_id,
      "previous_at_first_release_vintage_id":previous.vintage_id if previous is not None else None,
      "previous_at_first_release_value":previous.value_text if previous is not None else None,
      "revision_numbers_as_of_150":[x.revision_number for x in h.revision_history_as_of(decision_time_ns=150)],
      "revision_numbers_as_of_205":[x.revision_number for x in h.revision_history_as_of(decision_time_ns=205)],
      "snapshot_150":h.snapshot_as_of(decision_time_ns=150).payload(),
      "late_previous_revision_value":h.previous_at(decision_time_ns=130).value_text if h.previous_at(decision_time_ns=130) is not None else None,
      "production_revision_provider":rp.production_revision_provider,"forecast_in_scope":rp.forecast_values_in_scope,
      "surprise_in_scope":rp.surprise_in_scope,"network_required":rp.network_required,
      "country_assumption":"NONE","live_trading":rp.live_trading,"auto_trading":rp.auto_trading,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P10C_EVIDENCE=PASS output={args.output}"); return 0
if __name__=="__main__": raise SystemExit(main())
