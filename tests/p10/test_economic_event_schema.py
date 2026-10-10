from __future__ import annotations

from pathlib import Path
import unittest

from packages.fundamental_intelligence.economic_events import (
    EconomicCalendarEvent,
    EconomicEventError,
    EconomicEventPolicy,
    assert_no_event_value_or_trade_authority_fields,
    validate_economic_event,
)
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy, OfficialSourceRegistry

ROOT=Path(__file__).resolve().parents[2]
EVENT_POLICY=ROOT/"config/fundamental-intelligence/economic-event-policy.json"
SOURCE_POLICY=ROOT/"config/fundamental-intelligence/official-source-policy.json"
SOURCE_REGISTRY=ROOT/"config/fundamental-intelligence/official-source-registry.json"
DATASET="7"*64
QUALITY="8"*64

def event_policy()->EconomicEventPolicy: return EconomicEventPolicy.from_path(EVENT_POLICY)
def registry()->OfficialSourceRegistry:
    p=OfficialSourcePolicy.from_path(SOURCE_POLICY)
    return OfficialSourceRegistry.from_path(SOURCE_REGISTRY,policy=p)

def event(**changes: object)->EconomicCalendarEvent:
    values:dict[str,object]={
        "source_id":"BLS","source_event_id":"CPI-US-2026-09","event_name":"Consumer Price Index",
        "event_kind":"INFLATION","jurisdiction":"US","reference_period":"2026-09",
        "scheduled_release_time_ns":2_000,"release_timezone":"America/New_York","status":"SCHEDULED",
        "observed_at_ns":1_000,"source_dataset_version":DATASET,"quality_evidence_sha256":QUALITY,
        "actual_release_time_ns":None,"rescheduled_from_ns":None,"cancellation_reason":None,
    }
    values.update(changes)
    return EconomicCalendarEvent(**values)  # type: ignore[arg-type]

class EconomicEventTests(unittest.TestCase):
    def test_scheduled_future_event_is_valid_and_deterministic(self)->None:
        first=validate_economic_event(event(),policy=event_policy(),source_registry=registry())
        second=validate_economic_event(event(),policy=event_policy(),source_registry=registry())
        self.assertEqual(first.event_id,second.event_id)
        self.assertGreater(first.scheduled_release_time_ns,first.observed_at_ns)

    def test_released_requires_actual_not_after_observed(self)->None:
        valid=validate_economic_event(event(status="RELEASED",scheduled_release_time_ns=900,actual_release_time_ns=950,observed_at_ns=1_000),policy=event_policy(),source_registry=registry())
        self.assertEqual(valid.actual_release_time_ns,950)
        with self.assertRaises(EconomicEventError):
            validate_economic_event(event(status="RELEASED",actual_release_time_ns=1_100,observed_at_ns=1_000),policy=event_policy(),source_registry=registry())

    def test_rescheduled_requires_distinct_prior_schedule(self)->None:
        valid=validate_economic_event(event(status="RESCHEDULED",scheduled_release_time_ns=3_000,rescheduled_from_ns=2_000),policy=event_policy(),source_registry=registry())
        self.assertEqual(valid.rescheduled_from_ns,2_000)
        with self.assertRaises(EconomicEventError):
            validate_economic_event(event(status="RESCHEDULED",rescheduled_from_ns=2_000),policy=event_policy(),source_registry=registry())

    def test_cancelled_requires_reason(self)->None:
        with self.assertRaises(EconomicEventError):
            validate_economic_event(event(status="CANCELLED"),policy=event_policy(),source_registry=registry())
        valid=validate_economic_event(event(status="CANCELLED",cancellation_reason="Official cancellation"),policy=event_policy(),source_registry=registry())
        self.assertEqual(valid.cancellation_reason,"Official cancellation")

    def test_lifecycle_incompatible_fields_fail_closed(self)->None:
        with self.assertRaises(EconomicEventError):
            validate_economic_event(event(actual_release_time_ns=900),policy=event_policy(),source_registry=registry())
        with self.assertRaises(EconomicEventError):
            validate_economic_event(event(status="RELEASED",actual_release_time_ns=900,cancellation_reason="x"),policy=event_policy(),source_registry=registry())

    def test_unknown_source_timezone_kind_and_bad_hash_fail_closed(self)->None:
        for changed in (
            {"source_id":"UNKNOWN"},{"release_timezone":"Mars/Olympus"},{"event_kind":"TRADE_SIGNAL"},
            {"source_dataset_version":"bad"},{"quality_evidence_sha256":"bad"},
        ):
            with self.assertRaises((EconomicEventError,ValueError)):
                validate_economic_event(event(**changed),policy=event_policy(),source_registry=registry())

    def test_identity_is_content_sensitive(self)->None:
        first=validate_economic_event(event(),policy=event_policy(),source_registry=registry())
        second=validate_economic_event(event(scheduled_release_time_ns=2_100),policy=event_policy(),source_registry=registry())
        self.assertNotEqual(first.event_id,second.event_id)

    def test_no_value_surprise_trade_authority_or_network_imports(self)->None:
        assert_no_event_value_or_trade_authority_fields()
        source=(ROOT/"packages/fundamental_intelligence/economic_events.py").read_text(encoding="utf-8").lower()
        for forbidden in ("import requests","from requests","import httpx","from httpx","adapters.execution","packages.execution"):
            self.assertNotIn(forbidden,source)

if __name__=="__main__": unittest.main()
