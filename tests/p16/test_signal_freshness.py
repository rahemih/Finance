from __future__ import annotations

from dataclasses import replace
import unittest

from packages.pretrade_firewall.signal_freshness import (
    PreTradeFreshnessError,
    PreTradeFreshnessPolicy,
    PreTradeFreshnessRequest,
    evaluate_signal_freshness,
)
from packages.signal_intelligence.signal_output_contract import AnalyticalSignalOutput


def signal(**overrides: object) -> AnalyticalSignalOutput:
    values: dict[str, object] = {
        "candidate_id": "candidate-1",
        "asset_id": "BTC-USD",
        "strategy_id": "trend",
        "timeframe": "1h",
        "regime_label": "TREND",
        "as_of_time_ns": 1_000,
        "action": "LONG",
        "action_reason_codes": ("ANALYTICAL_CHAIN_CLEAR",),
        "fusion_id": "fusion-1",
        "qualification_id": "qualification-1",
        "tp_stop_prediction_id": "tpstop-1",
        "explanation_id": "explanation-1",
        "challenge_id": "challenge-1",
        "empirical_probability_bps": 6500,
        "overall_uncertainty_bps": 1000,
        "tp_first_probability_bps": 6000,
        "stop_first_probability_bps": 2500,
        "neither_probability_bps": 1500,
        "entry_low_scaled": 100_000,
        "entry_high_scaled": 101_000,
        "invalidation_price_scaled": 98_000,
        "candidate_stop_scaled": 99_000,
        "candidate_target_scaled": 104_000,
        "price_scale": 100,
        "geometry_version_sha256": "a" * 64,
        "evidence_freshness_exclusions": (),
        "reasons_for": ("support",),
        "reasons_against": (),
    }
    values.update(overrides)
    return AnalyticalSignalOutput(**values)  # type: ignore[arg-type]


POLICY = PreTradeFreshnessPolicy(
    policy_version="p16a-test-v1",
    max_signal_age_ns=500,
    max_price_deviation_bps=100,
)


def request(**overrides: object) -> PreTradeFreshnessRequest:
    values: dict[str, object] = {
        "request_id": "pretrade-a-1",
        "signal": signal(),
        "current_price_scaled": 100_500,
        "current_price_scale": 100,
        "as_of_ns": 1_400,
    }
    values.update(overrides)
    return PreTradeFreshnessRequest(**values)  # type: ignore[arg-type]


class SignalFreshnessTests(unittest.TestCase):
    def test_fresh_price_aligned_signal_is_eligible(self) -> None:
        decision = evaluate_signal_freshness(policy=POLICY, request=request())
        self.assertEqual(decision.status, "PRETRADE_A_ELIGIBLE")
        self.assertEqual(decision.signal_age_ns, 400)
        self.assertEqual(decision.price_deviation_bps, 0)
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_wait_and_no_trade_fail_closed(self) -> None:
        for action in ("WAIT", "NO_TRADE"):
            with self.subTest(action=action):
                s = signal(
                    action=action,
                    entry_low_scaled=None,
                    entry_high_scaled=None,
                    invalidation_price_scaled=None,
                    candidate_stop_scaled=None,
                    candidate_target_scaled=None,
                    price_scale=None,
                    geometry_version_sha256=None,
                )
                decision = evaluate_signal_freshness(
                    policy=POLICY,
                    request=request(signal=s),
                )
                self.assertEqual(decision.status, "VETO")
                self.assertIn("NON_DIRECTIONAL_SIGNAL", decision.reason_codes)

    def test_future_dated_signal_fails_closed(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(as_of_ns=999),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("FUTURE_DATED_SIGNAL", decision.reason_codes)

    def test_mismatched_price_scale_fails_closed(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(current_price_scale=1000),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("PRICE_SCALE_MISMATCH", decision.reason_codes)

    def test_signal_age_above_limit_vetoes(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(as_of_ns=1501),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("SIGNAL_AGE_LIMIT_EXCEEDED", decision.reason_codes)

    def test_age_boundary_is_eligible(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(as_of_ns=1500),
        )
        self.assertEqual(decision.status, "PRETRADE_A_ELIGIBLE")

    def test_deviation_above_entry_zone_is_ceiling_bps(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(current_price_scaled=102_011),
        )
        self.assertEqual(decision.price_deviation_bps, 101)
        self.assertEqual(decision.status, "VETO")
        self.assertIn("PRICE_DEVIATION_LIMIT_EXCEEDED", decision.reason_codes)

    def test_deviation_below_entry_zone_uses_lower_boundary(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(current_price_scaled=99_000),
        )
        self.assertEqual(decision.price_deviation_bps, 100)
        self.assertEqual(decision.status, "PRETRADE_A_ELIGIBLE")

    def test_missing_directional_geometry_vetoes(self) -> None:
        decision = evaluate_signal_freshness(
            policy=POLICY,
            request=request(signal=replace(signal(), entry_low_scaled=None)),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("MISSING_DIRECTIONAL_GEOMETRY", decision.reason_codes)

    def test_invalid_policy_fails_closed(self) -> None:
        with self.assertRaises(PreTradeFreshnessError):
            PreTradeFreshnessPolicy("x", -1, 1)
        with self.assertRaises(PreTradeFreshnessError):
            PreTradeFreshnessPolicy("x", 1, 10_001)

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_signal_freshness(policy=POLICY, request=request())
        right = evaluate_signal_freshness(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
