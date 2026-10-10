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
from packages.technical_intelligence.market_structure_price_action import (
    MarketStructurePriceActionModel,
    MarketStructurePriceActionPolicy,
)

FOUNDATION_POLICY = ROOT / "config/technical-intelligence/indicator-foundation-policy.json"
P08D_POLICY = ROOT / "config/technical-intelligence/market-structure-price-action-policy.json"
BULLISH_VALUES = (
    100, 102, 105, 103, 101, 104, 108, 105,
    103, 106, 111, 108, 106, 109, 114, 111,
    109, 113, 117, 114, 112, 116, 120, 117,
    115, 119, 123, 120, 118, 122, 126, 130,
)
BEARISH_VALUES = tuple(400 - value for value in BULLISH_VALUES)


def bars(
    values: tuple[int, ...],
    *,
    latest_open: int | None = None,
    latest_high: int | None = None,
    latest_low: int | None = None,
) -> tuple[TrustedOHLCVBar, ...]:
    result: list[TrustedOHLCVBar] = []
    for index, close in enumerate(values):
        is_latest = index == len(values) - 1
        open_value = latest_open if is_latest and latest_open is not None else close
        high_value = latest_high if is_latest and latest_high is not None else max(open_value, close) + 1
        low_value = latest_low if is_latest and latest_low is not None else min(open_value, close) - 1
        result.append(
            TrustedOHLCVBar(
                symbol="CRYPTO:BTC-USD",
                timeframe="1m",
                open_text=str(open_value),
                high_text=str(high_value),
                low_text=str(low_value),
                close_text=str(close),
                volume_text="100",
                event_time_ns=(index + 1) * 100,
                as_of_time_ns=10_000,
                source_dataset_version="5" * 64,
                quality_evidence_sha256="6" * 64,
            )
        )
    return tuple(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    foundation = TechnicalFoundationPolicy.from_path(FOUNDATION_POLICY)
    policy = MarketStructurePriceActionPolicy.from_path(P08D_POLICY)
    model = MarketStructurePriceActionModel(
        foundation_policy=foundation,
        policy=policy,
    )
    flat = tuple(100 for _ in range(31))
    cases = {
        "bullish_structure": model.evaluate(bars(BULLISH_VALUES)),
        "bearish_structure": model.evaluate(bars(BEARISH_VALUES)),
        "bullish_price_action": model.evaluate(
            bars(flat + (109,), latest_open=100, latest_high=110, latest_low=99)
        ),
        "bearish_price_action": model.evaluate(
            bars(flat + (100,), latest_open=109, latest_high=110, latest_low=99)
        ),
        "neutral": model.evaluate(bars(flat + (100,), latest_open=100, latest_high=110, latest_low=90)),
    }
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08D_MARKET_STRUCTURE_PRICE_ACTION_EVIDENCE",
        "task_id": "FIN-P08-WD-001",
        "foundation_policy_sha256": hashlib.sha256(
            FOUNDATION_POLICY.read_bytes()
        ).hexdigest(),
        "p08d_policy_sha256": hashlib.sha256(P08D_POLICY.read_bytes()).hexdigest(),
        "cases": {
            name: {
                "structure_direction": value.structure_evidence.direction,
                "structure_strength_bps": value.structure_evidence.strength_bps,
                "structure_confidence_bps": value.structure_evidence.confidence_bps,
                "structure_break_direction": value.structure_break_direction,
                "structure_group": value.structure_evidence.independence_group,
                "structure_evidence_id": value.structure_evidence.evidence_id,
                "price_action_direction": value.price_action_evidence.direction,
                "price_action_strength_bps": value.price_action_evidence.strength_bps,
                "price_action_confidence_bps": value.price_action_evidence.confidence_bps,
                "body_to_range_bps": value.body_to_range_bps,
                "price_action_group": value.price_action_evidence.independence_group,
                "price_action_evidence_id": value.price_action_evidence.evidence_id,
                "cross_family_independence_status": value.cross_family_independence_status,
            }
            for name, value in sorted(cases.items())
        },
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
    print(f"P08D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
