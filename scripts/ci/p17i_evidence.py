from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant.backtesting.quant_gate import BenchmarkCriterion, WorkstreamEvidence, certify_g9_quant_validated


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    ws=tuple(
        WorkstreamEvidence(f"P17-{letter}", f"{i:x}".rjust(64,"0"))
        for i,letter in enumerate("ABCDEFGH",start=1)
    )
    criteria=(
        BenchmarkCriterion("OOS_EDGE","fixture-oos",110,100,"GE","a"*64),
        BenchmarkCriterion("RISK","fixture-risk",80,100,"LE","b"*64),
        BenchmarkCriterion("ROBUSTNESS","fixture-robust",105,100,"GE","c"*64),
        BenchmarkCriterion("CAPACITY","fixture-capacity",120,100,"GE","d"*64),
        BenchmarkCriterion("EXECUTION_REALISM","fixture-execution",90,100,"LE","e"*64),
    )
    gate=certify_g9_quant_validated(
        workstream_evidence=ws,
        benchmark_criteria=criteria,
        strategy_registry_sha256="f"*64,
        model_registry_sha256="1"*64,
    )
    payload={
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P17I_G9_QUANT_GATE_EVIDENCE",
        "task_id":"FIN-P17-WI-001",
        "fixture_only":True,
        "gate_name":gate.gate_name,
        "state":gate.state,
        "gate_id":gate.gate_id,
        "workstream_coverage":[x.workstream for x in gate.workstream_evidence],
        "benchmark_categories":[x.category for x in gate.benchmark_criteria],
        "production_numeric_defaults":None,
        "automatic_p18_promotion":False,
        "profitability_guarantee":False,
        "execution_authority":False,
        "next_phase":"P18",
        "next_phase_state":"NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        "live_trading":"DISABLED",
        "auto_trading":"DISABLED",
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"P17I_EVIDENCE=PASS output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
