from __future__ import annotations

from pathlib import Path
import unittest

from packages.news_sentiment.classification import ClassificationPolicy, classify_news_item
from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.reliability import (
    ReliabilityControlError,
    ReliabilityPolicy,
    assess_reliability,
)
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY = ROOT / "config/news-sentiment/source-license-policy.json"
RELIABILITY_POLICY = ROOT / "config/news-sentiment/reliability-rumor-policy.json"
CLASSIFICATION_POLICY = ROOT / "config/news-sentiment/sentiment-topic-importance-policy.json"
REGISTRY = ROOT / "config/news-sentiment/entity-asset-registry.json"


def source(
    *,
    source_class: str = "OFFICIAL",
    admissibility_state: str = "CONFIRMED",
    corroborators: tuple[str, ...] = (),
) -> NewsSourceRecord:
    return NewsSourceRecord(
        source_id=f"{source_class.lower()}-example",
        source_class=source_class,
        source_name="Example Source",
        source_url="https://example.gov/news/1",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state=admissibility_state,
        attribution="Example Source",
        published_at="2026-10-11T08:00:00+00:00",
        observed_at="2026-10-11T08:00:05+00:00",
        corroborating_source_ids=corroborators,
    )


def item(record: NewsSourceRecord, title: str) -> RawNewsItem:
    return RawNewsItem(source=record, title=title, body="Market update.")


def classify(news: RawNewsItem):
    registry = EntityRegistry.from_path(REGISTRY)
    mapping = map_news_item(news, registry=registry)
    policy = ClassificationPolicy.from_path(CLASSIFICATION_POLICY)
    return classify_news_item(news, mapping=mapping, policy=policy)


class ReliabilityRumorControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_policy = NewsSourcePolicy.from_path(SOURCE_POLICY)
        self.reliability_policy = ReliabilityPolicy.from_path(RELIABILITY_POLICY)

    def test_official_confirmed_reaches_high_reliability(self) -> None:
        news = item(source(), "Bitcoin rallied.")
        result = assess_reliability(
            news,
            classification=classify(news),
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        self.assertEqual(result.reliability_band, "HIGH")
        self.assertEqual(result.rumor_state, "CONFIRMED")
        self.assertEqual(result.review_state, "ACCEPT_DESCRIPTIVE")

    def test_community_single_source_requires_review(self) -> None:
        news = item(
            source(source_class="COMMUNITY", admissibility_state="SINGLE_SOURCE"),
            "Bitcoin market update.",
        )
        result = assess_reliability(
            news,
            classification=classify(news),
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        self.assertEqual(result.reliability_band, "LOW")
        self.assertEqual(result.review_state, "REVIEW_REQUIRED")
        self.assertIn("REVIEW:COMMUNITY_SOCIAL_NO_CORROBORATION", result.reason_codes)

    def test_unconfirmed_content_is_quarantined(self) -> None:
        news = item(
            source(source_class="NEWSROOM", admissibility_state="UNCONFIRMED"),
            "Bitcoin market update.",
        )
        result = assess_reliability(
            news,
            classification=classify(news),
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        self.assertEqual(result.reliability_band, "BLOCKED")
        self.assertEqual(result.review_state, "QUARANTINED")
        self.assertEqual(result.score, -100)

    def test_corroborated_social_source_gets_deterministic_bonus(self) -> None:
        news = item(
            source(
                source_class="SOCIAL",
                admissibility_state="CORROBORATED",
                corroborators=("official-1", "wire-1", "newsroom-1"),
            ),
            "Bitcoin market update.",
        )
        result = assess_reliability(
            news,
            classification=classify(news),
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        self.assertEqual(result.corroboration_count, 3)
        self.assertEqual(result.score, 4)
        self.assertEqual(result.reliability_band, "MEDIUM")
        self.assertIn("CORROBORATION_BONUS:2", result.reason_codes)

    def test_high_importance_single_source_requires_review(self) -> None:
        news = item(
            source(source_class="NEWSROOM", admissibility_state="SINGLE_SOURCE"),
            "Bitcoin moved after CPI release.",
        )
        classification = classify(news)
        self.assertEqual(classification.importance, "HIGH")
        result = assess_reliability(
            news,
            classification=classification,
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        self.assertEqual(result.reliability_band, "LOW")
        self.assertEqual(result.review_state, "REVIEW_REQUIRED")
        self.assertIn("REVIEW:HIGH_IMPORTANCE_SINGLE_SOURCE", result.reason_codes)

    def test_content_identity_mismatch_fails_closed(self) -> None:
        news = item(source(), "Bitcoin rallied.")
        classification = classify(news)
        bad = type(classification)(
            news_content_id="wrong",
            entity_ids=classification.entity_ids,
            topics=classification.topics,
            sentiment=classification.sentiment,
            importance=classification.importance,
            evidence_terms=classification.evidence_terms,
            reason_codes=classification.reason_codes,
        )
        with self.assertRaises(ReliabilityControlError):
            assess_reliability(
                news,
                classification=bad,
                source_policy=self.source_policy,
                reliability_policy=self.reliability_policy,
            )

    def test_reason_codes_are_deterministic_and_module_has_no_network_execution_imports(self) -> None:
        news = item(source(), "Bitcoin rallied.")
        classification = classify(news)
        first = assess_reliability(
            news,
            classification=classification,
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        second = assess_reliability(
            news,
            classification=classification,
            source_policy=self.source_policy,
            reliability_policy=self.reliability_policy,
        )
        self.assertEqual(first, second)
        self.assertEqual(first.reason_codes, tuple(sorted(first.reason_codes)))
        source_text = (ROOT / "packages/news_sentiment/reliability.py").read_text(encoding="utf-8").lower()
        for forbidden in ("packages.execution", "adapters.execution", "import requests", "import httpx"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
