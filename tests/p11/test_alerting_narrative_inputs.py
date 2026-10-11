from __future__ import annotations

from pathlib import Path
import unittest

from packages.news_sentiment.alerting import AlertNarrativeError, AlertNarrativePolicy, build_alert_narrative_input
from packages.news_sentiment.classification import ClassificationPolicy, ClassificationResult, classify_news_item
from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.event_decay import EventDecayAssessment, EventDecayPolicy, assess_event_decay
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.reliability import ReliabilityAssessment, ReliabilityPolicy, assess_reliability
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord


ROOT = Path(__file__).resolve().parents[2]
ALERT_POLICY = ROOT / "config/news-sentiment/alerting-narrative-policy.json"
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


def chain(news: RawNewsItem, *, as_of: str):
    registry = EntityRegistry.from_path(REGISTRY)
    mapping = map_news_item(news, registry=registry)
    classification = classify_news_item(
        news,
        mapping=mapping,
        policy=ClassificationPolicy.from_path(CLASSIFICATION_POLICY),
    )
    reliability = assess_reliability(
        news,
        classification=classification,
        source_policy=NewsSourcePolicy.from_path(SOURCE_POLICY),
        reliability_policy=ReliabilityPolicy.from_path(RELIABILITY_POLICY),
    )
    decay = assess_event_decay(
        news,
        classification=classification,
        reliability=reliability,
        policy=EventDecayPolicy.from_path(DECAY_POLICY),
        as_of=as_of,
    )
    return classification, reliability, decay


class AlertingNarrativeInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = AlertNarrativePolicy.from_path(ALERT_POLICY)

    def test_high_reliability_fresh_high_importance_is_critical(self) -> None:
        news = item("Bitcoin rallied after CPI beat expectations.")
        classification, reliability, decay = chain(news, as_of="2026-10-11T08:05:05+00:00")
        result = build_alert_narrative_input(
            news,
            classification=classification,
            reliability=reliability,
            decay=decay,
            policy=self.policy,
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.severity, "CRITICAL")
        self.assertEqual(result.news_content_id, news.content_id)

    def test_medium_context_is_important(self) -> None:
        news = item("Bitcoin and gold moved during the session.")
        classification, reliability, decay = chain(news, as_of="2026-10-11T08:10:05+00:00")
        self.assertEqual(classification.importance, "MEDIUM")
        result = build_alert_narrative_input(
            news,
            classification=classification,
            reliability=reliability,
            decay=decay,
            policy=self.policy,
        )
        self.assertEqual(result.severity, "IMPORTANT")

    def test_low_context_is_informational(self) -> None:
        news = item("Bitcoin market update remains unchanged.")
        classification, reliability, decay = chain(news, as_of="2026-10-11T08:10:05+00:00")
        result = build_alert_narrative_input(
            news,
            classification=classification,
            reliability=reliability,
            decay=decay,
            policy=self.policy,
        )
        self.assertEqual(result.severity, "INFORMATIONAL")
        self.assertTrue(result.eligible)

    def test_expired_content_is_suppressed(self) -> None:
        news = item("Bitcoin market update remains unchanged.")
        classification, reliability, decay = chain(news, as_of="2026-10-11T10:00:05+00:00")
        self.assertEqual(decay.freshness_state, "EXPIRED")
        result = build_alert_narrative_input(
            news,
            classification=classification,
            reliability=reliability,
            decay=decay,
            policy=self.policy,
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.severity, "SUPPRESSED")

    def test_quarantined_content_is_suppressed(self) -> None:
        news = item("Bitcoin market update.", admissibility_state="UNCONFIRMED")
        classification, reliability, decay = chain(news, as_of="2026-10-11T08:10:05+00:00")
        result = build_alert_narrative_input(
            news,
            classification=classification,
            reliability=reliability,
            decay=decay,
            policy=self.policy,
        )
        self.assertEqual(reliability.review_state, "QUARANTINED")
        self.assertEqual(result.severity, "SUPPRESSED")
        self.assertFalse(result.eligible)

    def test_grouping_key_is_deterministic(self) -> None:
        news = item("Bitcoin rallied after CPI beat expectations.")
        classification, reliability, decay = chain(news, as_of="2026-10-11T08:05:05+00:00")
        first = build_alert_narrative_input(
            news, classification=classification, reliability=reliability, decay=decay, policy=self.policy
        )
        second = build_alert_narrative_input(
            news, classification=classification, reliability=reliability, decay=decay, policy=self.policy
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first.grouping_key), 64)
        self.assertEqual(first.reason_codes, tuple(sorted(first.reason_codes)))

    def test_content_identity_mismatch_fails_closed(self) -> None:
        news = item("Bitcoin market update.")
        classification, reliability, decay = chain(news, as_of="2026-10-11T08:05:05+00:00")
        bad_decay = EventDecayAssessment(
            news_content_id="wrong",
            observed_at=decay.observed_at,
            as_of=decay.as_of,
            base_horizon_minutes=decay.base_horizon_minutes,
            topic_minimum_horizon_minutes=decay.topic_minimum_horizon_minutes,
            effective_horizon_minutes=decay.effective_horizon_minutes,
            age_seconds=decay.age_seconds,
            decay_basis_points=decay.decay_basis_points,
            freshness_state=decay.freshness_state,
            reason_codes=decay.reason_codes,
        )
        with self.assertRaises(AlertNarrativeError):
            build_alert_narrative_input(
                news,
                classification=classification,
                reliability=reliability,
                decay=bad_decay,
                policy=self.policy,
            )

    def test_module_has_no_llm_network_or_execution_imports(self) -> None:
        source_text = (ROOT / "packages/news_sentiment/alerting.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "packages.execution",
            "adapters.execution",
            "import requests",
            "import httpx",
            "openai",
            "anthropic",
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
