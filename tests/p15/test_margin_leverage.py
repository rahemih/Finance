from __future__ import annotations

import unittest

from packages.risk.margin_leverage import (
    MarginLeverageError,
    MarginLeveragePolicy,
    MarginLeverageRequest,
    evaluate_margin_leverage,
)


def policy(**overrides: int | str) -> MarginLeveragePolicy:
    values: dict[str, int | str] = {
        "policy_version": "p15e-test-v1",
        "max_leverage_milli": 3000,
        "max_margin_utilization_bps": 5000,
    }
    values.update(overrides)
    return MarginLeveragePolicy(**values)  # type: ignore[arg-type]


def request(**overrides: object) -> MarginLeverageRequest:
    values: dict[str, object] = {
        "request_id": "margin-1",
        "upstream_portfolio_decision_id": "portfolio-1",
        "upstream_portfolio_status": "PORTFOLIO_ELIGIBLE",
        "account_equity": "10000",
        "current_gross_notional": "10000",
        "current_margin_used": "1000",
        "candidate_notional": "5000",
        "initial_margin_rate_bps": 2000,
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return MarginLeverageRequest(**values)  # type: ignore[arg-type]


class MarginLeverageTests(unittest.TestCase):
    def test_eligible_metrics_are_deterministic(self) -> None:
        decision = evaluate_margin_leverage(policy=policy(), request=request())
        self.assertEqual(decision.status, "MARGIN_LEVERAGE_ELIGIBLE")
        self.assertEqual(decision.total_gross_notional, "15000")
        self.assertEqual(decision.candidate_initial_margin, "1000")
        self.assertEqual(decision.total_margin_used, "2000")
        self.assertEqual(decision.leverage_milli, 1500)
        self.assertEqual(decision.margin_utilization_bps, 2000)
        self.assertFalse(decision.execution_authority)

    def test_upstream_non_eligible_vetoes(self) -> None:
        decision = evaluate_margin_leverage(
            policy=policy(),
            request=request(upstream_portfolio_status="VETO"),
        )
        self.assertIn("UPSTREAM_PORTFOLIO_NOT_ELIGIBLE", decision.reason_codes)

    def test_leverage_ceiling_vetoes(self) -> None:
        decision = evaluate_margin_leverage(
            policy=policy(max_leverage_milli=1499),
            request=request(),
        )
        self.assertIn("LEVERAGE_LIMIT_EXCEEDED", decision.reason_codes)

    def test_margin_ceiling_vetoes(self) -> None:
        decision = evaluate_margin_leverage(
            policy=policy(max_margin_utilization_bps=1999),
            request=request(),
        )
        self.assertIn("MARGIN_UTILIZATION_LIMIT_EXCEEDED", decision.reason_codes)

    def test_exact_boundaries_are_eligible(self) -> None:
        decision = evaluate_margin_leverage(
            policy=policy(
                max_leverage_milli=1500,
                max_margin_utilization_bps=2000,
            ),
            request=request(),
        )
        self.assertEqual(decision.status, "MARGIN_LEVERAGE_ELIGIBLE")

    def test_conservative_rounding_ceilings(self) -> None:
        decision = evaluate_margin_leverage(
            policy=policy(
                max_leverage_milli=3000,
                max_margin_utilization_bps=5000,
            ),
            request=request(
                account_equity="3",
                current_gross_notional="0",
                current_margin_used="0",
                candidate_notional="1",
                initial_margin_rate_bps=1,
            ),
        )
        self.assertEqual(decision.leverage_milli, 334)
        self.assertEqual(decision.margin_utilization_bps, 1)

    def test_invalid_values_fail_closed(self) -> None:
        with self.assertRaises(MarginLeverageError):
            request(account_equity="0")
        with self.assertRaises(MarginLeverageError):
            request(candidate_notional="0")
        with self.assertRaises(MarginLeverageError):
            request(initial_margin_rate_bps=0)

    def test_identity_is_repeatable(self) -> None:
        left = evaluate_margin_leverage(policy=policy(), request=request())
        right = evaluate_margin_leverage(policy=policy(), request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
