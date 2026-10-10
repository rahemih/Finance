from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
)
from packages.technical_intelligence.momentum import (
    MomentumFamilyError,
    MomentumFamilyModel,
    MomentumFamilyPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
MOMENTUM_POLICY = ROOT / "config/technical-intelligence/momentum-family-policy.json"
DATASET = "1" * 64
QUALITY = "2" * 64


def policies() -> tuple[TechnicalFoundationPolicy, MomentumFamilyPolicy]:
    return (
        TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY),
        MomentumFamilyPolicy.from_path(MOMENTUM_POLICY),
    )


def bars(*, start: int, step: int, count: int = 24) -> tuple[TrustedOHLCVBar, ...]:
    values: list[TrustedOHLCVBar] = []
    for index in range(count):
        close = start + step * index
        values.append(
            TrustedOHLCVBar(
                symbol="CRYPTO:BTC-USD",
                timeframe="1m",
                open_text=str(close),
                high_text=str(close + 2),
                low_text=str(close - 2),
                close_text=str(close),
                volume_text="100",
                event_time_ns=(index + 1) * 100,
                as_of_time_ns=10_000,
                source_dataset_version=DATASET,
                quality_evidence_sha256=QUALITY,
            )
        )
    return tuple(values)


def model() -> MomentumFamilyModel:
    foundation, momentum = policies()
    return MomentumFamilyModel(foundation_policy=foundation, momentum_policy=momentum)


class MomentumFamilyTests(unittest.TestCase):
    def test_policy_and_safety(self) -> None:
        foundation, momentum = policies()
        self.assertIn("MOMENTUM", foundation.allowed_families)
        self.assertLess(momentum.short_window, momentum.long_window)
        self.assertEqual(momentum.independence_group, "return-momentum")
        self.assertFalse(momentum.direct_trade_output_allowed)

    def test_rising_falling_and_flat_paths(self) -> None:
        bullish = model().evaluate(bars(start=100, step=2))
        bearish = model().evaluate(bars(start=300, step=-2))
        neutral = model().evaluate(bars(start=100, step=0))
        self.assertEqual(bullish.evidence.direction, 1)
        self.assertEqual(bearish.evidence.direction, -1)
        self.assertEqual(neutral.evidence.direction, 0)
        self.assertGreater(bullish.short_roc_bps, 0)
        self.assertGreater(bullish.long_roc_bps, 0)
        self.assertLess(bearish.short_roc_bps, 0)
        self.assertLess(bearish.long_roc_bps, 0)
        self.assertEqual(neutral.evidence.strength_bps, 0)

    def test_evaluation_is_deterministic(self) -> None:
        source = bars(start=100, step=2)
        first = model().evaluate(source)
        second = model().evaluate(source)
        self.assertEqual(first, second)
        self.assertEqual(first.evidence.evidence_id, second.evidence.evidence_id)

    def test_correlated_momentum_counts_once(self) -> None:
        value = model().evaluate(bars(start=100, step=2))
        duplicate = replace(
            value.evidence,
            strength_bps=max(1, value.evidence.strength_bps - 1),
        )
        self.assertEqual(
            count_independent_confirmations((value.evidence, duplicate), direction=1),
            1,
        )

    def test_insufficient_history_fails_closed(self) -> None:
        with self.assertRaises(MomentumFamilyError):
            model().evaluate(bars(start=100, step=2, count=19))

    def test_mixed_lineage_fails_closed(self) -> None:
        source = list(bars(start=100, step=2))
        mutations = (
            replace(source[-2], symbol="CRYPTO:ETH-USD"),
            replace(source[-2], timeframe="5m"),
            replace(source[-2], source_dataset_version="3" * 64),
            replace(source[-2], quality_evidence_sha256="4" * 64),
        )
        for mutation in mutations:
            changed = list(source)
            changed[-2] = mutation
            with self.assertRaises(MomentumFamilyError):
                model().evaluate(tuple(changed))

    def test_time_invariants_fail_closed(self) -> None:
        source = list(bars(start=100, step=2))
        source[-2] = replace(source[-2], event_time_ns=source[-3].event_time_ns)
        with self.assertRaises(MomentumFamilyError):
            model().evaluate(tuple(source))
        source = list(bars(start=100, step=2))
        source[-2] = replace(source[-2], as_of_time_ns=source[-1].as_of_time_ns + 1)
        with self.assertRaises(MomentumFamilyError):
            model().evaluate(tuple(source))

    def test_scores_are_bounded_and_not_trade_probability(self) -> None:
        value = model().evaluate(bars(start=100, step=4))
        self.assertLessEqual(value.evidence.strength_bps, 10_000)
        self.assertLessEqual(value.evidence.confidence_bps, 10_000)
        payload = value.evidence.payload()
        for forbidden in ("trade_probability", "order", "quantity", "leverage"):
            self.assertNotIn(forbidden, payload)

    def test_core_has_no_network_clients(self) -> None:
        source = (ROOT / "packages/technical_intelligence/momentum.py").read_text(
            encoding="utf-8"
        ).lower()
        for forbidden in ("requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
