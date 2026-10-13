from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from packages.timing_opportunity.session_calendar import (
    SessionCalendarError,
    SessionCalendarPolicy,
    evaluate_session,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/session-calendar-policy.json"


def ns(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()) * 1_000_000_000


class SessionCalendarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SessionCalendarPolicy.from_path(POLICY_PATH)

    def test_crypto_is_open_24_7_and_weekend_sessions_remain_contextual(self) -> None:
        result = evaluate_session(
            ns("2026-10-17T14:00:00"),
            market_kind="CRYPTO_SPOT",
            policy=self.policy,
        )
        self.assertTrue(result.is_market_open)
        self.assertEqual(result.active_sessions, ("EUROPE", "US"))
        self.assertEqual(result.state, "OVERLAP")

    def test_forex_weekend_and_week_boundary_fail_closed(self) -> None:
        saturday = evaluate_session(
            ns("2026-10-17T14:00:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        sunday_before = evaluate_session(
            ns("2026-10-18T21:59:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        sunday_open = evaluate_session(
            ns("2026-10-18T22:00:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        friday_before = evaluate_session(
            ns("2026-10-16T21:59:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        friday_closed = evaluate_session(
            ns("2026-10-16T22:00:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        self.assertFalse(saturday.is_market_open)
        self.assertFalse(sunday_before.is_market_open)
        self.assertTrue(sunday_open.is_market_open)
        self.assertTrue(friday_before.is_market_open)
        self.assertFalse(friday_closed.is_market_open)

    def test_europe_us_overlap_is_deterministic(self) -> None:
        result = evaluate_session(
            ns("2026-10-12T14:00:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        self.assertEqual(result.weekday_utc, 0)
        self.assertEqual(result.minute_of_day_utc, 840)
        self.assertEqual(result.active_sessions, ("EUROPE", "US"))
        self.assertEqual(result.overlap_count, 2)
        self.assertEqual(result.state, "OVERLAP")

    def test_asia_and_single_session_context(self) -> None:
        result = evaluate_session(
            ns("2026-10-12T03:00:00"),
            market_kind="FOREX_SPOT",
            policy=self.policy,
        )
        self.assertEqual(result.active_sessions, ("ASIA",))
        self.assertEqual(result.state, "SINGLE_SESSION")

    def test_unknown_market_and_negative_timestamp_fail_closed(self) -> None:
        with self.assertRaises(SessionCalendarError):
            evaluate_session(ns("2026-10-12T14:00:00"), market_kind="UNKNOWN", policy=self.policy)
        with self.assertRaises(SessionCalendarError):
            evaluate_session(-1, market_kind="FOREX_SPOT", policy=self.policy)

    def test_policy_preserves_scope_and_safety_boundaries(self) -> None:
        self.assertEqual(self.policy.calendar_timezone, "UTC")
        self.assertFalse(self.policy.holiday_calendar_in_scope)
        self.assertFalse(self.policy.dynamic_dst_adjustment_in_scope)
        self.assertEqual(self.policy.production_calendar_vendor, "NOT_SELECTED")
        self.assertFalse(self.policy.best_trading_time_in_scope)
        self.assertFalse(self.policy.opportunity_ranking_in_scope)
        self.assertFalse(self.policy.signal_probability_in_scope)
        self.assertEqual(self.policy.live_trading, "DISABLED")
        self.assertEqual(self.policy.auto_trading, "DISABLED")

    def test_policy_rejects_trade_or_probability_authority(self) -> None:
        raw = POLICY_PATH.read_text(encoding="utf-8").replace(
            '"signal_probability_in_scope": false',
            '"signal_probability_in_scope": true',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(SessionCalendarError):
                SessionCalendarPolicy.from_path(path)

    def test_identical_inputs_are_deterministic(self) -> None:
        first = evaluate_session(
            ns("2026-10-12T14:00:00"),
            market_kind="CRYPTO_FUTURES",
            policy=self.policy,
        )
        second = evaluate_session(
            ns("2026-10-12T14:00:00"),
            market_kind="CRYPTO_FUTURES",
            policy=self.policy,
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
