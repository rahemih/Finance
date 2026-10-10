from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.fundamental_intelligence.commodity_context import (
    CommodityContextPolicy,
    CommodityContextStore,
    CommodityFundamentalPoint,
    assert_no_commodity_trade_authority_fields,
    compute_oil_balance,
)
from packages.fundamental_intelligence.source_registry import OfficialSourcePolicy, OfficialSourceRegistry
from packages.historical_data.macro_vintage import MacroVintage, MacroVintagePolicy

ROOT = Path(__file__).resolve().parents[2]
PP = ROOT / "config/fundamental-intelligence/commodity-context-policy.json"
SP = ROOT / "config/fundamental-intelligence/official-source-policy.json"
SR = ROOT / "config/fundamental-intelligence/official-source-registry.json"
MP = ROOT / "config/historical-data/macro-vintage-policy.json"
DATASET = "d" * 64


def macro(
    series: str,
    observation: int,
    release: int,
    observed: int,
    revision: int,
    value: str,
    unit: str,
    source: str,
) -> MacroVintage:
    digest = hashlib.sha256(
        f"{series}:{observation}:{release}:{observed}:{revision}:{value}:{unit}:{source}".encode()
    ).hexdigest()
    return MacroVintage(
        series,
        observation,
        release,
        observed,
        revision,
        value,
        unit,
        source,
        DATASET,
        digest,
        f"macro/{digest}.raw",
        f"rev-{revision}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = CommodityContextPolicy.from_path(PP)
    registry = OfficialSourceRegistry.from_path(SR, policy=OfficialSourcePolicy.from_path(SP))
    macro_policy = MacroVintagePolicy.from_path(MP)

    points = (
        CommodityFundamentalPoint(
            macro("OIL:INVENTORY:US", 100, 100, 105, 0, "430", "MILLION_BARRELS", "EIA"),
            "CRUDE_OIL",
            "OIL_INVENTORY_LEVEL",
            "US",
        ),
        CommodityFundamentalPoint(
            macro("OIL:INVENTORY:US", 100, 200, 205, 1, "432", "MILLION_BARRELS", "EIA"),
            "CRUDE_OIL",
            "OIL_INVENTORY_LEVEL",
            "US",
        ),
        CommodityFundamentalPoint(
            macro("OIL:SUPPLY:GLOBAL", 110, 110, 112, 0, "102", "MILLION_BARRELS_PER_DAY", "OPEC"),
            "CRUDE_OIL",
            "OIL_SUPPLY_LEVEL",
            "GLOBAL",
        ),
        CommodityFundamentalPoint(
            macro("OIL:DEMAND:GLOBAL", 111, 111, 113, 0, "100", "MILLION_BARRELS_PER_DAY", "IEA"),
            "CRUDE_OIL",
            "OIL_DEMAND_LEVEL",
            "GLOBAL",
        ),
        CommodityFundamentalPoint(
            macro("GOLD:ETF:HOLDINGS", 120, 120, 122, 0, "3100", "TONNES", "WGC"),
            "GOLD",
            "GOLD_ETF_HOLDINGS",
            "GLOBAL",
        ),
        CommodityFundamentalPoint(
            macro("GOLD:ETF:HOLDINGS", 120, 220, 222, 1, "3125", "TONNES", "WGC"),
            "GOLD",
            "GOLD_ETF_HOLDINGS",
            "GLOBAL",
        ),
    )
    store = CommodityContextStore(
        points,
        policy=policy,
        source_registry=registry,
        macro_policy=macro_policy,
    )
    balance = compute_oil_balance(
        store=store,
        supply_series_id="OIL:SUPPLY:GLOBAL",
        demand_series_id="OIL:DEMAND:GLOBAL",
        decision_time_ns=150,
    )
    inventory_before = store.resolve_latest_as_of(
        series_id="OIL:INVENTORY:US",
        decision_time_ns=150,
    )
    inventory_after = store.resolve_latest_as_of(
        series_id="OIL:INVENTORY:US",
        decision_time_ns=250,
    )
    gold_before = store.resolve_latest_as_of(
        series_id="GOLD:ETF:HOLDINGS",
        decision_time_ns=150,
    )
    gold_after = store.resolve_latest_as_of(
        series_id="GOLD:ETF:HOLDINGS",
        decision_time_ns=250,
    )
    if inventory_before is None or inventory_after is None or gold_before is None or gold_after is None:
        raise RuntimeError("evidence fixture failed")
    assert_no_commodity_trade_authority_fields()

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P10F_COMMODITY_CONTEXT_EVIDENCE",
        "task_id": "FIN-P10-WF-001",
        "policy_sha256": hashlib.sha256(PP.read_bytes()).hexdigest(),
        "store_fingerprint": store.fingerprint,
        "oil_balance": balance.payload(),
        "pre_revision_oil_inventory_value": inventory_before.vintage.value_text,
        "post_revision_oil_inventory_value": inventory_after.vintage.value_text,
        "pre_revision_gold_etf_holdings": gold_before.vintage.value_text,
        "post_revision_gold_etf_holdings": gold_after.vintage.value_text,
        "latest_as_of_rule": policy.latest_as_of_rule,
        "oil_balance_rule": policy.oil_balance_rule,
        "market_direction_interpretation_allowed": policy.market_direction_interpretation_allowed,
        "causal_market_impact_claim_allowed": policy.causal_market_impact_claim_allowed,
        "production_source_mapping": policy.production_source_mapping,
        "country_assumption": "NONE",
        "live_trading": policy.live_trading,
        "auto_trading": policy.auto_trading,
        "network_required": policy.network_required,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P10F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
