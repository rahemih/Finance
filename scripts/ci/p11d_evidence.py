from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.classification import ClassificationPolicy, classify_news_item
from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.source_policy import NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/news-sentiment/sentiment-topic-importance-policy.json"
REGISTRY = ROOT / "config/news-sentiment/entity-asset-registry.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = ClassificationPolicy.from_path(POLICY)
    registry = EntityRegistry.from_path(REGISTRY)
    source = NewsSourceRecord(
        source_id="official-evidence",
        source_class="OFFICIAL",
        source_name="Official Evidence",
        source_url="https://example.gov/news/evidence",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",
        attribution="Official Evidence",
        published_at="2026-10-11T08:00:00+00:00",
        observed_at="2026-10-11T08:00:05+00:00",
    )
    item = RawNewsItem(
        source=source,
        title="Bitcoin rallied after CPI beat expectations.",
        body="Gold also moved after the release.",
    )
    mapping = map_news_item(item, registry=registry)
    result = classify_news_item(item, mapping=mapping, policy=policy)
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P11D_SENTIMENT_TOPIC_IMPORTANCE_EVIDENCE",
        "task_id": "FIN-P11-WD-001",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "news_content_id": result.news_content_id,
        "entity_ids": list(result.entity_ids),
        "topics": list(result.topics),
        "sentiment": result.sentiment,
        "importance": result.importance,
        "evidence_terms": list(result.evidence_terms),
        "reason_codes": list(result.reason_codes),
        "network_required": policy.canonical_tests_network_required,
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P11D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
