from __future__ import annotations

from pathlib import Path
import unittest

from packages.order_flow_liquidity.derivatives_crowding import (
    CrowdingEvidenceSnapshot,
    DerivativesCrowdingError,
    DerivativesCrowdingPolicy,
    DerivativesObservation,
    assert_no_crowding_trade_authority_fields,
    build_crowding_evidence,
    validate_derivatives_observation,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/derivatives-crowding-policy.json"
DATASET = "5" * 64
QUALITY = "6" * 64


def policy() -> DerivativesCrowdingPolicy:
    return DerivativesCrowdingPolicy.from_path(POLICY_PATH)


def obs(
    kind: str,
    value: str,
    *,
    unit: str,
    sequence: int,
    interval: int | None = None,
    symbol: str = "CRYPTO:BTC-PERP",
    market_class: str = "CRYPTO_DERIVATIVE",
    provider: str = "KAIKO",
    venue: str = "BINANCE",
    coverage_scope: str = "BINANCE_ONLY",
    as_of_time_ns: int = 2_000,
) -> DerivativesObservation:
    return DerivativesObservation(
        symbol=symbol,
        market_class=market_class,
        metric_kind=kind,
        provider=provider,
        venue=venue,
        value_text=value,
        value_unit=unit,
        event_time_ns=1_900 + sequence,
        as_of_time_ns=as_of_time_ns,
        sequence=sequence,
        coverage_scope=coverage_scope,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
        funding_interval_seconds=interval,
    )


def complete_set(
    *,
    provider: str = "KAIKO",
    venue: str = "BINANCE",
    long_value: str = "300000",
    short_value: str = "100000",
) -> tuple[DerivativesObservation, ...]:
    return (
        obs("FUNDING_RATE", "0.0001", unit="DECIMAL_RATE", sequence=1, interval=28800, provider=provider, venue=venue),
        obs("OPEN_INTEREST", "1000000", unit="USD_NOTIONAL", sequence=2, provider=provider, venue=venue),
        obs("LONG_LIQUIDATION", long_value, unit="USD_NOTIONAL", sequence=3, provider=provider, venue=venue),
        obs("SHORT_LIQUIDATION", short_value, unit="USD_NOTIONAL", sequence=4, provider=provider, venue=venue),
    )


class DerivativesPolicyTests(unittest.TestCase):
    def test_policy_forbids_unvalidated_authority(self) -> None:
        p = policy()
        self.assertFalse(p.cross_provider_aggregation_allowed)
        self.assertFalse(p.spot_fx_derivatives_metric_allowed)
        self.assertFalse(p.crowding_score_allowed)
        self.assertFalse(p.liquidation_forecast_allowed)
        self.assertFalse(p.direct_trade_output_allowed)
        self.assertEqual(p.production_derivatives_vendor, "NOT_SELECTED")


class DerivativesObservationTests(unittest.TestCase):
    def test_funding_requires_interval_and_governed_unit(self) -> None:
        valid = validate_derivatives_observation(
            obs("FUNDING_RATE", "0.0001", unit="DECIMAL_RATE", sequence=1, interval=28800),
            policy=policy(),
        )
        self.assertEqual(valid.funding_interval_seconds, 28800)
        with self.assertRaises(DerivativesCrowdingError):
            validate_derivatives_observation(
                obs("FUNDING_RATE", "0.0001", unit="DECIMAL_RATE", sequence=1),
                policy=policy(),
            )
        with self.assertRaises(DerivativesCrowdingError):
            validate_derivatives_observation(
                obs("FUNDING_RATE", "0.0001", unit="PERCENT", sequence=1, interval=28800),
                policy=policy(),
            )

    def test_non_funding_values_are_non_negative_and_interval_free(self) -> None:
        with self.assertRaises(DerivativesCrowdingError):
            validate_derivatives_observation(
                obs("OPEN_INTEREST", "-1", unit="USD_NOTIONAL", sequence=2),
                policy=policy(),
            )
        with self.assertRaises(DerivativesCrowdingError):
            validate_derivatives_observation(
                obs("OPEN_INTEREST", "1", unit="USD_NOTIONAL", sequence=2, interval=28800),
                policy=policy(),
            )

    def test_spot_fx_fails_closed(self) -> None:
        with self.assertRaises(DerivativesCrowdingError):
            validate_derivatives_observation(
                obs(
                    "OPEN_INTEREST",
                    "100",
                    unit="CONTRACTS",
                    sequence=1,
                    symbol="FX:EURUSD",
                    market_class="FOREX_SPOT",
                ),
                policy=policy(),
            )


class CrowdingEvidenceTests(unittest.TestCase):
    def test_complete_vector_is_deterministic_without_score(self) -> None:
        first = build_crowding_evidence(complete_set(), policy=policy())
        second = build_crowding_evidence(complete_set(), policy=policy())
        self.assertIsInstance(first, CrowdingEvidenceSnapshot)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.funding_rate_text, "0.0001")
        self.assertEqual(first.open_interest_text, "1000000")
        self.assertEqual(first.total_liquidation_text, "400000")
        self.assertTrue(first.liquidation_activity_present)
        self.assertEqual(first.liquidation_imbalance_bps, 5000)
        self.assertTrue(first.evidence_complete)

    def test_missing_duplicate_and_mixed_stream_fail_closed(self) -> None:
        items = complete_set()
        with self.assertRaises(DerivativesCrowdingError):
            build_crowding_evidence(items[:-1], policy=policy())
        with self.assertRaises(DerivativesCrowdingError):
            build_crowding_evidence(items + (items[0],), policy=policy())
        mixed = list(items)
        mixed[3] = obs(
            "SHORT_LIQUIDATION",
            "100000",
            unit="USD_NOTIONAL",
            sequence=4,
            provider="OTHER",
        )
        with self.assertRaises(DerivativesCrowdingError):
            build_crowding_evidence(tuple(mixed), policy=policy())

    def test_liquidation_units_must_match(self) -> None:
        items = list(complete_set())
        items[3] = obs(
            "SHORT_LIQUIDATION",
            "100000",
            unit="CONTRACTS",
            sequence=4,
        )
        with self.assertRaises(DerivativesCrowdingError):
            build_crowding_evidence(tuple(items), policy=policy())

    def test_zero_liquidation_has_no_directional_imbalance(self) -> None:
        result = build_crowding_evidence(
            complete_set(long_value="0", short_value="0"),
            policy=policy(),
        )
        self.assertFalse(result.liquidation_activity_present)
        self.assertIsNone(result.liquidation_imbalance_bps)
        self.assertEqual(result.total_liquidation_text, "0")

    def test_identity_changes_with_observation_content(self) -> None:
        first = build_crowding_evidence(complete_set(), policy=policy())
        second_items = list(complete_set())
        second_items[1] = obs("OPEN_INTEREST", "1000001", unit="USD_NOTIONAL", sequence=2)
        second = build_crowding_evidence(tuple(second_items), policy=policy())
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_no_trade_authority_or_network_imports(self) -> None:
        assert_no_crowding_trade_authority_fields()
        source = (ROOT / "packages/order_flow_liquidity/derivatives_crowding.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution", "packages.execution", "requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
