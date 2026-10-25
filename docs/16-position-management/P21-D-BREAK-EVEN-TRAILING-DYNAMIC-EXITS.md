# P21-D — Break-even / Trailing / Dynamic Exits

Task: `FIN-P21-WD-001`  
Phase: P21 — Position Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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

## Canonical closure evidence

- implementation PR #439 = MERGED;
- implementation head = `6952710955b22342385a41953d6ae7b51952d24f`;
- implementation Governance = `40194460051` / SUCCESS;
- implementation artifact = `12599507223` / `sha256:e23e2af534a615e19c6010ce7a939650d81b2f6f2a958b2174a53b0a7deb22e0`;
- deterministic P21-D evidence SHA256 = `a74b8a06083f8a1a0b32d463c154058ad6e1aee473541cfab124eb60cf25d5a1`;
- implementation merge SHA = `30082d9efd6cd0cd93583ef5eb9201210820a6b9`;
- post-merge Governance = `40194645962` / SUCCESS;
- post-merge artifact = `12598849254` / `sha256:41d8a222b2cb6110502e3bca4325e7ac160999006b92189c12003ed5e580a823`;
- post-merge Branch Hygiene = `40194645954` / SUCCESS;
- lock = RELEASED.

## Next workstream boundary

P21-E — Emergency Exit = READY_NOT_STARTED.  
P21-F..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

P21-D completion certifies deterministic reference-only monotonic protective-stop ratchets. It does not choose trailing distances/timing, mutate broker or OMS orders, query venues, or authorize Live trading.
