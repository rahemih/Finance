from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.alerting import AlertNarrativePolicy, build_alert_narrative_input
from packages.news_sentiment.classification import ClassificationPolicy, classify_news_item
from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.event_decay import EventDecayPolicy, assess_event_decay
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.reliability import ReliabilityPolicy, assess_reliability
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
ALERT_POLICY = ROOT / "config/news-sentiment/alerting-narrative-policy.json"
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
    alert_policy = AlertNarrativePolicy.from_path(ALERT_POLICY)
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
    decay = assess_event_decay(
        item,
        classification=classification,
        reliability=reliability,
        policy=decay_policy,
        as_of="2026-10-11T08:05:05+00:00",
    )
    result = build_alert_narrative_input(
        item,
        classification=classification,
        reliability=reliability,
        decay=decay,
        policy=alert_policy,
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P11G_ALERTING_NARRATIVE_INPUT_EVIDENCE",
        "task_id": "FIN-P11-WG-001",
        "policy_sha256": hashlib.sha256(ALERT_POLICY.read_bytes()).hexdigest(),
        "news_content_id": result.news_content_id,
        "source_id": result.source_id,
        "entity_ids": list(result.entity_ids),
        "topics": list(result.topics),
        "sentiment": result.sentiment,
        "importance": result.importance,
        "reliability_band": result.reliability_band,
        "rumor_state": result.rumor_state,
        "review_state": result.review_state,
        "freshness_state": result.freshness_state,
        "decay_basis_points": result.decay_basis_points,
        "eligible": result.eligible,
        "severity": result.severity,
        "grouping_key": result.grouping_key,
        "reason_codes": list(result.reason_codes),
        "network_required": alert_policy.canonical_tests_network_required,
        "llm_narrative_required": alert_policy.llm_narrative_required,
        "channel_delivery_enabled": alert_policy.channel_delivery_enabled,
        "production_news_vendor": alert_policy.production_news_vendor,
        "live_trading": alert_policy.live_trading,
        "auto_trading": alert_policy.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P11G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
