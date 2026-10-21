# P20-G — Execution Reconciliation

Task: `FIN-P20-WG-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WG-001-01`  
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
- P20-H..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.
