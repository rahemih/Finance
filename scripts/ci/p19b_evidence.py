#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from packages.shadow.data_replay import (
    DataReplayEngine,
    DataReplayPolicy,
    ReplayDataEvent,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
P19A = ROOT / "docs/14-shadow/p19-a-shadow-decisioning.json"
POLICY_PATH = ROOT / "config/shadow/data-replay-policy.json"
SNAPSHOT_POLICY_PATH = ROOT / "config/historical-data/replay-snapshot-policy.json"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    p19a = json.loads(P19A.read_text(encoding="utf-8"))
    if (
        not isinstance(p19a, dict)
        or p19a.get("kind") != "NEXUS_QUANT_P19A_SHADOW_DECISIONING"
        or p19a.get("state") != "CANONICAL_COMPLETE"
        or p19a.get("lock") != "RELEASED"
    ):
        raise RuntimeError("P19-A canonical closure is required before P19-B evidence")

    data = json.loads(DATA.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("kind") != "NEXUS_QUANT_PUBLIC_MARKET_REFERENCE_DATASET"
        or data.get("fixture_only") is not False
        or data.get("asset_id") != "BTC-USD"
    ):
        raise RuntimeError("non-fixture BTC-USD reference dataset required")
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) < 10:
        raise RuntimeError("reference dataset rows missing")

    dataset_sha = file_sha(DATA)
    membership_sha = hashlib.sha256(
        canonical_bytes({"asset_id": "BTC-USD", "member": True})
    ).hexdigest()
    snapshot_policy = ReplaySnapshotPolicy.from_path(SNAPSHOT_POLICY_PATH)
    policy = DataReplayPolicy.from_path(POLICY_PATH)

    last_event_time = len(rows) * 1000
    cutoff = last_event_time + 100
    replay_end = (len(rows) + 1) * 1000
    snapshot = ReplaySnapshot.build(
        replay_start_ns=1000,
        replay_end_ns=replay_end,
        snapshot_cutoff_ns=cutoff,
        clock_mode="CONTROLLED_SIMULATION_CLOCK",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                dataset_name="btc-usd-public-reference",
                dataset_version=dataset_sha,
                schema_version="1.0",
                window_start_ns=1000,
                window_end_ns=replay_end,
                membership_root_sha256=membership_sha,
                rights_class="PUBLIC_REFERENCE",
            ),
        ),
        feature_refs=(),
        vintage_refs=(),
        quality_rule_versions=("p19b-public-reference-v1",),
        config_sha256=file_sha(POLICY_PATH),
        code_artifact_sha256=file_sha(Path(__file__)),
        rights_class="PUBLIC_REFERENCE",
        policy=snapshot_policy,
    )

    events: list[ReplayDataEvent] = []
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            raise RuntimeError("market row must be object")
        event_time = index * 1000
        events.append(
            ReplayDataEvent.create(
                sequence=index,
                event_time_ns=event_time,
                available_at_ns=event_time + 100,
                dataset_name="btc-usd-public-reference",
                dataset_version=dataset_sha,
                entity_id="BTC-USD",
                payload=raw,
                source_evidence_sha256=hashlib.sha256(
                    canonical_bytes({"row": raw, "dataset_sha256": dataset_sha})
                ).hexdigest(),
            )
        )

    engine = DataReplayEngine(
        snapshot=snapshot,
        events=tuple(reversed(events)),
        policy=policy,
    )
    partial_time = 5100
    partial = engine.replay_through(partial_time)
    full = engine.replay_through(cutoff)

    if len(partial.events) != 5:
        raise RuntimeError("partial replay must expose exactly five visible events")
    if len(full.events) != len(rows):
        raise RuntimeError("full replay did not expose every reference row")
    if full.event_ids != tuple(event.event_id for event in events):
        raise RuntimeError("controlled replay ordering is not canonical")
    if any(
        (
            full.decision_authority,
            full.fill_authority,
            full.execution_authority,
            full.order_routing_authority,
            full.broker_exchange_routing,
            full.p20_started,
        )
    ):
        raise RuntimeError("P19-B authority escalation detected")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19B_DATA_REPLAY_EVIDENCE",
        "task_id": "FIN-P19-WB-001",
        "phase": "P19",
        "workstream": "P19-B",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "fixture_only": False,
        "p19a_manifest_sha256": file_sha(P19A),
        "dataset_sha256": dataset_sha,
        "snapshot_id": snapshot.snapshot_id,
        "policy_id": policy.policy_id,
        "clock_mode": snapshot.clock_mode,
        "partial_decision_time_ns": partial_time,
        "partial_event_count": len(partial.events),
        "partial_result_id": partial.result_id,
        "full_decision_time_ns": cutoff,
        "full_event_count": len(full.events),
        "full_result_id": full.result_id,
        "full_event_ids": list(full.event_ids),
        "anti_lookahead_owner": "P06_G_REPLAY_SNAPSHOT",
        "network_required": False,
        "credentials_required": False,
        "decision_authority": False,
        "fill_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p19_active_workstream": "P19-B",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19B_DATA_REPLAY_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
