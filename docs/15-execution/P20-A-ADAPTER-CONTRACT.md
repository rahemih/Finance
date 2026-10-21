# P20-A — Execution Adapter Contract

Task: `FIN-P20-WA-001`  
Phase: P20 — Execution & Order Management  
State: CANONICAL_COMPLETE  
Owner P20 authorization: GRANTED / CONSUMED  
Lock: RELEASED

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
- P20-B = READY_NOT_STARTED;\n- P20-C..P20-I = NOT_STARTED;
- P21 = NOT_STARTED;
- LIVE_TRADING = DISABLED;
- AUTO_TRADING = DISABLED.

Passing P20-A does not certify broker behavior, execution quality, reconciliation, production readiness or profitability.


## Canonical closure evidence

- implementation PR #411 = MERGED;
- implementation head = `a09b73bdb70667498e1ddd4bbd7e5215b3b809ec`;
- implementation Governance = `39557776142` / SUCCESS;
- implementation artifact = `12326560719` / `sha256:7098b51e93e29ec5cb5110b948cc1d89399f3eef10af8e9bd31059162dedc1c2`;
- implementation merge SHA = `fcf7444759a95dc42a59a63affc866c9eaf6dcf3`;
- post-merge Governance = `39558129871` / SUCCESS;
- post-merge artifact = `12326945603` / `sha256:108f3fb1e46329c97595c8f367d64bb21ebda12a1541c468bd1a48849d2d3d83`;
- post-merge Branch Hygiene = `39558129923` / SUCCESS;
- lock = RELEASED;
- P20-B = READY_NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED.

P20-A canonical completion grants no Live execution authority.
