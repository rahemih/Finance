from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from packages.news_sentiment.entity_mapping import EntityMappingError, EntityRegistry, map_news_item
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.source_policy import NewsSourceRecord

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"config/news-sentiment/entity-asset-registry.json"


def source() -> NewsSourceRecord:
    return NewsSourceRecord(
        source_id="official-example",source_class="OFFICIAL",source_name="Official Source",
        source_url="https://example.gov/news/1",access_kind="PUBLIC",license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",attribution="Official Source",
        published_at="2026-10-11T07:00:00+00:00",observed_at="2026-10-11T07:00:05+00:00",
    )


def item(title:str, body:str="Market update.") -> RawNewsItem:
    return RawNewsItem(source=source(),title=title,body=body)


class EntityAssetMappingTests(unittest.TestCase):
    def test_exact_and_alias_mapping_are_deterministic(self) -> None:
        reg=EntityRegistry.from_path(REGISTRY)
        first=map_news_item(item("Bitcoin and DXY moved after the release."),registry=reg)
        second=map_news_item(item("Bitcoin and DXY moved after the release."),registry=reg)
        self.assertEqual(first,second)
        self.assertEqual([m.symbol for m in first.matches],["BTC","DXY"])
        self.assertEqual(first.news_content_id,second.news_content_id)

    def test_alias_boundary_avoids_substring_false_positive(self) -> None:
        reg=EntityRegistry.from_path(REGISTRY)
        result=map_news_item(item("The ethics committee issued a report."),registry=reg)
        self.assertNotIn("ETH",[m.symbol for m in result.matches])

    def test_alias_match_and_none_state(self) -> None:
        reg=EntityRegistry.from_path(REGISTRY)
        mapped=map_news_item(item("Ether rallied."),registry=reg)
        self.assertEqual(mapped.matches[0].symbol,"ETH")
        self.assertEqual(mapped.matches[0].confidence,"ALIAS")
        none=map_news_item(item("No tracked market entity appears here."),registry=reg)
        self.assertEqual(none.state,"NONE")
        self.assertEqual(none.matches,())

    def test_ambiguous_registry_fails_closed(self) -> None:
        raw=json.loads(REGISTRY.read_text(encoding="utf-8"))
        raw["entities"].append({
            "entity_id":"bad:duplicate","canonical_name":"Duplicate","symbol":"DUP",
            "asset_class":"INDEX","venue_scope":"CONTEXT","aliases":["btc"]
        })
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"registry.json"
            path.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaises(EntityMappingError):
                EntityRegistry.from_path(path)

    def test_registry_keeps_offline_and_trading_disabled(self) -> None:
        reg=EntityRegistry.from_path(REGISTRY)
        self.assertFalse(reg.canonical_tests_network_required)
        self.assertEqual(reg.live_trading,"DISABLED")
        self.assertEqual(reg.auto_trading,"DISABLED")

    def test_module_has_no_execution_or_network_imports(self) -> None:
        source_text=(ROOT/"packages/news_sentiment/entity_mapping.py").read_text(encoding="utf-8").lower()
        for forbidden in ("packages.execution","adapters.execution","import requests","import httpx"):
            self.assertNotIn(forbidden,source_text)


if __name__=="__main__":
    unittest.main()
