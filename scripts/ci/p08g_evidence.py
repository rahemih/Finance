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
    TechnicalEvidence,
    TechnicalFoundationPolicy,
)
from packages.technical_intelligence.multi_timeframe_regime import (
    MultiTimeframeRegimeModel,
    MultiTimeframeRegimePolicy,
)
from packages.technical_intelligence.trend import (
    TrendFamilyModel,
    TrendFamilyPolicy,
)

FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
TREND_POLICY = ROOT / "config/technical-intelligence/trend-family-policy.json"
P08G_POLICY = ROOT / "config/technical-intelligence/multi-timeframe-regime-policy.json"


def trend_evidence(
    *,
    timeframe: str,
    direction: int,
    strength_bps: int = 5000,
    confidence_bps: int = 6000,
    event_time_ns: int = 9000,
) -> TechnicalEvidence:
    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    trend_policy = TrendFamilyPolicy.from_path(TREND_POLICY)
    definition = TrendFamilyModel(
        foundation_policy=foundation,
        trend_policy=trend_policy,
    ).definition()
    return TechnicalEvidence(
        definition_id=definition.definition_id,
        family="TREND",
        independence_group=trend_policy.independence_group,
        symbol="CRYPTO:BTC-USD",
        timeframe=timeframe,
        direction=direction,
        strength_bps=strength_bps if direction != 0 else 0,
        confidence_bps=confidence_bps if direction != 0 else 0,
        event_time_ns=event_time_ns,
        as_of_time_ns=10_000,
        value_text=str(direction * strength_bps if direction != 0 else 0),
        invalidation="P08-G evidence fixture",
        source_dataset_version="2" * 64,
        quality_evidence_sha256="3" * 64,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    policy = MultiTimeframeRegimePolicy.from_path(P08G_POLICY)
    model = MultiTimeframeRegimeModel(
        foundation_policy=foundation,
        policy=policy,
    )

    cases = {
        "aligned_bullish": model.evaluate(
            (
                trend_evidence(timeframe="15m", direction=1, strength_bps=4000),
                trend_evidence(timeframe="1h", direction=1, strength_bps=6000),
                trend_evidence(timeframe="4h", direction=1, strength_bps=8000),
            )
        ),
        "aligned_bearish": model.evaluate(
            (
                trend_evidence(timeframe="15m", direction=-1),
                trend_evidence(timeframe="1h", direction=-1),
                trend_evidence(timeframe="4h", direction=-1),
            )
        ),
        "transition": model.evaluate(
            (
                trend_evidence(timeframe="15m", direction=1),
                trend_evidence(timeframe="1h", direction=0),
                trend_evidence(timeframe="4h", direction=1),
            )
        ),
        "conflict": model.evaluate(
            (
                trend_evidence(timeframe="15m", direction=1),
                trend_evidence(timeframe="1h", direction=-1),
                trend_evidence(timeframe="4h", direction=0),
            )
        ),
        "neutral": model.evaluate(
            (
                trend_evidence(timeframe="15m", direction=0),
                trend_evidence(timeframe="1h", direction=0),
            )
        ),
    }

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08G_MULTI_TIMEFRAME_REGIME_EVIDENCE",
        "task_id": "FIN-P08-WG-001",
        "foundation_policy_sha256": hashlib.sha256(
            FOUNDATION_POLICY.read_bytes()
        ).hexdigest(),
        "trend_policy_sha256": hashlib.sha256(
            TREND_POLICY.read_bytes()
        ).hexdigest(),
        "p08g_policy_sha256": hashlib.sha256(
            P08G_POLICY.read_bytes()
        ).hexdigest(),
        "cases": {
            name: {
                "classification": value.classification,
                "timeframes": list(value.timeframes),
                "direction": value.evidence.direction,
                "strength_bps": value.evidence.strength_bps,
                "confidence_bps": value.evidence.confidence_bps,
                "independence_group": value.evidence.independence_group,
                "evidence_id": value.evidence.evidence_id,
                "cross_timeframe_independence_status": (
                    value.cross_timeframe_independence_status
                ),
                "cross_family_independence_status": (
                    value.cross_family_independence_status
                ),
            }
            for name, value in sorted(cases.items())
        },
        "timeframe_vote_semantics": "RELATED_NOT_INDEPENDENT",
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
    print(f"P08G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
