#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path

from adapters.market_data.databento import DatabentoGoldContextAdapter


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/p05/fixtures/databento_gc_mbp1.json"
RECEIVED_AT_NS = 1_780_820_500_000_123_456


def normalize(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    event = DatabentoGoldContextAdapter().parse_mbp1(
        raw, mapped_symbol="GCZ6", received_at_ns=RECEIVED_AT_NS
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05C_DATABENTO_CONTEXT_EVIDENCE",
        "event": normalize(asdict(event)),
        "safety": {
            "context_only": True,
            "provider_network": "DISABLED",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P05C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
