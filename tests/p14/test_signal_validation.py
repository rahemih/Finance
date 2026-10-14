from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from packages.signal_intelligence.signal_output_contract import SignalOutputPolicy, build_signal_output
from packages.signal_intelligence.signal_validation import (
    SignalValidationError,
    SignalValidationPolicy,
    certify_g7_signal_gate,
    validate_signal_output,
)
from tests.p14.test_signal_output_contract import (
    barrier,
    candidate,
    challenge,
    expiry,
    explanation,
    fusion,
    geometry,
    no_trade,
    outcomes,
    qualification,
)


ROOT = Path(__file__).resolve().parents[2]
VALIDATION_POLICY_PATH = ROOT / "config/signal-intelligence/signal-validation-policy.json"
SIGNAL_POLICY_PATH = ROOT / "config/signal-intelligence/signal-output-contract-policy.json"


def case(action: str):
    if action == "LONG":
        f = fusion(direction=1)
        q = qualification()
        o = outcomes(q)
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o, disposition="CLEAR")
        g = geometry()
        nt = no_trade()
        ex = expiry()
        b = barrier(direction=1)
    elif action == "SHORT":
        f = fusion(direction=-1)
        q = qualification()
        o = outcomes(q)
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o, disposition="CLEAR")
        g = geometry(short=True)
        nt = no_trade()
        ex = expiry()
        b = barrier(direction=-1)
    elif action == "WAIT":
        f = fusion(direction=1)
        q = qualification()
        o = outcomes(q)
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o, disposition="CLEAR")
        g = None
        nt = no_trade()
        ex = expiry(state="EXPIRED")
        b = barrier(direction=1)
    elif action == "NO_TRADE":
        f = fusion(direction=1)
        q = qualification()
        o = outcomes(q)
        e = explanation(f, q, o)
        ch = challenge(f, e, q, o, disposition="REJECT")
        g = None
        nt = no_trade(decision="NO_TRADE", reasons=("HIGH_EVENT_RISK",))
        ex = expiry()
        b = barrier(direction=1)
    else:
        raise AssertionError(action)

    signal_policy = SignalOutputPolicy.from_path(SIGNAL_POLICY_PATH)
    c = candidate()
    expected = build_signal_output(
        policy=signal_policy,
        candidate=c,
        no_trade=nt,
        expiry=ex,
        fusion=f,
        uncertainty=q,
        barrier=b,
        outcomes=o,
        explanation=e,
        challenge=ch,
        geometry=g,
    )
    return signal_policy, expected, c, nt, ex, f, q, b, o, e, ch, g


class SignalValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SignalValidationPolicy.from_path(VALIDATION_POLICY_PATH)

    def validate_case(self, action: str):
        signal_policy, expected, c, nt, ex, f, q, b, o, e, ch, g = case(action)
        certificate = validate_signal_output(
            validation_policy=self.policy,
            signal_policy=signal_policy,
            expected=expected,
            candidate=c,
            no_trade=nt,
            expiry=ex,
            fusion=f,
            uncertainty=q,
            barrier=b,
            outcomes=o,
            explanation=e,
            challenge=ch,
            geometry=g,
        )
        self.assertEqual(certificate.action, action)
        self.assertEqual(certificate.validation_state, "VALIDATED")
        self.assertEqual(certificate.signal_id, expected.signal_id)
        self.assertEqual(certificate.replay_signal_id, expected.signal_id)
        return certificate, expected

    def test_exact_replay_validates_all_required_actions(self) -> None:
        for action in ("LONG", "SHORT", "WAIT", "NO_TRADE"):
            with self.subTest(action=action):
                self.validate_case(action)

    def test_signal_id_or_payload_tamper_fails_closed(self) -> None:
        signal_policy, expected, c, nt, ex, f, q, b, o, e, ch, g = case("LONG")
        tampered = replace(expected, empirical_probability_bps=7100)
        with self.assertRaises(SignalValidationError):
            validate_signal_output(
                validation_policy=self.policy,
                signal_policy=signal_policy,
                expected=tampered,
                candidate=c,
                no_trade=nt,
                expiry=ex,
                fusion=f,
                uncertainty=q,
                barrier=b,
                outcomes=o,
                explanation=e,
                challenge=ch,
                geometry=g,
            )

    def test_directional_geometry_missing_fails_closed(self) -> None:
        signal_policy, expected, c, nt, ex, f, q, b, o, e, ch, g = case("LONG")
        tampered = replace(expected, candidate_target_scaled=None)
        with self.assertRaises(SignalValidationError):
            validate_signal_output(
                validation_policy=self.policy,
                signal_policy=signal_policy,
                expected=tampered,
                candidate=c,
                no_trade=nt,
                expiry=ex,
                fusion=f,
                uncertainty=q,
                barrier=b,
                outcomes=o,
                explanation=e,
                challenge=ch,
                geometry=g,
            )

    def test_non_directional_geometry_present_fails_closed(self) -> None:
        signal_policy, expected, c, nt, ex, f, q, b, o, e, ch, g = case("WAIT")
        tampered = replace(expected, entry_low_scaled=99500)
        with self.assertRaises(SignalValidationError):
            validate_signal_output(
                validation_policy=self.policy,
                signal_policy=signal_policy,
                expected=tampered,
                candidate=c,
                no_trade=nt,
                expiry=ex,
                fusion=f,
                uncertainty=q,
                barrier=b,
                outcomes=o,
                explanation=e,
                challenge=ch,
                geometry=g,
            )

    def test_validated_matrix_emits_g7_signal_validated(self) -> None:
        certificates = tuple(self.validate_case(action)[0] for action in ("LONG", "SHORT", "WAIT", "NO_TRADE"))
        gate = certify_g7_signal_gate(policy=self.policy, certificates=certificates)
        self.assertEqual(gate.gate_name, "G7_SIGNAL_VALIDATED")
        self.assertEqual(gate.state, "PASS")
        self.assertEqual(gate.action_coverage, ("LONG", "SHORT", "WAIT", "NO_TRADE"))
        self.assertFalse(gate.payload()["p15_started"])

    def test_missing_action_coverage_fails_closed(self) -> None:
        certificates = tuple(self.validate_case(action)[0] for action in ("LONG", "SHORT", "WAIT"))
        with self.assertRaises(SignalValidationError):
            certify_g7_signal_gate(policy=self.policy, certificates=certificates)

    def test_duplicate_action_certificate_fails_closed(self) -> None:
        long_cert = self.validate_case("LONG")[0]
        short_cert = self.validate_case("SHORT")[0]
        wait_cert = self.validate_case("WAIT")[0]
        with self.assertRaises(SignalValidationError):
            certify_g7_signal_gate(
                policy=self.policy,
                certificates=(long_cert, long_cert, short_cert, wait_cert),
            )

    def test_certificate_and_gate_identity_are_deterministic(self) -> None:
        first = tuple(self.validate_case(action)[0] for action in ("LONG", "SHORT", "WAIT", "NO_TRADE"))
        second = tuple(self.validate_case(action)[0] for action in ("LONG", "SHORT", "WAIT", "NO_TRADE"))
        self.assertEqual(tuple(item.certificate_id for item in first), tuple(item.certificate_id for item in second))
        self.assertEqual(
            certify_g7_signal_gate(policy=self.policy, certificates=first).gate_id,
            certify_g7_signal_gate(policy=self.policy, certificates=second).gate_id,
        )

    def test_policy_rejects_missing_fail_closed_guards(self) -> None:
        original = VALIDATION_POLICY_PATH.read_text(encoding="utf-8")
        variants = (
            original.replace('"exact_payload_match_required": true', '"exact_payload_match_required": false'),
            original.replace('"missing_action_coverage_behavior": "FAIL_CLOSED"', '"missing_action_coverage_behavior": "ALLOW"'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for index, content in enumerate(variants):
                path = Path(tmp) / f"policy-{index}.json"
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(SignalValidationError):
                    SignalValidationPolicy.from_path(path)


if __name__ == "__main__":
    unittest.main()
