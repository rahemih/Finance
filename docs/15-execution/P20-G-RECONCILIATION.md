# P20-G — Execution Reconciliation

Task: `FIN-P20-WG-001`  
Phase: P20 — Execution & Order Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
Dependency: P20-A..P20-F CANONICAL_COMPLETE

## Objective

Reconcile canonical internal execution lineage against explicit reference/sandbox venue observations without querying or mutating a real broker/exchange.

Every reconciliation is bound to:
- P20-D OMS record identity;
- P20-E idempotency claim identity;
- P20-F recovery checkpoint identity when a recovery hold exists.

## Verdicts

- `MATCHED`: reference observation agrees with canonical internal state/fills.
- `VENUE_AHEAD`: reference observation contains a clear later state; a suggested OMS event may be reported but never auto-applied.
- `INTERNAL_AHEAD`: internal state cannot be confirmed by the reference observation.
- `FILL_MISMATCH`: cumulative fill quantities differ.
- `STATE_CONFLICT`: states conflict without a safe deterministic one-event interpretation.
- `UNRESOLVED_AMBIGUITY`: P20-F post-dispatch hold cannot be resolved by the observation.

## Safety boundary

- source mode = explicit reference/sandbox observation only;
- real venue query = false;
- automatic OMS mutation = false;
- external order mutation = false;
- credentials/account/KYC/funding = NONE;
- network mode = DISABLED;
- Live execution authority = false;
- P20-H = READY_NOT_STARTED;
- P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.


## Canonical closure evidence

- implementation PR #423 = MERGED;
- implementation head = `e1267f53c6341329567b164504916000b8b7c5e8`;
- implementation Governance = `39574349533` / SUCCESS;
- implementation artifact = `12333651407` / `sha256:ca30e11bfc586bc8b465ba9b87a55d510a91c0ef719a9a84e73b9c7d600293d9`;
- implementation merge SHA = `031fe9b95b39a06cdc1f3641cd012d3c10d47cc6`;
- post-merge Governance = `39574656815` / SUCCESS;
- post-merge artifact = `12334086654` / `sha256:aa5867c9efd3cb1e6c6c297b826f880a831a28570b6aa115f3720cb0932350b3`;
- post-merge Branch Hygiene = `39574656745` / SUCCESS;
- lock = RELEASED;
- P20-H = READY_NOT_STARTED;
- P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED.

P20-G canonical completion grants no real-venue query, OMS mutation, external-order mutation, execution-quality certification or Live authority.
