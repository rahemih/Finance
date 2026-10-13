from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from packages.timing_opportunity.session_calendar import (
    SessionCalendarPolicy,
    evaluate_session,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/timing-opportunity/session-calendar-policy.json"


def ns(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()) * 1_000_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = SessionCalendarPolicy.from_path(POLICY_PATH)
    samples = (
        ("FOREX_SPOT", "2026-10-12T14:00:00"),
        ("FOREX_SPOT", "2026-10-17T14:00:00"),
        ("FOREX_SPOT", "2026-10-18T22:00:00"),
        ("CRYPTO_SPOT", "2026-10-17T14:00:00"),
    )
    contexts = [
        evaluate_session(ns(stamp), market_kind=market, policy=policy)
        for market, stamp in samples
    ]
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P13A_SESSION_MARKET_CALENDAR_EVIDENCE",
        "task_id": "FIN-P13-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "calendar_version": policy.calendar_version,
        "contexts": [
            {
                "timestamp_ns": item.timestamp_ns,
                "market_kind": item.market_kind,
                "weekday_utc": item.weekday_utc,
                "minute_of_day_utc": item.minute_of_day_utc,
                "is_market_open": item.is_market_open,
                "active_sessions": list(item.active_sessions),
                "overlap_count": item.overlap_count,
                "state": item.state,
            }
            for item in contexts
        ],
        "holiday_calendar_in_scope": policy.holiday_calendar_in_scope,
        "dynamic_dst_adjustment_in_scope": policy.dynamic_dst_adjustment_in_scope,
        "production_calendar_vendor": policy.production_calendar_vendor,
        "best_trading_time_in_scope": policy.best_trading_time_in_scope,
        "opportunity_ranking_in_scope": policy.opportunity_ranking_in_scope,
        "signal_probability_in_scope": policy.signal_probability_in_scope,
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P13A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
