from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
)
from packages.technical_intelligence.trend import (
    TrendFamilyError,
    TrendFamilyModel,
    TrendFamilyPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
TREND_POLICY = ROOT / "config/technical-intelligence/trend-family-policy.json"
DATASET = "c" * 64
QUALITY = "d" * 64


def policies() -> tuple[TechnicalFoundationPolicy, TrendFamilyPolicy]:
    return (
        TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY),
        TrendFamilyPolicy.from_path(TREND_POLICY),
    )


def bars(*, start: int, step: int, count: int = 60) -> tuple[TrustedOHLCVBar, ...]:
    result: list[TrustedOHLCVBar] = []
    as_of = 10_000
    for index in range(count):
        close = start + (step * index)
        result.append(
            TrustedOHLCVBar(
                symbol="CRYPTO:BTC-USD",
                timeframe="1m",
                open_text=str(close),
                high_text=str(close + 2),
                low_text=str(close - 2),
                close_text=str(close),
                volume_text="100",
                event_time_ns=(index + 1) * 100,
                as_of_time_ns=as_of,
                source_dataset_version=DATASET,
                quality_evidence_sha256=QUALITY,
            )
        )
    return tuple(result)


def model() -> TrendFamilyModel:
    foundation, trend = policies()
    return TrendFamilyModel(foundation_policy=foundation, trend_policy=trend)


class TrendPolicyTests(unittest.TestCase):
    def test_policy_is_single_family_and_no_trade_authority(self) -> None:
        foundation, trend = policies()
        self.assertIn("TREND", foundation.allowed_families)
        self.assertLess(trend.fast_window, trend.slow_window)
        self.assertEqual(trend.independence_group, "price-path-trend")
        self.assertFalse(trend.direct_trade_output_allowed)
        self.assertLessEqual(trend.required_bars, foundation.max_lookback_bars)


class TrendEvaluationTests(unittest.TestCase):
    def test_rising_path_is_bullish(self) -> None:
        value = model().evaluate(bars(start=100, step=1))
        self.assertEqual(value.evidence.direction, 1)
        self.assertEqual(value.evidence.family, "TREND")
        self.assertEqual(value.evidence.independence_group, "price-path-trend")
        self.assertGreater(value.alignment_bps, 0)
        self.assertGreater(value.slope_bps, 0)
        self.assertGreater(value.price_distance_bps, 0)
        self.assertGreater(value.evidence.strength_bps, 0)
        self.assertGreater(value.evidence.confidence_bps, 0)

    def test_falling_path_is_bearish(self) -> None:
        value = model().evaluate(bars(start=300, step=-1))
        self.assertEqual(value.evidence.direction, -1)
        self.assertLess(value.alignment_bps, 0)
        self.assertLess(value.slope_bps, 0)
        self.assertLess(value.price_distance_bps, 0)
        self.assertGreater(value.evidence.strength_bps, 0)

    def test_flat_path_is_neutral(self) -> None:
        value = model().evaluate(bars(start=100, step=0))
        self.assertEqual(value.evidence.direction, 0)
        self.assertEqual(value.evidence.strength_bps, 0)
        self.assertEqual(value.evidence.confidence_bps, 0)

    def test_evaluation_and_evidence_identity_are_deterministic(self) -> None:
        source = bars(start=100, step=1)
        first = model().evaluate(source)
        second = model().evaluate(source)
        self.assertEqual(first, second)
        self.assertEqual(first.evidence.evidence_id, second.evidence.evidence_id)

    def test_correlated_trend_transforms_count_as_one_confirmation(self) -> None:
        value = model().evaluate(bars(start=100, step=1))
        duplicate = replace(value.evidence, strength_bps=max(1, value.evidence.strength_bps - 1))
        self.assertEqual(
            count_independent_confirmations((value.evidence, duplicate), direction=1),
            1,
        )

    def test_insufficient_history_fails_closed(self) -> None:
        with self.assertRaises(TrendFamilyError):
            model().evaluate(bars(start=100, step=1, count=54))

    def test_mixed_symbol_timeframe_dataset_and_quality_fail_closed(self) -> None:
        source = list(bars(start=100, step=1))
        mutations = (
            replace(source[-2], symbol="CRYPTO:ETH-USD"),
            replace(source[-2], timeframe="5m"),
            replace(source[-2], source_dataset_version="e" * 64),
            replace(source[-2], quality_evidence_sha256="f" * 64),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = list(source)
                changed[-2] = mutation
                with self.assertRaises(TrendFamilyError):
                    model().evaluate(tuple(changed))

    def test_non_monotonic_event_time_fails_closed(self) -> None:
        source = list(bars(start=100, step=1))
        source[-2] = replace(source[-2], event_time_ns=source[-3].event_time_ns)
        with self.assertRaises(TrendFamilyError):
            model().evaluate(tuple(source))

    def test_future_as_of_information_fails_closed(self) -> None:
        source = list(bars(start=100, step=1))
        source[-2] = replace(source[-2], as_of_time_ns=source[-1].as_of_time_ns + 1)
        with self.assertRaises(TrendFamilyError):
            model().evaluate(tuple(source))

    def test_evidence_scores_are_bounded_and_not_trade_fields(self) -> None:
        value = model().evaluate(bars(start=100, step=2))
        self.assertLessEqual(value.evidence.strength_bps, 10_000)
        self.assertLessEqual(value.evidence.confidence_bps, 10_000)
        payload = value.evidence.payload()
        for forbidden in ("trade_probability", "order", "quantity", "leverage", "broker"):
            self.assertNotIn(forbidden, payload)

    def test_core_module_has_no_execution_or_network_clients(self) -> None:
        text = (ROOT / "packages/technical_intelligence/trend.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "requests",
            "httpx",
            "websocket",
            "boto3",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
