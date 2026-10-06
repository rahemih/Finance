from __future__ import annotations

import json
from pathlib import Path
import unittest

from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.market_data import (
    BackpressureError,
    BufferPressure,
    CanonicalNormalizer,
    CanonicalStreamBus,
    StreamHealth,
    StreamingError,
    StreamingPolicy,
    SymbolMaster,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOL_MASTER = ROOT / "config/market-data/symbol-master.json"
STREAMING_POLICY = ROOT / "config/market-data/streaming-policy.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def event(*, received_at_ns: int):
    envelope = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    ).parse_trade(
        load("kaiko_trade.json"),
        received_at_ns=received_at_ns,
    )
    return CanonicalNormalizer(
        SymbolMaster.from_path(SYMBOL_MASTER)
    ).normalize(envelope)


def small_policy() -> StreamingPolicy:
    return StreamingPolicy(
        max_buffer_events=4,
        high_watermark_events=2,
        critical_watermark_events=3,
        heartbeat_timeout_ns=10,
    )


class StreamingPolicyTests(unittest.TestCase):
    def test_default_policy_loads_and_covers_operating_60_second_peak(self):
        policy = StreamingPolicy.from_path(STREAMING_POLICY)
        raw = json.loads(STREAMING_POLICY.read_text(encoding="utf-8"))
        basis = raw["capacity_basis"]
        expected = basis["peak_events_per_sec"] * basis["minimum_buffer_seconds"]
        self.assertGreaterEqual(policy.max_buffer_events, expected)
        self.assertEqual(policy.max_buffer_events, basis["minimum_event_capacity"])
        self.assertEqual(policy.high_watermark_events, 840_000)
        self.assertEqual(policy.critical_watermark_events, 1_080_000)

    def test_invalid_threshold_order_is_rejected(self):
        with self.assertRaises(StreamingError):
            StreamingPolicy(
                max_buffer_events=4,
                high_watermark_events=3,
                critical_watermark_events=3,
                heartbeat_timeout_ns=10,
            )


class CanonicalStreamBusTests(unittest.TestCase):
    def test_fifo_order_is_preserved(self):
        bus = CanonicalStreamBus(small_policy())
        first = event(received_at_ns=100)
        second = event(received_at_ns=101)
        bus.publish(first)
        bus.publish(second)
        self.assertIs(bus.consume(), first)
        self.assertIs(bus.consume(), second)
        self.assertIsNone(bus.consume())

    def test_pressure_transitions_are_deterministic(self):
        bus = CanonicalStreamBus(small_policy())
        self.assertEqual(bus.pressure, BufferPressure.NORMAL)
        bus.publish(event(received_at_ns=100))
        self.assertEqual(bus.pressure, BufferPressure.NORMAL)
        bus.publish(event(received_at_ns=101))
        self.assertEqual(bus.pressure, BufferPressure.HIGH)
        bus.publish(event(received_at_ns=102))
        self.assertEqual(bus.pressure, BufferPressure.CRITICAL)
        bus.publish(event(received_at_ns=103))
        self.assertEqual(bus.pressure, BufferPressure.FULL)

    def test_overflow_is_explicit_and_does_not_overwrite(self):
        bus = CanonicalStreamBus(small_policy())
        accepted = [event(received_at_ns=100 + index) for index in range(4)]
        for item in accepted:
            bus.publish(item)

        with self.assertRaises(BackpressureError):
            bus.publish(event(received_at_ns=104))

        self.assertEqual(bus.queue_depth, 4)
        self.assertEqual(bus.high_watermark_seen, 4)
        self.assertEqual(bus.rejected_events, 1)
        self.assertEqual([bus.consume() for _ in range(4)], accepted)

    def test_heartbeat_transitions_never_seen_healthy_stale(self):
        bus = CanonicalStreamBus(small_policy())
        sample = event(received_at_ns=100)
        key = bus.key_for(sample)
        self.assertEqual(bus.health(key, now_ns=100), StreamHealth.NEVER_SEEN)

        bus.publish(sample)
        self.assertEqual(bus.health(key, now_ns=100), StreamHealth.HEALTHY)
        self.assertEqual(bus.health(key, now_ns=110), StreamHealth.HEALTHY)
        self.assertEqual(bus.health(key, now_ns=111), StreamHealth.STALE)

    def test_heartbeat_observation_before_last_accept_is_rejected(self):
        bus = CanonicalStreamBus(small_policy())
        sample = event(received_at_ns=100)
        key = bus.key_for(sample)
        bus.publish(sample)
        with self.assertRaises(StreamingError):
            bus.health(key, now_ns=99)

    def test_per_stream_receive_time_regression_is_rejected(self):
        bus = CanonicalStreamBus(small_policy())
        bus.publish(event(received_at_ns=100))
        with self.assertRaises(StreamingError):
            bus.publish(event(received_at_ns=99))
        self.assertEqual(bus.queue_depth, 1)

    def test_snapshot_exposes_queue_and_health_metrics(self):
        bus = CanonicalStreamBus(small_policy())
        sample = event(received_at_ns=100)
        key = bus.key_for(sample)
        bus.publish(sample)
        bus.publish(event(received_at_ns=101))
        snapshot = bus.snapshot(key, now_ns=105)
        self.assertEqual(snapshot.queue_depth, 2)
        self.assertEqual(snapshot.high_watermark_seen, 2)
        self.assertEqual(snapshot.rejected_events, 0)
        self.assertEqual(snapshot.pressure, BufferPressure.HIGH)
        self.assertEqual(snapshot.health, StreamHealth.HEALTHY)
        self.assertEqual(snapshot.last_accepted_receive_ns, 101)

    def test_streaming_module_is_provider_neutral(self):
        text = (ROOT / "packages/market_data/streaming.py").read_text(encoding="utf-8")
        self.assertNotIn("adapters.", text)


if __name__ == "__main__":
    unittest.main()
