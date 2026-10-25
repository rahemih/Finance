# P21-C — Partial Close

Task: `FIN-P21-WC-001`  
Phase: P21 — Position Management  
State: CANONICAL_COMPLETE  
Lock: RELEASED  
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

## Canonical closure evidence

- implementation PR #437 = MERGED;
- implementation head = `9195a80864f1df1ffb4a7dacfbd3fd40c0cc567b`;
- implementation Governance = `40193480084` / SUCCESS;
- implementation artifact = `12598976483` / `sha256:74bd1b7398bec33836ee06e3bfdd88adf8440311dbb48c035f3e42ec046ed297`;
- deterministic P21-C evidence SHA256 = `20ea9c8a3138cba6f28f93e32b274ae0f966fcc0ff6886641aa6c7ede279343f`;
- implementation merge SHA = `bbe748ab65d1071ba2518f8890ea2915fc7416ce`;
- post-merge Governance = `40193615383` / SUCCESS;
- post-merge artifact = `12599445840` / `sha256:35b2add4619701b4b1432f2dd3cf098c465aca4e3121ab9f92af0ed0f1e9f8cd`;
- post-merge Branch Hygiene = `40193615387` / SUCCESS;
- lock = RELEASED.

## Next workstream boundary

P21-D — Break-even / Trailing / Dynamic Exits = READY_NOT_STARTED.  
P21-E..P21-H = NOT_STARTED.  
P22 = NOT_STARTED.  
LIVE_TRADING = DISABLED.  
AUTO_TRADING = DISABLED.

P21-C completion certifies deterministic reference partial-close planning only. It does not select strategy-specific exit size/timing, execute reductions, mutate canonical state, or authorize Live trading.
