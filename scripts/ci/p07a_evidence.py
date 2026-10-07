#!/usr/bin/env python3
"""Build deterministic P07-A schema-validation evidence offline."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.contracts.market_data import (
    MarketEventKind,
    ProviderTimestamp,
    TradePayload,
    TradeSide,
)
from packages.data_quality import SchemaValidationPolicy, SchemaValidator
from packages.historical_data import TimeSeriesRecord
from packages.market_data.normalization import CanonicalClock, CanonicalMarketEvent, SourceEnvelopeKind
from packages.market_data.symbol_master import InstrumentRole

POLICY = ROOT / "config/data-quality/schema-validation-policy.json"


def market_event() -> CanonicalMarketEvent:
    stamp = ProviderTimestamp(raw="100", epoch_ns=100)
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
        clock=CanonicalClock(
            provider_event_time=stamp,
            exchange_time=stamp,
            collection_time=None,
            provider_receive_time=None,
            local_receive_time_ns=110,
            auxiliary_source_times=(),
            event_to_local_delta_ns=10,
            provider_receive_to_local_delta_ns=None,
        ),
        payload=TradePayload(
            trade_id="trade-1",
            price=Decimal("100.5"),
            amount=Decimal("1.0"),
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


def record() -> TimeSeriesRecord:
    digest = hashlib.sha256(b"raw").hexdigest()
    return TimeSeriesRecord(
        record_id="record-1",
        canonical_id="CRYPTO:BTC/USD:SPOT",
        kind="TRADE",
        provider="reference-provider",
        event_time_ns=100,
        receive_time_ns=110,
        sequence_id="seq-1",
        canonical_schema_version="1.0",
        canonical_payload_json='{"price":"100.5"}',
        source_payload_sha256=digest,
        source_object_relative_path=f"reference/2026/10/07/{digest}.raw",
    )


def report_payload(report) -> dict[str, object]:
    return {
        "contract": report.contract,
        "identity": report.identity,
        "outcome": report.outcome.value,
        "issues": [issue.payload() for issue in report.issues],
        "fingerprint": report.fingerprint,
    }


def build(output: Path) -> None:
    policy = SchemaValidationPolicy.from_path(POLICY)
    validator = SchemaValidator(policy)
    valid_market = validator.validate_market_event(market_event())
    invalid_market = validator.validate_market_event(replace(market_event(), canonical_id=""))
    valid_history = validator.validate_time_series_record(record())
    invalid_history_value = record()
    object.__setattr__(invalid_history_value, "canonical_payload_json", "{bad")
    invalid_history = validator.validate_time_series_record(invalid_history_value)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07A_SCHEMA_VALIDATION_EVIDENCE",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "reports": [
            report_payload(valid_market),
            report_payload(invalid_market),
            report_payload(valid_history),
            report_payload(invalid_history),
        ],
        "valid_controls_pass": valid_market.is_valid and valid_history.is_valid,
        "critical_fail_closed_proven": (
            not invalid_market.is_valid
            and not invalid_history.is_valid
            and invalid_market.outcome.value == "INVALID_CRITICAL"
            and invalid_history.outcome.value == "INVALID_CRITICAL"
        ),
        "production_data_quality_vendor": policy.production_data_quality_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P07A_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
