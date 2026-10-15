from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.pretrade_firewall.safety_gate import (
    PreTradeSafetyGateError,
    PreTradeSafetyGatePolicy,
    PreTradeStageCertificate,
    certify_g8_pretrade_safe,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-safety-gate.json"


def records(
    *,
    final_status: str = "PRETRADE_G_ELIGIBLE",
) -> tuple[PreTradeStageCertificate, ...]:
    statuses = (
        ("P16-A", "PRETRADE_A_ELIGIBLE"),
        ("P16-B", "PRETRADE_B_ELIGIBLE"),
        ("P16-C", "PRETRADE_C_ELIGIBLE"),
        ("P16-D", "PRETRADE_D_ELIGIBLE"),
        ("P16-E", "PRETRADE_E_ELIGIBLE"),
        ("P16-F", "PRETRADE_F_ELIGIBLE"),
        ("P16-G", final_status),
    )
    result: list[PreTradeStageCertificate] = []
    previous: str | None = None
    for index, (workstream, status) in enumerate(statuses):
        decision_id = f"fixture-{index + 1}"
        result.append(
            PreTradeStageCertificate(
                workstream,
                decision_id,
                status,
                previous,
            )
        )
        previous = decision_id
    return tuple(result)


def rejected(policy: PreTradeSafetyGatePolicy, status: str) -> bool:
    try:
        certify_g8_pretrade_safe(
            policy=policy,
            certificates=records(final_status=status),
        )
    except PreTradeSafetyGateError:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = PreTradeSafetyGatePolicy.from_path(POLICY_PATH)
    gate = certify_g8_pretrade_safe(
        policy=policy,
        certificates=records(),
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16H_G8_PRETRADE_SAFE_EVIDENCE",
        "task_id": "FIN-P16-WH-001",
        "fixture_only": True,
        "gate_id": gate.gate_id,
        "gate_name": gate.gate_name,
        "state": gate.state,
        "workstream_coverage": list(gate.workstream_coverage),
        "certificate_ids": list(gate.certificate_ids),
        "veto_rejected": rejected(policy, "VETO"),
        "waiting_for_approval_rejected": rejected(
            policy,
            "WAITING_FOR_APPROVAL",
        ),
        "p17_started": gate.p17_started,
        "next_phase": gate.next_phase,
        "next_phase_state": gate.next_phase_state,
        "execution_authority": gate.execution_authority,
        "order_routing_authority": gate.order_routing_authority,
        "live_trading": gate.live_trading,
        "auto_trading": gate.auto_trading,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P16H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
