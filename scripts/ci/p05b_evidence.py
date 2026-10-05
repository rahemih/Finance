#!/usr/bin/env python3
"""Build deterministic P05-B dxFeed Forex Quote evidence from an offline fixture."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.market_data.dxfeed import DxFeedForexQuoteAdapter, DxFeedForexSubscription


FIXTURE = ROOT / "tests/p05/fixtures/dxfeed_eurusd_quote.json"
RECEIVED_AT_NS = 1_780_820_401_999_000_222


def json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"unsupported evidence value: {type(value)!r}")


def build(output: Path) -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("dxFeed fixture must be an object")

    instance = DxFeedForexQuoteAdapter(
        DxFeedForexSubscription(
            symbol="EUR/USD",
            canonical_id="FX:EUR/USD:SPOT_OTC",
            credential_ref=None,
        )
    )
    event = instance.parse_quote(raw, received_at_ns=RECEIVED_AT_NS)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05B_DXFEED_FOREX_QUOTE_EVIDENCE",
        "provider": "dxfeed",
        "canonical_id": "FX:EUR/USD:SPOT_OTC",
        "provider_symbol": "EUR/USD",
        "network_used": False,
        "production_endpoint": "NOT_SELECTED",
        "entitlement": "NOT_PROVISIONED",
        "event": asdict(event),
        "subscription_spec": asdict(instance.subscription_spec()),
        "volume_policy": {
            "global_spot_fx_volume": "FORBIDDEN",
            "quote_size": "PROVIDER_QUOTE_SIZE_ONLY",
        },
        "safety": {
            "credential_value_present": False,
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=json_default,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"P05B_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
