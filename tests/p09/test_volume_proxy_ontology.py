from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import unittest

from packages.order_flow_liquidity import (
    VolumeObservation,
    VolumeOntologyError,
    VolumeProxyPolicy,
    validate_volume_observation,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/order-flow-liquidity/volume-proxy-ontology-policy.json"
DATASET = "a" * 64
QUALITY = "b" * 64


def policy() -> VolumeProxyPolicy:
    return VolumeProxyPolicy.from_path(POLICY)


def observation(
    *,
    market_class: str = "FOREX_SPOT",
    volume_kind: str = "TICK_VOLUME_PROXY",
    coverage_scope: str = "PROVIDER_FEED_ONLY",
    proxy_target: str = "SPOT_FX_MARKET_ACTIVITY",
    confidence_bps: int = 6500,
    value_text: str = "123",
    event_time_ns: int = 900,
    as_of_time_ns: int = 1_000,
) -> VolumeObservation:
    return VolumeObservation(
        symbol="FX:EURUSD",
        market_class=market_class,
        volume_kind=volume_kind,
        provider="DXFEED",
        venue="PROVIDER_AGGREGATE",
        value_text=value_text,
        event_time_ns=event_time_ns,
        as_of_time_ns=as_of_time_ns,
        coverage_confidence_bps=confidence_bps,
        coverage_scope=coverage_scope,
        proxy_target=proxy_target,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


class VolumeProxyPolicyTests(unittest.TestCase):
    def test_policy_forbids_spot_fx_consolidated_claim_and_trade_output(self) -> None:
        value = policy()
        self.assertFalse(value.forex_spot_consolidated_volume_claim_allowed)
        self.assertFalse(value.direct_trade_output_allowed)
        self.assertTrue(value.point_in_time_required)
        self.assertTrue(value.trusted_provenance_required)
        self.assertEqual(value.production_order_flow_vendor, "NOT_SELECTED")
        self.assertTrue(all(item.endswith("_PROXY") for item in value.forex_spot_allowed_volume_kinds))


class VolumeObservationTests(unittest.TestCase):
    def test_spot_fx_tick_proxy_is_valid_and_deterministic(self) -> None:
        first = validate_volume_observation(observation(), policy=policy())
        second = validate_volume_observation(observation(), policy=policy())
        self.assertTrue(first.is_proxy)
        self.assertEqual(first.freshness_ns, 100)
        self.assertEqual(first.observation_id, second.observation_id)

    def test_spot_fx_native_volume_fails_closed(self) -> None:
        with self.assertRaises(VolumeOntologyError):
            validate_volume_observation(
                observation(volume_kind="NATIVE_VENUE_VOLUME", proxy_target="NONE"),
                policy=policy(),
            )

    def test_spot_fx_global_or_consolidated_claim_fails_closed(self) -> None:
        for scope in ("GLOBAL_MARKET", "CONSOLIDATED_MARKET", "TOTAL_MARKET"):
            with self.subTest(scope=scope):
                with self.assertRaises(VolumeOntologyError):
                    validate_volume_observation(observation(coverage_scope=scope), policy=policy())

    def test_spot_fx_proxy_target_is_explicit(self) -> None:
        with self.assertRaises(VolumeOntologyError):
            validate_volume_observation(observation(proxy_target="NONE"), policy=policy())

    def test_native_crypto_volume_is_not_proxy(self) -> None:
        value = VolumeObservation(
            symbol="CRYPTO:BTC-USD",
            market_class="CRYPTO_SPOT",
            volume_kind="NATIVE_VENUE_VOLUME",
            provider="KAIKO",
            venue="COINBASE",
            value_text="42.5",
            event_time_ns=900,
            as_of_time_ns=1_000,
            coverage_confidence_bps=9000,
            coverage_scope="COINBASE_ONLY",
            proxy_target="NONE",
            source_dataset_version=DATASET,
            quality_evidence_sha256=QUALITY,
        )
        checked = validate_volume_observation(value, policy=policy())
        self.assertFalse(checked.is_proxy)

    def test_native_volume_cannot_claim_proxy_target(self) -> None:
        value = VolumeObservation(
            symbol="CRYPTO:BTC-USD",
            market_class="CRYPTO_SPOT",
            volume_kind="NATIVE_VENUE_VOLUME",
            provider="KAIKO",
            venue="COINBASE",
            value_text="42.5",
            event_time_ns=900,
            as_of_time_ns=1_000,
            coverage_confidence_bps=9000,
            coverage_scope="COINBASE_ONLY",
            proxy_target="SPOT_FX_MARKET_ACTIVITY",
            source_dataset_version=DATASET,
            quality_evidence_sha256=QUALITY,
        )
        with self.assertRaises(VolumeOntologyError):
            validate_volume_observation(value, policy=policy())

    def test_future_negative_or_bad_hash_fails_closed(self) -> None:
        with self.assertRaises(VolumeOntologyError):
            observation(event_time_ns=1_001)
        with self.assertRaises(VolumeOntologyError):
            observation(value_text="-1")
        with self.assertRaises(VolumeOntologyError):
            VolumeObservation(
                symbol="FX:EURUSD",
                market_class="FOREX_SPOT",
                volume_kind="TICK_VOLUME_PROXY",
                provider="DXFEED",
                venue="PROVIDER_AGGREGATE",
                value_text="1",
                event_time_ns=900,
                as_of_time_ns=1_000,
                coverage_confidence_bps=5000,
                coverage_scope="PROVIDER_FEED_ONLY",
                proxy_target="SPOT_FX_MARKET_ACTIVITY",
                source_dataset_version="bad",
                quality_evidence_sha256=QUALITY,
            )

    def test_unknown_kind_or_market_fails_closed(self) -> None:
        with self.assertRaises(VolumeOntologyError):
            validate_volume_observation(observation(market_class="UNKNOWN"), policy=policy())
        with self.assertRaises(VolumeOntologyError):
            validate_volume_observation(observation(volume_kind="MAGIC_VOLUME"), policy=policy())

    def test_trade_authority_fields_do_not_exist(self) -> None:
        names = {field.name for field in fields(VolumeObservation)}
        for forbidden in ("trade", "order", "side", "quantity", "leverage", "stop_loss", "take_profit"):
            self.assertNotIn(forbidden, names)

    def test_core_module_has_no_execution_or_network_clients(self) -> None:
        text = (ROOT / "packages/order_flow_liquidity/volume_ontology.py").read_text(encoding="utf-8").lower()
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
