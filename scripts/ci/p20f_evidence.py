from __future__ import annotations
import argparse
import json
from pathlib import Path
from packages.execution.retry_recovery import RecoveryCheckpoint, RecoverySignal, RetryRecoveryPlanner, RetryRecoveryPolicy

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"config/execution/retry-recovery-policy.json"

def build() -> dict[str, object]:
    policy=RetryRecoveryPolicy.from_path(POLICY)
    planner=RetryRecoveryPlanner(policy)
    base=dict(market="CRYPTO",operation="ORDER_SUBMIT",order_id="p20f-order-001",client_order_id="p20f-client-001",
              idempotency_key="p20f-idem-001",idempotency_claim_id="a"*64,request_id="b"*64,oms_record_id="c"*64,
              attempt=1,observed_at_ns=100)
    pre=RecoveryCheckpoint(**base,stage="PRE_DISPATCH")
    planner.record(pre)
    retry=planner.decide(pre.order_id,RecoverySignal("PRE_DISPATCH_TIMEOUT",101))

    hold_planner=RetryRecoveryPlanner(policy)
    post=RecoveryCheckpoint(**base,stage="POST_DISPATCH")
    hold_planner.record(post)
    hold=hold_planner.decide(post.order_id,RecoverySignal("DISPATCH_OUTCOME_UNKNOWN",101))

    terminal_planner=RetryRecoveryPlanner(policy)
    terminal=RecoveryCheckpoint(**base,stage="TERMINAL")
    terminal_planner.record(terminal)
    no_retry=terminal_planner.decide(terminal.order_id,RecoverySignal("ACKNOWLEDGED",101))

    return {
      "schema_version":"1.0","kind":"NEXUS_QUANT_P20F_RETRY_RECOVERY_EVIDENCE","task_id":"FIN-P20-WF-001",
      "state":"IN_PROGRESS_REFERENCE_VALIDATED","policy_id":policy.policy_id,
      "retry_decision":retry.payload()|{"decision_id":retry.decision_id},
      "safe_hold_decision":hold.payload()|{"decision_id":hold.decision_id},
      "terminal_decision":no_retry.payload()|{"decision_id":no_retry.decision_id},
      "snapshot":planner.snapshot(),
      "authority":{"network_mode":"DISABLED","actual_retry_dispatch":False,"external_order_submission":False,
                   "reconciliation_authority":False,"live_execution_authority":False,
                   "live_trading":"DISABLED","auto_trading":"DISABLED","g11_execution_validated":False,"p21_started":False}
    }

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True); args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(build(),indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"P20F_EVIDENCE=PASS output={args.output}"); return 0
if __name__=="__main__": raise SystemExit(main())
