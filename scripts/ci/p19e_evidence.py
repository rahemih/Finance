#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
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
from packages.shadow.digital_twin_fill import (
    DigitalTwinFillEngine,
    DigitalTwinFillPolicy,
    DigitalTwinFillRequest,
    DigitalTwinMarketSlice,
)
from quant.backtesting.engine import BacktestMarketEvent
from quant.backtesting.execution_realism import (
    HistoricalDepthLevel,
    HistoricalExecutionContext,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/reference-data/btc-usd-daily-2026-09-yahoo.json"
P19D_MANIFEST = ROOT / "docs/14-shadow/p19-d-incident-replay.json"
DATA_POLICY_PATH = ROOT / "config/shadow/data-replay-policy.json"
DIGITAL_TWIN_POLICY_PATH = ROOT / "config/shadow/digital-twin-fill-policy.json"
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


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


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
    if full.result_id != expected.get("full_result_id"):
        raise RuntimeError("P19-B full replay identity mismatch")
    return engine


def scaled_price(value: object, *, scale: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError("reference close must be numeric")
    return int(
        (Decimal(str(value)) * Decimal(scale)).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )


def derive_context(
    *,
    center_scaled: int,
    decision_time_ns: int,
    asset_id: str,
    price_scale: int,
    policy: DigitalTwinFillPolicy,
    source_evidence_sha256: str,
) -> DigitalTwinMarketSlice:
    center = Decimal(center_scaled)
    tenk = Decimal(10_000)
    half = Decimal(policy.reference_half_spread_bps) / tenk
    spacing = Decimal(policy.reference_level_spacing_bps) / tenk

    best_bid = int((center * (Decimal(1) - half)).to_integral_value(rounding=ROUND_FLOOR))
    best_ask = int((center * (Decimal(1) + half)).to_integral_value(rounding=ROUND_CEILING))
    bids = tuple(
        HistoricalDepthLevel(
            int(
                (
                    Decimal(best_bid)
                    * (Decimal(1) - spacing * Decimal(level))
                ).to_integral_value(rounding=ROUND_FLOOR)
            ),
            policy.reference_displayed_quantity,
        )
        for level in range(policy.reference_levels_per_side)
    )
    asks = tuple(
        HistoricalDepthLevel(
            int(
                (
                    Decimal(best_ask)
                    * (Decimal(1) + spacing * Decimal(level))
                ).to_integral_value(rounding=ROUND_CEILING)
            ),
            policy.reference_displayed_quantity,
        )
        for level in range(policy.reference_levels_per_side)
    )
    event = BacktestMarketEvent(
        sequence=1,
        event_time_ns=decision_time_ns,
        available_at_ns=decision_time_ns,
        asset_id=asset_id,
        price_scaled=center_scaled,
        price_scale=price_scale,
    )
    context = HistoricalExecutionContext(
        sequence=1,
        event_time_ns=decision_time_ns,
        available_at_ns=decision_time_ns,
        asset_id=asset_id,
        price_scale=price_scale,
        bids=bids,
        asks=asks,
        source_evidence_sha256=source_evidence_sha256,
    )
    return DigitalTwinMarketSlice(event=event, context=context)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p19a", type=Path, required=True)
    parser.add_argument("--p19b", type=Path, required=True)
    parser.add_argument("--p19c", type=Path, required=True)
    parser.add_argument("--p19d", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = load(P19D_MANIFEST)
    if manifest.get("state") != "CANONICAL_COMPLETE" or manifest.get("lock") != "RELEASED":
        raise RuntimeError("P19-D canonical closure required")

    p19a = load(args.p19a)
    p19b = load(args.p19b)
    p19c = load(args.p19c)
    p19d = load(args.p19d)
    if p19a.get("kind") != "NEXUS_QUANT_P19A_SHADOW_DECISION_EVIDENCE":
        raise RuntimeError("same-run P19-A evidence required")
    if p19b.get("kind") != "NEXUS_QUANT_P19B_DATA_REPLAY_EVIDENCE":
        raise RuntimeError("same-run P19-B evidence required")
    if p19c.get("kind") != "NEXUS_QUANT_P19C_DECISION_REPLAY_EVIDENCE":
        raise RuntimeError("same-run P19-C evidence required")
    if p19d.get("kind") != "NEXUS_QUANT_P19D_INCIDENT_REPLAY_EVIDENCE":
        raise RuntimeError("same-run P19-D evidence required")

    incident_root = sha(
        p19d.get("incident_replay_root_id"),
        field="incident_replay_root_id",
    )
    decision_session = sha(
        p19c.get("decision_replay_session_id"),
        field="decision_replay_session_id",
    )
    shadow_record = sha(p19a.get("record_id"), field="p19a.record_id")
    record = mapping(p19a.get("record"), field="p19a.record")
    action = record.get("signal_action")
    if action not in {"LONG", "SHORT"}:
        raise RuntimeError("P19-E reference evidence requires directional shadow decision")

    decision_time = p19c.get("decision_time_ns")
    if isinstance(decision_time, bool) or not isinstance(decision_time, int):
        raise RuntimeError("P19-C decision_time_ns must be integer")

    data_engine = build_data_replay(cast(Mapping[str, object], p19b))
    visible = data_engine.replay_through(decision_time)
    expected_visible = p19c.get("visible_event_ids")
    if not isinstance(expected_visible, list) or list(visible.event_ids) != expected_visible:
        raise RuntimeError("P19-C visible-event lineage mismatch")
    if not visible.events:
        raise RuntimeError("Digital Twin reference requires visible market data")

    latest = visible.events[-1]
    payload = latest.payload_value()
    latest_row = mapping(payload, field="latest visible market row")
    price_scale = 100
    reference_price_scaled = scaled_price(latest_row.get("close"), scale=price_scale)

    policy = DigitalTwinFillPolicy.from_path(DIGITAL_TWIN_POLICY_PATH)
    quantity = Decimal(policy.reference_quantity)
    signed_quantity = quantity if action == "LONG" else -quantity
    request = DigitalTwinFillRequest(
        twin_name="canonical-public-reference-twin",
        incident_replay_root_id=incident_root,
        decision_replay_session_id=decision_session,
        shadow_record_id=shadow_record,
        asset_id="BTC-USD",
        decision_time_ns=decision_time,
        quantity_delta=decimal_text(signed_quantity),
        reference_price_scaled=reference_price_scaled,
        price_scale=price_scale,
        context_quality="DERIVED_REFERENCE_DEPTH",
        source_evidence_sha256=file_sha(args.p19d),
    )
    market_slice = derive_context(
        center_scaled=reference_price_scaled,
        decision_time_ns=decision_time,
        asset_id=request.asset_id,
        price_scale=price_scale,
        policy=policy,
        source_evidence_sha256=file_sha(args.p19b),
    )
    result = DigitalTwinFillEngine(policy).simulate(
        request=request,
        timeline=(market_slice,),
    )

    if result.execution_realism_owner != "P17-B":
        raise RuntimeError("P17-B must remain execution-realism owner")
    if result.status != "FULL_FILL":
        raise RuntimeError("canonical small reference request must fully fill")
    if result.context_quality != "DERIVED_REFERENCE_DEPTH":
        raise RuntimeError("canonical reference must remain derived depth")
    if result.production_quality_context:
        raise RuntimeError("derived reference depth cannot be production-quality context")
    if result.production_fill_accuracy_claim or result.broker_truth:
        raise RuntimeError("reference Digital Twin cannot claim production accuracy/broker truth")
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
        raise RuntimeError("P19-E authority escalation")

    out = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19E_DIGITAL_TWIN_FILL_EVIDENCE",
        "task_id": "FIN-P19-WE-001",
        "phase": "P19",
        "workstream": "P19-E",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "fixture_only": False,
        "p19d_manifest_sha256": file_sha(P19D_MANIFEST),
        "p19a_same_run_evidence_sha256": file_sha(args.p19a),
        "p19b_same_run_evidence_sha256": file_sha(args.p19b),
        "p19c_same_run_evidence_sha256": file_sha(args.p19c),
        "p19d_same_run_evidence_sha256": file_sha(args.p19d),
        "incident_replay_root_id": incident_root,
        "decision_replay_session_id": decision_session,
        "shadow_record_id": shadow_record,
        "signal_action": action,
        "decision_time_ns": decision_time,
        "latest_visible_market_event_id": latest.event_id,
        "latest_visible_close_scaled": reference_price_scaled,
        "request_id": request.request_id,
        "policy_id": policy.policy_id,
        "execution_policy_id": policy.execution_policy.policy_id,
        "execution_realism_owner": result.execution_realism_owner,
        "context_quality": result.context_quality,
        "reference_depth_derivation": "CLOSE_CENTERED_SYNTHETIC_BOOK_V1",
        "production_quality_context": result.production_quality_context,
        "production_fill_accuracy_claim": result.production_fill_accuracy_claim,
        "broker_truth": result.broker_truth,
        "fill_status": result.status,
        "side": result.side,
        "requested_quantity": result.requested_quantity,
        "filled_quantity": result.filled_quantity,
        "remaining_quantity": result.remaining_quantity,
        "vwap_price_scaled": result.vwap_price_scaled,
        "adverse_slippage_bps": result.adverse_slippage_bps,
        "total_fee_cash": result.total_fee_cash,
        "fill_ids": list(result.fill_ids),
        "context_ids": list(result.context_ids),
        "diagnostic_ids": list(result.diagnostic_ids),
        "digital_twin_result_id": result.result_id,
        "decision_authority": False,
        "fill_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p19_active_workstream": "P19-E",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19E_DIGITAL_TWIN_FILL_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
