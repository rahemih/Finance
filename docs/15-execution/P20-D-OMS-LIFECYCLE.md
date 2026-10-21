# P20-D — OMS Lifecycle

Task: `FIN-P20-WD-001`  
Phase: P20 — Execution & Order Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P20-WD-001-01`  
Dependency: P20-A..P20-C CANONICAL_COMPLETE

## Objective

Implement the deterministic internal Order Management System lifecycle state machine without introducing any production venue, network, credential, retry, reconciliation or Live execution authority.

## Canonical lifecycle

States:
`CREATED → SUBMIT_PENDING → OPEN → PARTIALLY_FILLED / CANCEL_PENDING → terminal`.

Terminal states are `FILLED`, `CANCELED`, `REJECTED` and `EXPIRED`.

The lifecycle permits deterministic fill/cancel races while preserving cumulative filled quantity and remaining quantity. Every transition creates a content-addressed state record linked to the previous record.

## Ownership boundary

P20-D owns:
- state-transition legality;
- ordered lifecycle sequencing;
- event-time monotonicity;
- fill accounting and overfill prevention;
- terminal-state immutability;
- deterministic state-record lineage.

P20-D explicitly does **not** own:
- runtime idempotency / duplicate prevention — P20-E;
- retry / timeout / crash recovery — P20-F;
- reconciliation — P20-G;
- execution-quality metrics — P20-H;
- broker/exchange simulation and G11 — P20-I;
- position management — P21.

## Safety boundary

- credentials = NONE;
- network = DISABLED;
- external order submission = false;
- retry authority = false;
- reconciliation authority = false;
- Live execution authority = false;
- P20-E..P20-I = NOT_STARTED;
- G11_EXECUTION_VALIDATED = NOT_REACHED;
- P21 = NOT_STARTED;
- LIVE_TRADING/AUTO_TRADING = DISABLED.
