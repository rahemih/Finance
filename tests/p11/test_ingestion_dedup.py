from __future__ import annotations

from pathlib import Path
import unittest

from packages.news_sentiment.ingestion import (
    IngestionPolicy,
    NewsIngestionError,
    RawNewsItem,
    build_dedup_group,
    exact_duplicate,
    near_duplicate,
    near_duplicate_ratio,
    validate_raw_news_item,
)
from packages.news_sentiment.source_policy import NewsSourcePolicy, NewsSourceRecord

ROOT = Path(__file__).resolve().parents[2]
SOURCE_POLICY = ROOT / "config/news-sentiment/source-license-policy.json"
INGESTION_POLICY = ROOT / "config/news-sentiment/ingestion-dedup-policy.json"


def source_policy() -> NewsSourcePolicy:
    return NewsSourcePolicy.from_path(SOURCE_POLICY)


def ingestion_policy() -> IngestionPolicy:
    return IngestionPolicy.from_path(INGESTION_POLICY)


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
        published_at="2026-10-11T07:00:00+00:00",
        observed_at="2026-10-11T07:00:05+00:00",
    )


def item(title: str = "Rates held steady", body: str = "Policy makers held rates steady today.") -> RawNewsItem:
    return RawNewsItem(source=source(), title=title, body=body)


class IngestionDedupTests(unittest.TestCase):
    def test_normalization_and_content_identity_are_deterministic(self) -> None:
        first = item("  Rates   held steady ", "Policy makers\nheld rates steady today.")
        second = item("Rates held steady", "Policy makers held rates steady today.")
        self.assertEqual(first.normalized_title, second.normalized_title)
        self.assertEqual(first.normalized_body, second.normalized_body)
        self.assertEqual(first.content_id, second.content_id)
        self.assertTrue(exact_duplicate(first, second))

    def test_material_difference_changes_content_identity(self) -> None:
        first = item()
        second = item(body="Policy makers raised rates today.")
        self.assertNotEqual(first.content_id, second.content_id)
        self.assertFalse(exact_duplicate(first, second))

    def test_fingerprint_is_punctuation_and_case_stable(self) -> None:
        first = item("Central Bank Update!", "Rates HELD steady.")
        second = item("central bank update", "rates held steady")
        self.assertEqual(first.fingerprint_id, second.fingerprint_id)

    def test_near_duplicate_ratio_is_deterministic(self) -> None:
        p = ingestion_policy()
        first = item("Fed decision", "Federal Reserve held rates steady after meeting.")
        second = item("Fed decision update", "Federal Reserve held rates steady after the meeting.")
        ratio = near_duplicate_ratio(first, second)
        self.assertGreater(ratio, 0.7)
        self.assertEqual(near_duplicate(first, second, policy=p), ratio >= p.min_shared_ratio)

    def test_dedup_group_identity_is_order_independent(self) -> None:
        first = item()
        second = item(body="Policy makers held rates steady today after the meeting.")
        left = build_dedup_group((first, second))
        right = build_dedup_group((second, first))
        self.assertEqual(left.group_id, right.group_id)

    def test_empty_text_fails_closed(self) -> None:
        with self.assertRaises(NewsIngestionError):
            _ = item(title=" ").content_id
        with self.assertRaises(NewsIngestionError):
            _ = item(body="").fingerprint_id

    def test_source_policy_is_enforced_before_ingestion(self) -> None:
        good = item()
        validate_raw_news_item(good, source_policy=source_policy())
        bad_source = NewsSourceRecord(
            source_id="bad",
            source_class="BLOG",
            source_name="Bad",
            source_url="https://example.com/x",
            access_kind="PUBLIC",
            license_state="PUBLIC_REUSE",
            admissibility_state="UNCONFIRMED",
            attribution="Bad",
            published_at="2026-10-11T07:00:00+00:00",
            observed_at="2026-10-11T07:00:05+00:00",
        )
        with self.assertRaises(ValueError):
            validate_raw_news_item(RawNewsItem(source=bad_source, title="x", body="y"), source_policy=source_policy())

    def test_module_has_no_execution_or_network_imports(self) -> None:
        source_text = (ROOT / "packages/news_sentiment/ingestion.py").read_text(encoding="utf-8").lower()
        for forbidden in ("adapters.execution","packages.execution","import requests","import httpx","import websocket"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
