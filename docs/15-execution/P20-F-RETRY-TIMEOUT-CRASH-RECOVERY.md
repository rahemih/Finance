# P20-F — Retry / Timeout / Crash Recovery

Task: `FIN-P20-WF-001`  
Phase: P20 — Execution & Order Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Dependency: P20-A..P20-E CANONICAL_COMPLETE

## Objective

Provide deterministic retry planning, timeout classification and crash-recovery checkpointing without sending an order. P20-F preserves the exact P20-E idempotency lineage and fails closed whenever external dispatch outcome could be ambiguous.

## Fail-closed recovery classes

Retry may be planned only for:
- `PRE_DISPATCH_TIMEOUT`;
- `PRE_DISPATCH_FAILURE`;
- `PROCESS_CRASH_BEFORE_DISPATCH`.

These produce `RETRY_SAME_CLAIM` and preserve order, client-order, idempotency-key, claim and request identity.

The following never auto-retry:
- `DISPATCH_OUTCOME_UNKNOWN`;
- `PROCESS_CRASH_AFTER_DISPATCH`.

They produce `SAFE_HOLD_RECONCILIATION_REQUIRED` and explicitly defer truth resolution to P20-G.

Terminal `ACKNOWLEDGED`, `REJECTED` and `CANCEL_ACKNOWLEDGED` produce `NO_RETRY_TERMINAL`.

## Retry budget

The reference policy allows at most 3 logical attempts with deterministic backoff schedule `250 / 1000 / 4000 ms`. P20-F does not sleep or dispatch; the values are planning metadata only.

## Safety boundary

- credentials/account/KYC/funding = NONE;
- network mode = DISABLED;
- actual retry dispatch = false;
- external order submission = false;
- reconciliation authority = false;
- Live execution authority = false;
- P20-G = READY_NOT_STARTED;
- P20-H..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #421 = MERGED;
- implementation head = `0f7943f3abe2a0b14c8ee0aebea2a34bcbc0ca11`;
- implementation Governance = `39572472231` / SUCCESS;
- implementation artifact = `12332592731` / `sha256:10cbe9b854ece02f8f6a4b3963023a88a41140b195cd0e5f3f710dcf41e4e63e`;
- implementation merge SHA = `6e9b232ba53ebff9cfe0bbb1b2c4c3f112b0ce9c`;
- post-merge Governance = `39572746127` / SUCCESS;
- post-merge artifact = `12331619799` / `sha256:17bb7e19f0e7af012e5dafcbbefa8dbd92e3a0f247de3bfb556b464520c20067`;
- post-merge Branch Hygiene = `39572746125` / SUCCESS;
- lock = RELEASED;
- P20-G = READY_NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED.

P20-F canonical completion grants no network, external-order, reconciliation or Live execution authority.
