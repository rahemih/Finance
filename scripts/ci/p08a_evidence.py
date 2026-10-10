from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.technical_intelligence import (
    IndicatorDefinition,
    TechnicalEvidence,
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
    count_independent_confirmations,
    rate_of_change_bps,
    simple_moving_average,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = TechnicalFoundationPolicy.from_path(POLICY_PATH)
    dataset = "a" * 64
    quality = "b" * 64
    bars = tuple(
        TrustedOHLCVBar(
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            open_text=close,
            high_text=str(int(close) + 1),
            low_text=str(int(close) - 1),
            close_text=close,
            volume_text="10",
            event_time_ns=event_time,
            as_of_time_ns=1_000,
            source_dataset_version=dataset,
            quality_evidence_sha256=quality,
        )
        for close, event_time in (("100", 100), ("101", 200), ("103", 300))
    )

    sma = simple_moving_average(bars, lookback_bars=3, policy=policy)
    roc_bps = rate_of_change_bps(bars, lookback_bars=3, policy=policy)

    trend = IndicatorDefinition(
        name="sma",
        version="1.0.0",
        family="TREND",
        independence_group="price-level-trend",
        lookback_bars=3,
        output_unit="PRICE",
        parameters=(("window", "3"),),
    )
    momentum = IndicatorDefinition(
        name="roc",
        version="1.0.0",
        family="MOMENTUM",
        independence_group="return-momentum",
        lookback_bars=3,
        output_unit="BPS",
        parameters=(("window", "3"),),
    )

    evidence = (
        TechnicalEvidence(
            definition_id=trend.definition_id,
            family=trend.family,
            independence_group=trend.independence_group,
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            direction=1,
            strength_bps=6500,
            confidence_bps=8000,
            event_time_ns=300,
            as_of_time_ns=1_000,
            value_text=str(sma),
            invalidation="reference only; P08-B owns trend-model invalidation",
            source_dataset_version=dataset,
            quality_evidence_sha256=quality,
        ),
        TechnicalEvidence(
            definition_id=momentum.definition_id,
            family=momentum.family,
            independence_group=momentum.independence_group,
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            direction=1,
            strength_bps=6000,
            confidence_bps=7800,
            event_time_ns=300,
            as_of_time_ns=1_000,
            value_text=str(roc_bps),
            invalidation="reference only; P08-C owns momentum-model invalidation",
            source_dataset_version=dataset,
            quality_evidence_sha256=quality,
        ),
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08A_TECHNICAL_FOUNDATION_EVIDENCE",
        "task_id": "FIN-P08-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "bar_count": len(bars),
        "sma_3": str(sma),
        "roc_3_bps": roc_bps,
        "definition_ids": [trend.definition_id, momentum.definition_id],
        "evidence_ids": [item.evidence_id for item in evidence],
        "independent_long_confirmations": count_independent_confirmations(evidence, direction=1),
        "direct_trade_output_allowed": policy.direct_trade_output_allowed,
        "production_technical_intelligence_vendor": policy.production_technical_intelligence_vendor,
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
    print(f"P08A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
