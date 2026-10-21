# P20-A — Execution Adapter Contract

Task: `FIN-P20-WA-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Owner P20 authorization: GRANTED / CONSUMED  
Lock: `LOCK-FIN-P20-WA-001-01`

## Objective

Define the deterministic, vendor-neutral execution-adapter boundary shared by future Crypto and Forex execution work without provisioning credentials, opening accounts, funding, networking to a venue or submitting an external order.

## Canonical contract surface

P20-A defines:
- market taxonomy: `CRYPTO`, `FOREX`;
- contract environments: `SIMULATED`, `SANDBOX` only;
- sides: `BUY`, `SELL`;
- order types: `MARKET`, `LIMIT`, `STOP`;
- time-in-force: `GTC`, `IOC`, `FOK`, `DAY`;
- deterministic adapter descriptors and contract identities;
- normalized order-intent envelopes;
- deterministic adapter-to-intent binding;
- deterministic registry snapshots;
- mandatory client-order identity, idempotency-key and reconciliation capability declarations.

P20-B and P20-C will implement market-specific execution behavior against this contract. P20-A itself contains no venue client.

## Fail-closed invariants

The contract rejects:
- any `LIVE` environment;
- duplicate adapter names;
- duplicate venue/market/environment bindings;
- market mismatch;
- unsupported order type or time-in-force;
- missing mandatory idempotency or reconciliation capabilities;
- malformed MARKET/LIMIT/STOP price geometry.

## Safety boundary

- credential mode = `NONE`;
- network mode = `DISABLED`;
- routing mode = `CONTRACT_ONLY`;
- external order submission = false;
- Live execution authority = false;
- automatic Live promotion = false;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P20-B..P20-I = NOT_STARTED;
- P21 = NOT_STARTED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

Passing P20-A does not certify broker behavior, execution quality, reconciliation, production readiness or profitability.
