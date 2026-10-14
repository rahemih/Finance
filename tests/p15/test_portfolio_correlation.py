from __future__ import annotations

import unittest

from packages.risk.portfolio_correlation import (
    CorrelationPair,
    ExposureLeg,
    PortfolioCorrelationError,
    PortfolioExposurePolicy,
    PortfolioExposureRequest,
    evaluate_portfolio_exposure,
)


def policy(**overrides: int | str) -> PortfolioExposurePolicy:
    values: dict[str, int | str] = {
        "policy_version": "p15d-test-v1",
        "max_gross_exposure_bps": 7000,
        "max_abs_net_exposure_bps": 5000,
        "correlation_threshold_milli": 700,
        "max_correlated_cluster_gross_bps": 5000,
    }
    values.update(overrides)
    return PortfolioExposurePolicy(**values)  # type: ignore[arg-type]


def request(**overrides: object) -> PortfolioExposureRequest:
    values: dict[str, object] = {
        "request_id": "portfolio-1",
        "upstream_limit_decision_id": "limits-1",
        "upstream_limit_status": "LIMITS_ELIGIBLE",
        "candidate_asset_id": "ETH",
        "candidate_signed_exposure_bps": 1000,
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return PortfolioExposureRequest(**values)  # type: ignore[arg-type]


def existing() -> tuple[ExposureLeg, ...]:
    return (
        ExposureLeg("BTC", 2000),
        ExposureLeg("XAUUSD", -1000),
    )


def correlations() -> tuple[CorrelationPair, ...]:
    return (
        CorrelationPair("BTC", "ETH", 800),
        CorrelationPair("BTC", "XAUUSD", 100),
        CorrelationPair("ETH", "XAUUSD", 200),
    )


class PortfolioCorrelationTests(unittest.TestCase):
    def test_eligible_portfolio_is_deterministic(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(),
            request=request(),
            existing=existing(),
            correlations=correlations(),
        )
        self.assertEqual(decision.status, "PORTFOLIO_ELIGIBLE")
        self.assertEqual(decision.gross_exposure_bps, 4000)
        self.assertEqual(decision.abs_net_exposure_bps, 2000)
        self.assertEqual(decision.max_correlated_cluster_gross_bps, 3000)
        self.assertFalse(decision.leverage_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_non_eligible_vetoes(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(),
            request=request(upstream_limit_status="VETO"),
            existing=existing(),
            correlations=correlations(),
        )
        self.assertIn("UPSTREAM_LIMITS_NOT_ELIGIBLE", decision.reason_codes)

    def test_missing_correlation_vetoes(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(),
            request=request(),
            existing=existing(),
            correlations=(CorrelationPair("BTC", "ETH", 800),),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertTrue(
            any(code.startswith("MISSING_CORRELATION:") for code in decision.reason_codes)
        )

    def test_duplicate_correlation_pair_fails_closed(self) -> None:
        with self.assertRaises(PortfolioCorrelationError):
            evaluate_portfolio_exposure(
                policy=policy(),
                request=request(),
                existing=existing(),
                correlations=correlations()
                + (CorrelationPair("ETH", "BTC", 800),),
            )

    def test_gross_limit_vetoes(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(max_gross_exposure_bps=3999),
            request=request(),
            existing=existing(),
            correlations=correlations(),
        )
        self.assertIn("GROSS_EXPOSURE_LIMIT_EXCEEDED", decision.reason_codes)

    def test_net_limit_vetoes(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(max_abs_net_exposure_bps=1999),
            request=request(),
            existing=existing(),
            correlations=correlations(),
        )
        self.assertIn("NET_EXPOSURE_LIMIT_EXCEEDED", decision.reason_codes)

    def test_cluster_limit_vetoes(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(max_correlated_cluster_gross_bps=2999),
            request=request(),
            existing=existing(),
            correlations=correlations(),
        )
        self.assertIn(
            "CORRELATED_CLUSTER_LIMIT_EXCEEDED",
            decision.reason_codes,
        )

    def test_exact_boundaries_are_eligible(self) -> None:
        decision = evaluate_portfolio_exposure(
            policy=policy(
                max_gross_exposure_bps=4000,
                max_abs_net_exposure_bps=2000,
                max_correlated_cluster_gross_bps=3000,
            ),
            request=request(),
            existing=existing(),
            correlations=correlations(),
        )
        self.assertEqual(decision.status, "PORTFOLIO_ELIGIBLE")

    def test_input_order_does_not_change_identity(self) -> None:
        left = evaluate_portfolio_exposure(
            policy=policy(),
            request=request(),
            existing=existing(),
            correlations=correlations(),
        )
        right = evaluate_portfolio_exposure(
            policy=policy(),
            request=request(),
            existing=tuple(reversed(existing())),
            correlations=tuple(reversed(correlations())),
        )
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
