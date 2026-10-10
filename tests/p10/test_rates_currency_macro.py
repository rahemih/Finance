from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.fundamental_intelligence.rates_currency_macro import (
    RateYieldPoint, RatesCurrencyMacroError, RatesCurrencyMacroPolicy, RatesMacroStore,
    assert_no_rates_currency_trade_authority_fields, compute_currency_macro_differential,
    compute_yield_curve_spread, validate_rate_yield_point,
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

def point(v:MacroVintage,kind:str,currency:str,jurisdiction:str,tenor:int|None=None)->RateYieldPoint:
    return RateYieldPoint(v,kind,currency,jurisdiction,tenor)

def policy()->RatesCurrencyMacroPolicy:
    return RatesCurrencyMacroPolicy.from_path(PP)

def registry()->OfficialSourceRegistry:
    return OfficialSourceRegistry.from_path(SR,policy=OfficialSourcePolicy.from_path(SP))

def mp()->MacroVintagePolicy:
    return MacroVintagePolicy.from_path(MP)

def store()->RatesMacroStore:
    points=(
        point(macro("RATE:USD:POLICY",100,100,105,0,"5.0","FRED_ALFRED"),"POLICY_RATE","USD","US"),
        point(macro("RATE:USD:POLICY",100,200,205,1,"5.25","FRED_ALFRED"),"POLICY_RATE","USD","US"),
        point(macro("RATE:EUR:POLICY",100,100,106,0,"4.0","ECB"),"POLICY_RATE","EUR","EA"),
        point(macro("YIELD:USD:24M",110,110,112,0,"4.2","FRED_ALFRED"),"GOVERNMENT_YIELD","USD","US",24),
        point(macro("YIELD:USD:120M",111,111,113,0,"4.5","FRED_ALFRED"),"GOVERNMENT_YIELD","USD","US",120),
    )
    return RatesMacroStore(points,policy=policy(),source_registry=registry(),macro_policy=mp())

class RatesCurrencyMacroTests(unittest.TestCase):
    def test_official_source_and_tenor_guards(self)->None:
        good=point(macro("RATE:USD:X",1,1,1,0,"5","FRED_ALFRED"),"POLICY_RATE","USD","US")
        self.assertEqual(validate_rate_yield_point(good,policy=policy(),source_registry=registry()),good)
        bad=point(macro("RATE:USD:BAD",1,1,1,0,"5","UNOFFICIAL"),"POLICY_RATE","USD","US")
        with self.assertRaises(RatesCurrencyMacroError):
            validate_rate_yield_point(bad,policy=policy(),source_registry=registry())
        with self.assertRaises(RatesCurrencyMacroError):
            validate_rate_yield_point(point(macro("YIELD:X",1,1,1,0,"4","ECB"),"GOVERNMENT_YIELD","EUR","EA"),policy=policy(),source_registry=registry())

    def test_latest_as_of_excludes_later_revision(self)->None:
        s=store()
        before=s.resolve_latest_as_of(series_id="RATE:USD:POLICY",decision_time_ns=150)
        after=s.resolve_latest_as_of(series_id="RATE:USD:POLICY",decision_time_ns=250)
        self.assertIsNotNone(before); self.assertIsNotNone(after)
        if before is None or after is None: self.fail("points expected")
        self.assertEqual(before.vintage.value_text,"5.0")
        self.assertEqual(after.vintage.value_text,"5.25")

    def test_curve_and_currency_differential(self)->None:
        s=store()
        curve=compute_yield_curve_spread(store=s,short_series_id="YIELD:USD:24M",long_series_id="YIELD:USD:120M",decision_time_ns=150)
        self.assertEqual(curve.spread_value_text,"0.3")
        diff=compute_currency_macro_differential(store=s,base_series_id="RATE:USD:POLICY",quote_series_id="RATE:EUR:POLICY",decision_time_ns=150)
        self.assertEqual(diff.differential_value_text,"1")
        self.assertEqual(diff.base_currency,"USD")
        self.assertEqual(diff.quote_currency,"EUR")

    def test_mismatch_and_metadata_drift_fail_closed(self)->None:
        v0=macro("RATE:SAME",1,1,1,0,"5","FRED_ALFRED")
        v1=macro("RATE:SAME",1,2,2,1,"5.1","FRED_ALFRED")
        with self.assertRaises(RatesCurrencyMacroError):
            RatesMacroStore((point(v0,"POLICY_RATE","USD","US"),point(v1,"POLICY_RATE","EUR","EA")),policy=policy(),source_registry=registry(),macro_policy=mp())
        s=store()
        with self.assertRaises(RatesCurrencyMacroError):
            compute_currency_macro_differential(store=s,base_series_id="RATE:USD:POLICY",quote_series_id="RATE:USD:POLICY",decision_time_ns=150)
        assert_no_rates_currency_trade_authority_fields()

if __name__=="__main__":
    unittest.main()
