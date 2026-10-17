from __future__ import annotations

from dataclasses import replace
import unittest

from quant.backtesting.model_registry import (
    ModelRegistryError,
    ModelVersion,
    build_model_registry,
)


def record(**overrides: object) -> ModelVersion:
    values: dict[str, object] = {
        "model_id": "model-1",
        "version": "1.0.0",
        "lifecycle_state": "VALIDATED",
        "model_artifact_sha256": "a" * 64,
        "code_sha256": "b" * 64,
        "config_sha256": "c" * 64,
        "feature_schema_sha256": "d" * 64,
        "training_dataset_sha256": "e" * 64,
        "strategy_record_sha256": "f" * 64,
        "walk_forward_certificate_sha256": "1" * 64,
        "robustness_certificate_sha256": "2" * 64,
    }
    values.update(overrides)
    return ModelVersion(**values)  # type: ignore[arg-type]


class ModelRegistryTests(unittest.TestCase):
    def test_validated_record_builds(self) -> None:
        registry = build_model_registry([record()])
        self.assertEqual(len(registry.records), 1)
        self.assertFalse(registry.automatic_retraining)
        self.assertFalse(registry.automatic_promotion)
        self.assertFalse(registry.g9_authority)

    def test_validated_requires_lineage(self) -> None:
        with self.assertRaises(ModelRegistryError):
            record(walk_forward_certificate_sha256=None)

    def test_invalid_hash_fails_closed(self) -> None:
        with self.assertRaises(ModelRegistryError):
            record(model_artifact_sha256="bad")

    def test_unsupported_state_fails_closed(self) -> None:
        with self.assertRaises(ModelRegistryError):
            record(lifecycle_state="LIVE")

    def test_divergent_same_version_fails_closed(self) -> None:
        with self.assertRaises(ModelRegistryError):
            build_model_registry([record(), replace(record(), config_sha256="3" * 64)])

    def test_exact_duplicate_is_idempotent(self) -> None:
        r = record()
        self.assertEqual(len(build_model_registry([r, r]).records), 1)

    def test_order_independent_identity(self) -> None:
        a = record(model_id="a")
        b = record(model_id="b", version="2.0.0")
        self.assertEqual(
            build_model_registry([a, b]).registry_id,
            build_model_registry([b, a]).registry_id,
        )


if __name__ == "__main__":
    unittest.main()
