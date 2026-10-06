#!/usr/bin/env python3
"""Build deterministic P05-F reconnect/failover/gap-recovery evidence offline."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.market_data.dxfeed import DxFeedForexQuoteAdapter, DxFeedForexSubscription
from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.market_data import (
    CanonicalNormalizer,
    RecoveryCoordinator,
    RecoveryPolicy,
    SymbolMaster,
)


FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOLS = ROOT / "config/market-data/symbol-master.json"
RECOVERY = ROOT / "config/market-data/recovery-policy.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


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
    coordinator = RecoveryCoordinator(RecoveryPolicy.from_path(RECOVERY))

    kaiko_raw = load("kaiko_trade.json")
    kaiko_raw["sequenceId"] = "a000001"
    kaiko = normalizer.normalize(
        KaikoAdapter(
            KaikoSubscription(
                exchange="cbse",
                instrument_class="spot",
                code="btc-usd",
                credential_ref="secret://market-data/kaiko/api-key",
            )
        ).parse_trade(kaiko_raw, received_at_ns=100)
    )
    kaiko_next_raw = load("kaiko_trade.json")
    kaiko_next_raw["sequenceId"] = "a000003"
    kaiko_next = normalizer.normalize(
        KaikoAdapter(
            KaikoSubscription(
                exchange="cbse",
                instrument_class="spot",
                code="btc-usd",
                credential_ref="secret://market-data/kaiko/api-key",
            )
        ).parse_trade(kaiko_next_raw, received_at_ns=101)
    )

    dx_raw = load("dxfeed_eurusd_quote.json")
    dx_raw["sequence"] = 10
    dx = normalizer.normalize(
        DxFeedForexQuoteAdapter(
            DxFeedForexSubscription(
                symbol="EUR/USD",
                canonical_id="FX:EUR/USD:SPOT_OTC",
            )
        ).parse_quote(dx_raw, received_at_ns=200)
    )
    dx_old_raw = load("dxfeed_eurusd_quote.json")
    dx_old_raw["sequence"] = 9
    dx_old = normalizer.normalize(
        DxFeedForexQuoteAdapter(
            DxFeedForexSubscription(
                symbol="EUR/USD",
                canonical_id="FX:EUR/USD:SPOT_OTC",
            )
        ).parse_quote(dx_old_raw, received_at_ns=201)
    )

    kaiko_first = coordinator.observe(kaiko)
    kaiko_advance = coordinator.observe(kaiko_next)
    dx_first = coordinator.observe(dx)
    dx_out_of_order = coordinator.observe(dx_old)

    dx_key = coordinator.key_for(dx)
    reconnect_1 = coordinator.schedule_reconnect(
        dx_key,
        now_ns=1_000,
        reason="STALE",
    )
    coordinator.begin_reconnect(
        dx_key,
        now_ns=reconnect_1.next_retry_at_ns or 0,
    )
    recovery_validation = coordinator.reconnect_succeeded(dx_key)

    dx_recovered_raw = load("dxfeed_eurusd_quote.json")
    dx_recovered_raw["sequence"] = 100
    dx_recovered = normalizer.normalize(
        DxFeedForexQuoteAdapter(
            DxFeedForexSubscription(
                symbol="EUR/USD",
                canonical_id="FX:EUR/USD:SPOT_OTC",
            )
        ).parse_quote(dx_recovered_raw, received_at_ns=300)
    )
    recovered_sequence = coordinator.validate_recovery_event(dx_recovered)

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05F_RECOVERY_EVIDENCE",
        "sequence_observations": [
            canonicalize(asdict(kaiko_first)),
            canonicalize(asdict(kaiko_advance)),
            canonicalize(asdict(dx_first)),
            canonicalize(asdict(dx_out_of_order)),
            canonicalize(asdict(recovered_sequence)),
        ],
        "reconnect": {
            "scheduled": canonicalize(asdict(reconnect_1)),
            "after_connect": canonicalize(asdict(recovery_validation)),
            "final": canonicalize(asdict(coordinator.snapshot(dx_key))),
        },
        "failover_disposition_with_healthy_backup": coordinator.failover_disposition(
            dx_key,
            backup_healthy=True,
        ).value,
        "safety": {
            "network_required": False,
            "credentials_resolved": False,
            "automatic_data_failover": False,
            "synthetic_contiguity": False,
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
    print(f"P05F_EVIDENCE=PASS output={output}")
    print(f"P05F_SEQUENCE_OBSERVATIONS={len(payload['sequence_observations'])}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
