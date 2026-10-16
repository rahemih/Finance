from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant.backtesting.walk_forward import (
    CandidateSelection,
    OutOfSampleResultRef,
    WalkForwardFold,
    certify_walk_forward,
)


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()

    folds=(
        WalkForwardFold("f1",100,200,200,250,260,310),
        WalkForwardFold("f2",320,420,420,470,480,530),
    )
    selections=(
        CandidateSelection("s1","f1","c1",250,"a"*64,"b"*64),
        CandidateSelection("s2","f2","c2",470,"c"*64,"d"*64),
    )
    results=(
        OutOfSampleResultRef("r1","f1","e"*64,"f"*64,260,310),
        OutOfSampleResultRef("r2","f2","1"*64,"2"*64,480,530),
    )
    cert=certify_walk_forward(
        folds=folds,
        selections=selections,
        results=results,
    )
    payload={
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P17D_WALK_FORWARD_EVIDENCE",
        "task_id":"FIN-P17-WD-001",
        "fixture_only":True,
        "certificate_id":cert.certificate_id,
        "status":cert.status,
        "fold_ids":list(cert.fold_ids),
        "selection_ids":list(cert.selection_ids),
        "result_ref_ids":list(cert.result_ref_ids),
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
    print(f"P17D_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
