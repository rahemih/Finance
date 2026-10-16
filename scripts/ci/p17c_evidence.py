from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.historical_data.replay_snapshot import (
    ReplayDatasetRef,
    ReplayFeatureRef,
    ReplaySnapshot,
    ReplaySnapshotPolicy,
)
from quant.backtesting.information_hygiene import (
    DecisionInformationAudit,
    UniverseMembershipChange,
    certify_information_hygiene,
)


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()

    policy=ReplaySnapshotPolicy(
        allowed_clock_modes=frozenset(
            {"EVENT_TIME","RECEIVE_TIME","CONTROLLED_SIMULATION_CLOCK"}
        ),
        max_dataset_refs=4,
        max_feature_refs=4,
        max_vintage_refs=4,
        max_snapshot_bytes=100_000,
        production_replay_storage_vendor="UNSELECTED",
    )
    snapshot=ReplaySnapshot.build(
        replay_start_ns=100,
        replay_end_ns=2_000,
        snapshot_cutoff_ns=1_900,
        clock_mode="EVENT_TIME",
        scope_ids=("BTC-USD",),
        dataset_refs=(
            ReplayDatasetRef(
                "market","1"*64,"1.0",100,2_000,"2"*64,"INTERNAL"
            ),
        ),
        feature_refs=(
            ReplayFeatureRef(
                "3"*64,"4"*64,"BTC-USD",700,800,"5"*64
            ),
        ),
        vintage_refs=(),
        quality_rule_versions=("q1",),
        config_sha256="6"*64,
        code_artifact_sha256="7"*64,
        rights_class="INTERNAL",
        policy=policy,
    )
    decision=DecisionInformationAudit.build(
        decision_id="decision-ci",
        asset_id="BTC-USD",
        decision_time_ns=1_000,
        feature_materialization_ids=("4"*64,),
        dataset_versions=("1"*64,),
    )
    membership=UniverseMembershipChange(
        "membership-ci","BTC-USD",100,100,True,"8"*64
    )
    cert=certify_information_hygiene(
        snapshot=snapshot,
        decisions=(decision,),
        universe_changes=(membership,),
    )
    payload={
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P17C_INFORMATION_HYGIENE_EVIDENCE",
        "task_id":"FIN-P17-WC-001",
        "fixture_only":True,
        "certificate_id":cert.certificate_id,
        "snapshot_id":cert.snapshot_id,
        "status":cert.status,
        "audited_decision_ids":list(cert.audited_decision_ids),
        "universe_change_ids":list(cert.universe_change_ids),
        "g9_authority":False,
        "profitability_claim_authority":False,
        "execution_authority":False,
        "order_routing_authority":False,
        "live_trading":"DISABLED",
        "auto_trading":"DISABLED",
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(payload,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    print(f"P17C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
