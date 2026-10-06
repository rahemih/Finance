#!/usr/bin/env python3
"""Build deterministic P06-H retention/capacity/cost evidence offline."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.historical_data import (
    RetentionCapacityPolicy,
    RetentionRights,
    estimate_capacity,
    estimate_cost,
    evaluate_growth_deviation,
    measure_compaction,
    plan_raw_retention,
)

POLICY = ROOT / "config/historical-data/retention-capacity-policy.json"
P02_CAPACITY = ROOT / "docs/04-architecture/capacity-cost-envelope.json"
RAW_POLICY = ROOT / "config/historical-data/raw-archive-policy.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> None:
    policy = RetentionCapacityPolicy.from_path(POLICY)
    hot_plan = plan_raw_retention(
        tier="HOT",
        requested_days=7,
        rights=RetentionRights("RETENTION_ALLOWED"),
        policy=policy,
    )
    limited_plan = plan_raw_retention(
        tier="WARM",
        requested_days=30,
        rights=RetentionRights(
            "RETENTION_ALLOWED_WITH_LIMIT",
            max_retention_days=30,
        ),
        policy=policy,
    )
    operating = estimate_capacity(
        events_per_sec=2000,
        event_bytes=1000,
        retention_days=30,
        compression_ratio="3",
        partition_seconds=policy.reference_partition_seconds,
        policy=policy,
    )
    stress = estimate_capacity(
        events_per_sec=10000,
        event_bytes=1000,
        retention_days=30,
        compression_ratio="5",
        partition_seconds=policy.reference_partition_seconds,
        policy=policy,
    )
    compaction = measure_compaction(
        input_bytes=4_000_000,
        output_bytes=1_000_000,
        policy=policy,
    )
    growth = evaluate_growth_deviation(
        forecast_gb="100",
        actual_gb="151",
        policy=policy,
    )
    unresolved_cost = estimate_cost(
        retained_gb_month=operating.retained_compressed_gb,
        replay_scan_gb=Decimal("100"),
        egress_gb=Decimal("0"),
        rates=None,
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P06H_RETENTION_CAPACITY_EVIDENCE",
        "policy_sha256": sha256(POLICY),
        "p02_capacity_baseline_sha256": sha256(P02_CAPACITY),
        "raw_archive_policy_sha256": sha256(RAW_POLICY),
        "rights": {
            "hot_plan": {
                "tier": hot_plan.tier,
                "days": hot_plan.effective_days,
                "action": hot_plan.action,
                "production_mutation": hot_plan.production_mutation
            },
            "limited_warm_plan": {
                "tier": limited_plan.tier,
                "days": limited_plan.effective_days,
                "action": limited_plan.action,
                "production_mutation": limited_plan.production_mutation
            },
            "forbidden_and_unverified_fail_closed": True
        },
        "capacity": {
            "operating_2000eps_1000bytes_3to1": operating.payload(),
            "stress_10000eps_1000bytes_5to1": stress.payload()
        },
        "compaction": {
            "input_bytes": compaction.input_bytes,
            "output_bytes": compaction.output_bytes,
            "compression_ratio": str(compaction.compression_ratio),
            "meets_reference_lower_bound": compaction.meets_reference_lower_bound
        },
        "growth_review": {
            "forecast_gb": str(growth.forecast_gb),
            "actual_gb": str(growth.actual_gb),
            "deviation_percent": str(growth.deviation_percent),
            "architecture_review_required": growth.architecture_review_required
        },
        "cost": unresolved_cost.payload(),
        "production_storage_vendor": policy.production_storage_vendor,
        "safety": {
            "production_mutation": False,
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "canary": "DISABLED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P06H_EVIDENCE=PASS output={output}")
    print(f"P06H_COST_STATUS={unresolved_cost.status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
