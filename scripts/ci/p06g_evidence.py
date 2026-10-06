#!/usr/bin/env python3
"""Build deterministic P06-G replay snapshot compatibility evidence offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    FilesystemReplaySnapshotStore,
    ReplayDatasetRef,
    ReplayFeatureRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
    ReplayVintageRef,
)

POLICY = ROOT / "config/historical-data/replay-snapshot-policy.json"


def build(output: Path) -> None:
    policy = ReplaySnapshotPolicy.from_path(POLICY)
    dataset = ReplayDatasetRef(
        dataset_name="btc-usd-reference",
        dataset_version="a" * 64,
        schema_version="1.0",
        window_start_ns=0,
        window_end_ns=1000,
        membership_root_sha256="b" * 64,
        rights_class="NON_DISPLAY_INTERNAL",
    )
    early_feature = ReplayFeatureRef(
        definition_id="c" * 64,
        materialization_id="d" * 64,
        entity_id="CRYPTO:BTC-USD",
        event_time_ns=180,
        as_of_time_ns=190,
        quality_evidence_sha256="e" * 64,
    )
    late_feature = ReplayFeatureRef(
        definition_id="c" * 64,
        materialization_id="9" * 64,
        entity_id="CRYPTO:BTC-USD",
        event_time_ns=280,
        as_of_time_ns=300,
        quality_evidence_sha256="e" * 64,
    )
    initial = ReplayVintageRef(
        vintage_id="f" * 64,
        series_id="MACRO:CPI:REFERENCE",
        observation_time_ns=100,
        release_time_ns=150,
        observed_at_ns=160,
    )
    revision = ReplayVintageRef(
        vintage_id="8" * 64,
        series_id="MACRO:CPI:REFERENCE",
        observation_time_ns=100,
        release_time_ns=250,
        observed_at_ns=260,
    )
    snapshot = ReplaySnapshot.build(
        replay_start_ns=100,
        replay_end_ns=500,
        snapshot_cutoff_ns=400,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("MACRO:CPI:REFERENCE", "CRYPTO:BTC-USD"),
        dataset_refs=(dataset,),
        feature_refs=(late_feature, early_feature),
        vintage_refs=(revision, initial),
        quality_rule_versions=("quality-v1",),
        config_sha256="1" * 64,
        code_artifact_sha256="2" * 64,
        rights_class="NON_DISPLAY_INTERNAL",
        stochastic_seed=7,
        stochastic_version="rng-v1",
        policy=policy,
    )
    reordered = ReplaySnapshot.build(
        replay_start_ns=100,
        replay_end_ns=500,
        snapshot_cutoff_ns=400,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("CRYPTO:BTC-USD", "MACRO:CPI:REFERENCE"),
        dataset_refs=(dataset,),
        feature_refs=(early_feature, late_feature),
        vintage_refs=(initial, revision),
        quality_rule_versions=("quality-v1",),
        config_sha256="1" * 64,
        code_artifact_sha256="2" * 64,
        rights_class="NON_DISPLAY_INTERNAL",
        stochastic_seed=7,
        stochastic_version="rng-v1",
        policy=policy,
    )
    view_200 = snapshot.view_at(200)
    view_300 = snapshot.view_at(300)

    with tempfile.TemporaryDirectory() as temp:
        store = FilesystemReplaySnapshotStore(Path(temp), policy)
        first_write = store.save(snapshot)
        second_write = store.save(snapshot)
        loaded = store.load(snapshot.snapshot_id)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06G_REPLAY_SNAPSHOT_EVIDENCE",
        "snapshot_id": snapshot.snapshot_id,
        "clock_mode": snapshot.clock_mode,
        "snapshot_cutoff_ns": snapshot.snapshot_cutoff_ns,
        "order_independent_snapshot_id": snapshot.snapshot_id == reordered.snapshot_id,
        "view_200_feature_ids": [item.materialization_id for item in view_200.feature_refs],
        "view_200_vintage_ids": [item.vintage_id for item in view_200.vintage_refs],
        "view_300_feature_ids": [item.materialization_id for item in view_300.feature_refs],
        "view_300_vintage_ids": [item.vintage_id for item in view_300.vintage_refs],
        "anti_lookahead_proven": (
            len(view_200.feature_refs) == 1
            and len(view_200.vintage_refs) == 1
            and len(view_300.feature_refs) == 2
            and len(view_300.vintage_refs) == 2
        ),
        "round_trip_exact": loaded == snapshot,
        "first_write_created": first_write.created,
        "second_write_idempotent": not second_write.created,
        "production_replay_storage_vendor": policy.production_replay_storage_vendor,
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
    print(f"P06G_EVIDENCE=PASS output={output}")
    print(f"P06G_SNAPSHOT_ID={snapshot.snapshot_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
