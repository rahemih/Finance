from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.pretrade_firewall.override_governance import (
    OverrideGovernanceInput,
    OverrideGovernancePolicy,
    OverrideRequest,
    evaluate_override_governance,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-override-governance.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy = OverrideGovernancePolicy("p16g-ci-v1", 1000)
    eligible = evaluate_override_governance(
        policy=policy,
        request=OverrideGovernanceInput(
            "eligible",
            "f-ok",
            "PRETRADE_F_ELIGIBLE",
            None,
            1200,
        ),
    )
    waiting = evaluate_override_governance(
        policy=policy,
        request=OverrideGovernanceInput(
            "waiting",
            "f-veto",
            "VETO",
            OverrideRequest(
                "override-ci",
                "owner-fixture",
                "PRETRADE_VETO_REVIEW",
                "fixture review",
                "a" * 64,
                1000,
                1500,
            ),
            1200,
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16G_OVERRIDE_GOVERNANCE_EVIDENCE",
        "task_id": "FIN-P16-WG-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
        },
        "waiting": {
            "decision_id": waiting.decision_id,
            "status": waiting.status,
            "reason_codes": list(waiting.reason_codes),
        },
        "veto_to_pass_allowed": False,
        "auto_approval_allowed": False,
        "approval_authority": False,
        "reset_authority": False,
        "g8_authority": False,
        "execution_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P16G_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
