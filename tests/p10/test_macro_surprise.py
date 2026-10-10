from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent, EconomicEventPolicy
from packages.fundamental_intelligence.macro_surprise import (
    ConsensusSnapshot,
    MacroSurpriseError,
    MacroSurprisePolicy,
    assert_no_surprise_trade_probability_fields,
    compute_macro_surprise,
    validate_consensus_snapshot,
)
from packages.fundamental_intelligence.release_history import EconomicReleaseHistory, ReleaseHistoryPolicy
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy, OfficialSourceRegistry
from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy

ROOT=Path(__file__).resolve().parents[2]
DP=ROOT/"config/fundamental-intelligence/macro-surprise-policy.json"
RP=ROOT/"config/fundamental-intelligence/release-history-policy.json"
EP=ROOT/"config/fundamental-intelligence/economic-event-policy.json"
SP=ROOT/"config/fundamental-intelligence/official-source-policy.json"
SR=ROOT/"config/fundamental-intelligence/official-source-registry.json"
MP=ROOT/"config/historical-data/macro-vintage-policy.json"
DATASET="d"*64

def macro(*,observation:int,release:int,observed:int,revision:int,value:str)->MacroVintage:
    digest=hashlib.sha256(f"{observation}:{release}:{observed}:{revision}:{value}".encode()).hexdigest()
    return MacroVintage(
        series_id="MACRO:CPI:US",observation_time_ns=observation,release_time_ns=release,
        observed_at_ns=observed,revision_number=revision,value_text=value,unit="INDEX",source="BLS",
        source_dataset_version=DATASET,source_payload_sha256=digest,
        source_object_relative_path=f"bls/macro/{digest}.raw",source_revision_id=f"rev-{revision}",
    )

def history()->EconomicReleaseHistory:
    rp=ReleaseHistoryPolicy.from_path(RP); ep=EconomicEventPolicy.from_path(EP)
    sp=OfficialSourcePolicy.from_path(SP); sr=OfficialSourceRegistry.from_path(SR,policy=sp)
    mp=MacroVintagePolicy.from_path(MP)
    event=EconomicCalendarEvent(
        source_id="BLS",source_event_id="CPI-2026-09",event_name="Consumer Price Index",event_kind="INFLATION",
        jurisdiction="US",reference_period="2026-09",scheduled_release_time_ns=100,
        release_timezone="America/New_York",status="RELEASED",observed_at_ns=105,
        source_dataset_version="e"*64,quality_evidence_sha256="f"*64,actual_release_time_ns=100,
    )
    vintages=(
        macro(observation=10,release=10,observed=15,revision=0,value="98.0"),
        macro(observation=10,release=90,observed=95,revision=1,value="99.0"),
        macro(observation=20,release=100,observed=110,revision=0,value="100.0"),
        macro(observation=20,release=200,observed=205,revision=1,value="100.4"),
    )
    return EconomicReleaseHistory(
        event=event,vintages=vintages,current_observation_time_ns=20,
        policy=rp,event_policy=ep,source_registry=sr,macro_policy=mp,
    )

def policy()->MacroSurprisePolicy:
    return MacroSurprisePolicy.from_path(DP)

def consensus(**changes:object)->ConsensusSnapshot:
    values:dict[str,object]={
        "series_id":"MACRO:CPI:US","provider_id":"CONSENSUS:REFERENCE",
        "method":"CONSENSUS_MEDIAN","value_text":"99.8","unit":"INDEX",
        "observed_at_ns":99,"sample_size":12,
        "source_dataset_version":"a"*64,"source_payload_sha256":"b"*64,
    }
    values.update(changes)
    return ConsensusSnapshot(**values)  # type: ignore[arg-type]

class MacroSurpriseTests(unittest.TestCase):
    def test_first_release_actual_minus_consensus_is_deterministic(self)->None:
        h=history()
        result=compute_macro_surprise(history=h,consensus=consensus(),policy=policy())
        self.assertEqual(result.actual_value_text,"100")
        self.assertEqual(result.consensus_value_text,"99.8")
        self.assertEqual(result.surprise_value_text,"0.2")
        self.assertEqual(result.direction,"ABOVE_CONSENSUS")
        self.assertEqual(result.actual_vintage_id,h.first_release.vintage_id)
        self.assertEqual(result,compute_macro_surprise(history=h,consensus=consensus(),policy=policy()))

    def test_later_actual_revision_cannot_change_first_release_surprise(self)->None:
        h=history()
        revised=h.resolve_current_as_of(decision_time_ns=205)
        self.assertIsNotNone(revised)
        if revised is None:
            self.fail("later revision expected")
        self.assertEqual(revised.value_text,"100.4")
        result=compute_macro_surprise(history=h,consensus=consensus(),policy=policy())
        self.assertEqual(result.actual_value_text,"100")
        self.assertEqual(result.surprise_value_text,"0.2")

    def test_consensus_must_be_strictly_pre_release(self)->None:
        for observed in (100,101):
            with self.assertRaises(MacroSurpriseError):
                compute_macro_surprise(
                    history=history(),consensus=consensus(observed_at_ns=observed),policy=policy()
                )

    def test_series_unit_method_and_sample_guards_fail_closed(self)->None:
        for changed in (
            {"series_id":"MACRO:OTHER"},
            {"unit":"PERCENT"},
            {"method":"POINT_FORECAST"},
            {"sample_size":1},
        ):
            with self.assertRaises(MacroSurpriseError):
                compute_macro_surprise(history=history(),consensus=consensus(**changed),policy=policy())

    def test_non_finite_consensus_and_bad_hash_fail_closed(self)->None:
        for changed in (
            {"value_text":"NaN"},
            {"value_text":"Infinity"},
            {"source_dataset_version":"bad"},
            {"source_payload_sha256":"bad"},
        ):
            with self.assertRaises(MacroSurpriseError):
                validate_consensus_snapshot(consensus(**changed),policy=policy())

    def test_at_and_below_consensus_are_descriptive_not_market_direction(self)->None:
        at=compute_macro_surprise(history=history(),consensus=consensus(value_text="100.0"),policy=policy())
        below=compute_macro_surprise(history=history(),consensus=consensus(value_text="100.3"),policy=policy())
        self.assertEqual((at.surprise_value_text,at.direction),("0","AT_CONSENSUS"))
        self.assertEqual((below.surprise_value_text,below.direction),("-0.3","BELOW_CONSENSUS"))

    def test_consensus_and_result_identity_are_content_sensitive(self)->None:
        h=history()
        a=compute_macro_surprise(history=h,consensus=consensus(value_text="99.8"),policy=policy())
        b=compute_macro_surprise(history=h,consensus=consensus(value_text="99.7"),policy=policy())
        self.assertNotEqual(a.consensus_id,b.consensus_id)
        self.assertNotEqual(a.surprise_id,b.surprise_id)

    def test_previous_at_first_release_provenance_is_preserved(self)->None:
        h=history()
        previous=h.previous_at_first_release
        self.assertIsNotNone(previous)
        result=compute_macro_surprise(history=h,consensus=consensus(),policy=policy())
        self.assertEqual(
            result.previous_at_first_release_vintage_id,
            previous.vintage_id if previous is not None else None,
        )

    def test_no_probability_market_direction_trade_or_network_surface(self)->None:
        assert_no_surprise_trade_probability_fields()
        source=(ROOT/"packages/fundamental_intelligence/macro_surprise.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "import requests","from requests","import httpx","from httpx",
            "adapters.execution","packages.execution",
        ):
            self.assertNotIn(forbidden,source)

if __name__=="__main__":
    unittest.main()
