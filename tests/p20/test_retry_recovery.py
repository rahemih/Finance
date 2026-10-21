from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.execution.retry_recovery import (
    RecoveryCheckpoint, RecoverySignal, RetryRecoveryError, RetryRecoveryPlanner, RetryRecoveryPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/retry-recovery-policy.json"
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def checkpoint(*, attempt: int = 1, stage: str = "PRE_DISPATCH", previous: str | None = None, observed: int = 100) -> RecoveryCheckpoint:
    return RecoveryCheckpoint(
        market="CRYPTO", operation="ORDER_SUBMIT", order_id="order-001", client_order_id="client-001",
        idempotency_key="idem-001", idempotency_claim_id=HEX_A, request_id=HEX_B, oms_record_id=HEX_C,
        attempt=attempt, stage=stage, observed_at_ns=observed, previous_checkpoint_id=previous,
    )


class RetryRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = RetryRecoveryPolicy.from_path(POLICY)
        self.planner = RetryRecoveryPlanner(self.policy)

    def test_policy_is_fail_closed_and_zero_authority(self) -> None:
        self.assertEqual(self.policy.max_attempts, 3)
        self.assertEqual(self.policy.backoff_ms, (250, 1000, 4000))
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_pre_dispatch_timeout_retries_same_claim_deterministically(self) -> None:
        cp = checkpoint()
        self.planner.record(cp)
        first = self.planner.decide("order-001", RecoverySignal("PRE_DISPATCH_TIMEOUT", 101))
        second = self.planner.decide("order-001", RecoverySignal("PRE_DISPATCH_TIMEOUT", 101))
        self.assertEqual(first, second)
        self.assertEqual(first.disposition, "RETRY_SAME_CLAIM")
        self.assertEqual(first.next_attempt, 2)
        self.assertEqual(first.backoff_ms, 250)
        self.assertEqual(first.idempotency_claim_id, HEX_A)
        self.assertEqual(first.request_id, HEX_B)
        self.assertFalse(first.actual_retry_dispatch)
        self.assertEqual(first.network_mode, "DISABLED")

    def test_pre_dispatch_failure_and_crash_are_retryable(self) -> None:
        self.planner.record(checkpoint())
        for condition in ("PRE_DISPATCH_FAILURE", "PROCESS_CRASH_BEFORE_DISPATCH"):
            decision = self.planner.decide("order-001", RecoverySignal(condition, 101))
            self.assertEqual(decision.disposition, "RETRY_SAME_CLAIM")

    def test_post_dispatch_ambiguity_and_crash_fail_closed(self) -> None:
        self.planner.record(checkpoint(stage="POST_DISPATCH"))
        for condition in ("DISPATCH_OUTCOME_UNKNOWN", "PROCESS_CRASH_AFTER_DISPATCH"):
            decision = self.planner.decide("order-001", RecoverySignal(condition, 101))
            self.assertEqual(decision.disposition, "SAFE_HOLD_RECONCILIATION_REQUIRED")
            self.assertTrue(decision.reconciliation_required)
            self.assertIsNone(decision.next_attempt)
            self.assertFalse(decision.actual_retry_dispatch)

    def test_ambiguous_signal_cannot_use_pre_dispatch_checkpoint(self) -> None:
        self.planner.record(checkpoint())
        with self.assertRaises(RetryRecoveryError):
            self.planner.decide("order-001", RecoverySignal("DISPATCH_OUTCOME_UNKNOWN", 101))

    def test_terminal_outcomes_never_retry(self) -> None:
        self.planner.record(checkpoint(stage="TERMINAL"))
        for condition in ("ACKNOWLEDGED", "REJECTED", "CANCEL_ACKNOWLEDGED"):
            decision = self.planner.decide("order-001", RecoverySignal(condition, 101))
            self.assertEqual(decision.disposition, "NO_RETRY_TERMINAL")
            self.assertIsNone(decision.next_attempt)

    def test_retry_budget_exhaustion_is_deterministic(self) -> None:
        self.planner.record(checkpoint(attempt=3))
        decision = self.planner.decide("order-001", RecoverySignal("PRE_DISPATCH_TIMEOUT", 101))
        self.assertEqual(decision.disposition, "RETRY_BUDGET_EXHAUSTED")
        self.assertIsNone(decision.next_attempt)
        self.assertIsNone(decision.backoff_ms)

    def test_checkpoint_chain_preserves_exact_lineage(self) -> None:
        first = checkpoint()
        self.planner.record(first)
        second = checkpoint(attempt=2, previous=first.checkpoint_id, observed=200)
        self.planner.record(second)
        with self.assertRaises(RetryRecoveryError):
            self.planner.record(replace(second, attempt=3, previous_checkpoint_id="d" * 64, observed_at_ns=300))
        with self.assertRaises(RetryRecoveryError):
            self.planner.record(replace(second, attempt=3, previous_checkpoint_id=second.checkpoint_id, observed_at_ns=300, request_id="e" * 64))

    def test_checkpoint_time_and_attempt_cannot_regress_or_jump(self) -> None:
        first = checkpoint()
        self.planner.record(first)
        with self.assertRaises(RetryRecoveryError):
            self.planner.record(checkpoint(attempt=1, previous=first.checkpoint_id, observed=99))
        with self.assertRaises(RetryRecoveryError):
            self.planner.record(checkpoint(attempt=3, previous=first.checkpoint_id, observed=101))

    def test_snapshot_is_deterministic_and_zero_authority(self) -> None:
        self.planner.record(checkpoint())
        first = self.planner.snapshot()
        second = self.planner.snapshot()
        self.assertEqual(first, second)
        authority = first["authority"]
        assert isinstance(authority, dict)
        self.assertEqual(authority["network_mode"], "DISABLED")
        self.assertFalse(authority["actual_retry_dispatch"])
        self.assertFalse(authority["external_order_submission"])
        self.assertFalse(authority["reconciliation_authority"])
        self.assertFalse(authority["live_execution_authority"])


if __name__ == "__main__":
    unittest.main()
