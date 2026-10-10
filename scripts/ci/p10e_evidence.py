from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.fundamental_intelligence.rates_currency_macro import (
    RateYieldPoint, RatesCurrencyMacroPolicy, RatesMacroStore,
    assert_no_rates_currency_trade_authority_fields,
    compute_currency_macro_differential, compute_yield_curve_spread,
)
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy, OfficialSourceRegistry
from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy

ROOT=Path(__file__).resolve().parents[2]
PP=ROOT/"config/fundamental-intelligence/rates-currency-macro-policy.json"
SP=ROOT/"config/fundamental-intelligence/official-source-policy.json"
SR=ROOT/"config/fundamental-intelligence/official-source-registry.json"
MP=ROOT/"config/historical-data/macro-vintage-policy.json"
DATASET="d"*64

def macro(series:str,observation:int,release:int,observed:int,revision:int,value:str,source:str)->MacroVintage:
    digest=hashlib.sha256(f"{series}:{observation}:{release}:{observed}:{revision}:{value}:{source}".encode()).hexdigest()
    return MacroVintage(series,observation,release,observed,revision,value,"PERCENT",source,DATASET,digest,f"macro/{digest}.raw",f"rev-{revision}")

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    policy=RatesCurrencyMacroPolicy.from_path(PP)
    registry=OfficialSourceRegistry.from_path(SR,policy=OfficialSourcePolicy.from_path(SP))
    mp=MacroVintagePolicy.from_path(MP)
    points=(
        RateYieldPoint(macro("RATE:USD:POLICY",100,100,105,0,"5.0","FRED_ALFRED"),"POLICY_RATE","USD","US"),
        RateYieldPoint(macro("RATE:USD:POLICY",100,200,205,1,"5.25","FRED_ALFRED"),"POLICY_RATE","USD","US"),
        RateYieldPoint(macro("RATE:EUR:POLICY",100,100,106,0,"4.0","ECB"),"POLICY_RATE","EUR","EA"),
        RateYieldPoint(macro("YIELD:USD:24M",110,110,112,0,"4.2","FRED_ALFRED"),"GOVERNMENT_YIELD","USD","US",24),
        RateYieldPoint(macro("YIELD:USD:120M",111,111,113,0,"4.5","FRED_ALFRED"),"GOVERNMENT_YIELD","USD","US",120),
    )
    store=RatesMacroStore(points,policy=policy,source_registry=registry,macro_policy=mp)
    curve=compute_yield_curve_spread(store=store,short_series_id="YIELD:USD:24M",long_series_id="YIELD:USD:120M",decision_time_ns=150)
    diff=compute_currency_macro_differential(store=store,base_series_id="RATE:USD:POLICY",quote_series_id="RATE:EUR:POLICY",decision_time_ns=150)
    before=store.resolve_latest_as_of(series_id="RATE:USD:POLICY",decision_time_ns=150)
    after=store.resolve_latest_as_of(series_id="RATE:USD:POLICY",decision_time_ns=250)
    if before is None or after is None: raise RuntimeError("evidence fixture failed")
    assert_no_rates_currency_trade_authority_fields()
    payload={
        "schema_version":"1.0","kind":"NEXUS_QUANT_P10E_RATES_CURRENCY_MACRO_EVIDENCE","task_id":"FIN-P10-WE-001",
        "policy_sha256":hashlib.sha256(PP.read_bytes()).hexdigest(),"store_fingerprint":store.fingerprint,
        "yield_curve_spread":curve.payload(),"currency_macro_differential":diff.payload(),
        "pre_revision_us_policy_value":before.vintage.value_text,"post_revision_us_policy_value":after.vintage.value_text,
        "latest_as_of_rule":policy.latest_as_of_rule,"market_direction_interpretation_allowed":policy.market_direction_interpretation_allowed,
        "production_source_mapping":policy.production_source_mapping,"country_assumption":"NONE",
        "live_trading":policy.live_trading,"auto_trading":policy.auto_trading,"network_required":policy.network_required,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P10E_EVIDENCE=PASS output={args.output}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
