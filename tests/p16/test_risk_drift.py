from __future__ import annotations

from dataclasses import replace
import unittest

from packages.pretrade_firewall.risk_drift import (
    PreTradeRiskDriftError,
    PreTradeRiskDriftRequest,
    evaluate_risk_drift,
)
from packages.risk.margin_leverage import MarginLeverageDecision
from packages.risk.portfolio_correlation import PortfolioExposureDecision
from packages.risk.position_sizing import PositionSizeDecision


SIZE = PositionSizeDecision(
    decision_id="size-1",
    request_id="size-request",
    status="SIZE_CANDIDATE",
    reason_codes=(),
    risk_amount="100",
    per_unit_stop_loss="1",
    raw_quantity="100",
    candidate_quantity="100",
    planned_stop_loss="100",
    risk_budget_bps=100,
)

PORTFOLIO = PortfolioExposureDecision(
    decision_id="portfolio-1",
    request_id="portfolio-request",
    status="PORTFOLIO_ELIGIBLE",
    reason_codes=(),
    gross_exposure_bps=4000,
    abs_net_exposure_bps=2000,
    max_correlated_cluster_gross_bps=3000,
    cluster_members=(("BTC",),),
)

MARGIN = MarginLeverageDecision(
    decision_id="margin-1",
    request_id="margin-request",
    status="MARGIN_LEVERAGE_ELIGIBLE",
    reason_codes=(),
    total_gross_notional="15000",
    candidate_initial_margin="1000",
    total_margin_used="2000",
    leverage_milli=1500,
    margin_utilization_bps=2000,
)


def request(**overrides: object) -> PreTradeRiskDriftRequest:
    values: dict[str, object] = {
        "request_id": "c-1",
        "upstream_idempotency_decision_id": "b-1",
        "upstream_idempotency_status": "PRETRADE_B_ELIGIBLE",
        "approved_size": SIZE,
        "approved_portfolio": PORTFOLIO,
        "approved_margin": MARGIN,
        "final_quantity": "100",
        "final_gross_exposure_bps": 4000,
        "final_abs_net_exposure_bps": 2000,
        "final_max_correlated_cluster_gross_bps": 3000,
        "final_leverage_milli": 1500,
        "final_margin_utilization_bps": 2000,
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return PreTradeRiskDriftRequest(**values)  # type: ignore[arg-type]


class PreTradeRiskDriftTests(unittest.TestCase):
    def test_equal_approved_metrics_are_eligible(self) -> None:
        decision = evaluate_risk_drift(request())
        self.assertEqual(decision.status, "PRETRADE_C_ELIGIBLE")
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_lower_risk_metrics_are_eligible(self) -> None:
        decision = evaluate_risk_drift(
            request(
                final_quantity="90",
                final_gross_exposure_bps=3500,
                final_abs_net_exposure_bps=1500,
                final_max_correlated_cluster_gross_bps=2500,
                final_leverage_milli=1400,
                final_margin_utilization_bps=1800,
            )
        )
        self.assertEqual(decision.status, "PRETRADE_C_ELIGIBLE")

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_risk_drift(
            request(upstream_idempotency_status="VETO")
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_IDEMPOTENCY_VETO", decision.reason_codes)

    def test_noneligible_p15_decisions_veto(self) -> None:
        for field, value, reason in (
            ("approved_size", replace(SIZE, status="VETO"), "P15_SIZE_NOT_ELIGIBLE"),
            (
                "approved_portfolio",
                replace(PORTFOLIO, status="VETO"),
                "P15_PORTFOLIO_NOT_ELIGIBLE",
            ),
            (
                "approved_margin",
                replace(MARGIN, status="VETO"),
                "P15_MARGIN_LEVERAGE_NOT_ELIGIBLE",
            ),
        ):
            with self.subTest(field=field):
                decision = evaluate_risk_drift(request(**{field: value}))
                self.assertEqual(decision.status, "VETO")
                self.assertIn(reason, decision.reason_codes)

    def test_each_risk_increase_vetoes(self) -> None:
        cases = (
            ({"final_quantity": "100.1"}, "FINAL_SIZE_EXCEEDS_APPROVED"),
            (
                {"final_gross_exposure_bps": 4001},
                "FINAL_GROSS_EXPOSURE_EXCEEDS_APPROVED",
            ),
            (
                {"final_abs_net_exposure_bps": 2001},
                "FINAL_NET_EXPOSURE_EXCEEDS_APPROVED",
            ),
            (
                {"final_max_correlated_cluster_gross_bps": 3001},
                "FINAL_CORRELATED_CLUSTER_EXCEEDS_APPROVED",
            ),
            ({"final_leverage_milli": 1501}, "FINAL_LEVERAGE_EXCEEDS_APPROVED"),
            (
                {"final_margin_utilization_bps": 2001},
                "FINAL_MARGIN_UTILIZATION_EXCEEDS_APPROVED",
            ),
        )
        for overrides, reason in cases:
            with self.subTest(reason=reason):
                decision = evaluate_risk_drift(request(**overrides))
                self.assertEqual(decision.status, "VETO")
                self.assertIn(reason, decision.reason_codes)

    def test_invalid_final_quantity_fails_closed(self) -> None:
        with self.assertRaises(PreTradeRiskDriftError):
            request(final_quantity="0")

    def test_negative_metrics_fail_closed(self) -> None:
        with self.assertRaises(PreTradeRiskDriftError):
            request(final_leverage_milli=-1)

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_risk_drift(request())
        right = evaluate_risk_drift(request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
