from __future__ import annotations

import unittest

from packages.risk.counterparty_capital import (
    CapitalSegmentRule,
    CounterpartyCapitalError,
    CounterpartyCapitalPolicy,
    CounterpartyCapitalRequest,
    CounterpartyRule,
    evaluate_counterparty_capital,
)


POLICY = CounterpartyCapitalPolicy.build(
    policy_version="p15g-test-v1",
    counterparties=(CounterpartyRule("venue-a", 4000),),
    segments=(CapitalSegmentRule("core", 7000),),
)


def request(**overrides: object) -> CounterpartyCapitalRequest:
    values: dict[str, object] = {
        "request_id": "cp-1",
        "upstream_drawdown_decision_id": "dd-1",
        "upstream_drawdown_status": "WITHIN_LIMITS",
        "counterparty_id": "venue-a",
        "segment_id": "core",
        "current_total_allocated_bps": 3000,
        "current_counterparty_allocated_bps": 1000,
        "current_segment_allocated_bps": 2000,
        "candidate_allocation_bps": 500,
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return CounterpartyCapitalRequest(**values)  # type: ignore[arg-type]


class CounterpartyCapitalTests(unittest.TestCase):
    def test_eligible_allocation(self) -> None:
        decision = evaluate_counterparty_capital(policy=POLICY, request=request())
        self.assertEqual(decision.status, "CAPITAL_SEGMENT_ELIGIBLE")
        self.assertEqual(decision.total_after_bps, 3500)
        self.assertFalse(decision.venue_routing_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_counterparty_capital(
            policy=POLICY,
            request=request(upstream_drawdown_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_DRAWDOWN_RUIN_VETO", decision.reason_codes)

    def test_derisk_state_is_preserved_for_p15h(self) -> None:
        decision = evaluate_counterparty_capital(
            policy=POLICY,
            request=request(upstream_drawdown_status="DE_RISK_REQUIRED"),
        )
        self.assertEqual(decision.status, "CAPITAL_SEGMENT_ELIGIBLE")
        self.assertEqual(decision.upstream_drawdown_status, "DE_RISK_REQUIRED")

    def test_total_allocation_breach_vetoes(self) -> None:
        decision = evaluate_counterparty_capital(
            policy=POLICY,
            request=request(current_total_allocated_bps=9800),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("TOTAL_CAPITAL_ALLOCATION_EXCEEDED", decision.reason_codes)

    def test_counterparty_limit_breach_vetoes(self) -> None:
        decision = evaluate_counterparty_capital(
            policy=POLICY,
            request=request(current_counterparty_allocated_bps=3800),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "COUNTERPARTY_ALLOCATION_LIMIT_EXCEEDED",
            decision.reason_codes,
        )

    def test_segment_limit_breach_vetoes(self) -> None:
        decision = evaluate_counterparty_capital(
            policy=POLICY,
            request=request(current_segment_allocated_bps=6800),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("CAPITAL_SEGMENT_LIMIT_EXCEEDED", decision.reason_codes)

    def test_missing_rules_fail_closed(self) -> None:
        with self.assertRaises(CounterpartyCapitalError):
            evaluate_counterparty_capital(
                policy=POLICY,
                request=request(counterparty_id="missing"),
            )
        with self.assertRaises(CounterpartyCapitalError):
            evaluate_counterparty_capital(
                policy=POLICY,
                request=request(segment_id="missing"),
            )

    def test_duplicate_rules_fail_closed(self) -> None:
        with self.assertRaises(CounterpartyCapitalError):
            CounterpartyCapitalPolicy.build(
                policy_version="x",
                counterparties=(
                    CounterpartyRule("a", 1000),
                    CounterpartyRule("a", 2000),
                ),
                segments=(CapitalSegmentRule("core", 1000),),
            )

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_counterparty_capital(policy=POLICY, request=request())
        right = evaluate_counterparty_capital(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
