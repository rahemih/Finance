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
from packages.technical_intelligence.momentum import MomentumFamilyModel, MomentumFamilyPolicy

FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
MOMENTUM_POLICY = ROOT / "config/technical-intelligence/momentum-family-policy.json"


def bars(start: int, step: int, count: int = 24) -> tuple[TrustedOHLCVBar, ...]:
    return tuple(
        TrustedOHLCVBar(
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            open_text=str(start + step * i),
            high_text=str(start + step * i + 2),
            low_text=str(start + step * i - 2),
            close_text=str(start + step * i),
            volume_text="100",
            event_time_ns=(i + 1) * 100,
            as_of_time_ns=10_000,
            source_dataset_version="1" * 64,
            quality_evidence_sha256="2" * 64,
        )
        for i in range(count)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    policy = MomentumFamilyPolicy.from_path(MOMENTUM_POLICY)
    model = MomentumFamilyModel(foundation_policy=foundation, momentum_policy=policy)
    cases = {
        "bullish": model.evaluate(bars(100, 2)),
        "bearish": model.evaluate(bars(300, -2)),
        "neutral": model.evaluate(bars(100, 0)),
    }
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08C_MOMENTUM_FAMILY_EVIDENCE",
        "task_id": "FIN-P08-WC-001",
        "foundation_policy_sha256": hashlib.sha256(FOUNDATION_POLICY.read_bytes()).hexdigest(),
        "momentum_policy_sha256": hashlib.sha256(MOMENTUM_POLICY.read_bytes()).hexdigest(),
        "cases": {
            name: {
                "direction": value.evidence.direction,
                "strength_bps": value.evidence.strength_bps,
                "confidence_bps": value.evidence.confidence_bps,
                "short_roc_bps": value.short_roc_bps,
                "long_roc_bps": value.long_roc_bps,
                "normalized_acceleration_bps": value.normalized_acceleration_bps,
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
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P08C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
