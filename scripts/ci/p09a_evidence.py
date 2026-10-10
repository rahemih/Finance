from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.order_flow_liquidity import (
    VolumeObservation,
    VolumeProxyPolicy,
    validate_volume_observation,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/order-flow-liquidity/volume-proxy-ontology-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = VolumeProxyPolicy.from_path(POLICY_PATH)
    dataset = "a" * 64
    quality = "b" * 64

    fx = validate_volume_observation(
        VolumeObservation(
            symbol="FX:EURUSD",
            market_class="FOREX_SPOT",
            volume_kind="TICK_VOLUME_PROXY",
            provider="DXFEED",
            venue="PROVIDER_AGGREGATE",
            value_text="123",
            event_time_ns=900,
            as_of_time_ns=1_000,
            coverage_confidence_bps=6500,
            coverage_scope="PROVIDER_FEED_ONLY",
            proxy_target="SPOT_FX_MARKET_ACTIVITY",
            source_dataset_version=dataset,
            quality_evidence_sha256=quality,
        ),
        policy=policy,
    )
    crypto = validate_volume_observation(
        VolumeObservation(
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
            source_dataset_version=dataset,
            quality_evidence_sha256=quality,
        ),
        policy=policy,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09A_VOLUME_PROXY_ONTOLOGY_EVIDENCE",
        "task_id": "FIN-P09-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "forex_observation_id": fx.observation_id,
        "forex_volume_kind": fx.volume_kind,
        "forex_is_proxy": fx.is_proxy,
        "forex_coverage_confidence_bps": fx.coverage_confidence_bps,
        "forex_coverage_scope": fx.coverage_scope,
        "crypto_observation_id": crypto.observation_id,
        "crypto_volume_kind": crypto.volume_kind,
        "crypto_is_proxy": crypto.is_proxy,
        "forex_spot_consolidated_volume_claim_allowed": policy.forex_spot_consolidated_volume_claim_allowed,
        "direct_trade_output_allowed": policy.direct_trade_output_allowed,
        "production_order_flow_vendor": policy.production_order_flow_vendor,
        "country_assumption": "NONE",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
        "network_required": False,
        "credentials_required": False,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P09A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
