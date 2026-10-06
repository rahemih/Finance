from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from adapters.market_data.dxfeed import DxFeedForexQuoteAdapter, DxFeedForexSubscription
from adapters.market_data.kaiko import KaikoAdapter, KaikoSubscription
from packages.contracts.market_data import MarketEventKind
from packages.market_data import (
    CanonicalNormalizer,
    FailoverDisposition,
    ProviderRecoveryPolicy,
    RecoveryCoordinator,
    RecoveryError,
    RecoveryPending,
    RecoveryPolicy,
    RecoverySequenceDisposition,
    RecoveryState,
    SequenceMode,
    SequenceTracker,
    SymbolMaster,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/p05/fixtures"
SYMBOL_MASTER = ROOT / "config/market-data/symbol-master.json"
RECOVERY_POLICY = ROOT / "config/market-data/recovery-policy.json"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def normalizer() -> CanonicalNormalizer:
    return CanonicalNormalizer(SymbolMaster.from_path(SYMBOL_MASTER))


def kaiko_trade(*, sequence_id: str = "a000001", received_at_ns: int = 100):
    raw = load("kaiko_trade.json")
    raw["sequenceId"] = sequence_id
    envelope = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    ).parse_trade(raw, received_at_ns=received_at_ns)
    return normalizer().normalize(envelope)


def kaiko_book(
    fixture_name: str,
    *,
    sequence_id: str,
    received_at_ns: int,
):
    raw = load(fixture_name)
    raw["sequenceId"] = sequence_id
    envelope = KaikoAdapter(
        KaikoSubscription(
            exchange="cbse",
            instrument_class="spot",
            code="btc-usd",
            credential_ref="secret://market-data/kaiko/api-key",
        )
    ).parse_order_book(raw, received_at_ns=received_at_ns)
    return normalizer().normalize(envelope)


def dx_quote(*, sequence_id: int, received_at_ns: int = 200):
    raw = load("dxfeed_eurusd_quote.json")
    raw["sequence"] = sequence_id
    envelope = DxFeedForexQuoteAdapter(
        DxFeedForexSubscription(
            symbol="EUR/USD",
            canonical_id="FX:EUR/USD:SPOT_OTC",
        )
    ).parse_quote(raw, received_at_ns=received_at_ns)
    return normalizer().normalize(envelope)


def tiny_policy(*, contiguous: bool = False) -> RecoveryPolicy:
    return RecoveryPolicy(
        max_attempts=2,
        base_backoff_ns=10,
        max_backoff_ns=20,
        circuit_open_ns=100,
        automatic_data_failover=False,
        providers=(
            ProviderRecoveryPolicy(
                provider="kaiko",
                sequence_mode=SequenceMode.LEXICOGRAPHIC,
                contiguous=False,
                snapshot_required_kinds=(MarketEventKind.ORDER_BOOK,),
                backup_candidates=("coinapi",),
                backup_status="CONDITIONAL_SHORTLIST_ONLY",
            ),
            ProviderRecoveryPolicy(
                provider="dxfeed",
                sequence_mode=SequenceMode.INTEGER,
                contiguous=contiguous,
                snapshot_required_kinds=(),
                backup_candidates=("massive",),
                backup_status="CONDITIONAL_SHORTLIST_ONLY",
            ),
        ),
    )


class SequenceRecoveryTests(unittest.TestCase):
    def test_policy_loads_and_failover_is_disabled(self):
        policy = RecoveryPolicy.from_path(RECOVERY_POLICY)
        self.assertFalse(policy.automatic_data_failover)
        self.assertFalse(policy.provider("kaiko").contiguous)
        self.assertFalse(policy.provider("dxfeed").contiguous)
        self.assertFalse(policy.provider("databento").contiguous)

    def test_kaiko_lexicographic_jump_is_advancing_not_gap(self):
        tracker = SequenceTracker(tiny_policy())
        first = tracker.observe(kaiko_trade(sequence_id="a000001"))
        jump = tracker.observe(kaiko_trade(sequence_id="a000003", received_at_ns=101))
        self.assertEqual(first.disposition, RecoverySequenceDisposition.FIRST)
        self.assertEqual(jump.disposition, RecoverySequenceDisposition.ADVANCING)
        self.assertTrue(jump.accepted)
        self.assertIsNone(jump.expected_sequence)

    def test_dxfeed_integer_jump_is_not_gap_without_contiguity_evidence(self):
        tracker = SequenceTracker(tiny_policy())
        tracker.observe(dx_quote(sequence_id=10))
        jump = tracker.observe(dx_quote(sequence_id=12, received_at_ns=201))
        self.assertEqual(jump.disposition, RecoverySequenceDisposition.ADVANCING)
        self.assertTrue(jump.accepted)

    def test_proven_contiguous_integer_policy_detects_gap(self):
        tracker = SequenceTracker(tiny_policy(contiguous=True))
        tracker.observe(dx_quote(sequence_id=10))
        gap = tracker.observe(dx_quote(sequence_id=12, received_at_ns=201))
        self.assertEqual(gap.disposition, RecoverySequenceDisposition.GAP)
        self.assertEqual(gap.expected_sequence, "11")
        self.assertFalse(gap.accepted)

    def test_duplicate_and_out_of_order_are_not_accepted(self):
        tracker = SequenceTracker(tiny_policy())
        tracker.observe(dx_quote(sequence_id=10))
        duplicate = tracker.observe(dx_quote(sequence_id=10, received_at_ns=201))
        out_of_order = tracker.observe(dx_quote(sequence_id=9, received_at_ns=202))
        self.assertEqual(duplicate.disposition, RecoverySequenceDisposition.DUPLICATE)
        self.assertEqual(out_of_order.disposition, RecoverySequenceDisposition.OUT_OF_ORDER)
        self.assertFalse(duplicate.accepted)
        self.assertFalse(out_of_order.accepted)


class ReconnectControllerTests(unittest.TestCase):
    def test_reconnect_uses_capped_backoff_and_opens_circuit(self):
        coordinator = RecoveryCoordinator(tiny_policy())
        sample = kaiko_trade()
        key = coordinator.key_for(sample)

        first = coordinator.schedule_reconnect(key, now_ns=100, reason="STALE")
        self.assertEqual(first.state, RecoveryState.WAITING_RETRY)
        self.assertEqual(first.attempts, 1)
        self.assertEqual(first.next_retry_at_ns, 110)

        with self.assertRaises(RecoveryError):
            coordinator.begin_reconnect(key, now_ns=109)

        coordinator.begin_reconnect(key, now_ns=110)
        second = coordinator.reconnect_failed(key, now_ns=111, reason="CONNECT_FAILED")
        self.assertEqual(second.attempts, 2)
        self.assertEqual(second.next_retry_at_ns, 131)

        coordinator.begin_reconnect(key, now_ns=131)
        opened = coordinator.reconnect_failed(key, now_ns=132, reason="CONNECT_FAILED")
        self.assertEqual(opened.state, RecoveryState.CIRCUIT_OPEN)
        self.assertEqual(opened.circuit_open_until_ns, 232)

        with self.assertRaises(RecoveryError):
            coordinator.arm_probe_after_circuit(key, now_ns=231)

        probe = coordinator.arm_probe_after_circuit(key, now_ns=232)
        self.assertEqual(probe.state, RecoveryState.WAITING_RETRY)
        self.assertEqual(probe.next_retry_at_ns, 232)

    def test_reconnect_success_enters_validation_not_active(self):
        coordinator = RecoveryCoordinator(tiny_policy())
        sample = dx_quote(sequence_id=1)
        key = coordinator.key_for(sample)
        coordinator.schedule_reconnect(key, now_ns=100, reason="STALE")
        coordinator.begin_reconnect(key, now_ns=110)
        snapshot = coordinator.reconnect_succeeded(key)
        self.assertEqual(snapshot.state, RecoveryState.RECOVERY_VALIDATION)

        observation = coordinator.validate_recovery_event(dx_quote(sequence_id=50, received_at_ns=300))
        self.assertEqual(observation.disposition, RecoverySequenceDisposition.FIRST)
        self.assertEqual(coordinator.snapshot(key).state, RecoveryState.ACTIVE)

    def test_kaiko_order_book_recovery_requires_fresh_snapshot(self):
        coordinator = RecoveryCoordinator(tiny_policy())
        update = kaiko_book(
            "kaiko_orderbook_update.json",
            sequence_id="a000010",
            received_at_ns=300,
        )
        key = coordinator.key_for(update)
        coordinator.schedule_reconnect(key, now_ns=100, reason="DISCONNECT")
        coordinator.begin_reconnect(key, now_ns=110)
        coordinator.reconnect_succeeded(key)

        with self.assertRaises(RecoveryPending):
            coordinator.validate_recovery_event(update)

        snapshot = kaiko_book(
            "kaiko_orderbook_snapshot.json",
            sequence_id="a000020",
            received_at_ns=301,
        )
        observation = coordinator.validate_recovery_event(snapshot)
        self.assertTrue(observation.accepted)
        self.assertEqual(coordinator.snapshot(key).state, RecoveryState.ACTIVE)

    def test_out_of_order_degrades_stream_and_failover_requires_validation(self):
        coordinator = RecoveryCoordinator(tiny_policy())
        first = dx_quote(sequence_id=10)
        key = coordinator.key_for(first)
        coordinator.observe(first)
        observation = coordinator.observe(dx_quote(sequence_id=9, received_at_ns=201))
        self.assertEqual(observation.disposition, RecoverySequenceDisposition.OUT_OF_ORDER)
        self.assertEqual(coordinator.snapshot(key).state, RecoveryState.DEGRADED)
        self.assertEqual(
            coordinator.failover_disposition(key, backup_healthy=True),
            FailoverDisposition.BACKUP_VALIDATION_REQUIRED,
        )
        self.assertEqual(
            coordinator.failover_disposition(key, backup_healthy=False),
            FailoverDisposition.FAIL_CLOSED,
        )

    def test_duplicate_is_rejected_without_forcing_degraded_state(self):
        coordinator = RecoveryCoordinator(tiny_policy())
        first = dx_quote(sequence_id=10)
        key = coordinator.key_for(first)
        coordinator.observe(first)
        duplicate = coordinator.observe(dx_quote(sequence_id=10, received_at_ns=201))
        self.assertFalse(duplicate.accepted)
        self.assertEqual(duplicate.disposition, RecoverySequenceDisposition.DUPLICATE)
        self.assertEqual(coordinator.snapshot(key).state, RecoveryState.ACTIVE)

    def test_recovery_module_is_provider_neutral(self):
        text = (ROOT / "packages/market_data/recovery.py").read_text(encoding="utf-8")
        self.assertNotIn("adapters.", text)


if __name__ == "__main__":
    unittest.main()
