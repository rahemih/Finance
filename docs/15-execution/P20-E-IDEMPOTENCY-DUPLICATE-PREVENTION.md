# P20-E — Idempotency / Duplicate Prevention

Task: `FIN-P20-WE-001`  
Phase: P20 — Execution & Order Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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
- P20-F = READY_NOT_STARTED;
- P20-G..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #419 = MERGED;
- implementation head = `45341c348a61cc7d185c04b3e9f43511ab6e813e`;
- implementation Governance = `39568312563` / SUCCESS;
- implementation artifact = `12329894032` / `sha256:8ddecc9e8d4e0c13fb657dd44bb0a03cc2cfce67f7086b8024d210c9f0cf78be`;
- implementation merge SHA = `4094aa8e6de1557158451f13f74a95f009314d70`;
- post-merge Governance = `39570899056` / SUCCESS;
- post-merge artifact = `12331309376` / `sha256:3fe360a4b692c5def5d3668cf9b6f6700e8f8bb25083c4424a134765bf7cd059`;
- post-merge Branch Hygiene = `39570899369` / SUCCESS;
- lock = RELEASED;
- P20-F = READY_NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED.

P20-E canonical completion grants no retry, reconciliation, network, external-order or Live execution authority.
