from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.news_sentiment.entity_mapping import EntityRegistry, map_news_item
from packages.news_sentiment.ingestion import RawNewsItem
from packages.news_sentiment.source_policy import NewsSourceRecord

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"config/news-sentiment/entity-asset-registry.json"


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    registry=EntityRegistry.from_path(REGISTRY)
    source=NewsSourceRecord(
        source_id="official-evidence",source_class="OFFICIAL",source_name="Official Evidence",
        source_url="https://example.gov/news/evidence",access_kind="PUBLIC",license_state="ATTRIBUTION_REQUIRED",
        admissibility_state="CONFIRMED",attribution="Official Evidence",
        published_at="2026-10-11T07:00:00+00:00",observed_at="2026-10-11T07:00:05+00:00",
    )
    item=RawNewsItem(source=source,title="Bitcoin, gold and DXY reacted to the release.",body="EUR/USD was also active.")
    mapped=map_news_item(item,registry=registry)
    payload={
        "schema_version":"1.0","kind":"NEXUS_QUANT_P11C_ENTITY_ASSET_MAPPING_EVIDENCE",
        "task_id":"FIN-P11-WC-001","registry_sha256":hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "news_content_id":mapped.news_content_id,"state":mapped.state,
        "matches":[{"entity_id":m.entity_id,"symbol":m.symbol,"confidence":m.confidence} for m in mapped.matches],
        "network_required":registry.canonical_tests_network_required,
        "live_trading":registry.live_trading,"auto_trading":registry.auto_trading,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P11C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
