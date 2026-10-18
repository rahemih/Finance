#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from packages.shadow.data_replay import DataReplayEngine, DataReplayPolicy, ReplayDataEvent
from packages.shadow.incident_replay import (
    IncidentDecisionRef,
    IncidentMarker,
    IncidentReplayEngine,
    IncidentReplayPolicy,
    IncidentSystemEvent,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
P19B_MANIFEST = ROOT / "docs/14-shadow/p19-b-data-replay.json"
P19C_MANIFEST = ROOT / "docs/14-shadow/p19-c-decision-replay.json"
DATA_POLICY_PATH = ROOT / "config/shadow/data-replay-policy.json"
INCIDENT_POLICY_PATH = ROOT / "config/shadow/incident-replay-policy.json"
SNAPSHOT_POLICY_PATH = ROOT / "config/historical-data/replay-snapshot-policy.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"object required: {path}")
    return value


def sha(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"{field} must be SHA-256")
    parsed = value.strip().lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise RuntimeError(f"{field} must be SHA-256")
    if len(set(parsed)) < 4:
        raise RuntimeError(f"{field} cannot be placeholder identity")
    return parsed


def build_data_replay(expected: Mapping[str, object]) -> DataReplayEngine:
    data = load(DATA)
    if (
        data.get("kind") != "NEXUS_QUANT_PUBLIC_MARKET_REFERENCE_DATASET"
        or data.get("fixture_only") is not False
        or data.get("asset_id") != "BTC-USD"
    ):
        raise RuntimeError("canonical non-fixture BTC-USD reference data required")
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) < 10:
        raise RuntimeError("reference dataset rows missing")
    dataset_sha = file_sha(DATA)
    if expected.get("dataset_sha256") != dataset_sha:
        raise RuntimeError("P19-B dataset lineage mismatch")

    membership_sha = hashlib.sha256(
        canonical_bytes({"asset_id": "BTC-USD", "member": True})
    ).hexdigest()
    replay_end = (len(rows) + 1) * 1000
    cutoff = len(rows) * 1000 + 100
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
        config_sha256=file_sha(DATA_POLICY_PATH),
        code_artifact_sha256=file_sha(ROOT / "scripts/ci/p19b_evidence.py"),
        rights_class="PUBLIC_REFERENCE",
        policy=ReplaySnapshotPolicy.from_path(SNAPSHOT_POLICY_PATH),
    )
    if snapshot.snapshot_id != expected.get("snapshot_id"):
        raise RuntimeError("P19-B snapshot identity mismatch")

    events: list[ReplayDataEvent] = []
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            raise RuntimeError("market row must be object")
        t = index * 1000
        events.append(
            ReplayDataEvent.create(
                sequence=index,
                event_time_ns=t,
                available_at_ns=t + 100,
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
        policy=DataReplayPolicy.from_path(DATA_POLICY_PATH),
    )
    full = engine.replay_through(cutoff)
    if full.result_id != expected.get("full_result_id"):
        raise RuntimeError("P19-B full replay identity mismatch")
    expected_ids = expected.get("full_event_ids")
    if not isinstance(expected_ids, list) or list(full.event_ids) != expected_ids:
        raise RuntimeError("P19-B full event sequence mismatch")
    return engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p19b", type=Path, required=True)
    parser.add_argument("--p19c", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    p19b_manifest = load(P19B_MANIFEST)
    p19c_manifest = load(P19C_MANIFEST)
    if p19b_manifest.get("state") != "CANONICAL_COMPLETE" or p19b_manifest.get("lock") != "RELEASED":
        raise RuntimeError("P19-B canonical closure required")
    if p19c_manifest.get("state") != "CANONICAL_COMPLETE" or p19c_manifest.get("lock") != "RELEASED":
        raise RuntimeError("P19-C canonical closure required")

    p19b = load(args.p19b)
    p19c = load(args.p19c)
    if p19b.get("kind") != "NEXUS_QUANT_P19B_DATA_REPLAY_EVIDENCE":
        raise RuntimeError("same-run P19-B evidence required")
    if (
        p19c.get("kind") != "NEXUS_QUANT_P19C_DECISION_REPLAY_EVIDENCE"
        or p19c.get("match_state") != "EXACT_MATCH"
    ):
        raise RuntimeError("same-run exact-match P19-C evidence required")

    engine = build_data_replay(cast(Mapping[str, object], p19b))
    decision_time = p19c.get("decision_time_ns")
    if isinstance(decision_time, bool) or not isinstance(decision_time, int):
        raise RuntimeError("P19-C decision_time_ns must be integer")

    decision_ref = IncidentDecisionRef(
        decision_time_ns=decision_time,
        decision_replay_result_id=sha(
            p19c.get("decision_replay_result_id"),
            field="decision_replay_result_id",
        ),
        decision_replay_session_id=sha(
            p19c.get("decision_replay_session_id"),
            field="decision_replay_session_id",
        ),
        shadow_record_id=sha(
            p19c.get("replayed_record_id"),
            field="replayed_record_id",
        ),
        match_state="EXACT_MATCH",
        source_evidence_sha256=file_sha(args.p19c),
    )
    detected_at = decision_time + 100
    marker = IncidentMarker(
        incident_name="canonical-shadow-review",
        incident_type="MANUAL_REVIEW",
        detected_at_ns=detected_at,
        window_before_ns=1000,
        window_after_ns=2000,
        trigger_evidence_sha256=file_sha(args.p19c),
    )
    system_events = (
        IncidentSystemEvent(
            sequence=1,
            event_time_ns=decision_time - 1,
            available_at_ns=decision_time,
            event_type="REPLAY_EVENT",
            system_state="NORMAL",
            source_evidence_sha256=file_sha(args.p19c),
            detail_sha256=decision_ref.decision_replay_result_id,
        ),
        IncidentSystemEvent(
            sequence=2,
            event_time_ns=detected_at - 10,
            available_at_ns=detected_at,
            event_type="MANUAL_REVIEW_EVENT",
            system_state="NORMAL",
            source_evidence_sha256=file_sha(args.p19b),
            detail_sha256=sha(p19b.get("full_result_id"), field="p19b.full_result_id"),
        ),
    )

    result = IncidentReplayEngine(
        data_replay=engine,
        policy=IncidentReplayPolicy.from_path(INCIDENT_POLICY_PATH),
    ).replay(
        marker=marker,
        decisions=(decision_ref,),
        system_events=tuple(reversed(system_events)),
    )
    if len(result.data_event_ids) != 3:
        raise RuntimeError("canonical incident window must contain three newly-visible data events")
    if len(result.decision_ref_ids) != 1 or len(result.system_event_ids) != 2:
        raise RuntimeError("canonical incident context cardinality mismatch")
    if any(
        (
            result.decision_authority,
            result.fill_authority,
            result.execution_authority,
            result.order_routing_authority,
            result.broker_exchange_routing,
            result.p20_started,
        )
    ):
        raise RuntimeError("P19-D authority escalation detected")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19D_INCIDENT_REPLAY_EVIDENCE",
        "task_id": "FIN-P19-WD-001",
        "phase": "P19",
        "workstream": "P19-D",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "p19b_manifest_sha256": file_sha(P19B_MANIFEST),
        "p19c_manifest_sha256": file_sha(P19C_MANIFEST),
        "p19b_same_run_evidence_sha256": file_sha(args.p19b),
        "p19c_same_run_evidence_sha256": file_sha(args.p19c),
        "incident_marker_id": marker.marker_id,
        "incident_type": marker.incident_type,
        "window_start_ns": result.window_start_ns,
        "window_end_ns": result.window_end_ns,
        "data_event_count": len(result.data_event_ids),
        "data_event_ids": list(result.data_event_ids),
        "decision_ref_count": len(result.decision_ref_ids),
        "decision_ref_ids": list(result.decision_ref_ids),
        "system_event_count": len(result.system_event_ids),
        "system_event_ids": list(result.system_event_ids),
        "incident_replay_root_id": result.replay_root_id,
        "decision_match_state": "EXACT_MATCH",
        "decision_authority": False,
        "fill_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p19_active_workstream": "P19-D",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19D_INCIDENT_REPLAY_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
