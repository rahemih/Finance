# P20-E — Idempotency / Duplicate Prevention

Task: `FIN-P20-WE-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WE-001-01`  
Dependency: P20-A..P20-D CANONICAL_COMPLETE

## Objective

Provide deterministic, fail-closed admission for submit/cancel execution requests so exact replays are recognized without creating a second canonical claim and conflicting duplicates are rejected before later retry/reconciliation work.

## Canonical behavior

A request is bound to:
- market;
- operation;
- order id;
- client order id;
- idempotency key;
- canonical request fingerprint.

The first valid request returns `ADMIT_NEW`. Repeating the exact same request returns `REPLAY_EXISTING` and references the original claim.

The ledger rejects:
- reuse of an idempotency key with different lineage;
- duplicate client-order identity under another key within the same market;
- duplicate request fingerprint under another key within market/operation scope;
- duplicate operation/order claim under another key.

Submit and cancel are separate operations, so each may have its own canonical claim for the same order.

## Ownership boundary

- retry / timeout / crash recovery = P20-F;
- reconciliation = P20-G;
- execution-quality metrics = P20-H;
- broker/exchange simulation + G11 = P20-I;
- position management = P21.

P20-E does not send, retry or reconcile an order.

## Safety boundary

- credentials = NONE;
- network = DISABLED;
- external order submission = false;
- retry authority = false;
- reconciliation authority = false;
- Live execution authority = false;
- P20-F..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.
