from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy, MacroVintageError
from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent, EconomicEventPolicy
from packages.fundamental_intelligence.release_history import (
    EconomicReleaseHistory,
    ReleaseHistoryError,
    ReleaseHistoryPolicy,
    assert_no_release_history_forecast_surprise_trade_fields,
)
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy, OfficialSourceRegistry

ROOT=Path(__file__).resolve().parents[2]
RP=ROOT/"config/fundamental-intelligence/release-history-policy.json"
EP=ROOT/"config/fundamental-intelligence/economic-event-policy.json"
SP=ROOT/"config/fundamental-intelligence/official-source-policy.json"
SR=ROOT/"config/fundamental-intelligence/official-source-registry.json"
MP=ROOT/"config/historical-data/macro-vintage-policy.json"
DATASET="d"*64

def macro(*,observation:int,release:int,observed:int,revision:int,value:str,source:str="BLS")->MacroVintage:
    digest=hashlib.sha256(f"{observation}:{release}:{observed}:{revision}:{value}".encode()).hexdigest()
    return MacroVintage(
        series_id="MACRO:CPI:US",observation_time_ns=observation,release_time_ns=release,
        observed_at_ns=observed,revision_number=revision,value_text=value,unit="INDEX",source=source,
        source_dataset_version=DATASET,source_payload_sha256=digest,
        source_object_relative_path=f"{source.lower()}/macro/{digest}.raw",source_revision_id=f"rev-{revision}",
    )

def event(*,status:str="RELEASED",actual:int|None=100)->EconomicCalendarEvent:
    return EconomicCalendarEvent(
        source_id="BLS",source_event_id="CPI-2026-09",event_name="Consumer Price Index",event_kind="INFLATION",
        jurisdiction="US",reference_period="2026-09",scheduled_release_time_ns=100,
        release_timezone="America/New_York",status=status,observed_at_ns=105,
        source_dataset_version="e"*64,quality_evidence_sha256="f"*64,actual_release_time_ns=actual,
    )

def policies()->tuple[ReleaseHistoryPolicy,EconomicEventPolicy,OfficialSourceRegistry,MacroVintagePolicy]:
    rp=ReleaseHistoryPolicy.from_path(RP); ep=EconomicEventPolicy.from_path(EP)
    sp=OfficialSourcePolicy.from_path(SP); sr=OfficialSourceRegistry.from_path(SR,policy=sp)
    mp=MacroVintagePolicy.from_path(MP); return rp,ep,sr,mp

def history(*,event_value:EconomicCalendarEvent|None=None,vintages:tuple[MacroVintage,...]|None=None,current_observation:int=20)->EconomicReleaseHistory:
    rp,ep,sr,mp=policies()
    default=(
        macro(observation=10,release=10,observed=15,revision=0,value="98.0"),
        macro(observation=10,release=90,observed=95,revision=1,value="99.0"),
        macro(observation=10,release=120,observed=125,revision=2,value="99.5"),
        macro(observation=20,release=100,observed=110,revision=0,value="100.0"),
        macro(observation=20,release=200,observed=205,revision=1,value="100.4"),
    )
    return EconomicReleaseHistory(
        event=event_value or event(),vintages=vintages or default,current_observation_time_ns=current_observation,
        policy=rp,event_policy=ep,source_registry=sr,macro_policy=mp,
    )

class ReleaseHistoryTests(unittest.TestCase):
    def test_first_release_and_as_of_revision_are_point_in_time(self)->None:
        h=history()
        self.assertEqual(h.first_release.value_text,"100.0")
        self.assertIsNone(h.resolve_current_as_of(decision_time_ns=99))
        self.assertEqual(h.resolve_current_as_of(decision_time_ns=150),h.first_release)
        self.assertEqual(h.resolve_current_as_of(decision_time_ns=205).value_text,"100.4")  # type: ignore[union-attr]

    def test_previous_at_first_release_does_not_leak_later_revision(self)->None:
        h=history()
        previous=h.previous_at_first_release
        self.assertIsNotNone(previous)
        self.assertEqual(previous.value_text,"99.0")  # type: ignore[union-attr]
        self.assertEqual(previous.revision_number,1)  # type: ignore[union-attr]
        later=h.previous_at(decision_time_ns=130)
        self.assertEqual(later.value_text,"99.5")  # type: ignore[union-attr]

    def test_revision_history_as_of_filters_future_revisions(self)->None:
        h=history()
        self.assertEqual(tuple(v.revision_number for v in h.revision_history_as_of(decision_time_ns=150)),(0,))
        self.assertEqual(tuple(v.revision_number for v in h.revision_history_as_of(decision_time_ns=205)),(0,1))
        self.assertEqual(tuple(v.revision_number for v in h.audit_full_revision_history()),(0,1))

    def test_snapshot_is_deterministic_and_history_order_independent(self)->None:
        h=history()
        reversed_h=history(vintages=tuple(reversed(h._vintages)))  # type: ignore[attr-defined]
        self.assertEqual(h.history_id,reversed_h.history_id)
        self.assertEqual(h.snapshot_as_of(decision_time_ns=150).payload(),reversed_h.snapshot_as_of(decision_time_ns=150).payload())

    def test_event_must_be_released_and_release_time_match_revision_zero(self)->None:
        with self.assertRaises((ReleaseHistoryError,ValueError)):
            history(event_value=event(status="SCHEDULED",actual=None))
        with self.assertRaises(ReleaseHistoryError):
            history(event_value=event(actual=101))

    def test_series_source_and_revision_guards_fail_closed(self)->None:
        wrong_source=(macro(observation=20,release=100,observed=110,revision=0,value="100.0",source="BEA"),)
        with self.assertRaises(ReleaseHistoryError):
            history(vintages=wrong_source)
        other=MacroVintage(
            series_id="MACRO:OTHER",observation_time_ns=10,release_time_ns=10,observed_at_ns=15,
            revision_number=0,value_text="1",unit="X",source="BLS",source_dataset_version=DATASET,
            source_payload_sha256="a"*64,source_object_relative_path="bls/other.raw",
        )
        with self.assertRaises(ReleaseHistoryError):
            history(vintages=(macro(observation=20,release=100,observed=110,revision=0,value="100"),other))
        with self.assertRaises(MacroVintageError):
            history(vintages=(
                macro(observation=20,release=100,observed=110,revision=0,value="100"),
                macro(observation=20,release=200,observed=205,revision=2,value="101"),
            ))

    def test_no_previous_observation_returns_none(self)->None:
        h=history(vintages=(macro(observation=20,release=100,observed=110,revision=0,value="100"),))
        self.assertIsNone(h.previous_at_first_release)

    def test_no_forecast_surprise_trade_or_network_surface(self)->None:
        assert_no_release_history_forecast_surprise_trade_fields()
        source=(ROOT/"packages/fundamental_intelligence/release_history.py").read_text(encoding="utf-8").lower()
        for forbidden in ("import requests","from requests","import httpx","from httpx","adapters.execution","packages.execution"):
            self.assertNotIn(forbidden,source)

if __name__=="__main__": unittest.main()
