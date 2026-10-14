from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.pretrade_firewall.idempotency import (
    IdempotencyPolicy,
    IdempotencyPrecheckRequest,
    PriorAdmission,
    evaluate_idempotency,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/risk/pretrade-idempotency-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    fingerprint = "a" * 64
    policy = IdempotencyPolicy("p16b-ci-v1", 1000)
    eligible = evaluate_idempotency(
        policy=policy,
        request=IdempotencyPrecheckRequest.build(
            request_id="eligible",
            upstream_freshness_decision_id="a-ok",
            upstream_freshness_status="PRETRADE_A_ELIGIBLE",
            idempotency_key="key-new",
            intent_fingerprint_sha256=fingerprint,
            as_of_ns=5000,
            prior_admissions=(),
        ),
    )
    veto = evaluate_idempotency(
        policy=policy,
        request=IdempotencyPrecheckRequest.build(
            request_id="veto",
            upstream_freshness_decision_id="a-ok",
            upstream_freshness_status="PRETRADE_A_ELIGIBLE",
            idempotency_key="key-replayed",
            intent_fingerprint_sha256=fingerprint,
            as_of_ns=5000,
            prior_admissions=(PriorAdmission("key-replayed", fingerprint, 4500),),
        ),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P16B_DUPLICATE_IDEMPOTENCY_EVIDENCE",
        "task_id": "FIN-P16-WB-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "eligible": {
            "decision_id": eligible.decision_id,
            "status": eligible.status,
            "matched_record_count": eligible.matched_record_count,
        },
        "veto": {
            "decision_id": veto.decision_id,
            "status": veto.status,
            "reason_codes": list(veto.reason_codes),
        },
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
    print(f"P16B_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
