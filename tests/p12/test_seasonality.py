from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import unittest

from packages.market_memory.knowledge_graph import KnowledgeGraphPolicy
from packages.market_memory.seasonality import (
    SeasonalityError,
    SeasonalityObservation,
    SeasonalityPolicy,
    compute_seasonality,
)


ROOT = Path(__file__).resolve().parents[2]
GRAPH_POLICY_PATH = ROOT / "config/market-memory/knowledge-graph-policy.json"
POLICY_PATH = ROOT / "config/market-memory/seasonality-policy.json"
HASH_A = "a" * 64


def ns(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()) * 1_000_000_000


class SeasonalityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph_policy = KnowledgeGraphPolicy.from_path(GRAPH_POLICY_PATH)
        self.policy = SeasonalityPolicy.from_path(POLICY_PATH)

    def compute(
        self,
        observations: tuple[SeasonalityObservation, ...],
        *,
        bucket_kind: str = "MONTH_OF_YEAR_UTC",
        bucket_value: int = 1,
        regime: str | None = "ALIGNED_BULLISH",
    ):
        return compute_seasonality(
            observations,
            bucket_kind=bucket_kind,
            bucket_value=bucket_value,
            regime_label=regime,
            provenance_sha256=(HASH_A,),
            source_dataset_versions=("seasonality-v1",),
            graph_policy=self.graph_policy,
            policy=self.policy,
        )

    def test_month_bucket_mean_and_dispersion_are_deterministic(self) -> None:
        observations = (
            SeasonalityObservation(ns("2020-01-10T12:00:00"), 100, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-10T12:00:00"), 200, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2022-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        )
        result = self.compute(observations)
        self.assertEqual(result.sample_count, 3)
        self.assertEqual(result.mean_return_bps, 200)
        self.assertEqual(result.dispersion_bps, 66)

    def test_hour_day_and_month_mapping_are_utc(self) -> None:
        mondays = (
            SeasonalityObservation(ns("2020-01-06T14:00:00"), 100, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-04T14:00:00"), 101, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2022-01-03T14:00:00"), 102, "ALIGNED_BULLISH"),
        )
        self.assertEqual(
            self.compute(mondays, bucket_kind="HOUR_OF_DAY_UTC", bucket_value=14).sample_count,
            3,
        )
        self.assertEqual(
            self.compute(mondays, bucket_kind="DAY_OF_WEEK_UTC", bucket_value=0, regime=None).sample_count,
            3,
        )

    def test_invalid_bucket_value_fails_closed(self) -> None:
        observations = tuple(
            SeasonalityObservation(ns(f"202{year}-01-10T12:00:00"), 100, "ALIGNED_BULLISH")
            for year in range(3)
        )
        with self.assertRaises(SeasonalityError):
            self.compute(observations, bucket_kind="MONTH_OF_YEAR_UTC", bucket_value=13)

    def test_duplicate_timestamp_fails_closed(self) -> None:
        stamp = ns("2020-01-10T12:00:00")
        observations = (
            SeasonalityObservation(stamp, 100, "ALIGNED_BULLISH"),
            SeasonalityObservation(stamp, 200, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        )
        with self.assertRaises(SeasonalityError):
            self.compute(observations)

    def test_minimum_sample_and_regime_filter_fail_closed(self) -> None:
        observations = (
            SeasonalityObservation(ns("2020-01-10T12:00:00"), 100, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-10T12:00:00"), 200, "CONFLICT"),
            SeasonalityObservation(ns("2022-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        )
        with self.assertRaises(SeasonalityError):
            self.compute(observations)

    def test_input_order_does_not_change_result(self) -> None:
        observations = (
            SeasonalityObservation(ns("2020-01-10T12:00:00"), -100, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-10T12:00:00"), 200, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2022-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        )
        self.assertEqual(self.compute(observations), self.compute(tuple(reversed(observations))))

    def test_out_of_bound_return_and_missing_lineage_fail_closed(self) -> None:
        observations = (
            SeasonalityObservation(ns("2020-01-10T12:00:00"), 10001, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-10T12:00:00"), 200, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2022-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        )
        with self.assertRaises(SeasonalityError):
            self.compute(observations)

        valid = (
            SeasonalityObservation(ns("2020-01-10T12:00:00"), 100, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2021-01-10T12:00:00"), 200, "ALIGNED_BULLISH"),
            SeasonalityObservation(ns("2022-01-10T12:00:00"), 300, "ALIGNED_BULLISH"),
        )
        with self.assertRaises(SeasonalityError):
            compute_seasonality(
                valid,
                bucket_kind="MONTH_OF_YEAR_UTC",
                bucket_value=1,
                regime_label="ALIGNED_BULLISH",
                provenance_sha256=(),
                source_dataset_versions=("seasonality-v1",),
                graph_policy=self.graph_policy,
                policy=self.policy,
            )

    def test_session_calendar_causality_probability_and_trade_authority_are_absent(self) -> None:
        self.assertFalse(self.policy.session_calendar_in_scope)
        self.assertFalse(self.policy.seasonality_is_causation)
        self.assertFalse(self.policy.seasonality_is_probability)
        source = (ROOT / "packages/market_memory/seasonality.py").read_text(encoding="utf-8").lower()
        for forbidden in ("exchange_session", "best_trading_time", "trade_action", "risk_approval", "execution_authority"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
