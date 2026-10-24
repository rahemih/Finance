# P21-B — TP / SL

Task: `FIN-P21-WB-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WB-001-01`  
Dependency: P21-A CANONICAL_COMPLETE / RELEASED

## Objective

Create deterministic reference-only take-profit / stop-loss protection plans bound to an exact canonical P21-A position record.

P21-B validates caller-supplied protective levels. It does not choose strategy-specific profit/loss distances and does not submit orders.

## Binding

Every protection request binds to:
- exact `position_record_id`;
- `position_id`;
- LONG/SHORT side;
- canonical average-entry floor;
- signal-decision SHA256 lineage;
- risk-validation SHA256 lineage.

If the underlying canonical position changes, the old request becomes stale and fails closed.

## Geometry

For LONG:
- `SL < entry < TP`.

For SHORT:
- `TP < entry < SL`.

Equal, crossed, inverted, zero or negative levels are invalid.

## Eligible position state

Only:
- OPEN;
- PARTIALLY_CLOSED.

CLOSED or zero-exposure positions are rejected.

## Authority boundary

P21-B:
- performs no broker/exchange query;
- uses no credentials;
- performs no network I/O;
- submits/cancels/modifies no external order;
- performs no automatic OMS mutation;
- grants no Live execution authority.

The output is a content-addressed reference protection plan only.

P21-C..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
