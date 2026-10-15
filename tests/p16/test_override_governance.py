from __future__ import annotations

import unittest

from packages.pretrade_firewall.override_governance import (
    OverrideGovernanceError,
    OverrideGovernanceInput,
    OverrideGovernancePolicy,
    OverrideRequest,
    evaluate_override_governance,
)


POLICY = OverrideGovernancePolicy(
    policy_version="p16g-test-v1",
    max_request_ttl_ns=1000,
)


def override(**overrides: object) -> OverrideRequest:
    values: dict[str, object] = {
        "override_request_id": "override-1",
        "requested_by": "owner-fixture",
        "scope": "PRETRADE_VETO_REVIEW",
        "reason": "fixture review",
        "evidence_sha256": "a" * 64,
        "requested_at_ns": 1000,
        "expires_at_ns": 1500,
    }
    values.update(overrides)
    return OverrideRequest(**values)  # type: ignore[arg-type]


def request(**overrides: object) -> OverrideGovernanceInput:
    values: dict[str, object] = {
        "request_id": "g-1",
        "upstream_daily_loss_decision_id": "f-1",
        "upstream_daily_loss_status": "PRETRADE_F_ELIGIBLE",
        "override_request": None,
        "as_of_ns": 1200,
    }
    values.update(overrides)
    return OverrideGovernanceInput(**values)  # type: ignore[arg-type]


class OverrideGovernanceTests(unittest.TestCase):
    def test_normal_path_is_eligible(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(),
        )
        self.assertEqual(decision.status, "PRETRADE_G_ELIGIBLE")
        self.assertFalse(decision.approval_authority)
        self.assertFalse(decision.reset_authority)
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_veto_without_override_remains_veto(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(upstream_daily_loss_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_DAILY_LOSS_VETO", decision.reason_codes)

    def test_valid_override_request_waits_for_approval(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(override_request=override()),
        )
        self.assertEqual(decision.status, "WAITING_FOR_APPROVAL")
        self.assertIn("EXPLICIT_APPROVAL_REQUIRED", decision.reason_codes)

    def test_override_never_bypasses_upstream_veto(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(
                upstream_daily_loss_status="VETO",
                override_request=override(),
            ),
        )
        self.assertEqual(decision.status, "WAITING_FOR_APPROVAL")
        self.assertIn("UPSTREAM_VETO_REMAINS_BLOCKING", decision.reason_codes)
        self.assertNotEqual(decision.status, "PRETRADE_G_ELIGIBLE")

    def test_future_override_request_fails_closed(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(
                override_request=override(requested_at_ns=1300, expires_at_ns=1400)
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("FUTURE_OVERRIDE_REQUEST", decision.reason_codes)

    def test_expired_override_request_fails_closed(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(
                as_of_ns=1600,
                override_request=override(),
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("EXPIRED_OVERRIDE_REQUEST", decision.reason_codes)

    def test_overlong_override_ttl_fails_closed(self) -> None:
        decision = evaluate_override_governance(
            policy=POLICY,
            request=request(
                override_request=override(expires_at_ns=2501),
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("OVERRIDE_TTL_EXCEEDED", decision.reason_codes)

    def test_invalid_override_fields_fail_closed(self) -> None:
        with self.assertRaises(OverrideGovernanceError):
            override(requested_by="")
        with self.assertRaises(OverrideGovernanceError):
            override(evidence_sha256="bad")
        with self.assertRaises(OverrideGovernanceError):
            override(scope="UNKNOWN")

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_override_governance(policy=POLICY, request=request())
        right = evaluate_override_governance(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
