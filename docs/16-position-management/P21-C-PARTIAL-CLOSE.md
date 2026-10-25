# P21-C — Partial Close

Task: `FIN-P21-WC-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WC-001-01` / ACTIVE  
Dependency: P21-A and P21-B CANONICAL_COMPLETE / RELEASED

## Objective

Create deterministic reference-only partial-close plans for an exact canonical P21-A position state. P21-C validates a caller-supplied reduction quantity and reason; it does not choose strategy-specific exit percentages and does not place or mutate orders.

## Exact binding

Every request binds to the exact `position_record_id`, `position_id`, a caller-supplied strictly partial reduction quantity, governed reason code, exit-decision lineage, and the current P21-B protection plan for that same canonical position record. Stale position or protection lineage fails closed.

## Quantity rule

`0 < close_quantity_scaled < open_quantity_scaled`

Zero, full-close and over-close quantities are invalid. A positive remainder is mandatory. No universal 25%, 50% or other staged-exit percentage is hard-coded.

## Protected remainder

A successful P20 reduction fill creates a new P21-A canonical record. The prior P21-B protection plan is therefore stale by design. Every P21-C plan emits `P21B_REPLAN_REQUIRED_FOR_NEW_POSITION_RECORD`; the remainder must be rebound to P21-B protection using the new canonical record.

## Reason taxonomy

Allowed caller-supplied reasons: `PARTIAL_PROFIT`, `DE_RISK`, `HEDGE_REDUCTION`, `STAGED_EXIT`. The reason is audit lineage only and grants no execution authority.

## Authority boundary

No broker/exchange query, credentials, network I/O, external order submission/mutation, automatic OMS mutation, direct P21-A mutation or Live execution authority is introduced.

P21-D..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
