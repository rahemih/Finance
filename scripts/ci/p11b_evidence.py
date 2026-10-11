from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.ingestion import IngestionPolicy, RawNewsItem, build_dedup_group, near_duplicate_ratio
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord

ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY_PATH = ROOT / "config/news-sentiment/source-license-policy.json"
INGESTION_POLICY_PATH = ROOT / "config/news-sentiment/ingestion-dedup-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_policy = NewsSourcePolicy.from_path(SOURCE_POLICY_PATH)
    ingestion_policy = IngestionPolicy.from_path(INGESTION_POLICY_PATH)
    source = NewsSourceRecord(
        source_id="official-evidence",
        source_class="OFFICIAL",
        source_name="Official Evidence Source",
        source_url="https://example.gov/news/evidence",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",
        attribution="Official Evidence Source",
        published_at="2026-10-11T07:00:00+00:00",
        observed_at="2026-10-11T07:00:05+00:00",
    )
    first = RawNewsItem(source=source, title="Policy decision", body="Central bank held rates steady today.")
    second = RawNewsItem(source=source, title="Policy decision update", body="Central bank held rates steady today after meeting.")
    group = build_dedup_group((first, second))

    payload = {
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P11B_INGESTION_DEDUP_EVIDENCE",
        "task_id":"FIN-P11-WB-001",
        "source_policy_sha256":hashlib.sha256(SOURCE_POLICY_PATH.read_bytes()).hexdigest(),
        "ingestion_policy_sha256":hashlib.sha256(INGESTION_POLICY_PATH.read_bytes()).hexdigest(),
        "first_content_id":first.content_id,
        "second_content_id":second.content_id,
        "first_fingerprint_id":first.fingerprint_id,
        "second_fingerprint_id":second.fingerprint_id,
        "near_duplicate_ratio":near_duplicate_ratio(first, second),
        "dedup_group_id":group.group_id,
        "source_classes":list(source_policy.allowed_source_classes),
        "production_news_vendor":ingestion_policy.production_news_vendor,
        "canonical_tests_network_required":ingestion_policy.canonical_tests_network_required,
        "live_trading":ingestion_policy.live_trading,
        "auto_trading":ingestion_policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P11B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
