from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.execution.idempotency import (
    IdempotencyError,
    IdempotencyLedger,
    IdempotencyPolicy,
    IdempotencyRequest,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/idempotency-policy.json"


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def request(
    *,
    market: str = "CRYPTO",
    operation: str = "ORDER_SUBMIT",
    order_id: str = "order-001",
    client_order_id: str = "client-001",
    key: str = "idem-001",
    payload: str = "payload-001",
) -> IdempotencyRequest:
    return IdempotencyRequest(
        market=market,
        operation=operation,
        order_id=order_id,
        client_order_id=client_order_id,
        idempotency_key=key,
        request_fingerprint=fingerprint(payload),
    )


class IdempotencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = IdempotencyPolicy.from_path(POLICY)
        self.ledger = IdempotencyLedger(self.policy)

    def test_policy_is_fail_closed_and_zero_authority(self) -> None:
        self.assertEqual(self.policy.markets, ("CRYPTO", "FOREX"))
        self.assertEqual(self.policy.operations, ("ORDER_SUBMIT", "ORDER_CANCEL"))
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_first_request_is_admitted_deterministically(self) -> None:
        req = request()
        first = self.ledger.admit(req)
        self.assertEqual(first.disposition, "ADMIT_NEW")
        self.assertTrue(first.new_claim)
        self.assertFalse(first.replay_existing)
        self.assertEqual(first.claim_id, self.ledger.claim(req.idempotency_key).claim_id)

    def test_exact_replay_returns_existing_claim(self) -> None:
        req = request()
        first = self.ledger.admit(req)
        replay = self.ledger.admit(req)
        self.assertEqual(replay.disposition, "REPLAY_EXISTING")
        self.assertTrue(replay.replay_existing)
        self.assertFalse(replay.new_claim)
        self.assertEqual(replay.claim_id, first.claim_id)

    def test_conflicting_idempotency_key_reuse_fails_closed(self) -> None:
        self.ledger.admit(request())
        with self.assertRaises(IdempotencyError):
            self.ledger.admit(request(order_id="order-002", payload="different"))

    def test_duplicate_client_order_id_under_another_key_fails_closed(self) -> None:
        self.ledger.admit(request())
        with self.assertRaises(IdempotencyError):
            self.ledger.admit(
                request(
                    order_id="order-002",
                    key="idem-002",
                    payload="payload-002",
                )
            )

    def test_duplicate_fingerprint_under_another_key_fails_closed(self) -> None:
        self.ledger.admit(request())
        with self.assertRaises(IdempotencyError):
            self.ledger.admit(
                request(
                    order_id="order-002",
                    client_order_id="client-002",
                    key="idem-002",
                )
            )

    def test_duplicate_operation_order_under_another_key_fails_closed(self) -> None:
        self.ledger.admit(request())
        with self.assertRaises(IdempotencyError):
            self.ledger.admit(
                request(
                    client_order_id="client-002",
                    key="idem-002",
                    payload="payload-002",
                )
            )

    def test_submit_and_cancel_may_have_separate_claims(self) -> None:
        submit = self.ledger.admit(request())
        cancel = self.ledger.admit(
            request(
                operation="ORDER_CANCEL",
                client_order_id="cancel-client-001",
                key="cancel-idem-001",
                payload="cancel-payload-001",
            )
        )
        self.assertEqual(submit.disposition, "ADMIT_NEW")
        self.assertEqual(cancel.disposition, "ADMIT_NEW")
        self.assertNotEqual(submit.claim_id, cancel.claim_id)

    def test_market_scopes_are_independent(self) -> None:
        crypto = self.ledger.admit(request())
        forex = self.ledger.admit(
            request(
                market="FOREX",
                order_id="order-001",
                client_order_id="client-001",
                key="forex-idem-001",
                payload="forex-payload",
            )
        )
        self.assertNotEqual(crypto.claim_id, forex.claim_id)

    def test_invalid_fingerprint_fails_closed(self) -> None:
        bad = IdempotencyRequest(
            market="CRYPTO",
            operation="ORDER_SUBMIT",
            order_id="order-001",
            client_order_id="client-001",
            idempotency_key="idem-001",
            request_fingerprint="not-sha",
        )
        with self.assertRaises(IdempotencyError):
            self.ledger.admit(bad)

    def test_snapshot_is_deterministic_and_zero_authority(self) -> None:
        self.ledger.admit(request())
        self.ledger.admit(
            request(
                operation="ORDER_CANCEL",
                client_order_id="cancel-client-001",
                key="cancel-idem-001",
                payload="cancel-payload",
            )
        )
        first = self.ledger.snapshot()
        second = self.ledger.snapshot()
        self.assertEqual(first, second)
        authority = first["authority"]
        assert isinstance(authority, dict)
        self.assertFalse(authority["retry_authority"])
        self.assertFalse(authority["reconciliation_authority"])
        self.assertFalse(authority["live_execution_authority"])
        self.assertEqual(authority["network_mode"], "DISABLED")

    def test_unknown_claim_fails_closed(self) -> None:
        with self.assertRaises(IdempotencyError):
            self.ledger.claim("missing")


if __name__ == "__main__":
    unittest.main()
