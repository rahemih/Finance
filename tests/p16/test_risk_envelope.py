from __future__ import annotations

from dataclasses import replace
import unittest

from packages.pretrade_firewall.risk_envelope import (
    PreTradeRiskEnvelopeRequest,
    evaluate_risk_envelope,
)
from packages.risk.defensive_modes import DefensiveModeDecision
from packages.risk.margin_leverage import MarginLeverageDecision
from packages.risk.portfolio_correlation import PortfolioExposureDecision
from packages.risk.position_sizing import PositionSizeDecision


def position() -> PositionSizeDecision:
    return PositionSizeDecision(
        "size-decision",
        "size-request",
        "SIZE_CANDIDATE",
        (),
        "100",
        "10",
        "10",
        "10",
        "100",
        100,
    )


def portfolio() -> PortfolioExposureDecision:
    return PortfolioExposureDecision(
        "portfolio-decision",
        "portfolio-request",
        "PORTFOLIO_ELIGIBLE",
        (),
        2000,
        1000,
        1500,
        (("BTC",),),
    )


def margin() -> MarginLeverageDecision:
    return MarginLeverageDecision(
        "margin-decision",
        "margin-request",
        "MARGIN_LEVERAGE_ELIGIBLE",
        (),
        "15000",
        "1000",
        "2000",
        1500,
        2000,
    )


def defensive(
    *,
    mode: str = "NORMAL",
    scale: int = 10_000,
    allowed: bool = True,
) -> DefensiveModeDecision:
    return DefensiveModeDecision(
        "defensive-decision",
        "defensive-request",
        mode,
        scale,
        (),
        allowed,
    )


def request(**overrides: object) -> PreTradeRiskEnvelopeRequest:
    values: dict[str, object] = {
        "request_id": "c-1",
        "upstream_idempotency_decision_id": "b-decision",
        "upstream_idempotency_status": "PRETRADE_B_ELIGIBLE",
        "p15_validation_id": "p15-validation",
        "p15_validation_marker": "P15_INDEPENDENT_RISK_VALIDATION",
        "p15_validation_status": "PASS",
        "p15_validation_final_mode": "NORMAL",
        "p15_validation_risk_scale_bps": 10_000,
        "position_size": position(),
        "portfolio_exposure": portfolio(),
        "margin_leverage": margin(),
        "defensive_mode": defensive(),
        "proposed_quantity": "10",
        "quantity_step": "1",
        "final_gross_exposure_bps": 2000,
        "final_abs_net_exposure_bps": 1000,
        "final_correlated_cluster_gross_bps": 1500,
        "final_leverage_milli": 1500,
        "final_margin_utilization_bps": 2000,
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return PreTradeRiskEnvelopeRequest(**values)  # type: ignore[arg-type]


class RiskEnvelopeTests(unittest.TestCase):
    def test_approved_envelope_is_eligible(self) -> None:
        decision = evaluate_risk_envelope(request())
        self.assertEqual(decision.status, "PRETRADE_C_ELIGIBLE")
        self.assertEqual(decision.maximum_scaled_quantity, "10")
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_risk_envelope(
            request(upstream_idempotency_status="VETO")
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_IDEMPOTENCY_VETO", decision.reason_codes)

    def test_p15_validation_required(self) -> None:
        decision = evaluate_risk_envelope(
            request(p15_validation_status="FAIL")
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "P15_INDEPENDENT_VALIDATION_NOT_PASS",
            decision.reason_codes,
        )

    def test_defensive_scale_limits_quantity(self) -> None:
        mode = defensive(mode="DEFENSIVE", scale=5000)
        decision = evaluate_risk_envelope(
            request(
                p15_validation_final_mode="DEFENSIVE",
                p15_validation_risk_scale_bps=5000,
                defensive_mode=mode,
                proposed_quantity="6",
            )
        )
        self.assertEqual(decision.status, "VETO")
        self.assertEqual(decision.maximum_scaled_quantity, "5")
        self.assertIn("SIZE_ENVELOPE_EXCEEDED", decision.reason_codes)

    def test_validation_defensive_mismatch_vetoes(self) -> None:
        decision = evaluate_risk_envelope(
            request(
                p15_validation_risk_scale_bps=5000,
                defensive_mode=defensive(),
            )
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "P15_VALIDATION_DEFENSIVE_MISMATCH",
            decision.reason_codes,
        )

    def test_halt_new_risk_vetoes(self) -> None:
        mode = defensive(mode="HALT_NEW_RISK", scale=0, allowed=False)
        decision = evaluate_risk_envelope(
            request(
                p15_validation_final_mode="HALT_NEW_RISK",
                p15_validation_risk_scale_bps=0,
                defensive_mode=mode,
            )
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "P15_DEFENSIVE_MODE_BLOCKS_NEW_RISK",
            decision.reason_codes,
        )

    def test_quantity_step_misalignment_vetoes(self) -> None:
        decision = evaluate_risk_envelope(
            request(proposed_quantity="9.5", quantity_step="1")
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("QUANTITY_STEP_MISALIGNED", decision.reason_codes)

    def test_exposure_breach_vetoes(self) -> None:
        decision = evaluate_risk_envelope(
            request(final_gross_exposure_bps=2001)
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "GROSS_EXPOSURE_ENVELOPE_EXCEEDED",
            decision.reason_codes,
        )

    def test_leverage_breach_vetoes(self) -> None:
        decision = evaluate_risk_envelope(
            request(final_leverage_milli=1501)
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("LEVERAGE_ENVELOPE_EXCEEDED", decision.reason_codes)

    def test_authority_escalation_vetoes(self) -> None:
        tampered = replace(position(), execution_authority=True)
        decision = evaluate_risk_envelope(request(position_size=tampered))
        self.assertEqual(decision.status, "VETO")
        self.assertIn("P15_AUTHORITY_ESCALATION", decision.reason_codes)

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_risk_envelope(request())
        right = evaluate_risk_envelope(request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
