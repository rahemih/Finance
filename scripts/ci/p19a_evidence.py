#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.shadow.shadow_decisioning import (
    ShadowDecisionInput,
    ShadowDecisionLedger,
    ShadowDecisionPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/shadow/shadow-decisioning-policy.json"
P18_CLOSURE = ROOT / "docs/12-learning/p18-phase-closure.json"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal", type=Path, required=True)
    parser.add_argument("--risk", type=Path, required=True)
    parser.add_argument("--firewall", type=Path, required=True)
    parser.add_argument("--p17", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    closure = load(P18_CLOSURE)
    if (
        closure.get("kind") != "NEXUS_QUANT_P18_PHASE_CLOSURE"
        or closure.get("state") != "CANONICAL_COMPLETE"
        or closure.get("phase_closure_validation") != "PASS"
        or closure.get("all_locks_released") is not True
    ):
        raise RuntimeError("P18 canonical closure is required before P19-A")

    signal_evidence = load(args.signal)
    if signal_evidence.get("kind") != "NEXUS_QUANT_P14H_SIGNAL_OUTPUT_EVIDENCE":
        raise RuntimeError("P14-H signal evidence kind mismatch")
    signal_payload = mapping(signal_evidence.get("signal"), field="signal")
    signal_id = sha(signal_evidence.get("signal_id"), field="signal_id")
    if hashlib.sha256(canonical_bytes(dict(signal_payload))).hexdigest() != signal_id:
        raise RuntimeError("P14 signal payload identity mismatch")
    signal_action = signal_payload.get("action")
    if signal_action not in {"LONG", "SHORT", "WAIT", "NO_TRADE"}:
        raise RuntimeError("unsupported P14 signal action")
    signal_as_of_ns = signal_payload.get("as_of_time_ns")
    if isinstance(signal_as_of_ns, bool) or not isinstance(signal_as_of_ns, int):
        raise RuntimeError("P14 signal as_of_time_ns must be integer")

    risk_evidence = load(args.risk)
    if (
        risk_evidence.get("kind")
        != "NEXUS_QUANT_P15I_INDEPENDENT_RISK_VALIDATION_EVIDENCE"
        or risk_evidence.get("marker") != "P15_INDEPENDENT_RISK_VALIDATION"
    ):
        raise RuntimeError("P15 independent risk evidence mismatch")
    normal = mapping(risk_evidence.get("normal"), field="risk.normal")
    if normal.get("status") != "PASS":
        raise RuntimeError("P15 normal independent validation must PASS")
    risk_validation_id = sha(normal.get("validation_id"), field="risk.validation_id")
    risk_scale = normal.get("risk_scale_bps")
    if isinstance(risk_scale, bool) or not isinstance(risk_scale, int):
        raise RuntimeError("risk_scale_bps must be integer")
    if risk_evidence.get("execution_authority") is not False:
        raise RuntimeError("P15 evidence cannot carry execution authority")

    firewall_evidence = load(args.firewall)
    if (
        firewall_evidence.get("kind") != "NEXUS_QUANT_P16H_G8_PRETRADE_SAFE_EVIDENCE"
        or firewall_evidence.get("gate_name") != "G8_PRETRADE_SAFE"
        or firewall_evidence.get("state") != "PASS"
    ):
        raise RuntimeError("P16 G8 evidence must PASS")
    firewall_gate_id = sha(firewall_evidence.get("gate_id"), field="firewall.gate_id")
    if firewall_evidence.get("execution_authority") is not False:
        raise RuntimeError("P16 evidence cannot carry execution authority")
    if firewall_evidence.get("order_routing_authority") is not False:
        raise RuntimeError("P16 evidence cannot carry routing authority")

    p17 = load(args.p17)
    if (
        p17.get("kind") != "NEXUS_QUANT_P17_CANONICAL_EMPIRICAL_PIPELINE_EVIDENCE"
        or p17.get("gate_state") != "PASS_EMPIRICAL_REFERENCE"
        or p17.get("fixture_only") is not False
    ):
        raise RuntimeError("canonical P17 empirical G9 evidence is required")
    strategy_record_id = sha(p17.get("strategy_record_id"), field="strategy_record_id")
    model_record_id = sha(p17.get("model_record_id"), field="model_record_id")

    action = cast(str, signal_action)
    directional = action in {"LONG", "SHORT"}
    entry_low = opt_int(signal_payload.get("entry_low_scaled"), field="entry_low_scaled")
    entry_high = opt_int(signal_payload.get("entry_high_scaled"), field="entry_high_scaled")
    stop = opt_int(signal_payload.get("candidate_stop_scaled"), field="candidate_stop_scaled")
    target = opt_int(signal_payload.get("candidate_target_scaled"), field="candidate_target_scaled")
    price_scale = opt_int(signal_payload.get("price_scale"), field="price_scale")
    if directional and any(value is None for value in (entry_low, entry_high, stop, target, price_scale)):
        raise RuntimeError("directional P14 signal requires complete geometry")
    if not directional:
        entry_low = entry_high = stop = target = price_scale = None

    observed_at_ns = signal_as_of_ns + 1
    decision = ShadowDecisionInput(
        asset_id=str(signal_payload.get("asset_id")),
        observed_at_ns=observed_at_ns,
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
        firewall_state=str(firewall_evidence.get("state")),
        strategy_record_id=strategy_record_id,
        model_record_id=model_record_id,
        signal_evidence_sha256=file_sha(args.signal),
        risk_evidence_sha256=file_sha(args.risk),
        firewall_evidence_sha256=file_sha(args.firewall),
        quant_evidence_sha256=file_sha(args.p17),
        entry_low_scaled=entry_low,
        entry_high_scaled=entry_high,
        candidate_stop_scaled=stop,
        candidate_target_scaled=target,
        price_scale=price_scale,
    )

    policy = ShadowDecisionPolicy.from_path(POLICY_PATH)
    ledger = ShadowDecisionLedger(policy)
    record = ledger.append(decision)
    snapshot = ledger.snapshot()

    if action in {"LONG", "SHORT"} and record.disposition != "SHADOW_WOULD_TRADE":
        raise RuntimeError("eligible directional reference must become SHADOW_WOULD_TRADE")
    if any(
        (
            record.execution_authority,
            record.order_routing_authority,
            record.broker_exchange_routing,
            record.external_order_submission,
            record.automatic_live_promotion,
            record.p20_started,
        )
    ):
        raise RuntimeError("P19-A shadow record authority escalation")
    if record.live_trading != "DISABLED" or record.auto_trading != "DISABLED":
        raise RuntimeError("P19-A cannot enable trading")

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P19A_SHADOW_DECISION_EVIDENCE",
        "task_id": "FIN-P19-WA-001",
        "phase": "P19",
        "workstream": "P19-A",
        "state": "IN_PROGRESS_IMPLEMENTATION_EVIDENCE",
        "policy_sha256": file_sha(POLICY_PATH),
        "policy_id": policy.policy_id,
        "p18_closure_sha256": file_sha(P18_CLOSURE),
        "input_id": decision.input_id,
        "record_id": record.record_id,
        "ledger_snapshot_id": snapshot.snapshot_id,
        "record": record.payload(),
        "exact_typed_lineage": {
            "signal_id": signal_id,
            "risk_validation_id": risk_validation_id,
            "firewall_gate_id": firewall_gate_id,
            "strategy_record_id": strategy_record_id,
            "model_record_id": model_record_id,
        },
        "upstream_reference_flags": {
            "p15_fixture_only": risk_evidence.get("fixture_only"),
            "p16_fixture_only": firewall_evidence.get("fixture_only"),
            "p17_fixture_only": p17.get("fixture_only"),
        },
        "shadow_only": True,
        "execution_authority": False,
        "order_routing_authority": False,
        "broker_exchange_routing": False,
        "external_order_submission": False,
        "automatic_live_promotion": False,
        "p19_started": True,
        "p19_active_workstream": "P19-A",
        "p20_started": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P19A_SHADOW_DECISION_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
