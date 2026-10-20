#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.shadow.execution_drift import (
    ExecutionDriftPolicy,
    ObservedExecutionSample,
    PaperExecutionSample,
    build_drift_window,
    compare_execution_drift,
)


ROOT = Path(__file__).resolve().parents[2]
P19E_MANIFEST = ROOT / "docs/14-shadow/p19-e-digital-twin-fill-slippage.json"
P19F_POLICY = ROOT / "config/shadow/execution-drift-policy.json"
P19E_POLICY = ROOT / "config/shadow/digital-twin-fill-policy.json"


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


def text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{field} must be non-empty text")
    return value.strip()


def integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"{field} must be integer")
    return value


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    result = format(value.normalize(), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p19e", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = load(P19E_MANIFEST)
    if manifest.get("state") != "CANONICAL_COMPLETE" or manifest.get("lock") != "RELEASED":
        raise RuntimeError("P19-E canonical closure required")

    p19e = load(args.p19e)
    if p19e.get("kind") != "NEXUS_QUANT_P19E_DIGITAL_TWIN_FILL_EVIDENCE":
        raise RuntimeError("same-run P19-E evidence required")
    if p19e.get("context_quality") != "DERIVED_REFERENCE_DEPTH":
        raise RuntimeError("canonical P19-F CI requires P19-E derived reference context")
    if p19e.get("production_fill_accuracy_claim") is not False:
        raise RuntimeError("P19-E reference evidence cannot claim production accuracy")
    if p19e.get("broker_truth") is not False:
        raise RuntimeError("P19-E reference evidence cannot claim broker truth")

    twin_policy = load(P19E_POLICY)
    reference_execution = mapping(
        twin_policy.get("reference_execution_policy"),
        field="reference_execution_policy",
    )
    taker_fee_bps = reference_execution.get("taker_fee_bps")
    modeled_latency_ns = reference_execution.get("decision_latency_ns")
    if (
        isinstance(taker_fee_bps, bool)
        or not isinstance(taker_fee_bps, int)
        or isinstance(modeled_latency_ns, bool)
        or not isinstance(modeled_latency_ns, int)
    ):
        raise RuntimeError("P19-E reference execution policy integers required")

    slippage_raw = p19e.get("adverse_slippage_bps")
    slippage = None if slippage_raw is None else text(
        slippage_raw,
        field="adverse_slippage_bps",
    )
    paper = PaperExecutionSample(
        digital_twin_result_id=sha(
            p19e.get("digital_twin_result_id"),
            field="digital_twin_result_id",
        ),
        incident_replay_root_id=sha(
            p19e.get("incident_replay_root_id"),
            field="incident_replay_root_id",
        ),
        asset_id="BTC-USD",
        side=text(p19e.get("side"), field="side"),
        decision_time_ns=integer(p19e.get("decision_time_ns"), field="decision_time_ns"),
        requested_quantity=text(
            p19e.get("requested_quantity"),
            field="requested_quantity",
        ),
        filled_quantity=text(
            p19e.get("filled_quantity"),
            field="filled_quantity",
        ),
        adverse_slippage_bps=slippage,
        fee_bps=str(taker_fee_bps),
        modeled_latency_ns=modeled_latency_ns,
        fill_status=text(p19e.get("fill_status"), field="fill_status"),
        source_evidence_sha256=file_sha(args.p19e),
    )

    paper_slippage = (
        None
        if paper.adverse_slippage_bps is None
        else Decimal(paper.adverse_slippage_bps)
    )
    observed_slippage = (
        None
        if paper_slippage is None
        else decimal_text(paper_slippage + Decimal("2"))
    )
    reference_source = hashlib.sha256(
        canonical_bytes(
            {
                "kind": "P19F_REFERENCE_PERTURBATION_V1",
                "paper_sample_id": paper.sample_id,
                "slippage_delta_bps": "2",
                "fee_delta_bps": "1",
                "latency_delta_ns": 100_000_000,
            }
        )
    ).hexdigest()
    observed = ObservedExecutionSample(
        paper_sample_id=paper.sample_id,
        observation_name="canonical-reference-observation",
        observation_class="REFERENCE_OBSERVATION",
        asset_id=paper.asset_id,
        side=paper.side,
        observed_at_ns=paper.decision_time_ns + modeled_latency_ns + 100_000_000,
        requested_quantity=paper.requested_quantity,
        filled_quantity=paper.filled_quantity,
        adverse_slippage_bps=observed_slippage,
        fee_bps=str(taker_fee_bps + 1),
        observed_latency_ns=modeled_latency_ns + 100_000_000,
        fill_status=paper.fill_status,
        source_evidence_sha256=reference_source,
    )

    policy = ExecutionDriftPolicy.from_path(P19F_POLICY)
    pair = compare_execution_drift(paper=paper, observed=observed, policy=policy)
    window = build_drift_window(pairs=(pair,), policy=policy)

    if window.claim_scope != "REFERENCE_ONLY":
        raise RuntimeError("canonical P19-F CI must remain REFERENCE_ONLY")
    if window.observation_class != "REFERENCE_OBSERVATION":
        raise RuntimeError("canonical P19-F CI observation class drift")
    if window.severity != "NORMAL":
        raise RuntimeError("canonical P19-F reference perturbation must be NORMAL")
    if window.live_drift_validated:
        raise RuntimeError("reference observation cannot validate live drift")
    if any(
        (
            window.g10_authority,
            window.production_readiness_authority,
            window.execution_authority,
            window.order_routing_authority,
            window.p20_started,
        )
    ):
        raise RuntimeError("P19-F authority escalation detected")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19F_EXECUTION_DRIFT_EVIDENCE",
        "task_id": "FIN-P19-WF-001",
        "phase": "P19",
        "workstream": "P19-F",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "p19e_manifest_sha256": file_sha(P19E_MANIFEST),
        "p19e_same_run_evidence_sha256": file_sha(args.p19e),
        "policy_id": policy.policy_id,
        "paper_sample_id": paper.sample_id,
        "observed_sample_id": observed.observation_id,
        "pair_id": pair.pair_id,
        "drift_window_id": window.window_id,
        "observation_class": window.observation_class,
        "claim_scope": window.claim_scope,
        "severity": window.severity,
        "fill_ratio_drift_bps": pair.fill_ratio_drift_bps,
        "abs_slippage_drift_bps": pair.abs_slippage_drift_bps,
        "abs_fee_drift_bps": pair.abs_fee_drift_bps,
        "abs_latency_drift_ns": pair.abs_latency_drift_ns,
        "fill_status_match": pair.fill_status_match,
        "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
        "live_observation_owner": "P20-H",
        "broker_certification_owner": "P20-I",
        "reference_observation": True,
        "live_drift_validated": False,
        "g10_authority": False,
        "production_readiness_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "p19_active_workstream": "P19-F",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19F_EXECUTION_DRIFT_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
