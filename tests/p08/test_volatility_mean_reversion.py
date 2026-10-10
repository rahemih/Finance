from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
)
from packages.technical_intelligence.volatility_mean_reversion import (
    VolatilityMeanReversionError,
    VolatilityMeanReversionModel,
    VolatilityMeanReversionPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
P08E_POLICY = ROOT / "config/technical-intelligence/volatility-mean-reversion-policy.json"
DATASET = "9" * 64
QUALITY = "a" * 64


def policies() -> tuple[TechnicalFoundationPolicy, VolatilityMeanReversionPolicy]:
    return (
        TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY),
        VolatilityMeanReversionPolicy.from_path(P08E_POLICY),
    )


def bars(
    closes: tuple[int, ...],
    ranges: tuple[int, ...],
) -> tuple[TrustedOHLCVBar, ...]:
    if len(closes) != len(ranges):
        raise ValueError("closes/ranges length mismatch")
    values: list[TrustedOHLCVBar] = []
    for index, (close, candle_range) in enumerate(zip(closes, ranges, strict=True)):
        half = candle_range // 2
        high = close + half
        low = close - (candle_range - half)
        values.append(
            TrustedOHLCVBar(
                symbol="CRYPTO:BTC-USD",
                timeframe="1m",
                open_text=str(close),
                high_text=str(high),
                low_text=str(low),
                close_text=str(close),
                volume_text="100",
                event_time_ns=(index + 1) * 100,
                as_of_time_ns=10_000,
                source_dataset_version=DATASET,
                quality_evidence_sha256=QUALITY,
            )
        )
    return tuple(values)


def model() -> VolatilityMeanReversionModel:
    foundation, policy = policies()
    return VolatilityMeanReversionModel(
        foundation_policy=foundation,
        policy=policy,
    )


class P08EPolicyTests(unittest.TestCase):
    def test_policy_preserves_non_directional_volatility(self) -> None:
        foundation, policy = policies()
        self.assertIn("VOLATILITY", foundation.allowed_families)
        self.assertIn("MEAN_REVERSION", foundation.allowed_families)
        self.assertEqual(policy.volatility_independence_group, "range-volatility")
        self.assertEqual(
            policy.mean_reversion_independence_group,
            "price-deviation-mean-reversion",
        )
        self.assertEqual(
            policy.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )
        self.assertFalse(policy.direct_trade_output_allowed)


class P08EEvaluationTests(unittest.TestCase):
    def test_volatility_expansion_is_context_neutral(self) -> None:
        source = bars(
            tuple(100 for _ in range(20)),
            tuple([2] * 15 + [20] * 5),
        )
        value = model().evaluate(source)
        self.assertEqual(value.volatility_evidence.direction, 0)
        self.assertGreater(value.volatility_ratio_bps, 10_000)
        self.assertGreater(value.volatility_evidence.strength_bps, 0)

    def test_volatility_compression_is_context_neutral(self) -> None:
        source = bars(
            tuple(100 for _ in range(20)),
            tuple([20] * 15 + [2] * 5),
        )
        value = model().evaluate(source)
        self.assertEqual(value.volatility_evidence.direction, 0)
        self.assertLess(value.volatility_ratio_bps, 10_000)
        self.assertGreater(value.volatility_evidence.strength_bps, 0)

    def test_volatility_never_counts_as_directional_confirmation(self) -> None:
        value = model().evaluate(
            bars(
                tuple(100 for _ in range(20)),
                tuple([2] * 15 + [20] * 5),
            )
        )
        self.assertEqual(
            count_independent_confirmations(
                (value.volatility_evidence,),
                direction=1,
            ),
            0,
        )
        self.assertEqual(
            count_independent_confirmations(
                (value.volatility_evidence,),
                direction=-1,
            ),
            0,
        )

    def test_above_mean_extreme_is_bearish_reversion(self) -> None:
        value = model().evaluate(
            bars(
                tuple([100] * 19 + [130]),
                tuple([2] * 20),
            )
        )
        self.assertEqual(value.mean_reversion_evidence.direction, -1)
        self.assertGreater(value.deviation_mad_bps, 15_000)
        self.assertGreater(value.mean_reversion_evidence.strength_bps, 0)

    def test_below_mean_extreme_is_bullish_reversion(self) -> None:
        value = model().evaluate(
            bars(
                tuple([100] * 19 + [70]),
                tuple([2] * 20),
            )
        )
        self.assertEqual(value.mean_reversion_evidence.direction, 1)
        self.assertLess(value.deviation_mad_bps, -15_000)
        self.assertGreater(value.mean_reversion_evidence.strength_bps, 0)

    def test_flat_prices_are_neutral_reversion(self) -> None:
        value = model().evaluate(
            bars(
                tuple([100] * 20),
                tuple([2] * 20),
            )
        )
        self.assertEqual(value.mean_reversion_evidence.direction, 0)
        self.assertEqual(value.mean_reversion_evidence.strength_bps, 0)
        self.assertEqual(value.deviation_mad_bps, 0)

    def test_evaluation_and_evidence_are_deterministic(self) -> None:
        source = bars(
            tuple([100] * 19 + [130]),
            tuple([2] * 20),
        )
        first = model().evaluate(source)
        second = model().evaluate(source)
        self.assertEqual(first, second)
        self.assertEqual(
            first.volatility_evidence.evidence_id,
            second.volatility_evidence.evidence_id,
        )
        self.assertEqual(
            first.mean_reversion_evidence.evidence_id,
            second.mean_reversion_evidence.evidence_id,
        )

    def test_correlated_mean_reversion_transforms_count_once(self) -> None:
        value = model().evaluate(
            bars(
                tuple([100] * 19 + [70]),
                tuple([2] * 20),
            )
        )
        duplicate = replace(
            value.mean_reversion_evidence,
            strength_bps=max(1, value.mean_reversion_evidence.strength_bps - 1),
        )
        self.assertEqual(
            count_independent_confirmations(
                (value.mean_reversion_evidence, duplicate),
                direction=1,
            ),
            1,
        )

    def test_cross_family_independence_remains_provisional(self) -> None:
        value = model().evaluate(
            bars(
                tuple([100] * 19 + [130]),
                tuple([2] * 15 + [20] * 5),
            )
        )
        self.assertEqual(
            value.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )

    def test_insufficient_history_fails_closed(self) -> None:
        with self.assertRaises(VolatilityMeanReversionError):
            model().evaluate(
                bars(
                    tuple([100] * 19),
                    tuple([2] * 19),
                )
            )

    def test_mixed_lineage_fails_closed(self) -> None:
        source = list(
            bars(
                tuple([100] * 20),
                tuple([2] * 20),
            )
        )
        mutations = (
            replace(source[-2], symbol="CRYPTO:ETH-USD"),
            replace(source[-2], timeframe="5m"),
            replace(source[-2], source_dataset_version="b" * 64),
            replace(source[-2], quality_evidence_sha256="c" * 64),
        )
        for mutation in mutations:
            changed = list(source)
            changed[-2] = mutation
            with self.assertRaises(VolatilityMeanReversionError):
                model().evaluate(tuple(changed))

    def test_time_invariants_fail_closed(self) -> None:
        source = list(
            bars(
                tuple([100] * 20),
                tuple([2] * 20),
            )
        )
        source[-2] = replace(source[-2], event_time_ns=source[-3].event_time_ns)
        with self.assertRaises(VolatilityMeanReversionError):
            model().evaluate(tuple(source))

        source = list(
            bars(
                tuple([100] * 20),
                tuple([2] * 20),
            )
        )
        source[-2] = replace(
            source[-2],
            as_of_time_ns=source[-1].as_of_time_ns + 1,
        )
        with self.assertRaises(VolatilityMeanReversionError):
            model().evaluate(tuple(source))

    def test_scores_are_bounded_and_not_trade_fields(self) -> None:
        value = model().evaluate(
            bars(
                tuple([100] * 19 + [130]),
                tuple([2] * 15 + [20] * 5),
            )
        )
        for evidence in (
            value.volatility_evidence,
            value.mean_reversion_evidence,
        ):
            self.assertLessEqual(evidence.strength_bps, 10_000)
            self.assertLessEqual(evidence.confidence_bps, 10_000)
            payload = evidence.payload()
            for forbidden in (
                "trade_probability",
                "order",
                "quantity",
                "leverage",
                "broker",
            ):
                self.assertNotIn(forbidden, payload)

    def test_core_module_has_no_execution_or_network_clients(self) -> None:
        source = (
            ROOT / "packages/technical_intelligence/volatility_mean_reversion.py"
        ).read_text(encoding="utf-8").lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "requests",
            "httpx",
            "websocket",
            "boto3",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
