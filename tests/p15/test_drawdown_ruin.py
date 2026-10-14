from __future__ import annotations

import unittest

from packages.risk.drawdown_ruin import (
    DrawdownRuinError,
    DrawdownRuinPolicy,
    DrawdownRuinRequest,
    evaluate_drawdown_ruin,
)


POLICY = DrawdownRuinPolicy(
    policy_version="p15f-test-v1",
    soft_drawdown_bps=1000,
    hard_stop_drawdown_bps=2000,
    max_ruin_probability_ppm=50000,
)


def request(**overrides: object) -> DrawdownRuinRequest:
    values: dict[str, object] = {
        "request_id": "dd-1",
        "upstream_margin_decision_id": "margin-1",
        "upstream_margin_status": "MARGIN_LEVERAGE_ELIGIBLE",
        "peak_equity": "10000",
        "current_equity": "9500",
        "ruin_probability_ppm": 10000,
        "ruin_model_id": "validated-model-v1",
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return DrawdownRuinRequest(**values)  # type: ignore[arg-type]


class DrawdownRuinTests(unittest.TestCase):
    def test_within_limits(self) -> None:
        decision = evaluate_drawdown_ruin(policy=POLICY, request=request())
        self.assertEqual(decision.status, "WITHIN_LIMITS")
        self.assertEqual(decision.drawdown_bps, 500)
        self.assertFalse(decision.execution_authority)

    def test_equity_above_peak_has_zero_drawdown(self) -> None:
        decision = evaluate_drawdown_ruin(
            policy=POLICY,
            request=request(current_equity="11000"),
        )
        self.assertEqual(decision.drawdown_bps, 0)

    def test_soft_drawdown_requires_derisk(self) -> None:
        decision = evaluate_drawdown_ruin(
            policy=POLICY,
            request=request(current_equity="8900"),
        )
        self.assertEqual(decision.status, "DE_RISK_REQUIRED")
        self.assertIn("SOFT_DRAWDOWN_LIMIT_REACHED", decision.reason_codes)

    def test_hard_drawdown_vetoes(self) -> None:
        decision = evaluate_drawdown_ruin(
            policy=POLICY,
            request=request(current_equity="7900"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("HARD_DRAWDOWN_LIMIT_REACHED", decision.reason_codes)

    def test_ruin_probability_breach_vetoes(self) -> None:
        decision = evaluate_drawdown_ruin(
            policy=POLICY,
            request=request(ruin_probability_ppm=50001),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("RUIN_PROBABILITY_LIMIT_EXCEEDED", decision.reason_codes)

    def test_upstream_noneligible_vetoes(self) -> None:
        decision = evaluate_drawdown_ruin(
            policy=POLICY,
            request=request(upstream_margin_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "UPSTREAM_MARGIN_LEVERAGE_NOT_ELIGIBLE",
            decision.reason_codes,
        )

    def test_missing_model_identity_fails_closed(self) -> None:
        with self.assertRaises(DrawdownRuinError):
            request(ruin_model_id="")

    def test_invalid_thresholds_fail_closed(self) -> None:
        with self.assertRaises(DrawdownRuinError):
            DrawdownRuinPolicy("x", 2000, 1000, 1)

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_drawdown_ruin(policy=POLICY, request=request())
        right = evaluate_drawdown_ruin(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
