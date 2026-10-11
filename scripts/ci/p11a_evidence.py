from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.source_policy import (
    NewsSourcePolicy,
    NewsSourceRecord,
    can_grant_trade_authority,
    validate_source_record,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/news-sentiment/source-license-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = NewsSourcePolicy.from_path(POLICY_PATH)
    record = NewsSourceRecord(
        source_id="official-policy-evidence",
        source_class="OFFICIAL",
        source_name="Canonical Official Source",
        source_url="https://example.gov/news/item",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",
        attribution="Canonical Official Source",
        published_at="2026-10-11T06:00:00+00:00",
        observed_at="2026-10-11T06:00:05+00:00",
    )
    validate_source_record(record, policy=policy)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P11A_SOURCE_LICENSE_POLICY_EVIDENCE",
        "task_id": "FIN-P11-WA-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "record_id": record.record_id,
        "allowed_source_classes": list(policy.allowed_source_classes),
        "allowed_admissibility_states": list(policy.allowed_admissibility_states),
        "unconfirmed_news_trade_authority": policy.unconfirmed_news_trade_authority,
        "sample_trade_authority": can_grant_trade_authority(record, policy=policy),
        "canonical_tests_network_required": policy.canonical_tests_network_required,
        "production_news_vendor": policy.production_news_vendor,
        "country_assumption": "NONE",
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P11A_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
