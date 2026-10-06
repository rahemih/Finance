from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from packages.historical_data import (
    FeatureArtifactIntegrityError,
    FeatureBatch,
    FeatureDefinition,
    FeatureMaterialization,
    FeatureMaterializationError,
    FeatureMaterializationPolicy,
    FeatureMaterializer,
    FilesystemFeatureArtifactStore,
    QualityEligibility,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/historical-data/feature-materialization-policy.json"
DATASET_VERSION = "a" * 64
VINTAGE_A = "b" * 64
VINTAGE_B = "c" * 64
QUALITY_EVIDENCE = "d" * 64


def definition(*, config_seed: str = "config-v1") -> FeatureDefinition:
    return FeatureDefinition(
        feature_name="feature.reference.momentum",
        definition_version="1.0.0",
        output_type="DECIMAL",
        code_sha256=hashlib.sha256(b"reference-feature-code-v1").hexdigest(),
        config_sha256=hashlib.sha256(config_seed.encode("utf-8")).hexdigest(),
        description="Deterministic reference feature used to certify P06-F contracts.",
    )


def quality(status: str = "ELIGIBLE") -> QualityEligibility:
    return QualityEligibility(
        status=status,
        quality_policy_version="reference-quality-v1",
        evidence_sha256=QUALITY_EVIDENCE,
    )


def materialization(
    *,
    vintages: tuple[str, ...] = (VINTAGE_A, VINTAGE_B),
    value: str = "1.25",
    as_of: int = 200,
    cutoff: int = 190,
    eligibility: str = "ELIGIBLE",
) -> FeatureMaterialization:
    return FeatureMaterializer.materialize(
        definition=definition(),
        entity_id="CRYPTO:BTC-USD",
        event_time_ns=180,
        as_of_time_ns=as_of,
        value_text=value,
        source_dataset_version=DATASET_VERSION,
        source_vintage_ids=vintages,
        source_cutoff_ns=cutoff,
        quality=quality(eligibility),
    )


class FeaturePolicyTests(unittest.TestCase):
    def test_policy_is_offline_and_vendor_neutral(self):
        policy = FeatureMaterializationPolicy.from_path(POLICY)
        self.assertEqual(policy.production_feature_storage_vendor, "NOT_SELECTED")
        self.assertGreater(policy.max_materializations_per_batch, 0)
        self.assertGreater(policy.max_artifact_bytes, 0)


class FeatureDefinitionTests(unittest.TestCase):
    def test_definition_identity_is_deterministic_and_content_sensitive(self):
        first = definition()
        second = definition()
        changed = definition(config_seed="config-v2")
        self.assertEqual(first.definition_id, second.definition_id)
        self.assertNotEqual(first.definition_id, changed.definition_id)
        self.assertEqual(FeatureDefinition.from_bytes(first.to_bytes()), first)


class FeatureMaterializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = FeatureMaterializationPolicy.from_path(POLICY)

    def test_vintage_lineage_is_order_independent(self):
        first = materialization(vintages=(VINTAGE_A, VINTAGE_B))
        second = materialization(vintages=(VINTAGE_B, VINTAGE_A, VINTAGE_B))
        self.assertEqual(first.source_vintage_ids, (VINTAGE_A, VINTAGE_B))
        self.assertEqual(first.materialization_id, second.materialization_id)
        self.assertEqual(first.to_bytes(), second.to_bytes())

    def test_materialization_identity_changes_with_value(self):
        self.assertNotEqual(
            materialization(value="1.25").materialization_id,
            materialization(value="1.26").materialization_id,
        )

    def test_only_explicit_eligible_quality_can_materialize(self):
        for status in ("INELIGIBLE", "QUARANTINED", "UNKNOWN"):
            with self.subTest(status=status):
                with self.assertRaises(FeatureMaterializationError):
                    materialization(eligibility=status)

    def test_source_cutoff_after_as_of_fails_closed(self):
        with self.assertRaises(FeatureMaterializationError):
            materialization(as_of=200, cutoff=201)

    def test_event_time_after_as_of_fails_closed(self):
        d = definition()
        with self.assertRaises(FeatureMaterializationError):
            FeatureMaterializer.materialize(
                definition=d,
                entity_id="CRYPTO:BTC-USD",
                event_time_ns=201,
                as_of_time_ns=200,
                value_text="1.0",
                source_dataset_version=DATASET_VERSION,
                source_vintage_ids=(),
                source_cutoff_ns=199,
                quality=quality(),
            )

    def test_invalid_lineage_hash_fails_closed(self):
        d = definition()
        with self.assertRaises(FeatureMaterializationError):
            FeatureMaterializer.materialize(
                definition=d,
                entity_id="CRYPTO:BTC-USD",
                event_time_ns=100,
                as_of_time_ns=200,
                value_text="1.0",
                source_dataset_version="bad",
                source_vintage_ids=(),
                source_cutoff_ns=150,
                quality=quality(),
            )

    def test_round_trip_verifies_materialization_identity(self):
        value = materialization()
        self.assertEqual(FeatureMaterialization.from_bytes(value.to_bytes()), value)

    def test_tampered_materialization_fails_integrity(self):
        value = materialization()
        payload = json.loads(value.to_bytes().decode("utf-8"))
        payload["value_text"] = "999.0"
        tampered = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        with self.assertRaises(FeatureArtifactIntegrityError):
            FeatureMaterialization.from_bytes(tampered)

    def test_batch_fingerprint_is_order_independent(self):
        first = materialization(value="1.25")
        second = FeatureMaterializer.materialize(
            definition=definition(),
            entity_id="CRYPTO:ETH-USD",
            event_time_ns=181,
            as_of_time_ns=200,
            value_text="2.50",
            source_dataset_version=DATASET_VERSION,
            source_vintage_ids=(),
            source_cutoff_ns=190,
            quality=quality(),
        )
        a = FeatureBatch.build((first, second), self.policy)
        b = FeatureBatch.build((second, first), self.policy)
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertEqual(a.materializations, b.materializations)

    def test_duplicate_logical_key_fails_closed(self):
        first = materialization(value="1.25")
        second = materialization(value="1.26")
        with self.assertRaises(FeatureMaterializationError):
            FeatureBatch.build((first, second), self.policy)

    def test_store_is_write_once_idempotent_and_verifies_loads(self):
        d = definition()
        value = materialization()
        with tempfile.TemporaryDirectory() as temp:
            store = FilesystemFeatureArtifactStore(Path(temp), self.policy)
            d1 = store.save_definition(d)
            d2 = store.save_definition(d)
            m1 = store.save_materialization(value)
            m2 = store.save_materialization(value)
            self.assertTrue(d1.created)
            self.assertFalse(d2.created)
            self.assertTrue(m1.created)
            self.assertFalse(m2.created)
            self.assertEqual(store.load_definition(d.definition_id), d)
            self.assertEqual(
                store.load_materialization(d.definition_id, value.materialization_id),
                value,
            )

    def test_tampered_stored_artifact_fails_on_load(self):
        value = materialization()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = FilesystemFeatureArtifactStore(root, self.policy)
            saved = store.save_materialization(value)
            target = root / saved.relative_path
            raw = bytearray(target.read_bytes())
            raw[-2] = ord(" ")
            target.write_bytes(bytes(raw))
            with self.assertRaises(FeatureArtifactIntegrityError):
                store.load_materialization(value.definition_id, value.materialization_id)

    def test_batch_policy_bound_fails_closed(self):
        tiny = FeatureMaterializationPolicy(
            max_materializations_per_batch=1,
            max_artifact_bytes=self.policy.max_artifact_bytes,
            production_feature_storage_vendor="NOT_SELECTED",
        )
        first = materialization()
        second = FeatureMaterializer.materialize(
            definition=definition(),
            entity_id="CRYPTO:ETH-USD",
            event_time_ns=181,
            as_of_time_ns=200,
            value_text="2.0",
            source_dataset_version=DATASET_VERSION,
            source_vintage_ids=(),
            source_cutoff_ns=190,
            quality=quality(),
        )
        with self.assertRaises(FeatureMaterializationError):
            FeatureBatch.build((first, second), tiny)

    def test_core_module_has_no_feature_store_database_or_cloud_clients(self):
        text = (ROOT / "packages/historical_data/feature_materialization.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "feast",
            "tecton",
            "psycopg",
            "sqlalchemy",
            "clickhouse",
            "timescale",
            "boto3",
            "adapters.",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
