from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent,EconomicEventPolicy
from packages.fundamental_intelligence.macro_surprise import ConsensusSnapshot,MacroSurprisePolicy,compute_macro_surprise
from packages.fundamental_intelligence.release_history import EconomicReleaseHistory,ReleaseHistoryPolicy
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy,OfficialSourceRegistry
from packages.historical_data.macro_vintage import MacroVintage,MacroVintagePolicy

ROOT=Path(__file__).resolve().parents[2]
DP=ROOT/"config/fundamental-intelligence/macro-surprise-policy.json"
RP=ROOT/"config/fundamental-intelligence/release-history-policy.json"
EP=ROOT/"config/fundamental-intelligence/economic-event-policy.json"
SP=ROOT/"config/fundamental-intelligence/official-source-policy.json"
SR=ROOT/"config/fundamental-intelligence/official-source-registry.json"
MP=ROOT/"config/historical-data/macro-vintage-policy.json"

def macro(observation:int,release:int,observed:int,revision:int,value:str)->MacroVintage:
    digest=hashlib.sha256(f"{observation}:{release}:{observed}:{revision}:{value}".encode()).hexdigest()
    return MacroVintage("MACRO:CPI:US",observation,release,observed,revision,value,"INDEX","BLS","d"*64,digest,f"bls/macro/{digest}.raw",f"rev-{revision}")

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    dp=MacroSurprisePolicy.from_path(DP); rp=ReleaseHistoryPolicy.from_path(RP); ep=EconomicEventPolicy.from_path(EP)
    sp=OfficialSourcePolicy.from_path(SP); sr=OfficialSourceRegistry.from_path(SR,policy=sp); mp=MacroVintagePolicy.from_path(MP)
    event=EconomicCalendarEvent("BLS","CPI-2026-09","Consumer Price Index","INFLATION","US","2026-09",100,"America/New_York","RELEASED",105,"e"*64,"f"*64,100)
    vintages=(
      macro(10,10,15,0,"98.0"),macro(10,90,95,1,"99.0"),
      macro(20,100,110,0,"100.0"),macro(20,200,205,1,"100.4"),
    )
    history=EconomicReleaseHistory(event=event,vintages=vintages,current_observation_time_ns=20,policy=rp,event_policy=ep,source_registry=sr,macro_policy=mp)
    consensus=ConsensusSnapshot("MACRO:CPI:US","CONSENSUS:REFERENCE","CONSENSUS_MEDIAN","99.8","INDEX",99,12,"a"*64,"b"*64)
    result=compute_macro_surprise(history=history,consensus=consensus,policy=dp)
    payload={
      "schema_version":"1.0","kind":"NEXUS_QUANT_P10D_MACRO_SURPRISE_EVIDENCE","task_id":"FIN-P10-WD-001",
      "policy_sha256":hashlib.sha256(DP.read_bytes()).hexdigest(),
      "history_id":history.history_id,"first_release_vintage_id":history.first_release.vintage_id,
      "consensus_id":consensus.consensus_id,"surprise":result.payload(),
      "later_revision_value":history.resolve_current_as_of(decision_time_ns=205).value_text if history.resolve_current_as_of(decision_time_ns=205) is not None else None,
      "actual_rule":dp.actual_rule,"consensus_time_rule":dp.consensus_time_rule,
      "market_direction_interpretation_allowed":dp.market_direction_interpretation_allowed,
      "production_consensus_provider":dp.production_consensus_provider,
      "country_assumption":"NONE","live_trading":dp.live_trading,"auto_trading":dp.auto_trading,"network_required":dp.network_required,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P10D_EVIDENCE=PASS output={args.output}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
