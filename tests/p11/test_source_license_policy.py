from __future__ import annotations

from pathlib import Path
import unittest

from packages.news_sentiment.source_policy import (
    NewsSourcePolicy,
    NewsSourcePolicyError,
    NewsSourceRecord,
    can_grant_trade_authority,
    record_with,
    validate_source_record,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/news-sentiment/source-license-policy.json"


def policy() -> NewsSourcePolicy:
    return NewsSourcePolicy.from_path(POLICY_PATH)


def sample() -> NewsSourceRecord:
    return NewsSourceRecord(
        source_id="official-fed-example",
        source_class="OFFICIAL",
        source_name="Federal Reserve",
        source_url="https://www.federalreserve.gov/newsevents/pressreleases/test.htm",
        access_kind="PUBLIC",
        license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",
        attribution="Federal Reserve",
        published_at="2026-10-11T06:00:00+00:00",
        observed_at="2026-10-11T06:00:05+00:00",
    )


class NewsSourcePolicyTests(unittest.TestCase):
    def test_policy_keeps_network_vendor_and_trading_disabled(self) -> None:
        p = policy()
        self.assertFalse(p.canonical_tests_network_required)
        self.assertEqual(p.production_news_vendor, "NOT_SELECTED")
        self.assertFalse(p.unconfirmed_news_trade_authority)
        self.assertEqual(p.live_trading, "DISABLED")
        self.assertEqual(p.auto_trading, "DISABLED")

    def test_valid_record_is_deterministic_and_content_sensitive(self) -> None:
        p = policy()
        first = sample()
        validate_source_record(first, policy=p)
        self.assertEqual(first.record_id, sample().record_id)
        self.assertNotEqual(first.record_id, record_with(first, attribution="Federal Reserve Board").record_id)

    def test_unknown_enums_fail_closed(self) -> None:
        p = policy()
        for field, value in (
            ("source_class", "BLOG"),
            ("access_kind", "MAGIC"),
            ("license_state", "UNKNOWN"),
            ("admissibility_state", "TRUST_ME"),
        ):
            with self.assertRaises(NewsSourcePolicyError):
                validate_source_record(record_with(sample(), **{field: value}), policy=p)

    def test_https_and_time_semantics_fail_closed(self) -> None:
        p = policy()
        with self.assertRaises(NewsSourcePolicyError):
            validate_source_record(record_with(sample(), source_url="http://example.com/news"), policy=p)
        with self.assertRaises(NewsSourcePolicyError):
            validate_source_record(
                record_with(sample(), published_at="2026-10-11T06:01:00+00:00"),
                policy=p,
            )

    def test_social_confirmed_requires_corroboration(self) -> None:
        p = policy()
        social = record_with(
            sample(),
            source_class="SOCIAL",
            admissibility_state="CONFIRMED",
        )
        with self.assertRaises(NewsSourcePolicyError):
            validate_source_record(social, policy=p)
        validate_source_record(
            record_with(social, corroborating_source_ids=("official-fed",)),
            policy=p,
        )

    def test_corroborated_requires_corroborating_sources(self) -> None:
        p = policy()
        with self.assertRaises(NewsSourcePolicyError):
            validate_source_record(record_with(sample(), admissibility_state="CORROBORATED"), policy=p)

    def test_unconfirmed_news_never_grants_trade_authority(self) -> None:
        p = policy()
        unconfirmed = record_with(
            sample(),
            source_class="SOCIAL",
            admissibility_state="UNCONFIRMED",
        )
        validate_source_record(unconfirmed, policy=p)
        self.assertFalse(can_grant_trade_authority(unconfirmed, policy=p))
        self.assertFalse(can_grant_trade_authority(sample(), policy=p))

    def test_module_has_no_execution_or_network_runtime_imports(self) -> None:
        source = (ROOT / "packages/news_sentiment/source_policy.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "adapters.execution",
            "packages.execution",
            "import requests",
            "from requests",
            "import httpx",
            "from httpx",
            "import websocket",
            "from websocket",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
