from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from packages.order_flow_liquidity.forex_proxy_coverage import (
    ForexProxyCoverageError,
    ForexProxyCoverageInputs,
    ForexProxyCoveragePolicy,
    assert_no_global_share_or_trade_authority_fields,
    assess_forex_proxy_coverage,
)
from packages.order_flow_liquidity.volume_ontology import (
    VolumeObservation,
    VolumeProxyPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
COVERAGE_POLICY_PATH = ROOT / "config/order-flow-liquidity/forex-proxy-coverage-policy.json"
VOLUME_POLICY_PATH = ROOT / "config/order-flow-liquidity/volume-proxy-ontology-policy.json"
DATASET = "7" * 64
QUALITY = "8" * 64
SCOPE_EVIDENCE = "9" * 64
COMPLETENESS_EVIDENCE = "a" * 64
FRESHNESS_EVIDENCE = "b" * 64
BENCHMARK_EVIDENCE = "c" * 64


def coverage_policy() -> ForexProxyCoveragePolicy:
    return ForexProxyCoveragePolicy.from_path(COVERAGE_POLICY_PATH)


def volume_policy() -> VolumeProxyPolicy:
    return VolumeProxyPolicy.from_path(VOLUME_POLICY_PATH)


def observation(
    *,
    market_class: str = "FOREX_SPOT",
    volume_kind: str = "ECN_VOLUME_PROXY",
    coverage_scope: str = "ECN_X_ONLY",
    confidence_bps: int = 8500,
    proxy_target: str = "SPOT_FX_MARKET_ACTIVITY",
) -> VolumeObservation:
    return VolumeObservation(
        symbol="FX:EURUSD",
        market_class=market_class,
        volume_kind=volume_kind,
        provider="PROVIDER_X",
        venue="ECN_X",
        value_text="12345",
        event_time_ns=1_000,
        as_of_time_ns=1_100,
        coverage_confidence_bps=confidence_bps,
        coverage_scope=coverage_scope,
        proxy_target=proxy_target,
        source_dataset_version=DATASET,
        quality_evidence_sha256=QUALITY,
    )


def evidence(
    *,
    scope_bps: int = 9000,
    completeness_bps: int = 8200,
    freshness_bps: int = 8800,
    benchmark_bps: int | None = None,
) -> ForexProxyCoverageInputs:
    return ForexProxyCoverageInputs(
        provider_scope_confidence_bps=scope_bps,
        provider_scope_evidence_sha256=SCOPE_EVIDENCE,
        internal_completeness_confidence_bps=completeness_bps,
        internal_completeness_evidence_sha256=COMPLETENESS_EVIDENCE,
        freshness_confidence_bps=freshness_bps,
        freshness_evidence_sha256=FRESHNESS_EVIDENCE,
        benchmark_agreement_confidence_bps=benchmark_bps,
        benchmark_agreement_evidence_sha256=BENCHMARK_EVIDENCE if benchmark_bps is not None else None,
    )


class ForexCoveragePolicyTests(unittest.TestCase):
    def test_policy_forbids_global_share_and_weighted_score(self) -> None:
        p = coverage_policy()
        self.assertEqual(p.confidence_aggregation, "CONSERVATIVE_MINIMUM")
        self.assertFalse(p.global_market_share_claim_allowed)
        self.assertFalse(p.cross_provider_aggregation_allowed)
        self.assertFalse(p.weighted_confidence_score_allowed)
        self.assertFalse(p.direct_trade_output_allowed)

    def test_benchmark_required_policy_fails_when_missing(self) -> None:
        raw = json.loads(COVERAGE_POLICY_PATH.read_text(encoding="utf-8"))
        raw["benchmark_agreement_required"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            p = ForexProxyCoveragePolicy.from_path(path)
            with self.assertRaises(ForexProxyCoverageError):
                assess_forex_proxy_coverage(
                    observation(),
                    evidence=evidence(),
                    coverage_policy=p,
                    volume_policy=volume_policy(),
                )


class ForexCoverageAssessmentTests(unittest.TestCase):
    def test_conservative_minimum_is_deterministic(self) -> None:
        first = assess_forex_proxy_coverage(
            observation(),
            evidence=evidence(),
            coverage_policy=coverage_policy(),
            volume_policy=volume_policy(),
        )
        second = assess_forex_proxy_coverage(
            observation(),
            evidence=evidence(),
            coverage_policy=coverage_policy(),
            volume_policy=volume_policy(),
        )
        self.assertEqual(first.validated_proxy_coverage_confidence_bps, 8200)
        self.assertEqual(first.assessment_id, second.assessment_id)
        self.assertFalse(first.global_market_share_claimed)
        self.assertEqual(
            first.confidence_semantics,
            "PROXY_SCOPE_CONFIDENCE_NOT_GLOBAL_MARKET_SHARE",
        )

    def test_benchmark_participates_in_minimum_when_present(self) -> None:
        result = assess_forex_proxy_coverage(
            observation(),
            evidence=evidence(benchmark_bps=7600),
            coverage_policy=coverage_policy(),
            volume_policy=volume_policy(),
        )
        self.assertEqual(result.validated_proxy_coverage_confidence_bps, 7600)
        self.assertEqual(result.benchmark_agreement_confidence_bps, 7600)

    def test_component_bounds_and_evidence_digest_fail_closed(self) -> None:
        with self.assertRaises(ForexProxyCoverageError):
            assess_forex_proxy_coverage(
                observation(),
                evidence=evidence(scope_bps=10001),
                coverage_policy=coverage_policy(),
                volume_policy=volume_policy(),
            )
        bad = ForexProxyCoverageInputs(
            provider_scope_confidence_bps=9000,
            provider_scope_evidence_sha256="bad",
            internal_completeness_confidence_bps=8200,
            internal_completeness_evidence_sha256=COMPLETENESS_EVIDENCE,
            freshness_confidence_bps=8800,
            freshness_evidence_sha256=FRESHNESS_EVIDENCE,
        )
        with self.assertRaises(ForexProxyCoverageError):
            assess_forex_proxy_coverage(
                observation(),
                evidence=bad,
                coverage_policy=coverage_policy(),
                volume_policy=volume_policy(),
            )

    def test_non_fx_native_and_global_claims_fail_closed(self) -> None:
        with self.assertRaises(ForexProxyCoverageError):
            assess_forex_proxy_coverage(
                observation(
                    market_class="CRYPTO_SPOT",
                    volume_kind="NATIVE_VENUE_VOLUME",
                    coverage_scope="COINBASE_ONLY",
                    proxy_target="NONE",
                ),
                evidence=evidence(),
                coverage_policy=coverage_policy(),
                volume_policy=volume_policy(),
            )
        with self.assertRaises(ValueError):
            assess_forex_proxy_coverage(
                observation(coverage_scope="GLOBAL_MARKET"),
                evidence=evidence(),
                coverage_policy=coverage_policy(),
                volume_policy=volume_policy(),
            )

    def test_identity_changes_with_evidence(self) -> None:
        first = assess_forex_proxy_coverage(
            observation(),
            evidence=evidence(completeness_bps=8200),
            coverage_policy=coverage_policy(),
            volume_policy=volume_policy(),
        )
        second = assess_forex_proxy_coverage(
            observation(),
            evidence=evidence(completeness_bps=8100),
            coverage_policy=coverage_policy(),
            volume_policy=volume_policy(),
        )
        self.assertNotEqual(first.assessment_id, second.assessment_id)

    def test_no_global_share_trade_authority_or_network_imports(self) -> None:
        assert_no_global_share_or_trade_authority_fields()
        source = (ROOT / "packages/order_flow_liquidity/forex_proxy_coverage.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution", "packages.execution", "requests", "httpx", "websocket", "boto3"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
