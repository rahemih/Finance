from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.classification import ClassificationPolicy, classify_news_item
from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.event_decay import EventDecayPolicy, assess_event_decay
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.reliability import ReliabilityPolicy, assess_reliability
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY = ROOT / "config/news-sentiment/source-license-policy.json"
RELIABILITY_POLICY = ROOT / "config/news-sentiment/reliability-rumor-policy.json"
CLASSIFICATION_POLICY = ROOT / "config/news-sentiment/sentiment-topic-importance-policy.json"
DECAY_POLICY = ROOT / "config/news-sentiment/event-horizon-decay-policy.json"
REGISTRY = ROOT / "config/news-sentiment/entity-asset-registry.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_policy = NewsSourcePolicy.from_path(SOURCE_POLICY)
    reliability_policy = ReliabilityPolicy.from_path(RELIABILITY_POLICY)
    classification_policy = ClassificationPolicy.from_path(CLASSIFICATION_POLICY)
    decay_policy = EventDecayPolicy.from_path(DECAY_POLICY)
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
    classification = classify_news_item(item, mapping=mapping, policy=classification_policy)
    reliability = assess_reliability(
        item,
        classification=classification,
        source_policy=source_policy,
        reliability_policy=reliability_policy,
    )
    assessment = assess_event_decay(
        item,
        classification=classification,
        reliability=reliability,
        policy=decay_policy,
        as_of="2026-10-11T10:00:05+00:00",
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P11F_EVENT_HORIZON_DECAY_EVIDENCE",
        "task_id": "FIN-P11-WF-001",
        "policy_sha256": hashlib.sha256(DECAY_POLICY.read_bytes()).hexdigest(),
        "news_content_id": assessment.news_content_id,
        "observed_at": assessment.observed_at,
        "as_of": assessment.as_of,
        "base_horizon_minutes": assessment.base_horizon_minutes,
        "topic_minimum_horizon_minutes": assessment.topic_minimum_horizon_minutes,
        "effective_horizon_minutes": assessment.effective_horizon_minutes,
        "age_seconds": assessment.age_seconds,
        "decay_basis_points": assessment.decay_basis_points,
        "freshness_state": assessment.freshness_state,
        "reason_codes": list(assessment.reason_codes),
        "network_required": decay_policy.canonical_tests_network_required,
        "production_news_vendor": decay_policy.production_news_vendor,
        "live_trading": decay_policy.live_trading,
        "auto_trading": decay_policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P11F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
