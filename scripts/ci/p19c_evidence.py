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
from packages.shadow.data_replay import (
    DataReplayEngine,
    DataReplayPolicy,
    ReplayDataEvent,
)
from packages.shadow.decision_replay import (
    DecisionReplayCase,
    DecisionReplayEngine,
    DecisionReplayPolicy,
)
from packages.shadow.shadow_decisioning import (
    ShadowDecisionInput,
    ShadowDecisionLedger,
    ShadowDecisionPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
P19A_MANIFEST = ROOT / "docs/14-shadow/p19-a-shadow-decisioning.json"
P19B_MANIFEST = ROOT / "docs/14-shadow/p19-b-data-replay.json"
DATA_POLICY_PATH = ROOT / "config/shadow/data-replay-policy.json"
DECISION_POLICY_PATH = ROOT / "config/shadow/decision-replay-policy.json"
SHADOW_POLICY_PATH = ROOT / "config/shadow/shadow-decisioning-policy.json"
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


def mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def sha(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"{field} must be SHA-256")
    parsed = value.strip().lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise RuntimeError(f"{field} must be SHA-256")
    if len(set(parsed)) < 4:
        raise RuntimeError(f"{field} cannot be placeholder identity")
    return parsed


def opt_int(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"{field} must be integer or null")
    return value


def build_data_replay(expected_p19b: Mapping[str, object]) -> DataReplayEngine:
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
    if expected_p19b.get("dataset_sha256") != dataset_sha:
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
    if snapshot.snapshot_id != expected_p19b.get("snapshot_id"):
        raise RuntimeError("P19-B ReplaySnapshot identity mismatch")

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
        policy=DataReplayPolicy.from_path(DATA_POLICY_PATH),
    )
    full = engine.replay_through(cutoff)
    if full.result_id != expected_p19b.get("full_result_id"):
        raise RuntimeError("P19-B full replay identity mismatch")
    expected_ids = expected_p19b.get("full_event_ids")
    if not isinstance(expected_ids, list) or list(full.event_ids) != expected_ids:
        raise RuntimeError("P19-B full event identity sequence mismatch")
    return engine


def build_shadow_input(
    *,
    signal_path: Path,
    risk_path: Path,
    firewall_path: Path,
    p17_path: Path,
) -> ShadowDecisionInput:
    signal_evidence = load(signal_path)
    if signal_evidence.get("kind") != "NEXUS_QUANT_P14H_SIGNAL_OUTPUT_EVIDENCE":
        raise RuntimeError("P14 signal evidence kind mismatch")
    signal_payload = mapping(signal_evidence.get("signal"), field="signal")
    signal_id = sha(signal_evidence.get("signal_id"), field="signal_id")
    if hashlib.sha256(canonical_bytes(dict(signal_payload))).hexdigest() != signal_id:
        raise RuntimeError("P14 signal identity mismatch")

    signal_action = signal_payload.get("action")
    if signal_action not in {"LONG", "SHORT", "WAIT", "NO_TRADE"}:
        raise RuntimeError("unsupported signal action")
    signal_as_of_ns = signal_payload.get("as_of_time_ns")
    if isinstance(signal_as_of_ns, bool) or not isinstance(signal_as_of_ns, int):
        raise RuntimeError("signal as_of_time_ns must be integer")

    risk = load(risk_path)
    if (
        risk.get("kind")
        != "NEXUS_QUANT_P15I_INDEPENDENT_RISK_VALIDATION_EVIDENCE"
        or risk.get("marker") != "P15_INDEPENDENT_RISK_VALIDATION"
    ):
        raise RuntimeError("P15 risk evidence mismatch")
    normal = mapping(risk.get("normal"), field="risk.normal")
    risk_validation_id = sha(normal.get("validation_id"), field="risk_validation_id")
    risk_scale = normal.get("risk_scale_bps")
    if normal.get("status") != "PASS" or isinstance(risk_scale, bool) or not isinstance(risk_scale, int):
        raise RuntimeError("P15 normal risk validation must PASS")

    firewall = load(firewall_path)
    if (
        firewall.get("kind") != "NEXUS_QUANT_P16H_G8_PRETRADE_SAFE_EVIDENCE"
        or firewall.get("gate_name") != "G8_PRETRADE_SAFE"
        or firewall.get("state") != "PASS"
    ):
        raise RuntimeError("P16 G8 evidence must PASS")
    firewall_gate_id = sha(firewall.get("gate_id"), field="firewall_gate_id")

    p17 = load(p17_path)
    if (
        p17.get("kind") != "NEXUS_QUANT_P17_CANONICAL_EMPIRICAL_PIPELINE_EVIDENCE"
        or p17.get("gate_state") != "PASS_EMPIRICAL_REFERENCE"
        or p17.get("fixture_only") is not False
    ):
        raise RuntimeError("canonical P17 empirical evidence required")

    action = cast(str, signal_action)
    directional = action in {"LONG", "SHORT"}
    entry_low = opt_int(signal_payload.get("entry_low_scaled"), field="entry_low_scaled")
    entry_high = opt_int(signal_payload.get("entry_high_scaled"), field="entry_high_scaled")
    stop = opt_int(signal_payload.get("candidate_stop_scaled"), field="candidate_stop_scaled")
    target = opt_int(signal_payload.get("candidate_target_scaled"), field="candidate_target_scaled")
    price_scale = opt_int(signal_payload.get("price_scale"), field="price_scale")
    if not directional:
        entry_low = entry_high = stop = target = price_scale = None

    return ShadowDecisionInput(
        asset_id=str(signal_payload.get("asset_id")),
        observed_at_ns=signal_as_of_ns + 1,
        market_available_at_ns=signal_as_of_ns,
        signal_id=signal_id,
        signal_as_of_ns=signal_as_of_ns,
        signal_action=action,
        empirical_probability_bps=opt_int(
            signal_payload.get("empirical_probability_bps"),
            field="empirical_probability_bps",
        ),
        overall_uncertainty_bps=opt_int(
            signal_payload.get("overall_uncertainty_bps"),
            field="overall_uncertainty_bps",
        ),
        risk_validation_id=risk_validation_id,
        risk_status=str(normal.get("status")),
        risk_scale_bps=risk_scale,
        firewall_gate_id=firewall_gate_id,
        firewall_state=str(firewall.get("state")),
        strategy_record_id=sha(p17.get("strategy_record_id"), field="strategy_record_id"),
        model_record_id=sha(p17.get("model_record_id"), field="model_record_id"),
        signal_evidence_sha256=file_sha(signal_path),
        risk_evidence_sha256=file_sha(risk_path),
        firewall_evidence_sha256=file_sha(firewall_path),
        quant_evidence_sha256=file_sha(p17_path),
        entry_low_scaled=entry_low,
        entry_high_scaled=entry_high,
        candidate_stop_scaled=stop,
        candidate_target_scaled=target,
        price_scale=price_scale,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal", type=Path, required=True)
    parser.add_argument("--risk", type=Path, required=True)
    parser.add_argument("--firewall", type=Path, required=True)
    parser.add_argument("--p17", type=Path, required=True)
    parser.add_argument("--p19a", type=Path, required=True)
    parser.add_argument("--p19b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    p19a_manifest = load(P19A_MANIFEST)
    p19b_manifest = load(P19B_MANIFEST)
    if p19a_manifest.get("state") != "CANONICAL_COMPLETE" or p19a_manifest.get("lock") != "RELEASED":
        raise RuntimeError("P19-A canonical closure required")
    if p19b_manifest.get("state") != "CANONICAL_COMPLETE" or p19b_manifest.get("lock") != "RELEASED":
        raise RuntimeError("P19-B canonical closure required")

    p19a = load(args.p19a)
    if p19a.get("kind") != "NEXUS_QUANT_P19A_SHADOW_DECISION_EVIDENCE":
        raise RuntimeError("P19-A same-run evidence required")
    p19b = load(args.p19b)
    if p19b.get("kind") != "NEXUS_QUANT_P19B_DATA_REPLAY_EVIDENCE":
        raise RuntimeError("P19-B same-run evidence required")

    data_engine = build_data_replay(p19b)
    shadow_input = build_shadow_input(
        signal_path=args.signal,
        risk_path=args.risk,
        firewall_path=args.firewall,
        p17_path=args.p17,
    )
    if shadow_input.input_id != p19a.get("input_id"):
        raise RuntimeError("reconstructed P19-A input identity mismatch")

    baseline = ShadowDecisionLedger(
        ShadowDecisionPolicy.from_path(SHADOW_POLICY_PATH)
    )
    baseline_record = baseline.append(shadow_input)
    if baseline_record.record_id != p19a.get("record_id"):
        raise RuntimeError("reconstructed P19-A record identity mismatch")

    visible = data_engine.replay_through(shadow_input.observed_at_ns)
    case = DecisionReplayCase(
        case_name="canonical-p19a-reference-decision",
        decision_time_ns=shadow_input.observed_at_ns,
        required_event_ids=visible.event_ids,
        shadow_input=shadow_input,
        expected_input_id=sha(p19a.get("input_id"), field="p19a.input_id"),
        expected_record_id=sha(p19a.get("record_id"), field="p19a.record_id"),
        expected_disposition=str(mapping(p19a.get("record"), field="p19a.record").get("disposition")),
        expected_previous_record_id=None,
    )
    session = DecisionReplayEngine(
        data_replay=data_engine,
        shadow_policy=ShadowDecisionPolicy.from_path(SHADOW_POLICY_PATH),
        policy=DecisionReplayPolicy.from_path(DECISION_POLICY_PATH),
    ).replay((case,))

    result = session.results[0]
    if result.match_state != "EXACT_MATCH":
        raise RuntimeError("P19-C canonical decision replay did not exact-match")
    if result.replayed_input_id != p19a.get("input_id"):
        raise RuntimeError("P19-C input replay mismatch")
    if result.replayed_record_id != p19a.get("record_id"):
        raise RuntimeError("P19-C record replay mismatch")
    if any(
        (
            session.fill_authority,
            session.execution_authority,
            session.order_routing_authority,
            session.p20_started,
        )
    ):
        raise RuntimeError("P19-C authority escalation")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19C_DECISION_REPLAY_EVIDENCE",
        "task_id": "FIN-P19-WC-001",
        "phase": "P19",
        "workstream": "P19-C",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "p19a_manifest_sha256": file_sha(P19A_MANIFEST),
        "p19b_manifest_sha256": file_sha(P19B_MANIFEST),
        "p19a_same_run_evidence_sha256": file_sha(args.p19a),
        "p19b_same_run_evidence_sha256": file_sha(args.p19b),
        "decision_time_ns": shadow_input.observed_at_ns,
        "visible_event_ids": list(result.visible_event_ids),
        "visible_event_count": len(result.visible_event_ids),
        "expected_input_id": p19a["input_id"],
        "replayed_input_id": result.replayed_input_id,
        "expected_record_id": p19a["record_id"],
        "replayed_record_id": result.replayed_record_id,
        "replayed_disposition": result.replayed_disposition,
        "decision_replay_result_id": result.result_id,
        "decision_replay_session_id": session.session_id,
        "match_state": result.match_state,
        "fill_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p19_active_workstream": "P19-C",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19C_DECISION_REPLAY_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
