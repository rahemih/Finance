from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import socket
import unittest

from tests.harness import (
    DeterministicClock,
    DeterministicIdSequence,
    FailureInjector,
    InjectedFailure,
    InvalidReconciliationError,
    InvalidReplayError,
    NetworkDeniedError,
    NetworkDenyGuard,
    ReplayTape,
    ScriptedProviderSimulator,
    UnsafeRetryError,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/foundation"


class DeterministicClockTests(unittest.TestCase):
    def test_clock_advance_and_set_are_deterministic(self):
        clock = DeterministicClock("2026-01-01T00:00:00Z")
        self.assertEqual(clock.now_iso(), "2026-01-01T00:00:00Z")
        clock.advance(timedelta(seconds=5))
        self.assertEqual(clock.now_iso(), "2026-01-01T00:00:05Z")
        clock.set("2026-01-01T00:00:10Z")
        self.assertEqual(clock.now_iso(), "2026-01-01T00:00:10Z")

    def test_clock_cannot_move_backwards(self):
        clock = DeterministicClock("2026-01-01T00:00:10Z")
        with self.assertRaises(ValueError):
            clock.set("2026-01-01T00:00:09Z")
        with self.assertRaises(ValueError):
            clock.advance(timedelta(seconds=-1))


class DeterministicIdTests(unittest.TestCase):
    def test_same_initial_state_repeats_ids(self):
        first = DeterministicIdSequence("intent", start=7)
        second = DeterministicIdSequence("intent", start=7)
        self.assertEqual(
            [first.next(), first.next(), first.next()],
            [second.next(), second.next(), second.next()],
        )
        self.assertEqual(first.next(), "intent-000010")


class ReplayTapeTests(unittest.TestCase):
    def test_fixture_replay_is_stable(self):
        first = ReplayTape.from_fixture(FIXTURES / "replay-basic.json")
        second = ReplayTape.from_fixture(FIXTURES / "replay-basic.json")
        self.assertEqual(first.digest(), second.digest())
        self.assertEqual(first.normalized_events(), second.normalized_events())
        self.assertEqual([event.sequence for event in first], [1, 2, 3])

    def test_duplicate_sequence_is_rejected(self):
        with self.assertRaises(InvalidReplayError):
            ReplayTape([
                {"sequence": 1, "event_time": "2026-01-01T00:00:00Z", "event_type": "A", "payload": {}},
                {"sequence": 1, "event_time": "2026-01-01T00:00:01Z", "event_type": "B", "payload": {}},
            ])

    def test_non_monotonic_sequence_is_rejected(self):
        with self.assertRaises(InvalidReplayError):
            ReplayTape([
                {"sequence": 2, "event_time": "2026-01-01T00:00:00Z", "event_type": "A", "payload": {}},
                {"sequence": 1, "event_time": "2026-01-01T00:00:01Z", "event_type": "B", "payload": {}},
            ])

    def test_backwards_event_time_is_rejected(self):
        with self.assertRaises(InvalidReplayError):
            ReplayTape([
                {"sequence": 1, "event_time": "2026-01-01T00:00:02Z", "event_type": "A", "payload": {}},
                {"sequence": 2, "event_time": "2026-01-01T00:00:01Z", "event_type": "B", "payload": {}},
            ])


class ProviderSimulatorTests(unittest.TestCase):
    def test_unknown_blocks_blind_retry_until_reconciliation(self):
        provider = ScriptedProviderSimulator.from_fixture(FIXTURES / "provider-unknown.json")
        intent = "intent-000001"

        self.assertEqual(provider.submit(intent), "TIMEOUT_UNKNOWN")
        self.assertTrue(provider.unresolved(intent))

        with self.assertRaises(UnsafeRetryError):
            provider.submit(intent)

        self.assertEqual(provider.reconcile(intent, "REJECTED"), "REJECTED")
        self.assertFalse(provider.unresolved(intent))
        self.assertEqual(provider.submit(intent), "ACKNOWLEDGED")

    def test_unknown_is_not_success_or_rejection(self):
        provider = ScriptedProviderSimulator(["TIMEOUT_UNKNOWN"])
        outcome = provider.submit("intent-unknown")
        self.assertEqual(outcome, "TIMEOUT_UNKNOWN")
        self.assertNotIn(outcome, {"ACKNOWLEDGED", "REJECTED", "FILLED", "CANCELED"})

    def test_reconciliation_requires_proved_state(self):
        provider = ScriptedProviderSimulator(["TIMEOUT_UNKNOWN"])
        provider.submit("intent-2")
        with self.assertRaises(InvalidReconciliationError):
            provider.reconcile("intent-2", "UNKNOWN")

    def test_reconcile_non_unresolved_intent_is_rejected(self):
        provider = ScriptedProviderSimulator(["ACKNOWLEDGED"])
        self.assertEqual(provider.submit("intent-3"), "ACKNOWLEDGED")
        with self.assertRaises(InvalidReconciliationError):
            provider.reconcile("intent-3", "FILLED")


class FailureInjectorTests(unittest.TestCase):
    def test_failure_fires_on_exact_configured_call(self):
        injector = FailureInjector({"before-persist": 2})
        injector.checkpoint("before-persist")
        with self.assertRaises(InjectedFailure):
            injector.checkpoint("before-persist")
        self.assertEqual(injector.count("before-persist"), 2)

    def test_other_checkpoint_is_not_affected(self):
        injector = FailureInjector({"target": 1})
        injector.checkpoint("other")
        self.assertEqual(injector.count("other"), 1)


class NetworkDenyGuardTests(unittest.TestCase):
    def test_create_connection_is_denied(self):
        with NetworkDenyGuard():
            with self.assertRaises(NetworkDeniedError):
                socket.create_connection(("example.invalid", 443), timeout=0.01)

    def test_socket_connect_is_denied(self):
        sock = socket.socket()
        try:
            with NetworkDenyGuard():
                with self.assertRaises(NetworkDeniedError):
                    sock.connect(("127.0.0.1", 9))
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()
