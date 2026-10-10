from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.technical_intelligence.breakout_expansion import (
    BreakoutExpansionModel,
    BreakoutExpansionPolicy,
)
from packages.technical_intelligence.foundation import (
    TechnicalFoundationPolicy,
    TrustedOHLCVBar,
)

FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
P08F_POLICY = ROOT / "config/technical-intelligence/breakout-expansion-policy.json"


def prior_bars() -> list[TrustedOHLCVBar]:
    return [
        TrustedOHLCVBar(
            symbol="CRYPTO:BTC-USD",
            timeframe="1m",
            open_text="100",
            high_text="102",
            low_text="98",
            close_text="100",
            volume_text="100",
            event_time_ns=(index + 1) * 100,
            as_of_time_ns=10_000,
            source_dataset_version="d" * 64,
            quality_evidence_sha256="e" * 64,
        )
        for index in range(20)
    ]


def current(
    *,
    open_value: int,
    high: int,
    low: int,
    close: int,
) -> TrustedOHLCVBar:
    return TrustedOHLCVBar(
        symbol="CRYPTO:BTC-USD",
        timeframe="1m",
        open_text=str(open_value),
        high_text=str(high),
        low_text=str(low),
        close_text=str(close),
        volume_text="100",
        event_time_ns=2100,
        as_of_time_ns=10_000,
        source_dataset_version="d" * 64,
        quality_evidence_sha256="e" * 64,
    )


def source(bar: TrustedOHLCVBar) -> tuple[TrustedOHLCVBar, ...]:
    return tuple(prior_bars() + [bar])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    policy = BreakoutExpansionPolicy.from_path(P08F_POLICY)
    model = BreakoutExpansionModel(
        foundation_policy=foundation,
        policy=policy,
    )
    cases = {
        "up_expanded": model.evaluate(
            source(current(open_value=100, high=107, low=99, close=105))
        ),
        "up_unexpanded": model.evaluate(
            source(current(open_value=103, high=105, low=101, close=105))
        ),
        "down_expanded": model.evaluate(
            source(current(open_value=100, high=101, low=93, close=95))
        ),
        "neutral": model.evaluate(
            source(current(open_value=100, high=102, low=98, close=101))
        ),
    }

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08F_BREAKOUT_EXPANSION_EVIDENCE",
        "task_id": "FIN-P08-WF-001",
        "foundation_policy_sha256": hashlib.sha256(
            FOUNDATION_POLICY.read_bytes()
        ).hexdigest(),
        "p08f_policy_sha256": hashlib.sha256(P08F_POLICY.read_bytes()).hexdigest(),
        "cases": {
            name: {
                "direction": value.evidence.direction,
                "strength_bps": value.evidence.strength_bps,
                "confidence_bps": value.evidence.confidence_bps,
                "breakout_distance_bps": value.breakout_distance_bps,
                "expansion_ratio_bps": value.expansion_ratio_bps,
                "expansion_confirmed": value.expansion_confirmed,
                "prior_channel_high_text": value.prior_channel_high_text,
                "prior_channel_low_text": value.prior_channel_low_text,
                "independence_group": value.evidence.independence_group,
                "evidence_id": value.evidence.evidence_id,
                "cross_family_independence_status": value.cross_family_independence_status,
            }
            for name, value in sorted(cases.items())
        },
        "expansion_vote_semantics": "CORRELATED_CONTEXT_NOT_SECOND_VOTE",
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
    print(f"P08F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
