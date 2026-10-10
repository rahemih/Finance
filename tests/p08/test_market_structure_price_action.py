from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
)
from packages.technical_intelligence.market_structure_price_action import (
    MarketStructurePriceActionError,
    MarketStructurePriceActionModel,
    MarketStructurePriceActionPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
P08D_POLICY = ROOT / "config/technical-intelligence/market-structure-price-action-policy.json"
DATASET = "5" * 64
QUALITY = "6" * 64
BULLISH_VALUES = (
    100, 102, 105, 103, 101, 104, 108, 105,
    103, 106, 111, 108, 106, 109, 114, 111,
    109, 113, 117, 114, 112, 116, 120, 117,
    115, 119, 123, 120, 118, 122, 126, 130,
)
BEARISH_VALUES = tuple(400 - value for value in BULLISH_VALUES)


def policies() -> tuple[TechnicalFoundationPolicy, MarketStructurePriceActionPolicy]:
    return (
        TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY),
        MarketStructurePriceActionPolicy.from_path(P08D_POLICY),
    )


def bars(
    values: tuple[int, ...],
    *,
    latest_open: int | None = None,
    latest_high: int | None = None,
    latest_low: int | None = None,
) -> tuple[TrustedOHLCVBar, ...]:
    result: list[TrustedOHLCVBar] = []
    for index, close in enumerate(values):
        is_latest = index == len(values) - 1
        open_value = latest_open if is_latest and latest_open is not None else close
        high_value = latest_high if is_latest and latest_high is not None else max(open_value, close) + 1
        low_value = latest_low if is_latest and latest_low is not None else min(open_value, close) - 1
        result.append(
            TrustedOHLCVBar(
                symbol="CRYPTO:BTC-USD",
                timeframe="1m",
                open_text=str(open_value),
                high_text=str(high_value),
                low_text=str(low_value),
                close_text=str(close),
                volume_text="100",
                event_time_ns=(index + 1) * 100,
                as_of_time_ns=10_000,
                source_dataset_version=DATASET,
                quality_evidence_sha256=QUALITY,
            )
        )
    return tuple(result)


def model() -> MarketStructurePriceActionModel:
    foundation, policy = policies()
    return MarketStructurePriceActionModel(
        foundation_policy=foundation,
        policy=policy,
    )


class P08DPolicyTests(unittest.TestCase):
    def test_policy_keeps_cross_family_independence_provisional(self) -> None:
        foundation, policy = policies()
        self.assertIn("MARKET_STRUCTURE", foundation.allowed_families)
        self.assertIn("PRICE_ACTION", foundation.allowed_families)
        self.assertEqual(policy.structure_independence_group, "swing-structure")
        self.assertEqual(policy.price_action_independence_group, "candle-price-action")
        self.assertEqual(
            policy.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )
        self.assertFalse(policy.direct_trade_output_allowed)


class P08DEvaluationTests(unittest.TestCase):
    def test_higher_high_higher_low_structure_is_bullish(self) -> None:
        value = model().evaluate(bars(BULLISH_VALUES))
        self.assertEqual(value.structure_evidence.direction, 1)
        self.assertEqual(value.structure_evidence.family, "MARKET_STRUCTURE")
        self.assertEqual(value.structure_evidence.independence_group, "swing-structure")
        self.assertEqual(value.structure_break_direction, 1)
        self.assertIsNotNone(value.previous_swing_high)
        self.assertIsNotNone(value.latest_swing_high)
        self.assertIsNotNone(value.previous_swing_low)
        self.assertIsNotNone(value.latest_swing_low)
        self.assertGreater(value.structure_evidence.strength_bps, 0)

    def test_lower_high_lower_low_structure_is_bearish(self) -> None:
        value = model().evaluate(bars(BEARISH_VALUES))
        self.assertEqual(value.structure_evidence.direction, -1)
        self.assertEqual(value.structure_break_direction, -1)
        self.assertGreater(value.structure_evidence.strength_bps, 0)

    def test_flat_structure_is_neutral_without_inventing_swings(self) -> None:
        value = model().evaluate(bars(tuple(100 for _ in range(32))))
        self.assertEqual(value.structure_evidence.direction, 0)
        self.assertEqual(value.structure_evidence.strength_bps, 0)
        self.assertIsNone(value.latest_swing_high)
        self.assertIsNone(value.latest_swing_low)

    def test_bullish_bearish_and_weak_price_action(self) -> None:
        flat = tuple(100 for _ in range(31))
        bullish = model().evaluate(
            bars(flat + (109,), latest_open=100, latest_high=110, latest_low=99)
        )
        bearish = model().evaluate(
            bars(flat + (100,), latest_open=109, latest_high=110, latest_low=99)
        )
        neutral = model().evaluate(
            bars(flat + (100,), latest_open=100, latest_high=110, latest_low=90)
        )
        self.assertEqual(bullish.price_action_evidence.direction, 1)
        self.assertEqual(bearish.price_action_evidence.direction, -1)
        self.assertEqual(neutral.price_action_evidence.direction, 0)
        self.assertGreater(bullish.body_to_range_bps, 6000)
        self.assertGreater(bearish.body_to_range_bps, 6000)

    def test_right_edge_extrema_are_not_unconfirmed_swings(self) -> None:
        value = model().evaluate(bars(BULLISH_VALUES))
        _, policy = policies()
        self.assertIsNotNone(value.latest_swing_high)
        self.assertIsNotNone(value.latest_swing_low)
        assert value.latest_swing_high is not None
        assert value.latest_swing_low is not None
        last_confirmable = len(BULLISH_VALUES) - policy.swing_right_bars - 1
        self.assertLessEqual(value.latest_swing_high.index, last_confirmable)
        self.assertLessEqual(value.latest_swing_low.index, last_confirmable)

    def test_evaluation_and_evidence_are_deterministic(self) -> None:
        source = bars(BULLISH_VALUES)
        first = model().evaluate(source)
        second = model().evaluate(source)
        self.assertEqual(first, second)
        self.assertEqual(
            first.structure_evidence.evidence_id,
            second.structure_evidence.evidence_id,
        )
        self.assertEqual(
            first.price_action_evidence.evidence_id,
            second.price_action_evidence.evidence_id,
        )

    def test_correlated_transforms_within_each_family_count_once(self) -> None:
        value = model().evaluate(
            bars(
                BULLISH_VALUES[:-1] + (130,),
                latest_open=120,
                latest_high=131,
                latest_low=119,
            )
        )
        structure_duplicate = replace(
            value.structure_evidence,
            strength_bps=max(1, value.structure_evidence.strength_bps - 1),
        )
        price_duplicate = replace(
            value.price_action_evidence,
            strength_bps=max(1, value.price_action_evidence.strength_bps - 1),
        )
        self.assertEqual(
            count_independent_confirmations(
                (value.structure_evidence, structure_duplicate),
                direction=1,
            ),
            1,
        )
        self.assertEqual(
            count_independent_confirmations(
                (value.price_action_evidence, price_duplicate),
                direction=1,
            ),
            1,
        )
        self.assertEqual(
            value.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )

    def test_insufficient_history_fails_closed(self) -> None:
        with self.assertRaises(MarketStructurePriceActionError):
            model().evaluate(bars(BULLISH_VALUES[:31]))

    def test_mixed_lineage_fails_closed(self) -> None:
        source = list(bars(BULLISH_VALUES))
        mutations = (
            replace(source[-2], symbol="CRYPTO:ETH-USD"),
            replace(source[-2], timeframe="5m"),
            replace(source[-2], source_dataset_version="7" * 64),
            replace(source[-2], quality_evidence_sha256="8" * 64),
        )
        for mutation in mutations:
            changed = list(source)
            changed[-2] = mutation
            with self.assertRaises(MarketStructurePriceActionError):
                model().evaluate(tuple(changed))

    def test_time_invariants_fail_closed(self) -> None:
        source = list(bars(BULLISH_VALUES))
        source[-2] = replace(source[-2], event_time_ns=source[-3].event_time_ns)
        with self.assertRaises(MarketStructurePriceActionError):
            model().evaluate(tuple(source))
        source = list(bars(BULLISH_VALUES))
        source[-2] = replace(source[-2], as_of_time_ns=source[-1].as_of_time_ns + 1)
        with self.assertRaises(MarketStructurePriceActionError):
            model().evaluate(tuple(source))

    def test_scores_are_bounded_and_not_trade_fields(self) -> None:
        value = model().evaluate(
            bars(
                BULLISH_VALUES,
                latest_open=120,
                latest_high=131,
                latest_low=119,
            )
        )
        for evidence in (value.structure_evidence, value.price_action_evidence):
            self.assertLessEqual(evidence.strength_bps, 10_000)
            self.assertLessEqual(evidence.confidence_bps, 10_000)
            payload = evidence.payload()
            for forbidden in ("trade_probability", "order", "quantity", "leverage", "broker"):
                self.assertNotIn(forbidden, payload)

    def test_core_module_has_no_execution_or_network_clients(self) -> None:
        source = (
            ROOT / "packages/technical_intelligence/market_structure_price_action.py"
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
