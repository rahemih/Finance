from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from packages.technical_intelligence.foundation import (
    TechnicalEvidence,
    TechnicalFoundationPolicy,
    count_independent_confirmations,
)
from packages.technical_intelligence.multi_timeframe_regime import (
    MultiTimeframeRegimeError,
    MultiTimeframeRegimeModel,
    MultiTimeframeRegimePolicy,
)
from packages.technical_intelligence.trend import (
    TrendFamilyModel,
    TrendFamilyPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
TREND_POLICY = ROOT / "config/technical-intelligence/trend-family-policy.json"
P08G_POLICY = ROOT / "config/technical-intelligence/multi-timeframe-regime-policy.json"
DATASET = "2" * 64
QUALITY = "3" * 64


def policies() -> tuple[
    TechnicalFoundationPolicy,
    TrendFamilyPolicy,
    MultiTimeframeRegimePolicy,
]:
    return (
        TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY),
        TrendFamilyPolicy.from_path(TREND_POLICY),
        MultiTimeframeRegimePolicy.from_path(P08G_POLICY),
    )


def model() -> MultiTimeframeRegimeModel:
    foundation, _, regime_policy = policies()
    return MultiTimeframeRegimeModel(
        foundation_policy=foundation,
        policy=regime_policy,
    )


def trend_evidence(
    *,
    timeframe: str,
    direction: int,
    strength_bps: int = 5000,
    confidence_bps: int = 6000,
    event_time_ns: int = 9000,
) -> TechnicalEvidence:
    foundation, trend_policy, _ = policies()
    definition = TrendFamilyModel(
        foundation_policy=foundation,
        trend_policy=trend_policy,
    ).definition()
    return TechnicalEvidence(
        definition_id=definition.definition_id,
        family="TREND",
        independence_group=trend_policy.independence_group,
        symbol="CRYPTO:BTC-USD",
        timeframe=timeframe,
        direction=direction,
        strength_bps=strength_bps if direction != 0 else 0,
        confidence_bps=confidence_bps if direction != 0 else 0,
        event_time_ns=event_time_ns,
        as_of_time_ns=10_000,
        value_text=str(direction * strength_bps if direction != 0 else 0),
        invalidation="trend test evidence invalidation",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


class P08GPolicyTests(unittest.TestCase):
    def test_policy_preserves_non_independent_timeframe_rule(self) -> None:
        foundation, _, policy = policies()
        self.assertIn("TREND", foundation.allowed_families)
        self.assertIn("REGIME", foundation.allowed_families)
        self.assertEqual(
            policy.cross_timeframe_independence_status,
            "RELATED_NOT_INDEPENDENT",
        )
        self.assertEqual(
            policy.cross_family_independence_status,
            "PROVISIONAL_PENDING_P08_H",
        )
        self.assertFalse(policy.direct_trade_output_allowed)


class P08GModelTests(unittest.TestCase):
    def test_aligned_bullish_emits_one_regime_evidence(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(timeframe="15m", direction=1, strength_bps=4000),
                trend_evidence(timeframe="1h", direction=1, strength_bps=6000),
                trend_evidence(timeframe="4h", direction=1, strength_bps=8000),
            )
        )
        self.assertEqual(value.classification, "ALIGNED_BULLISH")
        self.assertEqual(value.evidence.family, "REGIME")
        self.assertEqual(value.evidence.direction, 1)
        self.assertEqual(value.evidence.strength_bps, 6000)
        self.assertEqual(value.evidence.confidence_bps, 6000)
        self.assertEqual(
            value.cross_timeframe_independence_status,
            "RELATED_NOT_INDEPENDENT",
        )

    def test_aligned_bearish_emits_one_bearish_regime(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(timeframe="15m", direction=-1),
                trend_evidence(timeframe="1h", direction=-1),
                trend_evidence(timeframe="4h", direction=-1),
            )
        )
        self.assertEqual(value.classification, "ALIGNED_BEARISH")
        self.assertEqual(value.evidence.direction, -1)

    def test_directional_plus_neutral_is_transition(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(timeframe="15m", direction=1),
                trend_evidence(timeframe="1h", direction=0),
                trend_evidence(timeframe="4h", direction=1),
            )
        )
        self.assertEqual(value.classification, "TRANSITION")
        self.assertEqual(value.evidence.direction, 0)
        self.assertEqual(value.evidence.strength_bps, 0)
        self.assertEqual(value.evidence.confidence_bps, 0)

    def test_opposing_directions_are_conflict(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(timeframe="15m", direction=1),
                trend_evidence(timeframe="1h", direction=-1),
                trend_evidence(timeframe="4h", direction=0),
            )
        )
        self.assertEqual(value.classification, "CONFLICT")
        self.assertEqual(value.evidence.direction, 0)

    def test_all_neutral_is_neutral(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(timeframe="15m", direction=0),
                trend_evidence(timeframe="1h", direction=0),
            )
        )
        self.assertEqual(value.classification, "NEUTRAL")
        self.assertEqual(value.evidence.direction, 0)

    def test_input_order_does_not_change_output_identity(self) -> None:
        source = (
            trend_evidence(timeframe="15m", direction=1, event_time_ns=8500),
            trend_evidence(timeframe="1h", direction=1, event_time_ns=8000),
            trend_evidence(timeframe="4h", direction=1, event_time_ns=7000),
        )
        first = model().evaluate(source)
        second = model().evaluate(tuple(reversed(source)))
        self.assertEqual(first, second)
        self.assertEqual(first.evidence.evidence_id, second.evidence.evidence_id)

    def test_duplicate_timeframe_fails_closed(self) -> None:
        with self.assertRaises(MultiTimeframeRegimeError):
            model().evaluate(
                (
                    trend_evidence(timeframe="1h", direction=1),
                    trend_evidence(timeframe="1h", direction=1),
                )
            )

    def test_insufficient_timeframes_fail_closed(self) -> None:
        with self.assertRaises(MultiTimeframeRegimeError):
            model().evaluate((trend_evidence(timeframe="1h", direction=1),))

    def test_non_trend_input_fails_closed(self) -> None:
        base = trend_evidence(timeframe="15m", direction=1)
        with self.assertRaises(MultiTimeframeRegimeError):
            model().evaluate(
                (
                    base,
                    replace(
                        trend_evidence(timeframe="1h", direction=1),
                        family="MOMENTUM",
                    ),
                )
            )

    def test_symbol_method_asof_and_lineage_mismatch_fail_closed(self) -> None:
        base = trend_evidence(timeframe="15m", direction=1)
        candidate = trend_evidence(timeframe="1h", direction=1)
        mutations = (
            replace(candidate, symbol="CRYPTO:ETH-USD"),
            replace(candidate, definition_id="4" * 64),
            replace(candidate, as_of_time_ns=10_001),
            replace(candidate, source_dataset_version="5" * 64),
            replace(candidate, quality_evidence_sha256="6" * 64),
        )
        for mutation in mutations:
            with self.assertRaises(MultiTimeframeRegimeError):
                model().evaluate((base, mutation))

    def test_related_timeframes_do_not_multiply_confirmation_count(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(timeframe="15m", direction=1),
                trend_evidence(timeframe="1h", direction=1),
                trend_evidence(timeframe="4h", direction=1),
            )
        )
        duplicate = replace(
            value.evidence,
            strength_bps=max(1, value.evidence.strength_bps - 1),
        )
        self.assertEqual(
            count_independent_confirmations(
                (value.evidence, duplicate),
                direction=1,
            ),
            1,
        )

    def test_scores_are_bounded_and_no_trade_fields_exist(self) -> None:
        value = model().evaluate(
            (
                trend_evidence(
                    timeframe="15m",
                    direction=1,
                    strength_bps=10_000,
                    confidence_bps=10_000,
                ),
                trend_evidence(
                    timeframe="1h",
                    direction=1,
                    strength_bps=10_000,
                    confidence_bps=10_000,
                ),
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
            ROOT / "packages/technical_intelligence/multi_timeframe_regime.py"
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
