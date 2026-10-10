from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity.forex_proxy_coverage import (
    ForexProxyCoverageInputs,
    ForexProxyCoveragePolicy,
    assess_forex_proxy_coverage,
)
from packages.order_flow_liquidity.volume_ontology import (
    VolumeObservation,
    VolumeProxyPolicy,
)

ROOT = Path(__file__).resolve().parents[2]
COVERAGE_POLICY_PATH = ROOT / "config/order-flow-liquidity/forex-proxy-coverage-policy.json"
VOLUME_POLICY_PATH = ROOT / "config/order-flow-liquidity/volume-proxy-ontology-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    coverage_policy = ForexProxyCoveragePolicy.from_path(COVERAGE_POLICY_PATH)
    volume_policy = VolumeProxyPolicy.from_path(VOLUME_POLICY_PATH)
    observation = VolumeObservation(
        symbol="FX:EURUSD",
        market_class="FOREX_SPOT",
        volume_kind="ECN_VOLUME_PROXY",
        provider="PROVIDER_X",
        venue="ECN_X",
        value_text="12345",
        event_time_ns=1_000,
        as_of_time_ns=1_100,
        coverage_confidence_bps=8500,
        coverage_scope="ECN_X_ONLY",
        proxy_target="SPOT_FX_MARKET_ACTIVITY",
        source_dataset_version="7" * 64,
        quality_evidence_sha256="8" * 64,
    )
    evidence = ForexProxyCoverageInputs(
        provider_scope_confidence_bps=9000,
        provider_scope_evidence_sha256="9" * 64,
        internal_completeness_confidence_bps=8200,
        internal_completeness_evidence_sha256="a" * 64,
        freshness_confidence_bps=8800,
        freshness_evidence_sha256="b" * 64,
        benchmark_agreement_confidence_bps=7900,
        benchmark_agreement_evidence_sha256="c" * 64,
    )
    assessment = assess_forex_proxy_coverage(
        observation,
        evidence=evidence,
        coverage_policy=coverage_policy,
        volume_policy=volume_policy,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09G_FOREX_PROXY_COVERAGE_EVIDENCE",
        "task_id": "FIN-P09-WG-001",
        "coverage_policy_sha256": hashlib.sha256(COVERAGE_POLICY_PATH.read_bytes()).hexdigest(),
        "volume_policy_sha256": hashlib.sha256(VOLUME_POLICY_PATH.read_bytes()).hexdigest(),
        "assessment_id": assessment.assessment_id,
        "observation_id": assessment.observation_id,
        "volume_kind": assessment.volume_kind,
        "coverage_scope": assessment.coverage_scope,
        "proxy_target": assessment.proxy_target,
        "declared_coverage_confidence_bps": assessment.declared_coverage_confidence_bps,
        "validated_proxy_coverage_confidence_bps": assessment.validated_proxy_coverage_confidence_bps,
        "confidence_semantics": assessment.confidence_semantics,
        "global_market_share_claimed": assessment.global_market_share_claimed,
        "benchmark_agreement_required": coverage_policy.benchmark_agreement_required,
        "confidence_aggregation": coverage_policy.confidence_aggregation,
        "global_market_share_claim_allowed": coverage_policy.global_market_share_claim_allowed,
        "cross_provider_aggregation_allowed": coverage_policy.cross_provider_aggregation_allowed,
        "weighted_confidence_score_allowed": coverage_policy.weighted_confidence_score_allowed,
        "direct_trade_output_allowed": coverage_policy.direct_trade_output_allowed,
        "production_fx_order_flow_vendor": coverage_policy.production_fx_order_flow_vendor,
        "country_assumption": "NONE",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "network_required": False,
        "credentials_required": False
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P09G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
