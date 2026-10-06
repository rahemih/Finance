#!/usr/bin/env python3
"""Build deterministic P05-D normalization evidence from offline canonical fixtures."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from adapters.market_data.databento import DatabentoGoldContextAdapter
from adapters.market_data.dxfeed import DxFeedForexQuoteAdapter, DxFeedForexSubscription
from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.market_data import CanonicalNormalizer, SymbolMaster


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOLS = ROOT / "config/market-data/symbol-master.json"
CLOCK = ROOT / "config/market-data/clock-model.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonicalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, tuple):
        return [canonicalize(item) for item in value]
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): canonicalize(item) for key, item in sorted(value.items(), key=lambda x: str(x[0]))}
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return getattr(value, "value")
    return value


def event_dict(event) -> dict[str, Any]:
    return canonicalize(asdict(event))


def build(output: Path) -> None:
    normalizer = CanonicalNormalizer(SymbolMaster.from_path(SYMBOLS))

    kaiko = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    ).parse_trade(
        load("kaiko_trade.json"),
        received_at_ns=1_759_651_200_223_656_789,
    )

    dx = DxFeedForexQuoteAdapter(
        DxFeedForexSubscription(
            symbol="EUR/USD",
            canonical_id="FX:EUR/USD:SPOT_OTC",
        )
    ).parse_quote(
        load("dxfeed_eurusd_quote.json"),
        received_at_ns=1_780_820_402_000_000_000,
    )

    gold = DatabentoGoldContextAdapter().parse_mbp1(
        load("databento_gc_mbp1.json"),
        mapped_symbol="GCZ6",
        received_at_ns=1_780_820_500_000_100_000,
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05D_NORMALIZATION_EVIDENCE",
        "symbol_master_sha256": sha256(SYMBOLS),
        "clock_model_sha256": sha256(CLOCK),
        "events": [
            event_dict(normalizer.normalize(kaiko)),
            event_dict(normalizer.normalize(dx)),
            event_dict(normalizer.normalize(gold)),
        ],
        "safety": {
            "network_required": False,
            "credentials_resolved": False,
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P05D_EVIDENCE=PASS output={output}")
    print(f"P05D_EVENTS={len(payload['events'])}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
