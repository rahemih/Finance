#!/usr/bin/env python3
"""Build deterministic P05-E streaming/heartbeat/backpressure evidence offline."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.market_data.databento import DatabentoGoldContextAdapter
from adapters.market_data.dxfeed import DxFeedForexQuoteAdapter, DxFeedForexSubscription
from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.market_data import (
    CanonicalNormalizer,
    CanonicalStreamBus,
    StreamingPolicy,
    SymbolMaster,
)


FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOLS = ROOT / "config/market-data/symbol-master.json"
STREAMING = ROOT / "config/market-data/streaming-policy.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonicalize(value: Any) -> Any:
    if isinstance(value, tuple):
        return [canonicalize(item) for item in value]
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): canonicalize(item)
            for key, item in sorted(value.items(), key=lambda x: str(x[0]))
        }
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return getattr(value, "value")
    return value


def build(output: Path) -> None:
    normalizer = CanonicalNormalizer(SymbolMaster.from_path(SYMBOLS))
    bus = CanonicalStreamBus(StreamingPolicy.from_path(STREAMING))

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

    normalized = [
        normalizer.normalize(kaiko),
        normalizer.normalize(dx),
        normalizer.normalize(gold),
    ]
    snapshots: list[dict[str, Any]] = []
    for item in normalized:
        bus.publish(item)
        snapshots.append(
            canonicalize(
                asdict(
                    bus.snapshot(
                        bus.key_for(item),
                        now_ns=item.clock.local_receive_time_ns,
                    )
                )
            )
        )

    dequeue_order: list[str] = []
    while True:
        item = bus.consume()
        if item is None:
            break
        dequeue_order.append(item.canonical_id)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05E_STREAMING_EVIDENCE",
        "streaming_policy_sha256": sha256(STREAMING),
        "accepted_canonical_ids": [item.canonical_id for item in normalized],
        "snapshots": snapshots,
        "dequeue_order": dequeue_order,
        "final_queue_depth": bus.queue_depth,
        "high_watermark_seen": bus.high_watermark_seen,
        "rejected_events": bus.rejected_events,
        "safety": {
            "network_required": False,
            "credentials_resolved": False,
            "silent_drop": False,
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P05E_EVIDENCE=PASS output={output}")
    print(f"P05E_EVENTS={len(normalized)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
