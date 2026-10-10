from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.technical_intelligence.foundation import TechnicalFoundationPolicy, TrustedOHLCVBar
from packages.technical_intelligence.trend import TrendFamilyModel, TrendFamilyPolicy

FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
TREND_POLICY = ROOT / "config/technical-intelligence/trend-family-policy.json"


def bars(*, start: int, step: int, count: int = 60) -> tuple[TrustedOHLCVBar, ...]:
    dataset = "c" * 64
    quality = "d" * 64
    return tuple(
        TrustedOHLCVBar(
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            open_text=str(start + (step * index)),
            high_text=str(start + (step * index) + 2),
            low_text=str(start + (step * index) - 2),
            close_text=str(start + (step * index)),
            volume_text="100",
            event_time_ns=(index + 1) * 100,
            as_of_time_ns=10_000,
            source_dataset_version=dataset,
            quality_evidence_sha256=quality,
        )
        for index in range(count)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    trend = TrendFamilyPolicy.from_path(TREND_POLICY)
    model = TrendFamilyModel(foundation_policy=foundation, trend_policy=trend)

    cases = {
        "bullish": model.evaluate(bars(start=100, step=1)),
        "bearish": model.evaluate(bars(start=300, step=-1)),
        "neutral": model.evaluate(bars(start=100, step=0)),
    }
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08B_TREND_FAMILY_EVIDENCE",
        "task_id": "FIN-P08-WB-001",
        "foundation_policy_sha256": hashlib.sha256(FOUNDATION_POLICY.read_bytes()).hexdigest(),
        "trend_policy_sha256": hashlib.sha256(TREND_POLICY.read_bytes()).hexdigest(),
        "cases": {
            name: {
                "direction": value.evidence.direction,
                "strength_bps": value.evidence.strength_bps,
                "confidence_bps": value.evidence.confidence_bps,
                "alignment_bps": value.alignment_bps,
                "slope_bps": value.slope_bps,
                "price_distance_bps": value.price_distance_bps,
                "independence_group": value.evidence.independence_group,
                "evidence_id": value.evidence.evidence_id,
            }
            for name, value in sorted(cases.items())
        },
        "score_semantics": "DETERMINISTIC_EVIDENCE_NOT_TRADE_PROBABILITY",
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
    print(f"P08B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
