#!/usr/bin/env python3
"""Build deterministic P05-A Kaiko adapter evidence from offline fixtures."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path

from adapters.market_data.kaiko import (
    KaikoAdapter,
    KaikoLexicographicSequenceGuard,
    KaikoSubscription,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/p05/fixtures"
RECEIVED_AT_NS = 1_780_820_400_999_000_111


def load(name: str) -> dict[str, object]:
    value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture {name} must be an object")
    return value


def json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"unsupported evidence value: {type(value)!r}")


def build(output: Path) -> None:
    instance = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    )
    trade = instance.parse_trade(load("kaiko_trade.json"), received_at_ns=RECEIVED_AT_NS)
    snapshot = instance.parse_order_book(
        load("kaiko_orderbook_snapshot.json"),
        received_at_ns=RECEIVED_AT_NS,
    )
    update = instance.parse_order_book(
        load("kaiko_orderbook_update.json"),
        received_at_ns=RECEIVED_AT_NS,
    )

    guard = KaikoLexicographicSequenceGuard()
    sequence = [
        guard.observe("book", "b000001").value,
        guard.observe("book", "b000003").value,
        guard.observe("book", "b000003").value,
        guard.observe("book", "b000002").value,
    ]

    trade_request = instance.trade_request_spec()
    book_request = instance.order_book_request_spec()

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05A_KAIKO_ADAPTER_EVIDENCE",
        "provider": "kaiko",
        "instrument": {"exchange": "cbse", "class": "spot", "code": "btc-usd"},
        "live_connectivity": "DISABLED_ENTITLEMENT_REQUIRED",
        "network_used": False,
        "received_at_ns": RECEIVED_AT_NS,
        "events": {
            "trade": asdict(trade),
            "orderbook_snapshot": asdict(snapshot),
            "orderbook_update": asdict(update),
        },
        "sequence_dispositions": sequence,
        "request_specs": {
            "trade": asdict(trade_request),
            "orderbook": asdict(book_request),
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
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"P05A_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
