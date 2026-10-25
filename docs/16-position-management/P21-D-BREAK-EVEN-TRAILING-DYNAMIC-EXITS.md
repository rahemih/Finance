# P21-D — Break-even / Trailing / Dynamic Exits

Task: `FIN-P21-WD-001`  
Phase: P21 — Position Management  
State: IN_PROGRESS  
Lock: `LOCK-FIN-P21-WD-001-01` / ACTIVE  
Dependency: P21-A through P21-C CANONICAL_COMPLETE / RELEASED

## Objective

Create deterministic reference-only protective-stop ratchet plans for break-even, trailing and dynamic-exit adjustments. P21-D validates caller-supplied reference price and requested stop; it does not query a venue, choose a universal trailing distance, or mutate orders/state.

## Exact binding

Every request binds to the exact current P21-A `position_record_id` and the current P21-B protection plan for that same record. Stale position or protection lineage fails closed.

## Monotonic protection rule

A stop may only tighten risk:

- LONG: requested stop must be strictly greater than the current stop.
- SHORT: requested stop must be strictly less than the current stop.
- Equal/no-op adjustments are rejected.

The current P21-B take-profit is preserved exactly.

## Break-even rule

`BREAK_EVEN` requires the requested stop to equal the canonical average-entry floor exactly. The caller reference must already be on the favorable side of entry:
- LONG: reference > entry;
- SHORT: reference < entry.

## Trailing / dynamic rule

`TRAILING` and `DYNAMIC_EXIT` may tighten the stop through entry into profit-lock territory. No universal percentage, ATR multiple, distance, trigger, or cadence is encoded.

For every mode, the requested stop must remain strictly on the non-triggered side of the caller reference price. The reference must also remain strictly before the current P21-B take-profit trigger; otherwise the current protection lifecycle may already have triggered and P21-D fails closed.

## Authority boundary

P21-D performs no broker/exchange query, uses no credentials/network, submits or mutates no external order, performs no automatic OMS mutation, directly mutates no canonical P21-A state, and grants no Live execution authority.

P21-E..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.
