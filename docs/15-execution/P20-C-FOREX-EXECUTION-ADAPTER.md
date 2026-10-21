# P20-C — Forex Execution Adapter

Task: `FIN-P20-WC-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WC-001-01`  
Dependency: P20-A..P20-B CANONICAL_COMPLETE

## Objective

Implement the deterministic Forex execution-adapter boundary against P20-A without selecting a production broker or creating any network, credential, account, funding or real-order authority.

## Scope

P20-C owns:
- Forex-only canonical intent binding;
- deterministic quantity-step/minimum validation;
- deterministic price-tick and pip geometry validation;
- deterministic submit and cancel envelopes;
- reference/sandbox ACK, REJECT and CANCEL_ACK normalization;
- exact lineage to P20-A adapter contract and binding identities.

It does not own OMS state, runtime retries, reconciliation, execution-quality metrics or broker certification.

## Broker boundary

Production Forex broker = NOT_SELECTED. Owner/entity jurisdiction is not inferred. No account opening, KYC, credentials, funding, network call or real order is performed by P20-C.

The `forex-reference-sandbox` descriptor is a deterministic test boundary only and is not a hidden production-broker decision.

## Safety boundary

- broker selection = NOT_SELECTED;
- credential mode = NONE;
- network mode = DISABLED;
- external order submission = false;
- Live execution authority = false;
- OMS state authority = false;
- retry authority = false;
- reconciliation authority = false;
- P20-D..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.
