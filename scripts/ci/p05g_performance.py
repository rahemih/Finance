#!/usr/bin/env python3
"""Measure and enforce the offline P05-G engineering performance envelope."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import sys
from time import perf_counter_ns
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.market_data.databento import DatabentoGoldContextAdapter
from adapters.market_data.dxfeed import DxFeedForexQuoteAdapter, DxFeedForexSubscription
from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.market_data import CanonicalNormalizer, CanonicalStreamBus, StreamingPolicy, SymbolMaster
from packages.market_data.normalization import CanonicalMarketEvent


FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOLS = ROOT / "config/market-data/symbol-master.json"
STREAMING = ROOT / "config/market-data/streaming-policy.json"
PERFORMANCE = ROOT / "config/market-data/performance-policy.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def percentile_ms(samples_ns: list[int], percentile: float) -> float:
    if not samples_ns:
        raise ValueError("samples must be non-empty")
    ordered = sorted(samples_ns)
    rank = max(1, math.ceil((percentile / 100.0) * len(ordered)))
    return ordered[rank - 1] / 1_000_000.0


def eps(events: int, elapsed_ns: int) -> float:
    if elapsed_ns <= 0:
        raise ValueError("elapsed_ns must be positive")
    return events * 1_000_000_000.0 / elapsed_ns


def fixture_builders() -> tuple[Callable[[int], CanonicalMarketEvent], ...]:
    normalizer = CanonicalNormalizer(SymbolMaster.from_path(SYMBOLS))

    kaiko_raw = load("kaiko_trade.json")
    kaiko_adapter = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    )

    dx_raw = load("dxfeed_eurusd_quote.json")
    dx_adapter = DxFeedForexQuoteAdapter(
        DxFeedForexSubscription(
            symbol="EUR/USD",
            canonical_id="FX:EUR/USD:SPOT_OTC",
        )
    )

    db_raw = load("databento_gc_mbp1.json")
    db_adapter = DatabentoGoldContextAdapter()

    def kaiko(received_at_ns: int) -> CanonicalMarketEvent:
        return normalizer.normalize(
            kaiko_adapter.parse_trade(kaiko_raw, received_at_ns=received_at_ns)
        )

    def dxfeed(received_at_ns: int) -> CanonicalMarketEvent:
        return normalizer.normalize(
            dx_adapter.parse_quote(dx_raw, received_at_ns=received_at_ns)
        )

    def databento(received_at_ns: int) -> CanonicalMarketEvent:
        return normalizer.normalize(
            db_adapter.parse_mbp1(
                db_raw,
                mapped_symbol="GCZ6",
                received_at_ns=received_at_ns,
            )
        )

    return (kaiko, dxfeed, databento)


def measure_latency(
    builders: tuple[Callable[[int], CanonicalMarketEvent], ...],
    *,
    warmup_events: int,
    sample_events: int,
) -> tuple[list[int], tuple[CanonicalMarketEvent, ...]]:
    base_ns = 1_800_000_000_000_000_000
    for index in range(warmup_events):
        builder = builders[index % len(builders)]
        builder(base_ns + index)

    samples: list[int] = []
    canonical: list[CanonicalMarketEvent] = []
    for index in range(sample_events):
        builder = builders[index % len(builders)]
        start = perf_counter_ns()
        event = builder(base_ns + warmup_events + index)
        elapsed = perf_counter_ns() - start
        samples.append(elapsed)
        if len(canonical) < len(builders):
            canonical.append(event)

    return samples, tuple(canonical)


def measure_stream_throughput(
    canonical: tuple[CanonicalMarketEvent, ...],
    *,
    event_count: int,
) -> tuple[float, int]:
    bus = CanonicalStreamBus(StreamingPolicy.from_path(STREAMING))
    start = perf_counter_ns()
    for index in range(event_count):
        bus.publish(canonical[index % len(canonical)])
    elapsed = perf_counter_ns() - start
    rejected = bus.rejected_events
    while bus.consume() is not None:
        pass
    if bus.queue_depth != 0:
        raise AssertionError("stream queue did not fully drain")
    return eps(event_count, elapsed), rejected


def validate_peak_burst(
    canonical: tuple[CanonicalMarketEvent, ...],
    *,
    event_count: int,
) -> tuple[int, int]:
    bus = CanonicalStreamBus(StreamingPolicy.from_path(STREAMING))
    for index in range(event_count):
        bus.publish(canonical[index % len(canonical)])
    depth = bus.queue_depth
    rejected = bus.rejected_events
    consumed = 0
    while bus.consume() is not None:
        consumed += 1
    if consumed != event_count:
        raise AssertionError(
            f"burst drain mismatch: accepted={event_count} consumed={consumed}"
        )
    return depth, rejected


def measure_soak_equivalent(
    canonical: tuple[CanonicalMarketEvent, ...],
    *,
    event_count: int,
) -> tuple[float, int, int]:
    bus = CanonicalStreamBus(StreamingPolicy.from_path(STREAMING))
    start = perf_counter_ns()
    consumed = 0
    for index in range(event_count):
        bus.publish(canonical[index % len(canonical)])
        item = bus.consume()
        if item is None:
            raise AssertionError("soak consume unexpectedly empty")
        consumed += 1
    elapsed = perf_counter_ns() - start
    if bus.queue_depth != 0:
        raise AssertionError("soak queue did not return to zero")
    return eps(event_count, elapsed), bus.rejected_events, consumed


def build(output: Path) -> None:
    policy = json.loads(PERFORMANCE.read_text(encoding="utf-8"))
    benchmark = policy["benchmark"]
    requirements = policy["pass_requirements"]
    fast = policy["l_fast_data"]
    stress = policy["stress_review_boundary"]

    builders = fixture_builders()
    latency_samples, canonical = measure_latency(
        builders,
        warmup_events=benchmark["warmup_events"],
        sample_events=benchmark["latency_sample_events"],
    )
    p50_ms = percentile_ms(latency_samples, 50.0)
    p95_ms = percentile_ms(latency_samples, 95.0)
    p99_ms = percentile_ms(latency_samples, 99.0)

    stream_eps, stream_rejected = measure_stream_throughput(
        canonical,
        event_count=benchmark["throughput_events"],
    )
    burst_depth, burst_rejected = validate_peak_burst(
        canonical,
        event_count=benchmark["operating_peak_burst_events"],
    )
    soak_eps, soak_rejected, soak_consumed = measure_soak_equivalent(
        canonical,
        event_count=benchmark["soak_equivalent_events"],
    )

    checks = {
        "latency_p95": p95_ms <= fast["p95_max_ms"],
        "latency_p99": p99_ms <= fast["p99_max_ms"],
        "stream_throughput": stream_eps
        >= requirements["canonical_stream_min_events_per_sec"],
        "stream_rejected_zero": stream_rejected == 0,
        "burst_depth_exact": burst_depth == benchmark["operating_peak_burst_events"],
        "burst_rejected_zero": burst_rejected == requirements["burst_rejected_events"],
        "soak_consumed_exact": soak_consumed == benchmark["soak_equivalent_events"],
        "soak_throughput": soak_eps >= requirements["soak_min_events_per_sec"],
        "soak_rejected_zero": soak_rejected == requirements["soak_rejected_events"],
    }
    verdict = "PASS" if all(checks.values()) else "FAIL"

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05G_MEASURED_PERFORMANCE",
        "verdict": verdict,
        "scope": policy["certification_scope"],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "latency": {
            "path": fast["path"],
            "samples": len(latency_samples),
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
            "p99_ms": p99_ms,
            "p95_target_ms": fast["p95_max_ms"],
            "p99_target_ms": fast["p99_max_ms"],
            "upstream_provider_latency_excluded": True,
        },
        "throughput": {
            "events": benchmark["throughput_events"],
            "measured_events_per_sec": stream_eps,
            "required_events_per_sec": requirements[
                "canonical_stream_min_events_per_sec"
            ],
            "rejected_events": stream_rejected,
        },
        "operating_peak_burst": {
            "events": benchmark["operating_peak_burst_events"],
            "observed_queue_depth": burst_depth,
            "rejected_events": burst_rejected,
        },
        "soak_equivalent": {
            "seconds_at_operating_average": benchmark["soak_equivalent_seconds"],
            "events": benchmark["soak_equivalent_events"],
            "consumed_events": soak_consumed,
            "measured_events_per_sec": soak_eps,
            "required_events_per_sec": requirements["soak_min_events_per_sec"],
            "rejected_events": soak_rejected,
        },
        "stress_review_boundary": {
            "events_per_sec": stress["peak_events_per_sec"],
            "certified": False,
            "observed_stream_eps_meets_boundary": stream_eps
            >= stress["peak_events_per_sec"],
            "rule": "REPORT_ONLY_ARCHITECTURE_REVIEW_BOUNDARY",
        },
        "checks": checks,
        "safety": {
            "network_required": False,
            "credentials_resolved": False,
            "automatic_data_failover": "DISABLED",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "P05G_PERFORMANCE="
        f"{verdict} p95_ms={p95_ms:.6f} p99_ms={p99_ms:.6f} "
        f"stream_eps={stream_eps:.2f} soak_eps={soak_eps:.2f}"
    )
    if verdict != "PASS":
        failed = ",".join(name for name, passed in checks.items() if not passed)
        print(f"P05G_FAILED_CHECKS={failed}")
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
