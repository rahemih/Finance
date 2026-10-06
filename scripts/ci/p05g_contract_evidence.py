#!/usr/bin/env python3
"""Build deterministic P05-G performance-contract evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/market-data/performance-policy.json"
CAPACITY = ROOT / "docs/04-architecture/capacity-cost-envelope.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    capacity = json.loads(CAPACITY.read_text(encoding="utf-8"))
    operating = next(
        item for item in capacity["workload_scenarios"] if item["id"] == "OPERATING"
    )
    stress = next(
        item for item in capacity["workload_scenarios"] if item["id"] == "STRESS"
    )

    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P05G_PERFORMANCE_CONTRACT_EVIDENCE",
        "performance_policy_sha256": sha256(POLICY),
        "capacity_envelope_sha256": sha256(CAPACITY),
        "operating": {
            "average_events_per_sec": operating["average_events_per_sec"],
            "peak_events_per_sec": operating["peak_events_per_sec"],
        },
        "stress_review_boundary_events_per_sec": stress["peak_events_per_sec"],
        "l_fast_data": policy["l_fast_data"],
        "benchmark": policy["benchmark"],
        "pass_requirements": policy["pass_requirements"],
        "measurement_rule": {
            "timing_evidence": policy["timing_evidence"],
            "contract_evidence": policy["contract_evidence"],
            "timing_byte_compare_forbidden": True,
        },
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "automatic_data_failover": "DISABLED",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P05G_CONTRACT_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
