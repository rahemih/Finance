from __future__ import annotations

from pathlib import Path
import unittest

from packages.news_sentiment.classification import ClassificationPolicy, ClassificationResult, classify_news_item
from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.event_decay import EventDecayError, EventDecayPolicy, assess_event_decay
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.reliability import ReliabilityAssessment, ReliabilityPolicy, assess_reliability
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY = ROOT / "config/news-sentiment/source-license-policy.json"
RELIABILITY_POLICY = ROOT / "config/news-sentiment/reliability-rumor-policy.json"
CLASSIFICATION_POLICY = ROOT / "config/news-sentiment/sentiment-topic-importance-policy.json"
DECAY_POLICY = ROOT / "config/news-sentiment/event-horizon-decay-policy.json"
REGISTRY = ROOT / "config/news-sentiment/entity-asset-registry.json"


def source(*, admissibility_state: str = "CONFIRMED") -> NewsSourceRecord:
    return NewsSourceRecord(
        source_id="official-example",
        source_class="OFFICIAL",
        source_name="Official Source",
        source_url="https://example.gov/news/1",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state=admissibility_state,
        attribution="Official Source",
        published_at="2026-10-11T08:00:00+00:00",
        observed_at="2026-10-11T08:00:05+00:00",
    )


def item(title: str, *, admissibility_state: str = "CONFIRMED") -> RawNewsItem:
    return RawNewsItem(source=source(admissibility_state=admissibility_state), title=title, body="Market update.")


def classify(news: RawNewsItem) -> ClassificationResult:
    registry = EntityRegistry.from_path(REGISTRY)
    mapping = map_news_item(news, registry=registry)
    policy = ClassificationPolicy.from_path(CLASSIFICATION_POLICY)
    return classify_news_item(news, mapping=mapping, policy=policy)


def reliability(news: RawNewsItem, classification: ClassificationResult) -> ReliabilityAssessment:
    return assess_reliability(
        news,
        classification=classification,
        source_policy=NewsSourcePolicy.from_path(SOURCE_POLICY),
        reliability_policy=ReliabilityPolicy.from_path(RELIABILITY_POLICY),
    )


class EventHorizonDecayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = EventDecayPolicy.from_path(DECAY_POLICY)

    def test_high_importance_macro_uses_observed_clock_and_long_horizon(self) -> None:
        news = item("Bitcoin rallied after CPI beat expectations.")
        classification = classify(news)
        result = assess_event_decay(
            news,
            classification=classification,
            reliability=reliability(news, classification),
            policy=self.policy,
            as_of="2026-10-11T08:00:05+00:00",
        )
        self.assertEqual(result.age_seconds, 0)
        self.assertEqual(result.base_horizon_minutes, 1440)
        self.assertEqual(result.topic_minimum_horizon_minutes, 720)
        self.assertEqual(result.effective_horizon_minutes, 1440)
        self.assertEqual(result.decay_basis_points, 10000)
        self.assertEqual(result.freshness_state, "FRESH")

    def test_decay_decreases_deterministically_and_expires(self) -> None:
        news = item("Bitcoin market update remains unchanged.")
        classification = classify(news)
        rel = reliability(news, classification)
        fresh = assess_event_decay(
            news,
            classification=classification,
            reliability=rel,
            policy=self.policy,
            as_of="2026-10-11T08:30:05+00:00",
        )
        later = assess_event_decay(
            news,
            classification=classification,
            reliability=rel,
            policy=self.policy,
            as_of="2026-10-11T09:30:05+00:00",
        )
        expired = assess_event_decay(
            news,
            classification=classification,
            reliability=rel,
            policy=self.policy,
            as_of="2026-10-11T10:00:05+00:00",
        )
        self.assertGreater(fresh.decay_basis_points, later.decay_basis_points)
        self.assertEqual(later.freshness_state, "DECAYING")
        self.assertEqual(expired.freshness_state, "EXPIRED")
        self.assertEqual(expired.decay_basis_points, 0)

    def test_medium_reliability_shortens_horizon(self) -> None:
        news = item("Bitcoin market update remains unchanged.")
        classification = classify(news)
        rel = ReliabilityAssessment(
            news_content_id=news.content_id,
            reliability_band="MEDIUM",
            rumor_state="CORROBORATED",
            review_state="ACCEPT_DESCRIPTIVE",
            score=4,
            corroboration_count=1,
            reason_codes=(),
        )
        result = assess_event_decay(
            news,
            classification=classification,
            reliability=rel,
            policy=self.policy,
            as_of="2026-10-11T08:00:05+00:00",
        )
        self.assertEqual(result.base_horizon_minutes, 120)
        self.assertEqual(result.effective_horizon_minutes, 90)

    def test_quarantined_unconfirmed_content_is_blocked(self) -> None:
        news = item("Bitcoin market update.", admissibility_state="UNCONFIRMED")
        classification = classify(news)
        rel = reliability(news, classification)
        result = assess_event_decay(
            news,
            classification=classification,
            reliability=rel,
            policy=self.policy,
            as_of="2026-10-11T08:10:05+00:00",
        )
        self.assertEqual(result.freshness_state, "BLOCKED")
        self.assertEqual(result.effective_horizon_minutes, 0)
        self.assertEqual(result.decay_basis_points, 0)

    def test_as_of_before_observed_at_fails_closed(self) -> None:
        news = item("Bitcoin market update.")
        classification = classify(news)
        with self.assertRaises(EventDecayError):
            assess_event_decay(
                news,
                classification=classification,
                reliability=reliability(news, classification),
                policy=self.policy,
                as_of="2026-10-11T08:00:04+00:00",
            )

    def test_content_identity_mismatch_fails_closed(self) -> None:
        news = item("Bitcoin market update.")
        classification = classify(news)
        bad = ReliabilityAssessment(
            news_content_id="wrong",
            reliability_band="HIGH",
            rumor_state="CONFIRMED",
            review_state="ACCEPT_DESCRIPTIVE",
            score=6,
            corroboration_count=0,
            reason_codes=(),
        )
        with self.assertRaises(EventDecayError):
            assess_event_decay(
                news,
                classification=classification,
                reliability=bad,
                policy=self.policy,
                as_of="2026-10-11T08:00:05+00:00",
            )

    def test_reason_codes_are_sorted_and_module_has_no_network_execution_imports(self) -> None:
        news = item("Bitcoin rallied after CPI beat expectations.")
        classification = classify(news)
        result = assess_event_decay(
            news,
            classification=classification,
            reliability=reliability(news, classification),
            policy=self.policy,
            as_of="2026-10-11T08:10:05+00:00",
        )
        self.assertEqual(result.reason_codes, tuple(sorted(result.reason_codes)))
        source_text = (ROOT / "packages/news_sentiment/event_decay.py").read_text(encoding="utf-8").lower()
        for forbidden in ("packages.execution", "adapters.execution", "import requests", "import httpx"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
