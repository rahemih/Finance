from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest

from packages.contracts.market_data import (
    MarketEventKind,
    ProviderTimestamp,
    QuotePayload,
    QuoteSizeSemantics,
    TradePayload,
    TradeSide,
)
from packages.data_quality import (
    SchemaValidationPolicy,
    SchemaValidator,
    ValidationOutcome,
)
from packages.historical_data import (
    FeatureDefinition,
    FeatureMaterializationPolicy,
    FeatureMaterializer,
    QualityEligibility,
    ReplayDatasetRef,
    ReplayFeatureRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
    ReplayVintageRef,
    TimeSeriesRecord,
)
from packages.market_data.normalization import (
    CanonicalClock,
    CanonicalMarketEvent,
    SourceEnvelopeKind,
)
from packages.market_data.symbol_master import InstrumentRole

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_POLICY = ROOT / "config/data-quality/schema-validation-policy.json"
REPLAY_POLICY = ROOT / "config/historical-data/replay-snapshot-policy.json"


def validator() -> SchemaValidator:
    return SchemaValidator(SchemaValidationPolicy.from_path(SCHEMA_POLICY))


def market_event() -> CanonicalMarketEvent:
    stamp = ProviderTimestamp(raw="100", epoch_ns=100)
    clock = CanonicalClock(
        provider_event_time=stamp,
        exchange_time=stamp,
        collection_time=None,
        provider_receive_time=None,
        local_receive_time_ns=110,
        auxiliary_source_times=(),
        event_to_local_delta_ns=10,
        provider_receive_to_local_delta_ns=None,
    )
    return CanonicalMarketEvent(
        canonical_id="CRYPTO:BTC/USD:SPOT",
        asset_class="CRYPTO",
        instrument_role=InstrumentRole.TRADABLE_RESEARCH_CANDIDATE,
        kind=MarketEventKind.TRADE,
        provider="reference-provider",
        provider_exchange="reference-exchange",
        provider_instrument_class="spot",
        provider_symbol="btc-usd",
        sequence_id="seq-1",
        source_envelope_kind=SourceEnvelopeKind.EVENT,
        clock=clock,
        payload=TradePayload(
            trade_id="trade-1",
            price=Decimal("100.5"),
            amount=Decimal("2.0"),
            side=TradeSide.BUY,
        ),
        provenance=(
            ("canonical_id", "CRYPTO:BTC/USD:SPOT"),
            ("provider", "reference-provider"),
            ("provider_exchange", "reference-exchange"),
            ("provider_instrument_class", "spot"),
            ("provider_symbol", "btc-usd"),
        ),
    )


def record(*, schema_version: str = "1.0", payload: str = '{"price":"100.5"}') -> TimeSeriesRecord:
    raw = b"raw"
    digest = hashlib.sha256(raw).hexdigest()
    return TimeSeriesRecord(
        record_id="record-1",
        canonical_id="CRYPTO:BTC/USD:SPOT",
        kind="TRADE",
        provider="reference-provider",
        event_time_ns=100,
        receive_time_ns=110,
        sequence_id="seq-1",
        canonical_schema_version=schema_version,
        canonical_payload_json=payload,
        source_payload_sha256=digest,
        source_object_relative_path=f"reference/2026/10/07/{digest}.raw",
        provenance=(("source", "test"),),
    )


def feature_materialization():
    definition = FeatureDefinition(
        feature_name="feature.reference",
        definition_version="1.0",
        output_type="DECIMAL",
        code_sha256="1" * 64,
        config_sha256="2" * 64,
        description="reference",
    )
    quality = QualityEligibility(
        status="ELIGIBLE",
        quality_policy_version="q-v1",
        evidence_sha256="3" * 64,
    )
    return FeatureMaterializer.materialize(
        definition=definition,
        entity_id="CRYPTO:BTC-USD",
        event_time_ns=100,
        as_of_time_ns=110,
        value_text="1.25",
        source_dataset_version="4" * 64,
        source_vintage_ids=("5" * 64,),
        source_cutoff_ns=105,
        quality=quality,
    )


def replay_snapshot() -> ReplaySnapshot:
    policy = ReplaySnapshotPolicy.from_path(REPLAY_POLICY)
    return ReplaySnapshot.build(
        replay_start_ns=0,
        replay_end_ns=500,
        snapshot_cutoff_ns=400,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("CRYPTO:BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                dataset_name="reference",
                dataset_version="6" * 64,
                schema_version="1.0",
                window_start_ns=0,
                window_end_ns=500,
                membership_root_sha256="7" * 64,
                rights_class="NON_DISPLAY_INTERNAL",
            ),
        ),
        feature_refs=(
            ReplayFeatureRef(
                definition_id="8" * 64,
                materialization_id="9" * 64,
                entity_id="CRYPTO:BTC-USD",
                event_time_ns=100,
                as_of_time_ns=110,
                quality_evidence_sha256="a" * 64,
            ),
        ),
        vintage_refs=(
            ReplayVintageRef(
                vintage_id="b" * 64,
                series_id="MACRO:CPI:REFERENCE",
                observation_time_ns=80,
                release_time_ns=90,
                observed_at_ns=95,
            ),
        ),
        quality_rule_versions=("q-v1",),
        config_sha256="c" * 64,
        code_artifact_sha256="d" * 64,
        rights_class="NON_DISPLAY_INTERNAL",
        stochastic_seed=7,
        stochastic_version="rng-v1",
        policy=policy,
    )


class SchemaValidationPolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = SchemaValidationPolicy.from_path(SCHEMA_POLICY)
        self.assertEqual(policy.production_data_quality_vendor, "NOT_SELECTED")
        self.assertIn("1.0", policy.supported_historical_schema_versions)


class MarketSchemaTests(unittest.TestCase):
    def test_valid_market_event_passes(self):
        report = validator().validate_market_event(market_event())
        self.assertTrue(report.is_valid)
        self.assertEqual(report.outcome, ValidationOutcome.VALID)
        self.assertEqual(report.issues, ())

    def test_kind_payload_mismatch_fails_critical(self):
        event = market_event()
        stamp = ProviderTimestamp(raw="101", epoch_ns=101)
        quote = QuotePayload(
            bid_time=stamp,
            ask_time=stamp,
            bid_exchange_code=None,
            ask_exchange_code=None,
            bid_price=Decimal("100"),
            ask_price=Decimal("101"),
            bid_size=None,
            ask_size=None,
            time_nano_part=0,
            size_semantics=QuoteSizeSemantics.PROVIDER_QUOTE_SIZE_NOT_GLOBAL_SPOT_FX_VOLUME,
        )
        report = validator().validate_market_event(replace(event, payload=quote))
        self.assertEqual(report.outcome, ValidationOutcome.INVALID_CRITICAL)
        self.assertIn("KIND_PAYLOAD_MISMATCH", {issue.code for issue in report.issues})

    def test_blank_id_and_provenance_mismatch_fail_critical(self):
        report = validator().validate_market_event(replace(market_event(), canonical_id=""))
        codes = {issue.code for issue in report.issues}
        self.assertEqual(report.outcome, ValidationOutcome.INVALID_CRITICAL)
        self.assertIn("REQUIRED_TEXT", codes)
        self.assertIn("PROVENANCE_MISMATCH", codes)

    def test_report_order_and_fingerprint_are_deterministic(self):
        event = replace(market_event(), canonical_id="", provider_symbol="")
        first = validator().validate_market_event(event)
        second = validator().validate_market_event(event)
        self.assertEqual(first.issues, second.issues)
        self.assertEqual(first.fingerprint, second.fingerprint)


class HistoricalSchemaTests(unittest.TestCase):
    def test_valid_record_passes(self):
        self.assertTrue(validator().validate_time_series_record(record()).is_valid)

    def test_invalid_json_fails_critical(self):
        report = validator().validate_time_series_record(record(payload="{bad"))
        self.assertIn("INVALID_JSON", {issue.code for issue in report.issues})

    def test_non_object_json_fails_critical(self):
        report = validator().validate_time_series_record(record(payload='["x"]'))
        self.assertIn("PAYLOAD_NOT_OBJECT", {issue.code for issue in report.issues})

    def test_unsupported_schema_version_fails_critical(self):
        report = validator().validate_time_series_record(record(schema_version="2.0"))
        self.assertIn("UNSUPPORTED_SCHEMA_VERSION", {issue.code for issue in report.issues})

    def test_tampered_digest_and_path_fail_critical(self):
        value = record()
        object.__setattr__(value, "source_payload_sha256", "bad")
        object.__setattr__(value, "source_object_relative_path", "../escape.raw")
        report = validator().validate_time_series_record(value)
        codes = {issue.code for issue in report.issues}
        self.assertIn("INVALID_SHA256", codes)
        self.assertIn("UNSAFE_SOURCE_PATH", codes)


class ArtifactSchemaTests(unittest.TestCase):
    def test_feature_round_trip_passes_and_tamper_fails(self):
        value = feature_materialization()
        v = validator()
        self.assertTrue(v.validate_feature_materialization(value).is_valid)
        payload = json.loads(value.to_bytes().decode("utf-8"))
        payload["value_text"] = "999"
        tampered = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        report = v.validate_feature_bytes(tampered)
        self.assertEqual(report.outcome, ValidationOutcome.INVALID_CRITICAL)
        self.assertIn("INTEGRITY_FAILURE", {issue.code for issue in report.issues})

    def test_replay_round_trip_passes_and_tamper_fails(self):
        value = replay_snapshot()
        replay_policy = ReplaySnapshotPolicy.from_path(REPLAY_POLICY)
        v = validator()
        self.assertTrue(v.validate_replay_snapshot(value, replay_policy).is_valid)
        payload = json.loads(value.to_bytes().decode("utf-8"))
        payload["clock_mode"] = "EVENT_TIME"
        tampered = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        report = v.validate_replay_bytes(tampered, replay_policy)
        self.assertEqual(report.outcome, ValidationOutcome.INVALID_CRITICAL)
        self.assertIn("INTEGRITY_FAILURE", {issue.code for issue in report.issues})


if __name__ == "__main__":
    unittest.main()
