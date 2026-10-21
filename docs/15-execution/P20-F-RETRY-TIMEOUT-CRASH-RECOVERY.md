# P20-F — Retry / Timeout / Crash Recovery

Task: `FIN-P20-WF-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WF-001-01`  
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
- P20-G..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.
