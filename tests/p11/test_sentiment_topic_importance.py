from __future__ import annotations

from pathlib import Path
import unittest

from packages.news_sentiment.classification import (
    ClassificationPolicy,
    NewsClassificationError,
    classify_news_item,
)
from packages.news_sentiment.entity_mapping import EntityRegistry, MappingResult, map_news_item
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.source_policy import NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/news-sentiment/sentiment-topic-importance-policy.json"
REGISTRY = ROOT / "config/news-sentiment/entity-asset-registry.json"


def source() -> NewsSourceRecord:
    return NewsSourceRecord(
        source_id="official-example",
        source_class="OFFICIAL",
        source_name="Official Source",
        source_url="https://example.gov/news/1",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",
        attribution="Official Source",
        published_at="2026-10-11T08:00:00+00:00",
        observed_at="2026-10-11T08:00:05+00:00",
    )


def item(title: str, body: str = "Market update.") -> RawNewsItem:
    return RawNewsItem(source=source(), title=title, body=body)


class SentimentTopicImportanceTests(unittest.TestCase):
    def test_positive_macro_classification_is_deterministic(self) -> None:
        policy = ClassificationPolicy.from_path(POLICY)
        registry = EntityRegistry.from_path(REGISTRY)
        news = item("Bitcoin rallied after CPI beat expectations.")
        mapping = map_news_item(news, registry=registry)
        first = classify_news_item(news, mapping=mapping, policy=policy)
        second = classify_news_item(news, mapping=mapping, policy=policy)
        self.assertEqual(first, second)
        self.assertEqual(first.sentiment, "POSITIVE")
        self.assertEqual(first.importance, "HIGH")
        self.assertIn("MACRO_DATA", first.topics)
        self.assertEqual(first.news_content_id, mapping.news_content_id)

    def test_negative_stress_and_mixed_states(self) -> None:
        policy = ClassificationPolicy.from_path(POLICY)
        registry = EntityRegistry.from_path(REGISTRY)

        stress = item("Ethereum network exploit triggered a selloff.")
        stress_mapping = map_news_item(stress, registry=registry)
        result = classify_news_item(stress, mapping=stress_mapping, policy=policy)
        self.assertEqual(result.sentiment, "NEGATIVE")
        self.assertEqual(result.importance, "HIGH")
        self.assertIn("MARKET_STRESS", result.topics)

        mixed = item("Bitcoin rallied after an upgrade but later faced a ban.")
        mixed_mapping = map_news_item(mixed, registry=registry)
        mixed_result = classify_news_item(mixed, mapping=mixed_mapping, policy=policy)
        self.assertEqual(mixed_result.sentiment, "MIXED")

    def test_neutral_fallback_and_low_importance_are_explicit(self) -> None:
        policy = ClassificationPolicy.from_path(POLICY)
        registry = EntityRegistry.from_path(REGISTRY)
        news = item("Bitcoin market update remains unchanged.")
        mapping = map_news_item(news, registry=registry)
        result = classify_news_item(news, mapping=mapping, policy=policy)
        self.assertEqual(result.sentiment, "NEUTRAL")
        self.assertEqual(result.importance, "LOW")
        self.assertEqual(result.topics, ("GENERAL",))

    def test_multi_entity_context_can_raise_medium_importance(self) -> None:
        policy = ClassificationPolicy.from_path(POLICY)
        registry = EntityRegistry.from_path(REGISTRY)
        news = item("Bitcoin and gold moved during the session.")
        mapping = map_news_item(news, registry=registry)
        result = classify_news_item(news, mapping=mapping, policy=policy)
        self.assertEqual(result.importance, "MEDIUM")
        self.assertEqual(result.entity_ids, ("asset:BTC", "context:XAUUSD"))

    def test_boundary_matching_avoids_substring_false_positive(self) -> None:
        policy = ClassificationPolicy.from_path(POLICY)
        registry = EntityRegistry.from_path(REGISTRY)
        news = item("The software shortcut was upgraded.")
        mapping = map_news_item(news, registry=registry)
        result = classify_news_item(news, mapping=mapping, policy=policy)
        self.assertNotIn("rate cut", result.evidence_terms)

    def test_mapping_identity_mismatch_fails_closed(self) -> None:
        policy = ClassificationPolicy.from_path(POLICY)
        news = item("Bitcoin rallied.")
        bad_mapping = MappingResult(news_content_id="wrong", matches=(), state="NONE")
        with self.assertRaises(NewsClassificationError):
            classify_news_item(news, mapping=bad_mapping, policy=policy)

    def test_module_has_no_execution_or_network_imports(self) -> None:
        source_text = (ROOT / "packages/news_sentiment/classification.py").read_text(encoding="utf-8").lower()
        for forbidden in ("packages.execution", "adapters.execution", "import requests", "import httpx"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
