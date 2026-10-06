#!/usr/bin/env python3
"""Build deterministic P06-F feature lineage and point-in-time evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    FeatureBatch,
    FeatureDefinition,
    FeatureMaterializationPolicy,
    FeatureMaterializer,
    FilesystemFeatureArtifactStore,
    QualityEligibility,
)

POLICY = ROOT / "config/historical-data/feature-materialization-policy.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    policy = FeatureMaterializationPolicy.from_path(POLICY)
    definition = FeatureDefinition(
        feature_name="feature.reference.macro-surprise",
        definition_version="1.0.0",
        output_type="DECIMAL",
        code_sha256=hashlib.sha256(b"p06f-reference-code").hexdigest(),
        config_sha256=hashlib.sha256(b"p06f-reference-config").hexdigest(),
        description="Reference P06-F feature proving exact lineage and point-in-time cutoff.",
    )
    dataset_version = "a" * 64
    vintage_a = "b" * 64
    vintage_b = "c" * 64
    quality = QualityEligibility(
        status="ELIGIBLE",
        quality_policy_version="reference-quality-v1",
        evidence_sha256="d" * 64,
    )
    first = FeatureMaterializer.materialize(
        definition=definition,
        entity_id="MACRO:CPI:REFERENCE",
        event_time_ns=180,
        as_of_time_ns=200,
        value_text="0.4",
        source_dataset_version=dataset_version,
        source_vintage_ids=(vintage_b, vintage_a),
        source_cutoff_ns=195,
        quality=quality,
    )
    reordered = FeatureMaterializer.materialize(
        definition=definition,
        entity_id="MACRO:CPI:REFERENCE",
        event_time_ns=180,
        as_of_time_ns=200,
        value_text="0.4",
        source_dataset_version=dataset_version,
        source_vintage_ids=(vintage_a, vintage_b),
        source_cutoff_ns=195,
        quality=quality,
    )
    batch = FeatureBatch.build((first,), policy)

    with tempfile.TemporaryDirectory() as temp:
        store = FilesystemFeatureArtifactStore(Path(temp), policy)
        definition_write = store.save_definition(definition)
        first_write = store.save_materialization(first)
        second_write = store.save_materialization(first)
        loaded_definition = store.load_definition(definition.definition_id)
        loaded_materialization = store.load_materialization(
            definition.definition_id,
            first.materialization_id,
        )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06F_FEATURE_MATERIALIZATION_EVIDENCE",
        "policy_sha256": sha256(POLICY),
        "definition_id": definition.definition_id,
        "materialization_id": first.materialization_id,
        "batch_fingerprint": batch.fingerprint,
        "source_dataset_version": first.source_dataset_version,
        "source_vintage_ids": list(first.source_vintage_ids),
        "source_cutoff_ns": first.source_cutoff_ns,
        "as_of_time_ns": first.as_of_time_ns,
        "quality_status": first.quality_status,
        "quality_policy_version": first.quality_policy_version,
        "quality_evidence_sha256": first.quality_evidence_sha256,
        "vintage_order_independent": first.materialization_id == reordered.materialization_id,
        "point_in_time_valid": first.source_cutoff_ns <= first.as_of_time_ns,
        "round_trip_exact": loaded_definition == definition and loaded_materialization == first,
        "definition_write_created": definition_write.created,
        "first_materialization_write_created": first_write.created,
        "second_materialization_write_idempotent": not second_write.created,
        "production_feature_storage_vendor": policy.production_feature_storage_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P06F_EVIDENCE=PASS output={output}")
    print(f"P06F_MATERIALIZATION_ID={first.materialization_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
