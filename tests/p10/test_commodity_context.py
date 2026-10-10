from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.fundamental_intelligence.commodity_context import (
    CommodityContextError,
    CommodityContextPolicy,
    CommodityContextStore,
    CommodityFundamentalPoint,
    assert_no_commodity_trade_authority_fields,
    compute_oil_balance,
    validate_commodity_point,
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


def point(
    vintage: MacroVintage,
    commodity: str,
    metric: str,
    geography: str,
) -> CommodityFundamentalPoint:
    return CommodityFundamentalPoint(vintage, commodity, metric, geography)


def policy() -> CommodityContextPolicy:
    return CommodityContextPolicy.from_path(PP)


def registry() -> OfficialSourceRegistry:
    return OfficialSourceRegistry.from_path(SR, policy=OfficialSourcePolicy.from_path(SP))


def macro_policy() -> MacroVintagePolicy:
    return MacroVintagePolicy.from_path(MP)


def store() -> CommodityContextStore:
    points = (
        point(
            macro("OIL:INVENTORY:US", 100, 100, 105, 0, "430", "MILLION_BARRELS", "EIA"),
            "CRUDE_OIL",
            "OIL_INVENTORY_LEVEL",
            "US",
        ),
        point(
            macro("OIL:INVENTORY:US", 100, 200, 205, 1, "432", "MILLION_BARRELS", "EIA"),
            "CRUDE_OIL",
            "OIL_INVENTORY_LEVEL",
            "US",
        ),
        point(
            macro("OIL:SUPPLY:GLOBAL", 110, 110, 112, 0, "102", "MILLION_BARRELS_PER_DAY", "OPEC"),
            "CRUDE_OIL",
            "OIL_SUPPLY_LEVEL",
            "GLOBAL",
        ),
        point(
            macro("OIL:DEMAND:GLOBAL", 111, 111, 113, 0, "100", "MILLION_BARRELS_PER_DAY", "IEA"),
            "CRUDE_OIL",
            "OIL_DEMAND_LEVEL",
            "GLOBAL",
        ),
        point(
            macro("GOLD:ETF:HOLDINGS", 120, 120, 122, 0, "3100", "TONNES", "WGC"),
            "GOLD",
            "GOLD_ETF_HOLDINGS",
            "GLOBAL",
        ),
        point(
            macro("GOLD:ETF:HOLDINGS", 120, 220, 222, 1, "3125", "TONNES", "WGC"),
            "GOLD",
            "GOLD_ETF_HOLDINGS",
            "GLOBAL",
        ),
    )
    return CommodityContextStore(
        points,
        policy=policy(),
        source_registry=registry(),
        macro_policy=macro_policy(),
    )


class CommodityContextTests(unittest.TestCase):
    def test_metric_unit_and_official_source_guards(self) -> None:
        good = point(
            macro("OIL:X", 1, 1, 1, 0, "430", "MILLION_BARRELS", "EIA"),
            "CRUDE_OIL",
            "OIL_INVENTORY_LEVEL",
            "US",
        )
        self.assertEqual(
            validate_commodity_point(good, policy=policy(), source_registry=registry()),
            good,
        )
        bad_source = point(
            macro("OIL:BAD", 1, 1, 1, 0, "430", "MILLION_BARRELS", "WGC"),
            "CRUDE_OIL",
            "OIL_INVENTORY_LEVEL",
            "US",
        )
        with self.assertRaises(CommodityContextError):
            validate_commodity_point(bad_source, policy=policy(), source_registry=registry())
        bad_unit = point(
            macro("GOLD:BAD", 1, 1, 1, 0, "100", "PERCENT", "WGC"),
            "GOLD",
            "GOLD_ETF_HOLDINGS",
            "GLOBAL",
        )
        with self.assertRaises(CommodityContextError):
            validate_commodity_point(bad_unit, policy=policy(), source_registry=registry())

    def test_latest_as_of_excludes_later_revision(self) -> None:
        s = store()
        before = s.resolve_latest_as_of(series_id="OIL:INVENTORY:US", decision_time_ns=150)
        after = s.resolve_latest_as_of(series_id="OIL:INVENTORY:US", decision_time_ns=250)
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        if before is None or after is None:
            self.fail("commodity points expected")
        self.assertEqual(before.vintage.value_text, "430")
        self.assertEqual(after.vintage.value_text, "432")

        gold_before = s.resolve_latest_as_of(series_id="GOLD:ETF:HOLDINGS", decision_time_ns=150)
        gold_after = s.resolve_latest_as_of(series_id="GOLD:ETF:HOLDINGS", decision_time_ns=250)
        self.assertIsNotNone(gold_before)
        self.assertIsNotNone(gold_after)
        if gold_before is None or gold_after is None:
            self.fail("gold points expected")
        self.assertEqual(gold_before.vintage.value_text, "3100")
        self.assertEqual(gold_after.vintage.value_text, "3125")

    def test_oil_balance_is_supply_minus_demand(self) -> None:
        result = compute_oil_balance(
            store=store(),
            supply_series_id="OIL:SUPPLY:GLOBAL",
            demand_series_id="OIL:DEMAND:GLOBAL",
            decision_time_ns=150,
        )
        self.assertEqual(result.balance_value_text, "2")
        self.assertEqual(result.unit, "MILLION_BARRELS_PER_DAY")
        self.assertEqual(result.geography, "GLOBAL")

    def test_oil_balance_mismatch_fails_closed(self) -> None:
        bad_store = CommodityContextStore(
            (
                point(
                    macro("OIL:S", 1, 1, 1, 0, "102", "MILLION_BARRELS_PER_DAY", "EIA"),
                    "CRUDE_OIL",
                    "OIL_SUPPLY_LEVEL",
                    "GLOBAL",
                ),
                point(
                    macro("OIL:D", 1, 1, 1, 0, "100", "MILLION_BARRELS_PER_DAY", "EIA"),
                    "CRUDE_OIL",
                    "OIL_DEMAND_LEVEL",
                    "US",
                ),
            ),
            policy=policy(),
            source_registry=registry(),
            macro_policy=macro_policy(),
        )
        with self.assertRaises(CommodityContextError):
            compute_oil_balance(
                store=bad_store,
                supply_series_id="OIL:S",
                demand_series_id="OIL:D",
                decision_time_ns=10,
            )
        assert_no_commodity_trade_authority_fields()


if __name__ == "__main__":
    unittest.main()
