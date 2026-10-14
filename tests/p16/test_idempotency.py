from __future__ import annotations

import unittest

from packages.pretrade_firewall.idempotency import (
    IdempotencyPolicy,
    IdempotencyPrecheckError,
    IdempotencyPrecheckRequest,
    PriorAdmission,
    evaluate_idempotency,
)


A = "a" * 64
B = "b" * 64


POLICY = IdempotencyPolicy(
    policy_version="p16b-test-v1",
    replay_lookback_ns=1000,
)


def request(
    *,
    upstream_status: str = "PRETRADE_A_ELIGIBLE",
    key: str = "key-1",
    fingerprint: str = A,
    as_of_ns: int = 5000,
    records: tuple[PriorAdmission, ...] = (),
) -> IdempotencyPrecheckRequest:
    return IdempotencyPrecheckRequest.build(
        request_id="b-1",
        upstream_freshness_decision_id="a-decision",
        upstream_freshness_status=upstream_status,
        idempotency_key=key,
        intent_fingerprint_sha256=fingerprint,
        as_of_ns=as_of_ns,
        prior_admissions=records,
    )


class IdempotencyPrecheckTests(unittest.TestCase):
    def test_unique_intent_is_eligible(self) -> None:
        decision = evaluate_idempotency(policy=POLICY, request=request())
        self.assertEqual(decision.status, "PRETRADE_B_ELIGIBLE")
        self.assertEqual(decision.matched_record_count, 0)
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(upstream_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_FRESHNESS_VETO", decision.reason_codes)

    def test_exact_key_replay_vetoes(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(records=(PriorAdmission("key-1", A, 4500),)),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("DUPLICATE_IDEMPOTENCY_KEY", decision.reason_codes)

    def test_key_collision_vetoes(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(records=(PriorAdmission("key-1", B, 4500),)),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("IDEMPOTENCY_KEY_COLLISION", decision.reason_codes)

    def test_duplicate_intent_under_other_key_vetoes(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(records=(PriorAdmission("key-2", A, 4500),)),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("DUPLICATE_INTENT_FINGERPRINT", decision.reason_codes)

    def test_outside_replay_window_is_eligible(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(records=(PriorAdmission("key-1", A, 3999),)),
        )
        self.assertEqual(decision.status, "PRETRADE_B_ELIGIBLE")

    def test_replay_window_boundary_is_included(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(records=(PriorAdmission("key-1", A, 4000),)),
        )
        self.assertEqual(decision.status, "VETO")

    def test_future_prior_admission_fails_closed(self) -> None:
        decision = evaluate_idempotency(
            policy=POLICY,
            request=request(records=(PriorAdmission("key-x", B, 5001),)),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("FUTURE_PRIOR_ADMISSION", decision.reason_codes)

    def test_invalid_fingerprint_fails_closed(self) -> None:
        with self.assertRaises(IdempotencyPrecheckError):
            request(fingerprint="bad")

    def test_order_independent_identity(self) -> None:
        records = (
            PriorAdmission("old", B, 3000),
            PriorAdmission("other", B, 4500),
        )
        left = evaluate_idempotency(
            policy=POLICY,
            request=request(records=records),
        )
        right = evaluate_idempotency(
            policy=POLICY,
            request=request(records=tuple(reversed(records))),
        )
        self.assertEqual(left.decision_id, right.decision_id)

    def test_invalid_policy_fails_closed(self) -> None:
        with self.assertRaises(IdempotencyPrecheckError):
            IdempotencyPolicy("x", 0)


if __name__ == "__main__":
    unittest.main()
