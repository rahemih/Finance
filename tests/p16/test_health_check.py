from __future__ import annotations

import unittest

from packages.data_quality.quality_slo import SloStatus
from packages.fundamental_intelligence.economic_events import EconomicCalendarEvent
from packages.market_data.recovery import RecoveryState
from packages.market_data.streaming import StreamHealth
from packages.pretrade_firewall.health_check import (
    PreTradeHealthError,
    PreTradeHealthPolicy,
    PreTradeHealthRequest,
    evaluate_pretrade_health,
)


POLICY = PreTradeHealthPolicy(
    policy_version="p16e-test-v1",
    event_block_before_ns=100,
    event_block_after_ns=100,
    max_event_observation_age_ns=500,
)


def event(
    *,
    status: str = "SCHEDULED",
    scheduled: int = 2000,
    observed: int = 1500,
    actual: int | None = None,
) -> EconomicCalendarEvent:
    return EconomicCalendarEvent(
        source_id="official-fixture",
        source_event_id=f"event-{status}-{scheduled}",
        event_name="Fixture Event",
        event_kind="RATE_DECISION",
        jurisdiction="US",
        reference_period="2026-10",
        scheduled_release_time_ns=scheduled,
        release_timezone="UTC",
        status=status,
        observed_at_ns=observed,
        source_dataset_version="a" * 64,
        quality_evidence_sha256="b" * 64,
        actual_release_time_ns=actual,
    )


def request(**overrides: object) -> PreTradeHealthRequest:
    values: dict[str, object] = {
        "request_id": "e-1",
        "upstream_liquidity_decision_id": "d-1",
        "upstream_liquidity_status": "PRETRADE_D_ELIGIBLE",
        "economic_events": (),
        "data_slo_status": SloStatus.HEALTHY,
        "stream_health": StreamHealth.HEALTHY,
        "recovery_state": RecoveryState.ACTIVE,
        "system_state": "NORMAL",
        "as_of_ns": 1600,
    }
    values.update(overrides)
    return PreTradeHealthRequest.build(**values)  # type: ignore[arg-type]


class PreTradeHealthTests(unittest.TestCase):
    def test_all_healthy_is_eligible(self) -> None:
        decision = evaluate_pretrade_health(policy=POLICY, request=request())
        self.assertEqual(decision.status, "PRETRADE_E_ELIGIBLE")
        self.assertFalse(decision.g8_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_pretrade_health(
            policy=POLICY,
            request=request(upstream_liquidity_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_LIQUIDITY_CAPACITY_VETO", decision.reason_codes)

    def test_event_window_blocks(self) -> None:
        decision = evaluate_pretrade_health(
            policy=POLICY,
            request=request(
                economic_events=(event(scheduled=1650, observed=1500),),
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("EVENT_RISK_WINDOW_BLOCKED", decision.reason_codes)
        self.assertEqual(len(decision.blocking_event_ids), 1)

    def test_cancelled_event_does_not_block(self) -> None:
        decision = evaluate_pretrade_health(
            policy=POLICY,
            request=request(
                economic_events=(event(status="CANCELLED", scheduled=1650),),
            ),
        )
        self.assertEqual(decision.status, "PRETRADE_E_ELIGIBLE")

    def test_stale_event_observation_vetoes(self) -> None:
        decision = evaluate_pretrade_health(
            policy=POLICY,
            request=request(
                economic_events=(event(scheduled=3000, observed=1000),),
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("STALE_EVENT_OBSERVATION", decision.reason_codes)

    def test_future_event_observation_vetoes(self) -> None:
        decision = evaluate_pretrade_health(
            policy=POLICY,
            request=request(
                economic_events=(event(scheduled=3000, observed=1700),),
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("FUTURE_EVENT_OBSERVATION", decision.reason_codes)

    def test_nonhealthy_data_states_veto(self) -> None:
        for state in (SloStatus.WARNING, SloStatus.CRITICAL, SloStatus.NO_DATA):
            with self.subTest(state=state):
                decision = evaluate_pretrade_health(
                    policy=POLICY,
                    request=request(data_slo_status=state),
                )
                self.assertEqual(decision.status, "VETO")

    def test_nonhealthy_stream_states_veto(self) -> None:
        for state in (StreamHealth.NEVER_SEEN, StreamHealth.STALE):
            with self.subTest(state=state):
                decision = evaluate_pretrade_health(
                    policy=POLICY,
                    request=request(stream_health=state),
                )
                self.assertEqual(decision.status, "VETO")

    def test_nonactive_recovery_states_veto(self) -> None:
        for state in RecoveryState:
            if state is RecoveryState.ACTIVE:
                continue
            with self.subTest(state=state):
                decision = evaluate_pretrade_health(
                    policy=POLICY,
                    request=request(recovery_state=state),
                )
                self.assertEqual(decision.status, "VETO")

    def test_nonnormal_system_states_veto(self) -> None:
        for state in (
            "DEGRADED",
            "SAFE_MODE",
            "HALTED",
            "EMERGENCY",
            "RECOVERY",
        ):
            with self.subTest(state=state):
                decision = evaluate_pretrade_health(
                    policy=POLICY,
                    request=request(system_state=state),
                )
                self.assertEqual(decision.status, "VETO")

    def test_invalid_system_state_fails_closed(self) -> None:
        with self.assertRaises(PreTradeHealthError):
            request(system_state="UNKNOWN")

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_pretrade_health(policy=POLICY, request=request())
        right = evaluate_pretrade_health(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
