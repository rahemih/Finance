from __future__ import annotations

from dataclasses import replace
import unittest

from quant.backtesting.strategy_registry import (
    StrategyRegistryError,
    StrategyVersion,
    build_strategy_registry,
)


def record(**overrides: object) -> StrategyVersion:
    values: dict[str, object] = {
        "strategy_id": "trend-1",
        "version": "1.0.0",
        "lifecycle_state": "VALIDATED",
        "definition_sha256": "a" * 64,
        "code_sha256": "b" * 64,
        "config_sha256": "c" * 64,
        "universe_id": "crypto-major",
        "timeframe_id": "1h",
        "walk_forward_certificate_sha256": "d" * 64,
        "robustness_certificate_sha256": "e" * 64,
        "capacity_certificate_sha256": "f" * 64,
    }
    values.update(overrides)
    return StrategyVersion(**values)  # type: ignore[arg-type]


class StrategyRegistryTests(unittest.TestCase):
    def test_validated_record_builds(self) -> None:
        registry = build_strategy_registry([record()])
        self.assertEqual(len(registry.records), 1)
        self.assertFalse(registry.automatic_promotion)
        self.assertFalse(registry.profitability_authority)
        self.assertFalse(registry.g9_authority)
        self.assertFalse(registry.execution_authority)

    def test_validated_requires_lineage(self) -> None:
        with self.assertRaises(StrategyRegistryError):
            record(capacity_certificate_sha256=None)

    def test_invalid_hash_fails_closed(self) -> None:
        with self.assertRaises(StrategyRegistryError):
            record(code_sha256="bad")

    def test_unsupported_state_fails_closed(self) -> None:
        with self.assertRaises(StrategyRegistryError):
            record(lifecycle_state="LIVE")

    def test_divergent_same_version_fails_closed(self) -> None:
        with self.assertRaises(StrategyRegistryError):
            build_strategy_registry([record(), replace(record(), config_sha256="1" * 64)])

    def test_exact_duplicate_is_idempotent(self) -> None:
        r = record()
        registry = build_strategy_registry([r, r])
        self.assertEqual(len(registry.records), 1)

    def test_order_independent_identity(self) -> None:
        a = record(strategy_id="a")
        b = record(strategy_id="b", version="2.0.0")
        left = build_strategy_registry([a, b])
        right = build_strategy_registry([b, a])
        self.assertEqual(left.registry_id, right.registry_id)


if __name__ == "__main__":
    unittest.main()
