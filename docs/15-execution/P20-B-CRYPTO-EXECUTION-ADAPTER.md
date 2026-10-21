# P20-B — Crypto Execution Adapter

Task: `FIN-P20-WB-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WB-001-01`  
Dependency: P20-A CANONICAL_COMPLETE

## Objective

Implement the deterministic Crypto execution-adapter boundary against P20-A without choosing a production exchange or creating any network/credential/order authority.

## Scope

P20-B owns:
- Crypto-only canonical intent binding;
- deterministic symbol/precision/filter validation;
- deterministic submit and cancel envelopes;
- reference/sandbox ACK, REJECT and CANCEL_ACK normalization;
- exact lineage to P20-A adapter contract and binding identities.

It does not own OMS state, retries, reconciliation, latency/slippage measurement or broker certification.

## Venue boundary

P01-C remains authoritative:
- production Crypto venue = NOT_SELECTED;
- Owner/entity jurisdiction = not inferred;
- account opening = none;
- credentials = none;
- funding = none;
- real orders = none.

Therefore P20-B uses a `crypto-reference-sandbox` descriptor only. It is not a hidden production-venue decision.

## Safety boundary

- venue selection = NOT_SELECTED;
- credential mode = NONE;
- network mode = DISABLED;
- external order submission = false;
- Live execution authority = false;
- OMS state authority = false;
- retry authority = false;
- reconciliation authority = false;
- P20-C..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.
