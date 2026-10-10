from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
)
from packages.technical_intelligence.volatility_mean_reversion import (
    VolatilityMeanReversionModel,
    VolatilityMeanReversionPolicy,
)

FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
P08E_POLICY = ROOT / "config/technical-intelligence/volatility-mean-reversion-policy.json"


def bars(
    closes: tuple[int, ...],
    ranges: tuple[int, ...],
) -> tuple[TrustedOHLCVBar, ...]:
    result: list[TrustedOHLCVBar] = []
    for index, (close, candle_range) in enumerate(zip(closes, ranges, strict=True)):
        half = candle_range // 2
        high = close + half
        low = close - (candle_range - half)
        result.append(
            TrustedOHLCVBar(
                symbol="CRYPTO:BTC-USD",
                timeframe="1m",
                open_text=str(close),
                high_text=str(high),
                low_text=str(low),
                close_text=str(close),
                volume_text="100",
                event_time_ns=(index + 1) * 100,
                as_of_time_ns=10_000,
                source_dataset_version="9" * 64,
                quality_evidence_sha256="a" * 64,
            )
        )
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    policy = VolatilityMeanReversionPolicy.from_path(P08E_POLICY)
    model = VolatilityMeanReversionModel(
        foundation_policy=foundation,
        policy=policy,
    )

    cases = {
        "volatility_expansion": model.evaluate(
            bars(tuple([100] * 20), tuple([2] * 15 + [20] * 5))
        ),
        "volatility_compression": model.evaluate(
            bars(tuple([100] * 20), tuple([20] * 15 + [2] * 5))
        ),
        "mean_reversion_above": model.evaluate(
            bars(tuple([100] * 19 + [130]), tuple([2] * 20))
        ),
        "mean_reversion_below": model.evaluate(
            bars(tuple([100] * 19 + [70]), tuple([2] * 20))
        ),
        "neutral": model.evaluate(
            bars(tuple([100] * 20), tuple([2] * 20))
        ),
    }

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08E_VOLATILITY_MEAN_REVERSION_EVIDENCE",
        "task_id": "FIN-P08-WE-001",
        "foundation_policy_sha256": hashlib.sha256(
            FOUNDATION_POLICY.read_bytes()
        ).hexdigest(),
        "p08e_policy_sha256": hashlib.sha256(P08E_POLICY.read_bytes()).hexdigest(),
        "cases": {
            name: {
                "short_range_bps": value.short_range_bps,
                "baseline_range_bps": value.baseline_range_bps,
                "volatility_ratio_bps": value.volatility_ratio_bps,
                "volatility_direction": value.volatility_evidence.direction,
                "volatility_strength_bps": value.volatility_evidence.strength_bps,
                "volatility_confidence_bps": value.volatility_evidence.confidence_bps,
                "volatility_group": value.volatility_evidence.independence_group,
                "volatility_evidence_id": value.volatility_evidence.evidence_id,
                "mean_text": value.mean_text,
                "mean_absolute_deviation_text": value.mean_absolute_deviation_text,
                "deviation_mad_bps": value.deviation_mad_bps,
                "mean_reversion_direction": value.mean_reversion_evidence.direction,
                "mean_reversion_strength_bps": value.mean_reversion_evidence.strength_bps,
                "mean_reversion_confidence_bps": value.mean_reversion_evidence.confidence_bps,
                "mean_reversion_group": value.mean_reversion_evidence.independence_group,
                "mean_reversion_evidence_id": value.mean_reversion_evidence.evidence_id,
                "cross_family_independence_status": value.cross_family_independence_status,
            }
            for name, value in sorted(cases.items())
        },
        "volatility_direction_semantics": "CONTEXT_NEUTRAL_ZERO_ONLY",
        "score_semantics": "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY",
        "cross_family_independence_status": "PROVISIONAL_PENDING_P08_H",
        "direct_trade_output_allowed": False,
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
    print(f"P08E_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
