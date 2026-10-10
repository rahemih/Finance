from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import unittest

from packages.technical_intelligence import (
    IndicatorDefinition,
    TechnicalEvidence,
    TechnicalFoundationError,
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
    rate_of_change_bps,
    simple_moving_average,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
DATASET = "a" * 64
QUALITY = "b" * 64


def policy() -> TechnicalFoundationPolicy:
    return TechnicalFoundationPolicy.from_path(POLICY)


def bar(
    close: str,
    *,
    event_time_ns: int,
    as_of_time_ns: int = 1_000,
    high: str | None = None,
    low: str | None = None,
    volume: str = "10",
) -> TrustedOHLCVBar:
    value = float(close)
    return TrustedOHLCVBar(
        symbol="CRYPTO:BTC-USD",
        timeframe="1m",
        open_text=close,
        high_text=high if high is not None else str(value + 1),
        low_text=low if low is not None else str(value - 1),
        close_text=close,
        volume_text=volume,
        event_time_ns=event_time_ns,
        as_of_time_ns=as_of_time_ns,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


def definition(*, group: str = "price-level-trend") -> IndicatorDefinition:
    return IndicatorDefinition(
        name="sma",
        version="1.0.0",
        family="TREND",
        independence_group=group,
        lookback_bars=3,
        output_unit="PRICE",
        parameters=(("window", "3"),),
    )


def evidence(
    *,
    group: str,
    direction: int,
    strength_bps: int = 7000,
    confidence_bps: int = 8000,
) -> TechnicalEvidence:
    d = definition(group=group)
    return TechnicalEvidence(
        definition_id=d.definition_id,
        family=d.family,
        independence_group=d.independence_group,
        symbol="CRYPTO:BTC-USD",
        timeframe="1m",
        direction=direction,
        strength_bps=strength_bps,
        confidence_bps=confidence_bps,
        event_time_ns=900,
        as_of_time_ns=1_000,
        value_text="101.25",
        invalidation="close below governed reference threshold",
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


class TechnicalFoundationPolicyTests(unittest.TestCase):
    def test_policy_forbids_direct_trade_output(self) -> None:
        value = policy()
        self.assertFalse(value.direct_trade_output_allowed)
        self.assertTrue(value.point_in_time_required)
        self.assertTrue(value.trusted_data_required)
        self.assertTrue(value.independent_confirmation_requires_unique_group)
        self.assertEqual(value.production_technical_intelligence_vendor, "NOT_SELECTED")


class TrustedBarTests(unittest.TestCase):
    def test_valid_bar_has_deterministic_freshness(self) -> None:
        value = bar("100", event_time_ns=900)
        self.assertEqual(value.freshness_ns, 100)
        self.assertEqual(value.close_text, "100")

    def test_future_event_time_fails_closed(self) -> None:
        with self.assertRaises(TechnicalFoundationError):
            bar("100", event_time_ns=1_001)

    def test_invalid_high_low_and_negative_volume_fail_closed(self) -> None:
        with self.assertRaises(TechnicalFoundationError):
            bar("100", event_time_ns=900, high="99")
        with self.assertRaises(TechnicalFoundationError):
            bar("100", event_time_ns=900, low="101")
        with self.assertRaises(TechnicalFoundationError):
            bar("100", event_time_ns=900, volume="-1")


class IndicatorDefinitionTests(unittest.TestCase):
    def test_identity_is_deterministic_and_content_sensitive(self) -> None:
        first = definition()
        second = definition()
        changed = definition(group="another-independent-property")
        self.assertEqual(first.definition_id, second.definition_id)
        self.assertNotEqual(first.definition_id, changed.definition_id)

    def test_independence_group_is_required(self) -> None:
        with self.assertRaises(TechnicalFoundationError):
            definition(group=" ")


class IndicatorPrimitiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = policy()
        self.bars = (
            bar("100", event_time_ns=100),
            bar("101", event_time_ns=200),
            bar("103", event_time_ns=300),
        )

    def test_sma_is_deterministic(self) -> None:
        first = simple_moving_average(self.bars, lookback_bars=3, policy=self.policy)
        second = simple_moving_average(tuple(reversed(tuple(reversed(self.bars)))), lookback_bars=3, policy=self.policy)
        self.assertEqual(str(first), "101.33333333")
        self.assertEqual(first, second)

    def test_rate_of_change_is_integer_bps(self) -> None:
        self.assertEqual(rate_of_change_bps(self.bars, lookback_bars=3, policy=self.policy), 300)

    def test_insufficient_or_unsorted_window_fails_closed(self) -> None:
        with self.assertRaises(TechnicalFoundationError):
            simple_moving_average(self.bars[:2], lookback_bars=3, policy=self.policy)
        with self.assertRaises(TechnicalFoundationError):
            simple_moving_average(tuple(reversed(self.bars)), lookback_bars=3, policy=self.policy)


class TechnicalEvidenceTests(unittest.TestCase):
    def test_evidence_identity_and_freshness_are_deterministic(self) -> None:
        first = evidence(group="trend-price", direction=1)
        second = evidence(group="trend-price", direction=1)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.freshness_ns, 100)
        self.assertNotIn("trade", first.payload())
        self.assertNotIn("order", first.payload())

    def test_trade_authority_fields_do_not_exist(self) -> None:
        names = {field.name for field in fields(TechnicalEvidence)}
        self.assertTrue({"direction", "strength_bps", "confidence_bps"}.issubset(names))
        for forbidden in ("trade", "order", "quantity", "leverage", "broker", "exchange"):
            self.assertNotIn(forbidden, names)

    def test_strength_confidence_and_direction_are_bounded(self) -> None:
        with self.assertRaises(TechnicalFoundationError):
            evidence(group="x", direction=1, strength_bps=10_001)
        with self.assertRaises(TechnicalFoundationError):
            evidence(group="x", direction=1, confidence_bps=10_001)
        with self.assertRaises(TechnicalFoundationError):
            evidence(group="x", direction=2)

    def test_correlated_transforms_count_once(self) -> None:
        values = (
            evidence(group="trend-price", direction=1),
            evidence(group="trend-price", direction=1, strength_bps=6000),
            evidence(group="momentum-return", direction=1),
            evidence(group="volatility-expansion", direction=-1),
        )
        self.assertEqual(count_independent_confirmations(values, direction=1), 2)
        self.assertEqual(count_independent_confirmations(values, direction=-1), 1)

    def test_core_module_has_no_execution_or_network_clients(self) -> None:
        text = (ROOT / "packages/technical_intelligence/foundation.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "broker",
            "exchange",
            "requests",
            "httpx",
            "websocket",
            "boto3",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
