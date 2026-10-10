from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.technical_intelligence.breakout_expansion import (
    BreakoutExpansionError,
    BreakoutExpansionModel,
    BreakoutExpansionPolicy,
)
from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
P08F_POLICY = ROOT / "config/technical-intelligence/breakout-expansion-policy.json"
DATASET = "d" * 64
QUALITY = "e" * 64


def policies() -> tuple[TechnicalFoundationPolicy, BreakoutExpansionPolicy]:
    return (
        TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY),
        BreakoutExpansionPolicy.from_path(P08F_POLICY),
    )


def prior_bars(count: int = 20) -> list[TrustedOHLCVBar]:
    return [
        TrustedOHLCVBar(
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            open_text="100",
            high_text="102",
            low_text="98",
            close_text="100",
            volume_text="100",
            event_time_ns=(index + 1) * 100,
            as_of_time_ns=10_000,
            source_dataset_version=DATASET,
            quality_evidence_sha256=QUALITY,
        )
        for index in range(count)
    ]


def current_bar(
    *,
    open_value: int,
    high: int,
    low: int,
    close: int,
    index: int = 20,
) -> TrustedOHLCVBar:
    return TrustedOHLCVBar(
        symbol="CRYPTO:BTC-USD",
        timeframe="1m",
        open_text=str(open_value),
        high_text=str(high),
        low_text=str(low),
        close_text=str(close),
        volume_text="100",
        event_time_ns=(index + 1) * 100,
        as_of_time_ns=10_000,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


def source_with(current: TrustedOHLCVBar) -> tuple[TrustedOHLCVBar, ...]:
    return tuple(prior_bars() + [current])


def model() -> BreakoutExpansionModel:
    foundation, policy = policies()
    return BreakoutExpansionModel(
        foundation_policy=foundation,
        policy=policy,
    )


class P08FPolicyTests(unittest.TestCase):
    def test_policy_has_single_breakout_independence_group(self) -> None:
        foundation, policy = policies()
        self.assertIn("BREAKOUT", foundation.allowed_families)
        self.assertEqual(policy.independence_group, "range-breakout-expansion")
        self.assertEqual(
            policy.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )
        self.assertEqual(policy.required_bars, policy.channel_lookback_bars + 1)
        self.assertFalse(policy.direct_trade_output_allowed)


class P08FEvaluationTests(unittest.TestCase):
    def test_upward_breakout_with_expansion_is_bullish(self) -> None:
        value = model().evaluate(
            source_with(
                current_bar(open_value=100, high=107, low=99, close=105)
            )
        )
        self.assertEqual(value.evidence.direction, 1)
        self.assertEqual(value.evidence.family, "BREAKOUT")
        self.assertEqual(
            value.evidence.independence_group,
            "range-breakout-expansion",
        )
        self.assertTrue(value.expansion_confirmed)
        self.assertGreater(value.expansion_ratio_bps, 12_000)
        self.assertGreater(value.breakout_distance_bps, 0)
        self.assertGreater(value.evidence.strength_bps, 0)

    def test_downward_breakout_with_expansion_is_bearish(self) -> None:
        value = model().evaluate(
            source_with(
                current_bar(open_value=100, high=101, low=93, close=95)
            )
        )
        self.assertEqual(value.evidence.direction, -1)
        self.assertTrue(value.expansion_confirmed)
        self.assertGreater(value.breakout_distance_bps, 0)

    def test_close_inside_prior_channel_is_neutral(self) -> None:
        value = model().evaluate(
            source_with(
                current_bar(open_value=100, high=102, low=98, close=101)
            )
        )
        self.assertEqual(value.evidence.direction, 0)
        self.assertEqual(value.evidence.strength_bps, 0)
        self.assertEqual(value.evidence.confidence_bps, 0)

    def test_current_bar_is_excluded_from_reference_channel(self) -> None:
        value = model().evaluate(
            source_with(
                current_bar(open_value=100, high=150, low=99, close=105)
            )
        )
        self.assertEqual(value.prior_channel_high_text, "102")
        self.assertEqual(value.prior_channel_low_text, "98")
        self.assertEqual(value.evidence.direction, 1)

    def test_expansion_is_bonus_context_not_second_vote(self) -> None:
        expanded = model().evaluate(
            source_with(
                current_bar(open_value=100, high=107, low=99, close=105)
            )
        )
        unexpanded = model().evaluate(
            source_with(
                current_bar(open_value=103, high=105, low=101, close=105)
            )
        )
        self.assertEqual(expanded.evidence.direction, 1)
        self.assertEqual(unexpanded.evidence.direction, 1)
        self.assertTrue(expanded.expansion_confirmed)
        self.assertFalse(unexpanded.expansion_confirmed)
        self.assertGreater(
            expanded.evidence.strength_bps,
            unexpanded.evidence.strength_bps,
        )
        duplicate = replace(
            expanded.evidence,
            strength_bps=max(1, expanded.evidence.strength_bps - 1),
        )
        self.assertEqual(
            count_independent_confirmations(
                (expanded.evidence, duplicate),
                direction=1,
            ),
            1,
        )

    def test_evaluation_and_evidence_are_deterministic(self) -> None:
        source = source_with(
            current_bar(open_value=100, high=107, low=99, close=105)
        )
        first = model().evaluate(source)
        second = model().evaluate(source)
        self.assertEqual(first, second)
        self.assertEqual(first.evidence.evidence_id, second.evidence.evidence_id)

    def test_cross_family_independence_remains_provisional(self) -> None:
        value = model().evaluate(
            source_with(
                current_bar(open_value=100, high=107, low=99, close=105)
            )
        )
        self.assertEqual(
            value.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )

    def test_insufficient_history_fails_closed(self) -> None:
        short = tuple(
            prior_bars(19)
            + [current_bar(open_value=100, high=107, low=99, close=105, index=19)]
        )
        with self.assertRaises(BreakoutExpansionError):
            model().evaluate(short)

    def test_mixed_lineage_fails_closed(self) -> None:
        source = list(
            source_with(
                current_bar(open_value=100, high=107, low=99, close=105)
            )
        )
        mutations = (
            replace(source[-2], symbol="CRYPTO:ETH-USD"),
            replace(source[-2], timeframe="5m"),
            replace(source[-2], source_dataset_version="f" * 64),
            replace(source[-2], quality_evidence_sha256="1" * 64),
        )
        for mutation in mutations:
            changed = list(source)
            changed[-2] = mutation
            with self.assertRaises(BreakoutExpansionError):
                model().evaluate(tuple(changed))

    def test_time_invariants_fail_closed(self) -> None:
        source = list(
            source_with(
                current_bar(open_value=100, high=107, low=99, close=105)
            )
        )
        source[-2] = replace(source[-2], event_time_ns=source[-3].event_time_ns)
        with self.assertRaises(BreakoutExpansionError):
            model().evaluate(tuple(source))

        source = list(
            source_with(
                current_bar(open_value=100, high=107, low=99, close=105)
            )
        )
        source[-2] = replace(
            source[-2],
            as_of_time_ns=source[-1].as_of_time_ns + 1,
        )
        with self.assertRaises(BreakoutExpansionError):
            model().evaluate(tuple(source))

    def test_scores_are_bounded_and_not_trade_fields(self) -> None:
        value = model().evaluate(
            source_with(
                current_bar(open_value=100, high=150, low=99, close=140)
            )
        )
        self.assertLessEqual(value.evidence.strength_bps, 10_000)
        self.assertLessEqual(value.evidence.confidence_bps, 10_000)
        payload = value.evidence.payload()
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
            ROOT / "packages/technical_intelligence/breakout_expansion.py"
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
