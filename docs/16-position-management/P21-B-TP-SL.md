# P21-B — TP / SL

Task: `FIN-P21-WB-001`  
Phase: P21 — Position Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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


## Canonical closure evidence

- implementation PR #435 = MERGED;
- implementation head = `8debfc8b740e6d1e26212db204f3b7ec04096bd3`;
- implementation Governance = `40103796390` / SUCCESS;
- implementation artifact = `12563568953` / `sha256:95571ca5ee32d677a066f2fabac2aa481e52d201d9bc2942402a4b839e94a0e7`;
- deterministic evidence SHA256 = `3f7b1c74651f53cc7efc0d9ad1b74674c5dc4da703d283298fd153f58a6f55f3`;
- implementation merge SHA = `c82b943d0be730a4a270d006ea8164218b52122a`;
- post-merge Governance = `40103969571` / SUCCESS;
- post-merge artifact = `12564002192` / `sha256:0ba7d000846ec01f151e8d761dec31832915953c2240be21283725c3260bc552`;
- post-merge Branch Hygiene = `40103969496` / SUCCESS;
- lock = RELEASED.

## Next workstream boundary

P21-C — Partial Close = READY_NOT_STARTED.  
P21-D..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

P21-B completion certifies deterministic reference TP/SL protection-plan validation only. It does not choose strategy-specific profit/loss distances, submit broker orders, validate Live execution, or authorize production trading.
