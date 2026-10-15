from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.pretrade_firewall.safety_gate import (
    PreTradeSafetyGateError,
    PreTradeSafetyGatePolicy,
    PreTradeStageCertificate,
    certify_g8_pretrade_safe,
)


POLICY_PATH = Path("config/risk/pretrade-safety-gate.json")


def certificates() -> tuple[PreTradeStageCertificate, ...]:
    statuses = (
        ("P16-A", "PRETRADE_A_ELIGIBLE"),
        ("P16-B", "PRETRADE_B_ELIGIBLE"),
        ("P16-C", "PRETRADE_C_ELIGIBLE"),
        ("P16-D", "PRETRADE_D_ELIGIBLE"),
        ("P16-E", "PRETRADE_E_ELIGIBLE"),
        ("P16-F", "PRETRADE_F_ELIGIBLE"),
        ("P16-G", "PRETRADE_G_ELIGIBLE"),
    )
    result: list[PreTradeStageCertificate] = []
    previous: str | None = None
    for index, (workstream, status) in enumerate(statuses):
        decision_id = f"decision-{index + 1}"
        result.append(
            PreTradeStageCertificate(
                workstream=workstream,
                decision_id=decision_id,
                status=status,
                upstream_decision_id=previous,
            )
        )
        previous = decision_id
    return tuple(result)


class PreTradeSafetyGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PreTradeSafetyGatePolicy.from_path(POLICY_PATH)

    def test_complete_chain_certifies_g8(self) -> None:
        gate = certify_g8_pretrade_safe(
            policy=self.policy,
            certificates=certificates(),
        )
        self.assertEqual(gate.gate_name, "G8_PRETRADE_SAFE")
        self.assertEqual(gate.state, "PASS")
        self.assertFalse(gate.p17_started)
        self.assertEqual(
            gate.next_phase_state,
            "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        )
        self.assertFalse(gate.execution_authority)
        self.assertFalse(gate.order_routing_authority)
        self.assertEqual(gate.live_trading, "DISABLED")
        self.assertEqual(gate.auto_trading, "DISABLED")

    def test_missing_workstream_fails_closed(self) -> None:
        with self.assertRaises(PreTradeSafetyGateError):
            certify_g8_pretrade_safe(
                policy=self.policy,
                certificates=certificates()[:-1],
            )

    def test_duplicate_workstream_fails_closed(self) -> None:
        records = list(certificates())
        records[-1] = replace(records[-1], workstream="P16-F")
        with self.assertRaises(PreTradeSafetyGateError):
            certify_g8_pretrade_safe(
                policy=self.policy,
                certificates=records,
            )

    def test_unsupported_workstream_fails_closed(self) -> None:
        records = list(certificates())
        records[-1] = replace(records[-1], workstream="P16-X")
        with self.assertRaises(PreTradeSafetyGateError):
            certify_g8_pretrade_safe(
                policy=self.policy,
                certificates=records,
            )

    def test_each_noncanonical_status_fails_closed(self) -> None:
        for index in range(7):
            records = list(certificates())
            records[index] = replace(records[index], status="VETO")
            with self.subTest(index=index):
                with self.assertRaises(PreTradeSafetyGateError):
                    certify_g8_pretrade_safe(
                        policy=self.policy,
                        certificates=records,
                    )

    def test_waiting_for_approval_fails_closed(self) -> None:
        records = list(certificates())
        records[-1] = replace(records[-1], status="WAITING_FOR_APPROVAL")
        with self.assertRaises(PreTradeSafetyGateError):
            certify_g8_pretrade_safe(
                policy=self.policy,
                certificates=records,
            )

    def test_broken_lineage_fails_closed(self) -> None:
        records = list(certificates())
        records[4] = replace(
            records[4],
            upstream_decision_id="tampered-decision",
        )
        with self.assertRaises(PreTradeSafetyGateError):
            certify_g8_pretrade_safe(
                policy=self.policy,
                certificates=records,
            )

    def test_duplicate_decision_id_fails_closed(self) -> None:
        records = list(certificates())
        records[3] = replace(
            records[3],
            decision_id=records[2].decision_id,
        )
        with self.assertRaises(PreTradeSafetyGateError):
            certify_g8_pretrade_safe(
                policy=self.policy,
                certificates=records,
            )

    def test_authority_escalation_fails_closed(self) -> None:
        for field in ("execution_authority", "g8_authority"):
            records = list(certificates())
            records[2] = replace(records[2], **{field: True})
            with self.subTest(field=field):
                with self.assertRaises(PreTradeSafetyGateError):
                    certify_g8_pretrade_safe(
                        policy=self.policy,
                        certificates=records,
                    )

    def test_input_order_does_not_change_gate_identity(self) -> None:
        records = certificates()
        left = certify_g8_pretrade_safe(
            policy=self.policy,
            certificates=records,
        )
        right = certify_g8_pretrade_safe(
            policy=self.policy,
            certificates=tuple(reversed(records)),
        )
        self.assertEqual(left.gate_id, right.gate_id)


if __name__ == "__main__":
    unittest.main()
