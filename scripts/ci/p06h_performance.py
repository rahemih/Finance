#!/usr/bin/env python3
"""Measured synthetic P06-H replay-scan and feature-rebuild sanity benchmark."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    FeatureDefinition,
    FeatureMaterializationPolicy,
    FeatureMaterializer,
    QualityEligibility,
    RetentionCapacityPolicy,
)

RETENTION_POLICY = ROOT / "config/historical-data/retention-capacity-policy.json"
FEATURE_POLICY = ROOT / "config/historical-data/feature-materialization-policy.json"
MIB = 1024 * 1024


def replay_scan_benchmark() -> tuple[int, float, float]:
    size_bytes = 16 * MIB
    seed = b"NEXUS_QUANT_P06H_REPLAY_SCAN_REFERENCE\n"
    repeats = (size_bytes // len(seed)) + 1
    payload = (seed * repeats)[:size_bytes]
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "replay-reference.bin"
        path.write_bytes(payload)
        digest = hashlib.sha256()
        started = time.perf_counter()
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(MIB)
                if not chunk:
                    break
                digest.update(chunk)
        elapsed = max(time.perf_counter() - started, 1e-9)
        if digest.hexdigest() != hashlib.sha256(payload).hexdigest():
            raise RuntimeError("replay scan digest mismatch")
    mib_per_sec = (size_bytes / MIB) / elapsed
    return size_bytes, elapsed, mib_per_sec


def feature_rebuild_benchmark() -> tuple[int, float, float]:
    _ = FeatureMaterializationPolicy.from_path(FEATURE_POLICY)
    definition = FeatureDefinition(
        feature_name="feature.reference.p06h-rebuild",
        definition_version="1.0.0",
        output_type="DECIMAL",
        code_sha256=hashlib.sha256(b"p06h-feature-code").hexdigest(),
        config_sha256=hashlib.sha256(b"p06h-feature-config").hexdigest(),
        description="Synthetic P06-H feature rebuild benchmark.",
    )
    quality = QualityEligibility(
        status="ELIGIBLE",
        quality_policy_version="reference-quality-v1",
        evidence_sha256="d" * 64,
    )
    count = 3000
    started = time.perf_counter()
    digest = hashlib.sha256()
    for index in range(count):
        item = FeatureMaterializer.materialize(
            definition=definition,
            entity_id=f"CRYPTO:REF-{index}",
            event_time_ns=index,
            as_of_time_ns=index + 1,
            value_text=str(index),
            source_dataset_version="a" * 64,
            source_vintage_ids=(),
            source_cutoff_ns=index,
            quality=quality,
        )
        digest.update(item.materialization_id.encode("ascii"))
    elapsed = max(time.perf_counter() - started, 1e-9)
    if not digest.hexdigest():
        raise RuntimeError("feature rebuild benchmark produced no digest")
    per_sec = count / elapsed
    return count, elapsed, per_sec


def build(output: Path) -> None:
    policy = RetentionCapacityPolicy.from_path(RETENTION_POLICY)
    scan_bytes, scan_elapsed, scan_rate = replay_scan_benchmark()
    feature_count, feature_elapsed, feature_rate = feature_rebuild_benchmark()

    scan_pass = Decimal(str(scan_rate)) >= policy.replay_scan_floor_mib_per_sec
    feature_pass = Decimal(str(feature_rate)) >= policy.feature_rebuild_floor_per_sec
    if not scan_pass:
        raise RuntimeError(
            f"replay scan below reference floor: {scan_rate:.3f} MiB/s"
        )
    if not feature_pass:
        raise RuntimeError(
            f"feature rebuild below reference floor: {feature_rate:.3f}/s"
        )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06H_MEASURED_SYNTHETIC_PERFORMANCE",
        "measurement_class": "CI_REFERENCE_SANITY_NOT_PRODUCTION_BENCHMARK",
        "replay_scan": {
            "bytes": scan_bytes,
            "elapsed_seconds": round(scan_elapsed, 6),
            "mib_per_sec": round(scan_rate, 3),
            "floor_mib_per_sec": str(policy.replay_scan_floor_mib_per_sec),
            "pass": scan_pass
        },
        "feature_rebuild": {
            "materializations": feature_count,
            "elapsed_seconds": round(feature_elapsed, 6),
            "materializations_per_sec": round(feature_rate, 3),
            "floor_per_sec": str(policy.feature_rebuild_floor_per_sec),
            "pass": feature_pass
        },
        "production_claim": False,
        "production_storage_vendor": policy.production_storage_vendor
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "P06H_PERFORMANCE=PASS "
        f"scan_mib_s={scan_rate:.3f} feature_rebuild_s={feature_rate:.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
